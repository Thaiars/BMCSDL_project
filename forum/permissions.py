from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from .models import ActivityLog, User


def log_activity(
    user, action, target_type=None, target_id=None, target_user=None, details=None
):
    """Helper to log user activities"""
    if details is None:
        details = {}
    ActivityLog.objects.create(
        user=user,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_user=target_user,
        details=details,
    )


# Permission check functions
def is_guest(user):
    """User is not authenticated"""
    return not user.is_authenticated


def is_member(user):
    """User is authenticated with member role"""
    return user.is_authenticated and user.role == User.ROLE_MEMBER


def is_moderator(user):
    """User is moderator or admin"""
    return user.is_authenticated and user.role in [User.ROLE_MODERATOR, User.ROLE_ADMIN]


def is_admin(user):
    """User is admin"""
    return user.is_authenticated and user.role == User.ROLE_ADMIN


def can_view_thread(user, thread):
    """Anyone can view published threads"""
    if thread.status == "published":
        return True
    # Hidden/Deleted threads: only author, moderators, and admins
    if thread.status in ["hidden", "deleted"]:
        return user.is_authenticated and (thread.author == user or is_moderator(user))
    return False


def can_edit_thread(user, thread):
    """Only author can edit, or admin"""
    return user.is_authenticated and (thread.author == user or is_admin(user))


def can_delete_thread(user, thread):
    """Author, moderator, or admin can delete"""
    return user.is_authenticated and (thread.author == user or is_moderator(user))


def can_hide_thread(user, thread):
    """Only moderator or admin can hide"""
    return is_moderator(user)


def can_create_comment(user):
    """Only authenticated members can comment"""
    return is_member(user) or is_moderator(user) or is_admin(user)


def can_edit_comment(user, comment):
    """Only author can edit"""
    return user.is_authenticated and comment.author == user


def can_delete_comment(user, comment):
    """Author, moderator, or admin can delete"""
    return user.is_authenticated and (comment.author == user or is_moderator(user))


def can_hide_comment(user, comment):
    """Only moderator or admin can hide"""
    return is_moderator(user)


def can_file_report(user):
    """Only authenticated members can file reports"""
    return user.is_authenticated


def can_view_user_profile(user, target_user):
    """Any authenticated user can view profiles"""
    return user.is_authenticated


def can_edit_user_profile(user, target_user):
    """User can only edit own profile or admin can edit anyone's"""
    if not user.is_authenticated:
        return False
    # User có thể edit profile của chính họ hoặc admin có thể edit profile bất kỳ ai
    return user == target_user or is_admin(user)


def can_view_user_ip(user, thread_or_comment):
    """Only moderator and admin can view IP"""
    return is_moderator(user)


def can_manage_users(user):
    """Only admin can manage users"""
    return is_admin(user)


def can_view_audit_log(user):
    """Only admin can view audit logs"""
    return is_admin(user)


# Decorators for views
def require_member(view_func):
    """Require authenticated member or higher"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_member(request.user):
            return redirect("forum:index")
        return view_func(request, *args, **kwargs)

    return wrapper


def require_moderator(view_func):
    """Require moderator or admin"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_moderator(request.user):
            return HttpResponseForbidden(
                "You do not have permission to perform this action."
            )
        return view_func(request, *args, **kwargs)

    return wrapper


def require_admin(view_func):
    """Require admin"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            return HttpResponseForbidden(
                "You do not have permission to perform this action."
            )
        return view_func(request, *args, **kwargs)

    return wrapper
