"""Core views for QR Attendance System (cleaned)."""
import csv
import json
import os
import zipfile
from datetime import datetime
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib import messages
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from .forms import SeminarForm, UploadFileForm
from .models import Attendance, Seminar, Student


def generate_qr_code(data, student_id=None, style='basic'):
    try:
        # Configure QR code based on style
        if style == 'styled':
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=12,
                border=4,
            )
        else:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
        
        qr.add_data(data)
        qr.make(fit=True)
        
        # Generate image based on style
        if style == 'colored':
            img = qr.make_image(fill_color="navy", back_color="lightblue")
        elif style == 'styled':
            img = qr.make_image(fill_color="darkgreen", back_color="lightgreen")
        else:  # basic
            img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Add student info for styled QR codes
        if student_id and style in ['styled', 'colored']:
            new_height = img.height + 80
            new_img = Image.new('RGB', (img.width, new_height), 'white')
            new_img.paste(img, (0, 0))
            
            # Add text
            draw = ImageDraw.Draw(new_img)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except (OSError, IOError):
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
            
            if font:
                text = f"Student ID: {student_id}"
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                except AttributeError:
                    # Fallback for older Pillow versions
                    text_width = len(text) * 10
                
                text_x = (img.width - text_width) // 2
                text_y = img.height + 25
                
                draw.text((text_x, text_y), text, fill='black', font=font)
                img = new_img
        
        return img
    
    except Exception as e:
        # Fallback to basic QR code on any error
        print(f"QR generation error: {e}")
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(str(data))
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")


def home(request):
    """Home page with overview statistics"""
    try:
        active_seminars_qs = Seminar.objects.filter(status='active')
        context = {
            'total_students': Student.objects.count(),
            'total_seminars': Seminar.objects.count(),
            'total_attendance': Attendance.objects.count(),
            'active_seminars': active_seminars_qs,            # queryset for iteration
            'active_seminars_count': active_seminars_qs.count(),  # separate count for stats card
            'recent_seminars': Seminar.objects.order_by('-start_time')[:5],
        }
        return render(request, 'attendance/home.html', context)
    except Exception as e:
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return render(request, 'attendance/home.html', {'error': True})


def upload_students(request):
    """Upload students from CSV file with validation"""
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file = request.FILES['file']
                if not file.name.endswith('.csv'):
                    messages.error(request, 'Please upload a CSV file.')
                    return render(request, 'attendance/upload.html', {'form': form})
                
                decoded_file = file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)
                
                created_count = 0
                updated_count = 0
                error_count = 0
                
                for row in reader:
                    try:
                        # Validate required fields
                        student_id = row.get('student_id', '').strip()
                        name = row.get('name', '').strip()
                        email = row.get('email', '').strip()
                        phone = row.get('phone', '').strip()
                        course = row.get('course', '').strip()
                        
                        if not all([student_id, name, email, course]):
                            error_count += 1
                            continue
                        
                        # Validate SBU format
                        if not student_id.startswith('SBU') or len(student_id) != 9:
                            print(f"Invalid student ID format: {student_id}")
                            error_count += 1
                            continue
                        
                        # Create or update student
                        student, created = Student.objects.get_or_create(
                            student_id=student_id,
                            defaults={
                                'name': name,
                                'email': email,
                                'phone': phone,
                                'course': course
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            # Update existing student
                            student.name = name
                            student.email = email
                            student.phone = phone
                            student.course = course
                            student.save()
                            updated_count += 1
                    
                    except Exception as row_error:
                        print(f"Error processing row {row}: {row_error}")
                        error_count += 1
                
                # Success message with detailed summary
                message_parts = []
                if created_count > 0:
                    message_parts.append(f"✅ {created_count} new students created")
                if updated_count > 0:
                    message_parts.append(f"🔄 {updated_count} students updated")
                if error_count > 0:
                    message_parts.append(f"⚠️ {error_count} errors encountered")
                
                total_processed = created_count + updated_count
                success_message = f"📊 Upload completed! {total_processed} students processed successfully."
                if message_parts:
                    success_message += f" Details: {'; '.join(message_parts)}"
                
                messages.success(request, success_message)
                return redirect('students')
            
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
        else:
            messages.error(request, 'Invalid form submission.')
    else:
        form = UploadFileForm()
    
    return render(request, 'attendance/upload.html', {'form': form})


def students(request):
    """Display all students with search functionality"""
    try:
        search_query = request.GET.get('search', '').strip()
        students = Student.objects.all()
        
        if search_query:
            students = students.filter(
                models.Q(student_id__icontains=search_query) |
                models.Q(name__icontains=search_query) |
                models.Q(email__icontains=search_query) |
                models.Q(course__icontains=search_query)
            )
        
        students = students.order_by('student_id')
        
        context = {
            'students': students,
            'search_query': search_query,
            'total_count': Student.objects.count(),
            'filtered_count': students.count(),
        }
        return render(request, 'attendance/students.html', context)
    
    except Exception as e:
        messages.error(request, f"Error loading students: {str(e)}")
        return render(request, 'attendance/students.html', {'error': True})


def seminars(request):
    """Manage seminars - list and create"""
    if request.method == 'POST':
        form = SeminarForm(request.POST)
        if form.is_valid():
            try:
                seminar = form.save()
                messages.success(request, f'Seminar "{seminar.title}" created successfully!')
                return redirect('seminars')
            except Exception as e:
                messages.error(request, f'Error creating seminar: {str(e)}')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = SeminarForm()
    
    try:
        seminars = Seminar.objects.all().order_by('-created_at')
        active_seminars = seminars.filter(status='active')
        
        context = {
            'seminars': seminars,
            'active_seminars': active_seminars,
            'form': form,
        }
        return render(request, 'attendance/seminars.html', context)
    
    except Exception as e:
        messages.error(request, f"Error loading seminars: {str(e)}")
        return render(request, 'attendance/seminars.html', {'form': form, 'error': True})


def update_seminar_status(request, seminar_id):
    """Update seminar status (activate/end)"""
    if request.method == 'POST':
        try:
            seminar = get_object_or_404(Seminar, id=seminar_id)
            new_status = request.POST.get('status')
            
            if new_status in ['active', 'inactive', 'ended']:
                old_status = seminar.status
                seminar.status = new_status
                seminar.save()
                
                status_messages = {
                    'active': f'Seminar "{seminar.title}" is now active and ready for attendance.',
                    'ended': f'Seminar "{seminar.title}" has been ended.',
                    'inactive': f'Seminar "{seminar.title}" has been deactivated.'
                }
                
                messages.success(request, status_messages.get(new_status, 'Seminar status updated.'))
            else:
                messages.error(request, 'Invalid status value.')
                
        except Exception as e:
            messages.error(request, f'Error updating seminar status: {str(e)}')
    
    return redirect('seminars')


def scan(request, seminar_id=None):
    """QR Code scanning view optimized for high-volume usage"""
    if seminar_id:
        try:
            # Optimize seminar query
            seminar = get_object_or_404(
                Seminar.objects.select_related(), 
                seminar_id=seminar_id
            )
            
            if seminar.status != 'active':
                messages.warning(request, f'⚠️ Seminar "{seminar.title}" is not active. Please activate it first.')
                return redirect('seminars')
            
        except Seminar.DoesNotExist:
            messages.error(request, '❌ Seminar not found.')
            return redirect('seminars')
    else:
        seminar = None
    
    if request.method == 'POST':
        try:
            # Handle manual student ID entry
            if 'manual_student_id' in request.POST:
                student_id = request.POST.get('manual_student_id', '').strip().upper()
                return process_attendance(request, student_id, seminar)
            
            # (Removed legacy image file QR decoding requiring external zbar library)
            
            # Handle QR code data from camera (most common case for high-volume scanning)
            elif 'qr_data' in request.POST:
                qr_data = request.POST.get('qr_data', '').strip()
                if not qr_data:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'error': 'Empty QR code data received.'})
                    messages.error(request, '❌ Empty QR code data received.')
                    return redirect('scan' if not seminar else f'/scan/{seminar.seminar_id}/')
                
                try:
                    # Try to parse as JSON first
                    data = json.loads(qr_data)
                    student_id = data.get('StudentID', '').strip().upper()
                    if student_id:
                        return process_attendance(request, student_id, seminar)
                    else:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({'error': 'Invalid QR code format: No StudentID found in JSON data.'})
                        messages.error(request, '❌ Invalid QR code format: No StudentID found in JSON data.')
                except json.JSONDecodeError:
                    # If not JSON, treat as plain student ID
                    student_id = qr_data.strip().upper()
                    if student_id:
                        return process_attendance(request, student_id, seminar)
                    else:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({'error': 'Invalid student ID format.'})
                        messages.error(request, '❌ Invalid student ID format.')
        
        except Exception as e:
            messages.error(request, f'❌ Error processing attendance: {str(e)}')
    
    try:
        # Optimize context queries for better performance with large datasets
        context = {
            'seminar': seminar,
        }
        
        # Only load other seminars if no specific seminar is selected
        if not seminar:
            context['seminars'] = Seminar.objects.filter(
                status='active'
            ).order_by('start_time')[:10]  # Limit to 10 for performance
        
        return render(request, 'attendance/scan.html', context)
    
    except Exception as e:
        messages.error(request, f"❌ Error loading scan page: {str(e)}")
        return render(request, 'attendance/scan.html', {'error': True})


def process_attendance(request, student_id, seminar=None):
    """Process attendance marking with validation and detailed feedback"""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        # Optimize database query with select_related for better performance
        try:
            student = Student.objects.select_related().get(student_id=student_id)
        except Student.DoesNotExist:
            error_msg = f'❌ Student with ID "{student_id}" not found in database.'
            if is_ajax:
                return JsonResponse({'error': error_msg})
            messages.error(request, error_msg)
            return redirect('scan' if not seminar else f'/scan/{seminar.seminar_id}/')
        
        # Use provided seminar or find active seminar
        if not seminar:
            active_seminars = Seminar.objects.filter(status='active')
            if not active_seminars.exists():
                error_msg = '❌ No active seminars found.'
                if is_ajax:
                    return JsonResponse({'error': error_msg})
                messages.error(request, error_msg)
                return redirect('seminars')
            elif active_seminars.count() > 1:
                warning_msg = '⚠️ Multiple active seminars found. Please select a specific seminar.'
                if is_ajax:
                    return JsonResponse({'warning': warning_msg})
                messages.warning(request, warning_msg)
                return redirect('scan')
            else:
                seminar = active_seminars.first()
        
        # Check if already marked (optimized query)
        existing_attendance = Attendance.objects.filter(
            student=student, 
            seminar=seminar
        ).select_related('student', 'seminar').first()
        
        if existing_attendance:
            # Show detailed information about existing attendance
            timestamp = existing_attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            warning_msg = (
                f'⚠️ Attendance already marked!\n'
                f'📋 Student: {student.name} ({student.student_id})\n'
                f'📚 Course: {student.course}\n'
                f'🎯 Seminar: {seminar.title}\n'
                f'⏰ Previously marked at: {timestamp}'
            )
            if is_ajax:
                return JsonResponse({
                    'warning': warning_msg,
                    'student_data': {
                        'name': student.name,
                        'student_id': student.student_id,
                        'course': student.course,
                        'timestamp': timestamp
                    }
                })
            messages.warning(request, warning_msg)
        else:
            # Mark attendance with timestamp
            attendance_record = Attendance.objects.create(
                student=student, 
                seminar=seminar
            )
            
            # Get current attendance count for this seminar (for progress tracking)
            current_count = Attendance.objects.filter(seminar=seminar).count()
            
            # Show detailed success message with QR data
            success_msg = (
                f'✅ Attendance marked successfully!\n'
                f'📋 Student: {student.name} ({student.student_id})\n'
                f'📧 Email: {student.email}\n'
                f'📱 Phone: {student.phone or "N/A"}\n'
                f'📚 Course: {student.course}\n'
                f'🎯 Seminar: {seminar.title} ({seminar.seminar_id})\n'
                f'⏰ Timestamp: {attendance_record.timestamp.strftime("%Y-%m-%d %H:%M:%S")}\n'
                f'📊 Total attendance: {current_count} students'
            )
            if is_ajax:
                return JsonResponse({
                    'success': success_msg,
                    'student_data': {
                        'name': student.name,
                        'student_id': student.student_id,
                        'email': student.email,
                        'phone': student.phone or "N/A",
                        'course': student.course,
                        'timestamp': attendance_record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        'total_count': current_count
                    }
                })
            messages.success(request, success_msg)
        
        if is_ajax:
            return JsonResponse({'redirect': 'scan' if not seminar else f'/scan/{seminar.seminar_id}/'})
        return redirect('scan' if not seminar else f'/scan/{seminar.seminar_id}/')
    
    except Exception as e:
        error_msg = f'❌ Error marking attendance: {str(e)}'
        if is_ajax:
            return JsonResponse({'error': error_msg})
        messages.error(request, error_msg)
        return redirect('scan')


def export_attendance(request, seminar_id=None):
    """Export attendance data to CSV - Seminar specific export"""
    try:
        if not seminar_id:
            messages.error(request, 'Seminar ID is required for attendance export.')
            return redirect('seminars')
            
        seminar = get_object_or_404(Seminar, seminar_id=seminar_id)
        attendance_records = Attendance.objects.filter(seminar=seminar).select_related('student', 'seminar')
        
        if not attendance_records.exists():
            messages.warning(request, f'No attendance records found for seminar "{seminar.title}".')
            return redirect('seminars')
        
        # Create filename with seminar details
        safe_title = "".join(c for c in seminar.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"attendance_{seminar.seminar_id}_{safe_title}_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        # Header with all student details contained in QR + phone + course
        writer.writerow([
            'Serial No.', 'Student ID', 'Student Name', 'Email', 'Phone', 'Course', 'Attendance Date', 'Attendance Time'
        ])

        # Data rows with full details
        for idx, record in enumerate(attendance_records.order_by('timestamp'), 1):
            ts = record.timestamp
            writer.writerow([
                idx,
                record.student.student_id,
                record.student.name,
                record.student.email,
                record.student.phone or 'N/A',
                record.student.course,
                ts.strftime('%Y-%m-%d'),
                ts.strftime('%H:%M:%S'),
            ])
        
        messages.success(request, f'Attendance exported successfully for "{seminar.title}" ({attendance_records.count()} records)')
        return response
    
    except Exception as e:
        messages.error(request, f'Error exporting attendance: {str(e)}')
        return redirect('seminars')


def qr_generator(request):
    """QR code generator page"""
    try:
        students = Student.objects.all().order_by('student_id')
        context = {
            'students': students,
            'total_students': students.count(),
        }
        return render(request, 'attendance/qr_generator.html', context)
    
    except Exception as e:
        messages.error(request, f"Error loading QR generator: {str(e)}")
        return render(request, 'attendance/qr_generator.html', {'error': True})


def generate_single_qr(request, student_id):
    """Generate single QR code for a student"""
    try:
        student = get_object_or_404(Student, student_id=student_id)
        style = request.GET.get('style', 'basic')
        
        # Create QR data
        data = json.dumps({
            "StudentID": student.student_id,
            "Name": student.name,
            "Email": student.email,
            "Course": student.course
        })
        
        # Generate QR code
        img = generate_qr_code(data, student.student_id, style=style)
        
        # Return as HTTP response
        response = HttpResponse(content_type="image/png")
        img.save(response, "PNG")
        response['Content-Disposition'] = f'attachment; filename="{student.student_id}_qr.png"'
        return response
    
    except Exception as e:
        messages.error(request, f'Error generating QR code: {str(e)}')
        return redirect('qr_generator')


def regenerate_qr_codes(request):
    """Regenerate QR codes for all students"""
    if request.method == 'POST':
        try:
            style = request.POST.get('style', 'basic')
            students = Student.objects.all()
            
            if not students.exists():
                messages.warning(request, 'No students found. Please upload students first.')
                return redirect('qr_generator')
            
            # Ensure QR codes directory exists
            qr_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
            os.makedirs(qr_dir, exist_ok=True)
            
            success_count = 0
            error_count = 0
            
            for student in students:
                try:
                    data = json.dumps({
                        "StudentID": student.student_id,
                        "Name": student.name,
                        "Email": student.email,
                        "Course": student.course
                    })
                    
                    img = generate_qr_code(data, student.student_id, style=style)
                    
                    # Save to media directory
                    filename = f"{student.student_id}_{style}.png"
                    filepath = os.path.join(qr_dir, filename)
                    img.save(filepath, "PNG")
                    
                    success_count += 1
                
                except Exception as e:
                    print(f"Error generating QR for {student.student_id}: {e}")
                    error_count += 1
            
            if success_count > 0:
                messages.success(request, f'Successfully generated {success_count} QR codes with {style} style.')
            if error_count > 0:
                messages.warning(request, f'{error_count} QR codes failed to generate.')
        
        except Exception as e:
            messages.error(request, f'Error regenerating QR codes: {str(e)}')
    
    return redirect('qr_generator')


def download_all_qr_codes(request):
    """Download all QR codes as a ZIP file"""
    try:
        style = request.GET.get('style', 'basic')
        students = Student.objects.all()
        
        if not students.exists():
            messages.warning(request, 'No students found.')
            return redirect('qr_generator')
        
        # Create ZIP file in memory
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            success_count = 0
            
            for student in students:
                try:
                    data = json.dumps({
                        "StudentID": student.student_id,
                        "Name": student.name,
                        "Email": student.email,
                        "Course": student.course
                    })
                    
                    img = generate_qr_code(data, student.student_id, style=style)
                    
                    # Save to ZIP
                    img_buffer = BytesIO()
                    img.save(img_buffer, format="PNG")
                    img_buffer.seek(0)
                    
                    filename = f"{student.student_id}_{style}.png"
                    zip_file.writestr(filename, img_buffer.getvalue())
                    
                    success_count += 1
                
                except Exception as e:
                    print(f"Error adding {student.student_id} to ZIP: {e}")
        
        if success_count == 0:
            messages.error(request, 'Failed to generate any QR codes.')
            return redirect('qr_generator')
        
        # Prepare response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        filename = f"qr_codes_{style}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    except Exception as e:
        messages.error(request, f'Error creating ZIP file: {str(e)}')
        return redirect('qr_generator')


def bulk_qr_generator(request):
    """Bulk QR generator page"""
    try:
        students = Student.objects.all().order_by('student_id')
        context = {
            'students': students,
            'total_students': students.count(),
        }
        return render(request, 'attendance/bulk_qr_generator.html', context)
    
    except Exception as e:
        messages.error(request, f"Error loading bulk QR generator: {str(e)}")
        return render(request, 'attendance/bulk_qr_generator.html', {'error': True})


def admin_guide(request):
    """Admin guide page"""
    try:
        context = {
            'total_students': Student.objects.count(),
            'total_seminars': Seminar.objects.count(),
            'total_attendance': Attendance.objects.count(),
        }
        return render(request, 'attendance/admin_guide.html', context)
    
    except Exception as e:
        messages.error(request, f"Error loading admin guide: {str(e)}")
        return render(request, 'attendance/admin_guide.html', {'error': True})
