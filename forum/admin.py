from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Thread, Comment, Report, ActivityLog

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Thêm trường role vào phần hiển thị chi tiết
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Security', {'fields': ('role',)}),
    )
    # Hiển thị thêm thông tin ra bảng ngoài để dễ nhìn
    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    # Thêm thanh tìm kiếm theo tên bài hoặc tên tác giả
    search_fields = ('title', 'author__username')
    # Thêm thanh điều hướng thời gian (Date Hierarchy) trên cùng
    date_hierarchy = 'created_at'

    # Thêm tính năng thao tác hàng loạt (Bulk Actions)
    actions = ['make_published', 'make_hidden']

    @admin.action(description='Duyệt: Cho phép hiển thị các bài đã chọn')
    def make_published(self, request, queryset):
        queryset.update(status='published') # Chú ý: Đổi 'published' cho khớp với choices trong models.py của bạn

    @admin.action(description='Khóa: Ẩn các bài đã chọn')
    def make_hidden(self, request, queryset):
        queryset.update(status='hidden')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'thread', 'author', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('content', 'author__username', 'thread__title')
    actions = ['make_hidden']

    @admin.action(description='Xóa/Ẩn các bình luận vi phạm')
    def make_hidden(self, request, queryset):
        queryset.update(status='hidden')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'report_type', 'object_id', 'resolved', 'created_at')
    list_filter = ('resolved', 'report_type', 'created_at')
    search_fields = ('reporter__username',)
    actions = ['mark_as_resolved']

    @admin.action(description='Đánh dấu đã giải quyết (Resolved)')
    def mark_as_resolved(self, request, queryset):
        queryset.update(resolved=True)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'target_type', 'target_id')
    list_filter = ('action', 'target_type', 'created_at')
    search_fields = ('user__username', 'details')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    # BẢO MẬT: Khóa hoàn toàn, không ai được phép sửa/xóa Audit Log
    def has_add_permission(self, request):
        return False # Cấm tạo log bằng tay

    def has_change_permission(self, request, obj=None):
        return False # Cấm sửa log

    def has_delete_permission(self, request, obj=None):
        return False # Cấm xóa log
