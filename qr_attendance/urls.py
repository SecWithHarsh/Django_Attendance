from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from attendance import views
from attendance.admin import minimal_admin_site

urlpatterns = [
    path('admin/', minimal_admin_site.urls),
    path('', views.home, name='home'),
    path('upload/', views.upload_students, name='upload_students'),
    path('students/', views.students, name='students'),
    path('seminars/', views.seminars, name='seminars'),
    path('seminars/update-status/<int:seminar_id>/', views.update_seminar_status, name='update_seminar_status'),
    path('scan/', views.scan, name='scan'),
    path('scan/<str:seminar_id>/', views.scan, name='scan_seminar'),
    path('export/', views.export_attendance, name='export_attendance'),
    path('export/<str:seminar_id>/', views.export_attendance, name='export_seminar_attendance'),
    path('generate-qr/', views.qr_generator, name='qr_generator'),
    path('generate-qr/<str:student_id>/', views.generate_single_qr, name='generate_single_qr'),
    path('regenerate-qr/', views.regenerate_qr_codes, name='regenerate_qr_codes'),
    path('download-all-qr/', views.download_all_qr_codes, name='download_all_qr_codes'),
    path('bulk-qr/', views.bulk_qr_generator, name='bulk_qr_generator'),
    path('admin-guide/', views.admin_guide, name='admin_guide'),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
