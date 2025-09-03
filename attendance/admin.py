from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin, GroupAdmin as DjangoGroupAdmin
from .models import Student, Attendance, Seminar


class MinimalAdminSite(AdminSite):
    site_header = "QR Attendance Administration"
    site_title = "QR Attendance Admin"
    index_title = "Administration"

    def index(self, request, extra_context=None):
        """Use default index (which builds app_list) then strip recent actions."""
        response = super().index(request, extra_context)
        # Remove or empty recent actions so panel disappears
        ctx = getattr(response, 'context_data', {}) or {}
        if 'recent_actions' in ctx:
            ctx['recent_actions'] = []
        response.context_data = ctx
        return response


minimal_admin_site = MinimalAdminSite()

# Register auth models for user management
minimal_admin_site.register(User, DjangoUserAdmin)
minimal_admin_site.register(Group, DjangoGroupAdmin)

@admin.register(Student, site=minimal_admin_site)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'email', 'phone', 'course')
    search_fields = ('student_id', 'name', 'email', 'phone')
    list_filter = ('course',)

@admin.register(Seminar, site=minimal_admin_site)
class SeminarAdmin(admin.ModelAdmin):
    list_display = ('seminar_id', 'title', 'status', 'start_time', 'end_time', 'created_at')
    list_filter = ('status', 'start_time', 'end_time')
    search_fields = ('seminar_id', 'title')
    list_editable = ('status',)
    ordering = ('-created_at',)

@admin.register(Attendance, site=minimal_admin_site)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'seminar', 'timestamp')
    list_filter = ('seminar', 'timestamp')
    search_fields = ('student__student_id', 'student__name', 'seminar__seminar_id')
