# QR Attendance System

Django-based QR code attendance tracking system.

## Features

- Student management via CSV upload & admin
- Manual seminar status (Inactive / Active / Ended)
- Camera, image upload, and manual entry scanning
- Bulk & individual QR code generation + downloadable ZIP
- Per-seminar CSV export (full student details)
- Placeholder for missing QR images
- Minimal custom admin (no recent actions clutter) with user/group management
- Whitenoise static file serving (production friendly)

## Quick Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup database**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. **Run server**
   ```bash
   python manage.py runserver
   ```

4. **Access**
   - App: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## Basic Workflow

1. Upload or add students (CSV format: `student_id,name,email,phone,course`).
2. Create seminar(s) then set status to Active when ready to scan.
3. Generate or regenerate all QR codes at /generate-qr/ (download ZIP if needed).
4. Scan via /scan/ (camera) or upload QR image / manual SBU ID entry.
5. Export CSV from seminars page (per seminar button).
6. Set seminar to Ended to finalize.

## Structure

```
qr_attendance_django/
├── manage.py
├── requirements.txt
├── health_check.py
├── qr_attendance/          # Settings
├── attendance/             # Main app
├── templates/              # HTML templates
└── media/qr_codes/        # Generated QR codes
```

## Environment & Deployment

Environment variables (optional `.env`):
- `SECRET_KEY`
- `DEBUG` (True/False)
- `ALLOWED_HOSTS` (comma separated)

For production add (example):
```bash
pip install gunicorn
gunicorn qr_attendance.wsgi:application
```
Serve behind Nginx; collect static files if STATIC_ROOT configured.

## Requirements

- Python 3.11 (tested) or 3.8+
- Django 4.2
- Pillow
- qrcode[pil]
- whitenoise

## Security Notes

- Change default admin credentials immediately.
- Set `DEBUG=False` in production and configure `ALLOWED_HOSTS`.
- Use HTTPS in deployment.

## License

MIT (add LICENSE file if required).
