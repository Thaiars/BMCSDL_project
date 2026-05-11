import json
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import (
    AccountSettingsForm,
    CommentForm,
    CustomPasswordChangeForm,
    CustomUserCreationForm,
    ThreadForm,
)
from .models import ActivityLog, Comment, Thread, User, Report, ThreadVote, CommentVote
from .permissions import (
    can_create_comment,
    can_delete_comment,
    can_delete_thread,
    can_view_thread,
    is_member,
    log_activity,
)


def index(request):
    thread_list = Thread.objects.filter(status=Thread.STATUS_PUBLISHED).order_by("-created_at")
    q = request.GET.get("q", "").strip()
    author = request.GET.get("author", "").strip()

    if q:
        thread_list = thread_list.filter(Q(title__icontains=q) | Q(content__icontains=q))
    if author:
        thread_list = thread_list.filter(author__name__icontains=author)

    user_votes = {}
    if request.user.is_authenticated:
        votes = ThreadVote.objects.filter(user=request.user, thread__in=thread_list)
        user_votes = {v.thread_id: v.value for v in votes}

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

    # Gán trực tiếp user_vote vào mỗi thread
    for t in threads:
        t.user_vote = user_votes.get(t.id, 0)

    return render(
        request, "forum/index.html",
        {"threads": threads, "query": q, "author_q": author, "is_paginated": is_paginated}
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
            log_activity(request.user, ActivityLog.ACTION_THREAD_CREATE, "thread", thread.id)
            messages.success(request, "Tạo thread thành công!")
            return redirect("forum:index")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin.")
    else:
        form = ThreadForm()

    return render(request, "forum/create_thread.html", {"form": form})


def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if thread.status == Thread.STATUS_DELETED and not request.user.is_moderator():
        return HttpResponseForbidden("Thread not available")
    if not can_view_thread(request.user, thread):
        return HttpResponseForbidden("You cannot view this thread")

    comments = thread.comments.filter(parent__isnull=True).exclude(status=Comment.STATUS_DELETED).order_by("created_at")
    reply_to = request.GET.get("reply_to")

    try:
        reply_to = int(reply_to) if reply_to else None
    except (TypeError, ValueError):
        reply_to = None

    user_thread_vote = 0
    user_comment_votes = {}
    if request.user.is_authenticated:
        tv = ThreadVote.objects.filter(user=request.user, thread=thread).first()
        if tv: user_thread_vote = tv.value
        cvs = CommentVote.objects.filter(user=request.user, comment__thread=thread)
        user_comment_votes = {cv.comment_id: cv.value for cv in cvs}

    if request.method == "POST":
        if not request.user.is_authenticated or not can_create_comment(request.user):
            return redirect("login")

        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.thread = thread
            comment.author = request.user

            parent_id = request.POST.get("parent_id")
            if parent_id and str(parent_id).strip().lower() != "none":
                try:
                    parent = Comment.objects.filter(pk=int(parent_id)).first()
                    if parent:
                        comment.parent = parent
                except ValueError:
                    pass

            if not form.cleaned_data.get("content") and not form.cleaned_data.get("image"):
                form.add_error(None, "Vui lòng nhập nội dung hoặc tải ảnh.")
            else:
                comment.save()
                log_activity(request.user, ActivityLog.ACTION_COMMENT_CREATE, "comment", comment.id)
                messages.success(request, "Bình luận thành công!")
                return redirect("forum:detail", thread_id=thread.id)
    else:
        form = CommentForm()

    # FIX Ở ĐÂY: Gán trực tiếp user_vote vào từng comment và reply
    for c in comments:
        c.user_vote = user_comment_votes.get(c.id, 0)
        c.replies_qs = c.replies.exclude(status=Comment.STATUS_DELETED).order_by("created_at")
        for reply in c.replies_qs:
            reply.user_vote = user_comment_votes.get(reply.id, 0)

    return render(
        request, "forum/detail.html",
        {"thread": thread, "comments": comments, "form": form, "reply_to": reply_to,
         "user_thread_vote": user_thread_vote}
    )


@require_http_methods(["POST"])
@login_required
def delete_thread(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if not can_delete_thread(request.user, thread):
        return HttpResponseForbidden("Not allowed")

    if request.user != thread.author and request.user.is_moderator():
        thread.is_removed_by_mod = True
    thread.status = Thread.STATUS_DELETED
    thread.save()
    log_activity(request.user, ActivityLog.ACTION_THREAD_DELETE, "thread", thread.id, target_user=thread.author)
    messages.success(request, "Đã xóa thread.")
    return redirect("forum:index")


@require_http_methods(["POST"])
@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    if not can_delete_comment(request.user, comment):
        return HttpResponseForbidden("Not allowed")

    thread_id = comment.thread.id

    if request.user != comment.author and request.user.is_moderator():
        comment.is_removed_by_mod = True
        comment.content = ""
        if comment.image: comment.image.delete()
    else:
        comment.status = Comment.STATUS_DELETED

    comment.save()
    log_activity(request.user, ActivityLog.ACTION_COMMENT_DELETE, "comment", comment.id, target_user=comment.author)
    messages.success(request, "Đã xóa bình luận.")
    return redirect("forum:detail", thread_id=thread_id)


# --- API VOTE ---
@require_http_methods(["POST"])
@login_required
def vote_api(request):
    data = json.loads(request.body)
    obj_type = data.get('type')
    obj_id = data.get('id')
    action = data.get('action')
    value = 1 if action == 'up' else -1

    if obj_type == 'thread':
        obj = get_object_or_404(Thread, pk=obj_id)
        vote, created = ThreadVote.objects.get_or_create(user=request.user, thread=obj, defaults={'value': value})
    else:
        obj = get_object_or_404(Comment, pk=obj_id)
        vote, created = CommentVote.objects.get_or_create(user=request.user, comment=obj, defaults={'value': value})

    if not created:
        if vote.value == value:
            vote.delete()
            user_vote = 0
        else:
            vote.value = value
            vote.save()
            user_vote = value
    else:
        user_vote = value

    return JsonResponse({'score': obj.score, 'user_vote': user_vote})


# --- API REPORT ---
@require_http_methods(["POST"])
@login_required
def create_report(request):
    obj_type = request.POST.get('type')
    obj_id = request.POST.get('id')
    reason = request.POST.get('reason', 'Vi phạm nội quy')

    Report.objects.create(reporter=request.user, report_type=obj_type, object_id=obj_id, reason=reason)
    messages.success(request, "Báo cáo của bạn đã được gửi tới Ban quản trị.")

    if obj_type == 'thread': return redirect("forum:detail", thread_id=obj_id)
    else:
        comment = get_object_or_404(Comment, pk=obj_id)
        return redirect("forum:detail", thread_id=comment.thread.id)


# --- MOD DASHBOARD ---
@login_required
def mod_dashboard(request):
    if not request.user.is_moderator():
        return HttpResponseForbidden("Chỉ dành cho Mod/Admin")

    reports = Report.objects.filter(resolved=False).order_by('-created_at')
    thread_reports = []
    comment_reports =[]

    for r in reports:
        if r.report_type == Report.TYPE_THREAD:
            target = Thread.objects.filter(pk=r.object_id).first()
            if target and target.status != Thread.STATUS_DELETED:
                thread_reports.append({'report': r, 'target': target})
            else:
                r.resolved = True
                r.save()
        elif r.report_type == Report.TYPE_COMMENT:
            target = Comment.objects.filter(pk=r.object_id).first()
            if target and target.status != Comment.STATUS_DELETED and not target.is_removed_by_mod:
                comment_reports.append({'report': r, 'target': target})
            else:
                r.resolved = True
                r.save()

    return render(request, "forum/mod_dashboard.html", {
        "thread_reports": thread_reports, "comment_reports": comment_reports
    })

@require_http_methods(["POST"])
@login_required
def resolve_report(request, report_id):
    if not request.user.is_moderator(): return HttpResponseForbidden()
    report = get_object_or_404(Report, pk=report_id)
    report.resolved = True
    report.save()
    messages.success(request, "Đã bỏ qua báo cáo.")
    return redirect("forum:mod_dashboard")


# --- USER VIEWS ---
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
    user_threads = target_user.threads.filter(status=Thread.STATUS_PUBLISHED).order_by("-created_at")[:10]

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
            log_activity(request.user, ActivityLog.ACTION_USER_UPDATE, "user", request.user.id)
            messages.success(request, "Cập nhật thành công!")
            return redirect("forum:account_settings")
        else:
            messages.error(request, "Cập nhật thất bại. Vui lòng kiểm tra lại thông tin.")
    else:
        form = AccountSettingsForm(instance=request.user)

    return render(request, "forum/account_settings.html", {"form": form})


@login_required
def password_change_view(request):
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            log_activity(request.user, ActivityLog.ACTION_USER_UPDATE, "user", request.user.id, details={"action": "password_changed"})
            messages.success(request, "Đổi mật khẩu thành công. Vui lòng đăng nhập lại.")
            return redirect("login")
        else:
            messages.error(request, "Đổi mật khẩu thất bại. Vui lòng kiểm tra lại.")
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, "forum/password_change.html", {"form": form})
