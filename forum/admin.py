from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Thread, Comment, Report, ActivityLog


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'status', 'created_at')
    list_filter = ('status', 'created_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'thread', 'author', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'report_type', 'object_id', 'resolved', 'created_at')
    list_filter = ('resolved', 'report_type')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'target_type', 'target_id')
    list_filter = ('action', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'user', 'action', 'target_type', 'target_id', 'target_user', 'details')
