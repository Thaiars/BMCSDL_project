from django.urls import path

from . import views

app_name = "forum"

urlpatterns = [
    path("", views.index, name="index"),
    path("threads/create/", views.create_thread, name="create_thread"),
    path("threads/<int:thread_id>/", views.thread_detail, name="detail"),
    path("threads/<int:thread_id>/delete/", views.delete_thread, name="delete_thread"),
    path(
        "comments/<int:comment_id>/delete/", views.delete_comment, name="delete_comment"
    ),
    path("accounts/signup/", views.signup, name="signup"),
    # User Profile URLs
    path("user/<str:username>/", views.user_profile, name="user_profile"),
    path("settings/account/", views.account_settings, name="account_settings"),
    path("settings/password/", views.password_change_view, name="password_change"),
]
