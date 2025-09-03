# Clean and robust views.py for QR Attendance System
import csv
import json
import os
import zipfile
from datetime import datetime
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from .forms import SeminarForm, UploadFileForm
from .models import Attendance, Seminar, Student


def generate_qr_code(data, student_id=None, style='basic'):
    """
    Generate QR code with different styles and error handling
    
    Args:
        data (str): The data to encode in QR code
        student_id (str, optional): Student ID for labeling
        style (str): QR code style - 'basic', 'styled', 'colored'
    
    Returns:
        PIL.Image: Generated QR code image
    """
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
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_x = (img.width - text_width) // 2
                text_y = img.height + 25
                
                draw.text((text_x, text_y), text, fill='black', font=font)
                img = new_img
        
        return img
    
    except Exception as e:
        print(f"Error generating QR code: {e}")
        # Fallback to basic QR code
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(str(data))
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")


def home(request):
    """Home page with overview statistics"""
    try:
        context = {
            'total_students': Student.objects.count(),
            'total_seminars': Seminar.objects.count(),
            'total_attendance': Attendance.objects.count(),
            'active_seminars': Seminar.objects.filter(
                start_time__lte=timezone.now(),
                end_time__gte=timezone.now()
            ).count(),
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
                        course = row.get('course', '').strip()
                        
                        if not all([student_id, name, email, course]):
                            error_count += 1
                            continue
                        
                        # Create or update student
                        student, created = Student.objects.get_or_create(
                            student_id=student_id,
                            defaults={
                                'name': name,
                                'email': email,
                                'course': course
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            # Update existing student
                            student.name = name
                            student.email = email
                            student.course = course
                            student.save()
                            updated_count += 1
                    
                    except Exception as row_error:
                        print(f"Error processing row {row}: {row_error}")
                        error_count += 1
                
                # Success message
                message_parts = []
                if created_count > 0:
                    message_parts.append(f"{created_count} students created")
                if updated_count > 0:
                    message_parts.append(f"{updated_count} students updated")
                if error_count > 0:
                    message_parts.append(f"{error_count} errors encountered")
                
                messages.success(request, "; ".join(message_parts))
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
        now = timezone.now()
        
        # Calculate status for each seminar
        for seminar in seminars:
            if now < seminar.start_time:
                seminar.status = 'upcoming'
                seminar.status_class = 'primary'
            elif seminar.start_time <= now <= seminar.end_time:
                seminar.status = 'active'
                seminar.status_class = 'success'
            else:
                seminar.status = 'ended'
                seminar.status_class = 'danger'
        
        context = {
            'seminars': seminars,
            'form': form,
            'current_time': now,
        }
        return render(request, 'attendance/seminars.html', context)
    
    except Exception as e:
        messages.error(request, f"Error loading seminars: {str(e)}")
        return render(request, 'attendance/seminars.html', {'form': form, 'error': True})


def scan(request, seminar_id=None):
    """QR code scanning with multiple methods"""
    if seminar_id:
        try:
            seminar = get_object_or_404(Seminar, seminar_id=seminar_id)
            
            # Check if seminar is active
            now = timezone.now()
            if now < seminar.start_time:
                messages.warning(request, f'Seminar "{seminar.title}" has not started yet.')
                return redirect('seminars')
            elif now > seminar.end_time:
                messages.warning(request, f'Seminar "{seminar.title}" has already ended.')
                return redirect('seminars')
            
        except Seminar.DoesNotExist:
            messages.error(request, 'Seminar not found.')
            return redirect('seminars')
    else:
        seminar = None
    
    if request.method == 'POST':
        try:
            # Handle manual student ID entry
            if 'manual_student_id' in request.POST:
                student_id = request.POST.get('manual_student_id', '').strip()
                return process_attendance(request, student_id, seminar)
            
            # Handle file upload
            elif 'qr_file' in request.FILES:
                file = request.FILES['qr_file']
                # Process QR code from image file
                try:
                    from pyzbar import pyzbar
                    from PIL import Image
                    
                    image = Image.open(file)
                    decoded_objects = pyzbar.decode(image)
                    
                    if decoded_objects:
                        qr_data = decoded_objects[0].data.decode('utf-8')
                        try:
                            data = json.loads(qr_data)
                            student_id = data.get('StudentID')
                            if student_id:
                                return process_attendance(request, student_id, seminar)
                        except json.JSONDecodeError:
                            # If not JSON, treat as plain student ID
                            return process_attendance(request, qr_data, seminar)
                    else:
                        messages.error(request, 'No QR code found in the uploaded image.')
                
                except ImportError:
                    messages.error(request, 'QR code scanning from file is not available. Please enter student ID manually.')
                except Exception as e:
                    messages.error(request, f'Error processing image: {str(e)}')
            
            # Handle QR code data from camera
            elif 'qr_data' in request.POST:
                qr_data = request.POST.get('qr_data', '').strip()
                try:
                    data = json.loads(qr_data)
                    student_id = data.get('StudentID')
                    if student_id:
                        return process_attendance(request, student_id, seminar)
                except json.JSONDecodeError:
                    # If not JSON, treat as plain student ID
                    return process_attendance(request, qr_data, seminar)
        
        except Exception as e:
            messages.error(request, f'Error processing attendance: {str(e)}')
    
    try:
        context = {
            'seminar': seminar,
            'seminars': Seminar.objects.filter(
                start_time__lte=timezone.now(),
                end_time__gte=timezone.now()
            ).order_by('start_time') if not seminar else None,
        }
        return render(request, 'attendance/scan.html', context)
    
    except Exception as e:
        messages.error(request, f"Error loading scan page: {str(e)}")
        return render(request, 'attendance/scan.html', {'error': True})


def process_attendance(request, student_id, seminar=None):
    """Process attendance marking with validation"""
    try:
        # Find student
        try:
            student = Student.objects.get(student_id=student_id)
        except Student.DoesNotExist:
            messages.error(request, f'Student with ID "{student_id}" not found.')
            return redirect('scan' if not seminar else f'/scan/{seminar.seminar_id}/')
        
        # Use provided seminar or find active seminar
        if not seminar:
            active_seminars = Seminar.objects.filter(
                start_time__lte=timezone.now(),
                end_time__gte=timezone.now()
            )
            if not active_seminars.exists():
                messages.error(request, 'No active seminars found.')
                return redirect('seminars')
            elif active_seminars.count() > 1:
                messages.warning(request, 'Multiple active seminars found. Please select a specific seminar.')
                return redirect('scan')
            else:
                seminar = active_seminars.first()
        
        # Check if already marked
        if Attendance.objects.filter(student=student, seminar=seminar).exists():
            messages.warning(request, f'Attendance already marked for {student.name} in "{seminar.title}".')
        else:
            # Mark attendance
            Attendance.objects.create(student=student, seminar=seminar)
            messages.success(request, f'Attendance marked successfully for {student.name} in "{seminar.title}".')
        
        return redirect('scan' if not seminar else f'/scan/{seminar.seminar_id}/')
    
    except Exception as e:
        messages.error(request, f'Error marking attendance: {str(e)}')
        return redirect('scan')


def export_attendance(request, seminar_id=None):
    """Export attendance data to CSV"""
    try:
        if seminar_id:
            seminar = get_object_or_404(Seminar, seminar_id=seminar_id)
            attendance_records = Attendance.objects.filter(seminar=seminar)
            filename = f"attendance_{seminar.seminar_id}_{timezone.now().strftime('%Y%m%d')}.csv"
        else:
            attendance_records = Attendance.objects.all()
            filename = f"attendance_all_{timezone.now().strftime('%Y%m%d')}.csv"
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow(['Student ID', 'Student Name', 'Email', 'Course', 'Seminar ID', 'Seminar Title', 'Timestamp'])
        
        for record in attendance_records.select_related('student', 'seminar'):
            writer.writerow([
                record.student.student_id,
                record.student.name,
                record.student.email,
                record.student.course,
                record.seminar.seminar_id,
                record.seminar.title,
                record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        return response
    
    except Exception as e:
        messages.error(request, f'Error exporting attendance: {str(e)}')
        return redirect('home')


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
