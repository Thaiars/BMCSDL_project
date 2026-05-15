from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_GUEST = "guest"
    ROLE_MEMBER = "member"
    ROLE_MODERATOR = "moderator"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES =[
        (ROLE_GUEST, "Guest"),
        (ROLE_MEMBER, "Member"),
        (ROLE_MODERATOR, "Moderator"),
        (ROLE_ADMIN, "Admin"),
    ]

    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, default="")
    name = models.CharField(max_length=255, blank=True, verbose_name="Tên hiển thị")

    class Meta:
        db_table = "auth_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def is_moderator(self):
        return self.role == self.ROLE_MODERATOR or self.is_staff or self.is_superuser

    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    def get_thread_count(self):
        return self.threads.filter(status=Thread.STATUS_PUBLISHED).count()

    def get_comment_count(self):
        return self.comments.filter(status=Comment.STATUS_PUBLISHED).count()

    def get_display_name(self):
        if self.name:
            return self.name
        return self.username

    def __str__(self):
        return self.get_display_name()


class Thread(models.Model):
    STATUS_PUBLISHED = "published"
    STATUS_HIDDEN = "hidden"
    STATUS_DELETED = "deleted"

    STATUS_CHOICES =[
        (STATUS_PUBLISHED, "Published"),
        (STATUS_HIDDEN, "Hidden"),
        (STATUS_DELETED, "Deleted"),
    ]

    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads"
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_PUBLISHED
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to="threads/", null=True, blank=True)
    is_removed_by_mod = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    @property
    def score(self):
        # Tính tổng điểm Vote
        return sum(vote.value for vote in self.votes.all())

    def soft_delete(self):
        self.status = self.STATUS_DELETED
        self.save()

    def __str__(self):
        return f"{self.title} ({self.author})"


class Comment(models.Model):
    STATUS_PUBLISHED = "published"
    STATUS_HIDDEN = "hidden"
    STATUS_DELETED = "deleted"

    STATUS_CHOICES =[
        (STATUS_PUBLISHED, "Published"),
        (STATUS_HIDDEN, "Hidden"),
        (STATUS_DELETED, "Deleted"),
    ]

    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField()
    image = models.ImageField(upload_to="comments/", null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_PUBLISHED
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="replies", on_delete=models.CASCADE
    )
    is_removed_by_mod = models.BooleanField(default=False)

    @property
    def score(self):
        return sum(vote.value for vote in self.votes.all())

    def soft_delete(self):
        self.status = self.STATUS_DELETED
        self.save()

    def __str__(self):
        return f"Comment by {self.author} on {self.thread_id}"


# --- BẢNG LƯU VOTE ---
class ThreadVote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='votes')
    value = models.SmallIntegerField() # 1: Upvote, -1: Downvote
    class Meta:
        unique_together = ('user', 'thread')

class CommentVote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='votes')
    value = models.SmallIntegerField()
    class Meta:
        unique_together = ('user', 'comment')


class Report(models.Model):
    TYPE_THREAD = "thread"
    TYPE_COMMENT = "comment"

    REPORT_TYPE_CHOICES =[
        (TYPE_THREAD, "Thread"),
        (TYPE_COMMENT, "Comment"),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports"
    )
    report_type = models.CharField(max_length=16, choices=REPORT_TYPE_CHOICES)
    object_id = models.PositiveIntegerField()
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Report {self.id} by {self.reporter}"


class ActivityLog(models.Model):
    ACTION_THREAD_CREATE = "thread_create"
    ACTION_THREAD_DELETE = "thread_delete"
    ACTION_THREAD_HIDE = "thread_hide"
    ACTION_COMMENT_CREATE = "comment_create"
    ACTION_COMMENT_DELETE = "comment_delete"
    ACTION_COMMENT_HIDE = "comment_hide"
    ACTION_USER_UPDATE = "user_update"
    ACTION_ROLE_CHANGE = "role_change"
    ACTION_REPORT_FILED = "report_filed"

    ACTION_CHOICES =[
        (ACTION_THREAD_CREATE, "Thread Created"),
        (ACTION_THREAD_DELETE, "Thread Deleted"),
        (ACTION_THREAD_HIDE, "Thread Hidden"),
        (ACTION_COMMENT_CREATE, "Comment Created"),
        (ACTION_COMMENT_DELETE, "Comment Deleted"),
        (ACTION_COMMENT_HIDE, "Comment Hidden"),
        (ACTION_USER_UPDATE, "User Info Updated"),
        (ACTION_ROLE_CHANGE, "User Role Changed"),
        (ACTION_REPORT_FILED, "Report Filed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="target_activity_logs",
    )
    target_type = models.CharField(
        max_length=32, blank=True
    )
    target_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.JSONField(
        default=dict, blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes =[
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.created_at.isoformat()} - {self.user} - {self.get_action_display()}"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Thread)
def log_thread_activity(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.author,
            action=ActivityLog.ACTION_THREAD_CREATE,
            target_type="thread",
            target_id=instance.id,
        )

@receiver(post_save, sender=Comment)
def log_comment_activity(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.author,
            action=ActivityLog.ACTION_COMMENT_CREATE,
            target_type="comment",
            target_id=instance.id,
        )
