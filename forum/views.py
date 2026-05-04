from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from .models import Thread, Comment, ActivityLog, User
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django import forms
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from .permissions import (
    can_view_thread, can_create_comment, can_delete_thread, can_delete_comment,
    can_hide_thread, can_hide_comment, log_activity, is_member, is_moderator
)


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ['title', 'content', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Thread title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Write your thread content...'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write a comment (optional)...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # allow image-only comments by making content optional on the form level
        self.fields['content'].required = False


def index(request):
    thread_list = Thread.objects.filter(status=Thread.STATUS_PUBLISHED).order_by('-created_at')
    q = request.GET.get('q', '').strip()
    author = request.GET.get('author', '').strip()
    if q:
        thread_list = thread_list.filter(Q(title__icontains=q) | Q(content__icontains=q))
    if author:
        thread_list = thread_list.filter(author__username__iexact=author)

    # By default show all threads on one page for easier browsing.
    # If you want pagination, pass `?paginate=1` and `page=` will be respected.
    paginate = request.GET.get('paginate')
    if paginate:
        paginator = Paginator(thread_list, 5)  # 5 threads per page when paginating
        page = request.GET.get('page')
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

    return render(request, 'forum/index.html', {'threads': threads, 'query': q, 'author_q': author, 'is_paginated': is_paginated})


@login_required
def create_thread(request):
    if not is_member(request.user):
        return HttpResponseForbidden('Only members can create threads')
    if request.method == 'POST':
        form = ThreadForm(request.POST, request.FILES)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.author = request.user
            # Save image if provided via form
            if form.cleaned_data.get('image'):
                thread.image = form.cleaned_data.get('image')
            thread.save()
            log_activity(request.user, ActivityLog.ACTION_THREAD_CREATE, 'thread', thread.id)
            return redirect('forum:index')
    else:
        form = ThreadForm()
    return render(request, 'forum/create_thread.html', {'form': form})


def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if thread.status == Thread.STATUS_DELETED:
        return HttpResponseForbidden('Thread not available')
    if not can_view_thread(request.user, thread):
        return HttpResponseForbidden('You cannot view this thread')
    # only top-level comments; replies are computed per comment below
    comments = thread.comments.filter(status=Comment.STATUS_PUBLISHED, parent__isnull=True).order_by('created_at')
    reply_to = request.GET.get('reply_to')
    # normalize reply_to to integer when possible so template comparisons work
    try:
        reply_to = int(reply_to) if reply_to is not None and reply_to != '' else None
    except (TypeError, ValueError):
        reply_to = None
    if request.method == 'POST':
        if not request.user.is_authenticated or not can_create_comment(request.user):
            return redirect('login')
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.thread = thread
            comment.author = request.user
            parent_id = request.POST.get('parent_id')
            if parent_id:
                try:
                    pid = int(parent_id)
                except (TypeError, ValueError):
                    pid = None
                if pid:
                    try:
                        parent = Comment.objects.get(pk=pid)
                        comment.parent = parent
                    except Comment.DoesNotExist:
                        pass
            if form.cleaned_data.get('image'):
                comment.image = form.cleaned_data.get('image')
            # require at least content or image
            content_val = form.cleaned_data.get('content')
            image_val = form.cleaned_data.get('image')
            if not content_val and not image_val:
                form.add_error(None, 'Please provide text or an image for the comment.')
                # preserve reply target so template can open correct inline form
                try:
                    reply_to = int(parent_id) if parent_id else None
                except (TypeError, ValueError):
                    reply_to = None
            else:
                comment.save()
                log_activity(request.user, ActivityLog.ACTION_COMMENT_CREATE, 'comment', comment.id)
                return redirect('forum:detail', thread_id=thread.id)
    else:
        form = CommentForm()

    # attach replies queryset to each top-level comment for template iteration
    for c in comments:
        c.replies_qs = c.replies.filter(status=Comment.STATUS_PUBLISHED).order_by('created_at')

    return render(request, 'forum/detail.html', {'thread': thread, 'comments': comments, 'form': form, 'reply_to': reply_to})


def delete_thread(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if not request.user.is_authenticated:
        return redirect('login')
    # allow author or moderator/admin to delete
    if not can_delete_thread(request.user, thread):
        return HttpResponseForbidden('Not allowed')
    if request.method == 'POST':
        thread.status = Thread.STATUS_DELETED
        thread.save()
        log_activity(request.user, ActivityLog.ACTION_THREAD_DELETE, 'thread', thread.id, target_user=thread.author)
        return redirect('forum:index')
    return HttpResponseForbidden('Only POST allowed')


def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    if not request.user.is_authenticated:
        return redirect('login')
    # allow author or moderator/admin to delete
    if not can_delete_comment(request.user, comment):
        return HttpResponseForbidden('Not allowed')
    if request.method == 'POST':
        thread_id = comment.thread.id
        comment.status = Comment.STATUS_DELETED
        comment.save()
        log_activity(request.user, ActivityLog.ACTION_COMMENT_DELETE, 'comment', comment.id, target_user=comment.author)
        # redirect back to thread detail
        return redirect('forum:detail', thread_id=thread_id)
    return HttpResponseForbidden('Only POST allowed')


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('forum:index')
    else:
        form = UserCreationForm()
    # Add form-control classes to signup fields for consistent styling
    for name, field in form.fields.items():
        field.widget.attrs.update({'class': 'form-control'})
    return render(request, 'registration/signup.html', {'form': form})
