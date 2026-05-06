from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import (
    AccountSettingsForm,
    CommentForm,
    CustomPasswordChangeForm,
    CustomUserCreationForm,
    ThreadForm,
)
from .models import ActivityLog, Comment, Thread, User
from .permissions import (
    can_create_comment,
    can_delete_comment,
    can_delete_thread,
    can_view_thread,
    is_member,
    log_activity,
)


def index(request):
    thread_list = Thread.objects.filter(status=Thread.STATUS_PUBLISHED).order_by(
        "-created_at"
    )
    q = request.GET.get("q", "").strip()
    author = request.GET.get("author", "").strip()

    if q:
        thread_list = thread_list.filter(
            Q(title__icontains=q) | Q(content__icontains=q)
        )
    if author:
        thread_list = thread_list.filter(author__username__iexact=author)

    paginate = request.GET.get("paginate", "1")
    if paginate != "0":
        paginator = Paginator(thread_list, 20)
        page = request.GET.get("page")
        try:
            threads = paginator.page(page)
        except PageNotAnInteger:
            threads = paginator.page(1)
        except EmptyPage:
            threads = paginator.page(paginator.num_pages)
        is_paginated = True
    else:
        threads = thread_list
        is_paginated = False

    return render(
        request,
        "forum/index.html",
        {
            "threads": threads,
            "query": q,
            "author_q": author,
            "is_paginated": is_paginated,
        },
    )


@login_required
def create_thread(request):
    if not is_member(request.user):
        return HttpResponseForbidden("Only members can create threads")

    if request.method == "POST":
        form = ThreadForm(request.POST, request.FILES)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.author = request.user
            thread.save()
            log_activity(
                request.user, ActivityLog.ACTION_THREAD_CREATE, "thread", thread.id
            )
            messages.success(request, "Tạo thread thành công!")
            return redirect("forum:index")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin.")
    else:
        form = ThreadForm()

    return render(request, "forum/create_thread.html", {"form": form})


def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if thread.status == Thread.STATUS_DELETED:
        return HttpResponseForbidden("Thread not available")
    if not can_view_thread(request.user, thread):
        return HttpResponseForbidden("You cannot view this thread")

    comments = thread.comments.filter(
        status=Comment.STATUS_PUBLISHED, parent__isnull=True
    ).order_by("created_at")
    reply_to = request.GET.get("reply_to")

    try:
        reply_to = int(reply_to) if reply_to else None
    except (TypeError, ValueError):
        reply_to = None

    if request.method == "POST":
        if not request.user.is_authenticated or not can_create_comment(request.user):
            return redirect("login")

        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.thread = thread
            comment.author = request.user

            parent_id = request.POST.get("parent_id")
            if parent_id:
                parent = Comment.objects.filter(pk=parent_id).first()
                if parent:
                    comment.parent = parent

            if not form.cleaned_data.get("content") and not form.cleaned_data.get(
                "image"
            ):
                form.add_error(None, "Vui lòng nhập nội dung hoặc tải ảnh.")
            else:
                comment.save()
                log_activity(
                    request.user,
                    ActivityLog.ACTION_COMMENT_CREATE,
                    "comment",
                    comment.id,
                )
                messages.success(request, "Bình luận thành công!")
                return redirect("forum:detail", thread_id=thread.id)
    else:
        form = CommentForm()

    for c in comments:
        c.replies_qs = c.replies.filter(status=Comment.STATUS_PUBLISHED).order_by(
            "created_at"
        )

    return render(
        request,
        "forum/detail.html",
        {"thread": thread, "comments": comments, "form": form, "reply_to": reply_to},
    )


@require_http_methods(["POST"])
@login_required
def delete_thread(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if not can_delete_thread(request.user, thread):
        return HttpResponseForbidden("Not allowed")

    thread.status = Thread.STATUS_DELETED
    thread.save()
    log_activity(
        request.user,
        ActivityLog.ACTION_THREAD_DELETE,
        "thread",
        thread.id,
        target_user=thread.author,
    )
    messages.success(request, "Đã xóa thread.")
    return redirect("forum:index")


@require_http_methods(["POST"])
@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    if not can_delete_comment(request.user, comment):
        return HttpResponseForbidden("Not allowed")

    thread_id = comment.thread.id
    comment.status = Comment.STATUS_DELETED
    comment.save()
    log_activity(
        request.user,
        ActivityLog.ACTION_COMMENT_DELETE,
        "comment",
        comment.id,
        target_user=comment.author,
    )
    messages.success(request, "Đã xóa bình luận.")
    return redirect("forum:detail", thread_id=thread_id)


def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f"Chào mừng {user.get_display_name()}!")
            return redirect("forum:index")
        else:
            messages.error(request, "Đăng ký thất bại. Vui lòng kiểm tra lại.")
    else:
        form = CustomUserCreationForm()

    return render(request, "registration/signup.html", {"form": form})


def user_profile(request, username):
    target_user = get_object_or_404(User, username=username)
    user_threads = target_user.threads.filter(status=Thread.STATUS_PUBLISHED).order_by(
        "-created_at"
    )[:10]

    context = {
        "target_user": target_user,
        "user_threads": user_threads,
        "thread_count": target_user.get_thread_count(),
        "comment_count": target_user.get_comment_count(),
        "is_own_profile": request.user.is_authenticated and request.user == target_user,
    }
    return render(request, "forum/user_profile.html", context)


@login_required
def account_settings(request):
    if request.method == "POST":
        form = AccountSettingsForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            log_activity(
                request.user, ActivityLog.ACTION_USER_UPDATE, "user", request.user.id
            )
            messages.success(request, "Cập nhật thành công!")
            return redirect("forum:account_settings")
        else:
            messages.error(
                request, "Cập nhật thất bại. Vui lòng kiểm tra lại thông tin."
            )
    else:
        form = AccountSettingsForm(instance=request.user)

    return render(request, "forum/account_settings.html", {"form": form})


@login_required
def password_change_view(request):
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            log_activity(
                request.user,
                ActivityLog.ACTION_USER_UPDATE,
                "user",
                request.user.id,
                details={"action": "password_changed"},
            )
            messages.success(
                request, "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."
            )
            return redirect("login")
        else:
            messages.error(request, "Đổi mật khẩu thất bại. Vui lòng kiểm tra lại.")
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, "forum/password_change.html", {"form": form})
