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

---

## How the System Works (Step by Step)

### 1. Data Model Overview
Core models (see `attendance/models.py`):
- Student: `student_id`, `name`, `email`, `phone`, `course`, timestamps.
- Seminar: Identified by `seminar_id` (auto or slug), has `title`, `start_time`, `end_time`, manual `status` (Inactive / Active / Ended).
- Attendance: Links a `Student` to a `Seminar` with a `timestamp` (scan or manual entry). Unique constraint prevents duplicate (student, seminar) pairs.

### 2. Student Onboarding
1. Admin or staff uploads a CSV (page `/upload/`).
2. Backend parses each row; existing students (same `student_id`) are updated, new ones created.
3. Students become visible on `/students/` and available for QR generation.

### 3. QR Code Generation
There are 3 usage patterns:
1. Bulk Regenerate (button on `/generate-qr/`): Iterates every student, builds a QR payload (usually the student ID or JSON) and writes image files into `media/qr_codes/` (or a structured path). Overwrites safely (idempotent).
2. Individual Generate (table action on `/generate-qr/`): Renders a single QR on‑demand (opens new tab) without needing a full regenerate.
3. Bulk Download: Zips all existing QR code images and streams them to the browser.

QR Generation Flow (simplified):
```
for each student:
   data = student.student_id (or enriched JSON)
   img = qrcode.make(data, config...)
   save to media/qr_codes/<STUDENT_ID>_basic.png
```
Styled or colored modes use different error correction + palette (see `generate_qr_code` in `views.py`).

### 4. Missing QR Handling
On the `/students/` page, if a static QR file 404s, a placeholder appears (“Not generated”). User can trigger a bulk regenerate to fill the gap.

### 5. Seminar Lifecycle
1. Create seminar in admin or a form (if enabled).
2. Set `status=Active` when you want scanning to list it in the scanner dropdown.
3. After session ends, set `status=Ended` to lock new scans.
4. Status changes are manual—no automatic time logic to avoid timezone pitfalls.

### 6. Scanning & Attendance Capture
The `/scan/` page uses the `html5-qrcode` JS library.
1. User selects (or it auto-loads) an Active seminar.
2. Camera feed decodes QR → returns text payload (student ID or JSON).
3. JavaScript sends an AJAX POST (`fetch`) to attendance endpoint (same page) with student ID + seminar ID.
4. Backend:
   - Validates seminar is Active.
   - Looks up Student; if not found → error JSON.
   - Creates Attendance if not exists (enforced by `get_or_create`).
   - Returns JSON status (new / duplicate / error).
5. Frontend plays success or duplicate sound and updates a result list.

Manual Entry Path: Form field allows typing a student ID; same POST route processes it identically (marked as manual in future you can add a flag if needed).

Image Upload Path: (If enabled) user selects a saved QR image → library attempts decode and triggers same success handler.

### 7. Duplicate Prevention
Attendance uniqueness: Database constraint + `get_or_create` ensures multiple scans of the same student for the same seminar do not create extra records. Duplicate response triggers a different audio tone and UI badge.

### 8. Exporting Attendance
Per‑seminar export at `/export/<seminar_id>/` or via buttons on the seminars page.
Flow:
1. Query Attendance rows filtered by seminar.
2. Join (related access) Student fields.
3. Stream CSV (`HttpResponse` with `text/csv`).
4. Columns: Student ID, Name, Email, Phone, Course, Date, Time (split timestamp for readability).

### 9. Admin Operations (Custom Minimal Admin)
Replaced default index to hide “Recent actions” clutter while retaining:
- CRUD for Students, Seminars, Attendance.
- Inline status editing (list_editable for seminars).
- Auth: Users & Groups registered for account management.

### 10. Regenerating After Data Changes
If you add students (or change IDs—should be rare), hit “Regenerate All” on the generator page to ensure each has a QR. Existing images are overwritten; exports & attendance remain unaffected.

### 11. Static & Media Handling
- `Whitenoise` serves static assets in production (CSS/JS).
- QR images stored under `media/qr_codes/` (served via Django in dev). In production you would configure a web server or object storage (S3) and set `MEDIA_URL` / `MEDIA_ROOT`.

### 12. Error & Edge Cases Considered
- Camera permission denied → user can fallback to upload/manual entry.
- Invalid QR payload → backend returns error JSON; UI shows warning.
- Duplicate scan → handled gracefully, no exception.
- Missing font for styled QR → falls back to default PIL font.
- Timezone: Using naive/UTC timestamps; manual status avoids drift issues.

### 13. Performance Notes
- Bulk QR regenerate loops through all students once; acceptable for moderate cohorts. Could batch or async later.
- Attendance insert is O(1) with indexed foreign keys.
- Export streams a lightweight in-memory CSV (fine unless extremely large—then consider chunked streaming).

### 14. Extensibility Hooks
Potential enhancements:
- Add a JSON payload with signature in QR (integrity verification).
- Add `source` field (camera/upload/manual) to Attendance.
- Rate limiting or debounce to prevent rapid duplicate scanning noise.
- Pagination & filtering on attendance list (currently not exposed in UI).
- WebSocket push for live dashboard counts.

### 15. Deployment Outline
1. Set env vars (`SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`).
2. `collectstatic` (if STATIC_ROOT configured) for production.
3. Run with Gunicorn/Uvicorn behind Nginx.
4. Use HTTPS (LetsEncrypt) and security headers.
5. Regularly back up database & `media/qr_codes/`.

### 16. Security Summary
- No student personal info in QR beyond ID (recommended). If expanded, sign/encrypt payload.
- Admin path hardened by removing noisy panels.
- Encourage strong admin passwords & limited staff accounts.

### 17. Troubleshooting Quick Table
| Issue | Cause | Action |
|-------|-------|--------|
| QR not scanning | Low contrast / glare | Reprint or increase lighting |
| Seminar missing in dropdown | Status not Active | Set to Active in admin |
| Duplicate sound constantly | Same code fixed in camera view | Move code away after first scan |
| Export empty | Wrong seminar or no attendance yet | Confirm seminar & re-scan |
| Missing QR image | Not regenerated after upload | Use Regenerate All |

---

This section is intentionally verbose for operators; trim for end-user distribution if needed.
