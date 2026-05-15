from django.urls import path
from . import views

app_name = "forum"

urlpatterns =[
    path("", views.index, name="index"),
    path("threads/create/", views.create_thread, name="create_thread"),
    path("threads/<int:thread_id>/", views.thread_detail, name="detail"),
    path("threads/<int:thread_id>/edit/", views.edit_thread, name="edit_thread"),
    path("threads/<int:thread_id>/delete/", views.delete_thread, name="delete_thread"),
    path("threads/<int:thread_id>/pin/", views.toggle_pin_thread, name="toggle_pin_thread"),
    path("comments/<int:comment_id>/delete/", views.delete_comment, name="delete_comment"),

    # Vote API
    path("api/vote/", views.vote_api, name="vote_api"),

    # Reports
    path("report/create/", views.create_report, name="create_report"),

    # Mod Dashboard
    path("mod/", views.mod_dashboard, name="mod_dashboard"),
    path("mod/report/<int:report_id>/resolve/", views.resolve_report, name="resolve_report"),

    path("accounts/signup/", views.signup, name="signup"),
    path("user/<str:username>/", views.user_profile, name="user_profile"),
    path("settings/account/", views.account_settings, name="account_settings"),
    path("settings/password/", views.password_change_view, name="password_change"),
]
