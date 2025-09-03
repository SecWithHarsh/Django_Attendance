#!/usr/bin/env python
"""
QR Attendance System Health Check
Run this to verify all components are working correctly
"""

import os
import sys
import django
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_attendance.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from attendance.models import Student, Seminar, Attendance

def check_database():
    print("🔍 Checking database connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Database connection: OK")
        Student.objects.count()
        Seminar.objects.count() 
        Attendance.objects.count()
        print("✅ Database tables: OK")
        
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def check_dependencies():
    print("\n🔍 Checking dependencies...")
    required_packages = {
        'django': 'Django',
        'qrcode': 'QR Code generation',
        'PIL': 'Image processing'
    }
    
    all_ok = True
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {description}: OK")
        except ImportError:
            print(f"❌ {description}: Missing ({package})")
            all_ok = False
    
    return all_ok

def check_directories():
    """Check required directories exist"""
    print("\n🔍 Checking directories...")
    required_dirs = [
        'templates',
        'static',
        'media',
        'media/qr_codes'
    ]
    
    all_ok = True
    for dir_path in required_dirs:
        full_path = project_dir / dir_path
        if full_path.exists():
            print(f"✅ {dir_path}: OK")
        else:
            print(f"❌ {dir_path}: Missing")
            # Create missing directories
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created: {dir_path}")
    
    return all_ok

def check_views():
    """Check view functions are importable"""
    print("\n🔍 Checking views...")
    try:
        from attendance import views
        
        required_views = [
            'home', 'upload_students', 'students', 'seminars',
            'scan', 'export_attendance', 'qr_generator',
            'generate_single_qr', 'regenerate_qr_codes',
            'download_all_qr_codes', 'bulk_qr_generator', 'admin_guide'
        ]
        
        missing_views = []
        for view_name in required_views:
            if hasattr(views, view_name):
                print(f"✅ {view_name}: OK")
            else:
                missing_views.append(view_name)
                print(f"❌ {view_name}: Missing")
        
        return len(missing_views) == 0
    
    except Exception as e:
        print(f"❌ Views import error: {e}")
        return False

def check_templates():
    """Check template files exist"""
    print("\n🔍 Checking templates...")
    required_templates = [
        'base.html',
        'attendance/home.html',
        'attendance/upload.html',
        'attendance/students.html',
        'attendance/seminars.html',
        'attendance/scan.html',
        'attendance/qr_generator.html'
    ]
    
    missing_templates = []
    for template in required_templates:
        template_path = project_dir / 'templates' / template
        if template_path.exists():
            print(f"✅ {template}: OK")
        else:
            missing_templates.append(template)
            print(f"❌ {template}: Missing")
    
    return len(missing_templates) == 0

def check_sample_data():
    """Check if sample data exists"""
    print("\n🔍 Checking sample data...")
    
    student_count = Student.objects.count()
    seminar_count = Seminar.objects.count()
    attendance_count = Attendance.objects.count()
    
    print(f"📊 Students: {student_count}")
    print(f"📊 Seminars: {seminar_count}")
    print(f"📊 Attendance records: {attendance_count}")
    
    if student_count == 0:
        print("💡 Tip: Upload sample_data.csv to get started")
    
    return True

def generate_qr_test():
    """Test QR code generation"""
    print("\n🔍 Testing QR code generation...")
    try:
        from attendance.views import generate_qr_code
        import json
        
        test_data = json.dumps({
            "StudentID": "TEST001",
            "Name": "Test Student",
            "Email": "test@example.com",
            "Course": "Test Course"
        })
        
        img = generate_qr_code(test_data, "TEST001", "basic")
        print("✅ QR code generation: OK")
        return True
    
    except Exception as e:
        print(f"❌ QR generation error: {e}")
        return False

def main():
    """Run all health checks"""
    print("🏥 QR Attendance System Health Check")
    print("=" * 50)
    
    checks = [
        check_dependencies,
        check_database,
        check_directories,
        check_views,
        check_templates,
        generate_qr_test,
        check_sample_data
    ]
    
    results = []
    for check in checks:
        results.append(check())
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All checks passed! ({passed}/{total})")
        print("🚀 System is ready to use!")
        print("\n💡 Quick start:")
        print("   1. Run: python manage.py runserver")
        print("   2. Visit: http://127.0.0.1:8000/")
        print("   3. Upload sample_data.csv to get started")
    else:
        print(f"⚠️  {passed}/{total} checks passed")
        print("🔧 Please fix the issues above before using the system")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
