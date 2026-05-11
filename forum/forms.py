from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm

from .models import Comment, Thread, User


class ThreadForm(forms.ModelForm):
    """Form để tạo/sửa Thread"""

    class Meta:
        model = Thread
        fields = ["title", "content", "image"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Thread title"}
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Write your thread content...",
                }
            ),
        }


class CommentForm(forms.ModelForm):
    """Form để tạo/sửa Comment"""

    class Meta:
        model = Comment
        fields = ["content", "image"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Write a comment (optional)...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # allow image-only comments by making content optional on the form level
        self.fields["content"].required = False


class AccountSettingsForm(forms.ModelForm):
    """
    Form để cập nhật thông tin cá nhân của user
    Cho phép sửa: name, email, bio, avatar
    """

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
        help_text="Địa chỉ email của bạn",
    )

    class Meta:
        model = User
        fields = ["name", "email", "bio", "avatar"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Tên"}
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Viết một chút về bạn (tối đa 500 ký tự)...",
                    "maxlength": "500",
                }
            ),
            "avatar": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/png, image/jpeg, image/gif, image/webp",
                }
            ),
        }
        help_texts = {
            "name": "Tên của bạn",
            "bio": "Tiểu sử cá nhân (tối đa 500 ký tự)",
            "avatar": "Ảnh đại diện (PNG, JPEG, GIF, WebP)",
        }

    def clean_email(self):
        """
        Validate email: kiểm tra xem email đã được sử dụng bởi user khác chưa
        """
        email = self.cleaned_data.get("email")
        user_id = self.instance.id

        # Kiểm tra xem có user nào khác dùng email này không
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError(
                "Email này đã được sử dụng bởi người khác. Vui lòng chọn email khác."
            )
        return email

    def clean_bio(self):
        """
        Validate bio: kiểm tra độ dài
        """
        bio = self.cleaned_data.get("bio", "")
        if len(bio) > 500:
            raise forms.ValidationError(
                f"Tiểu sử không được vượt quá 500 ký tự. Hiện tại: {len(bio)} ký tự."
            )
        return bio


class AvatarUploadForm(forms.ModelForm):
    """
    Form chuyên biệt chỉ để upload avatar
    Đơn giản hơn AccountSettingsForm, chỉ tập trung vào avatar
    """

    class Meta:
        model = User
        fields = ["avatar"]
        widgets = {
            "avatar": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/png, image/jpeg, image/gif, image/webp",
                }
            ),
        }
        help_texts = {
            "avatar": "Chọn ảnh mới cho hồ sơ (PNG, JPEG, GIF, WebP)",
        }

    def clean_avatar(self):
        """
        Validate avatar: kiểm tra kích cỡ file
        Giới hạn: 5MB
        """
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            # Kiểm tra kích cỡ file (5MB = 5242880 bytes)
            if avatar.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    f"Kích cỡ ảnh không được vượt quá 5MB. Ảnh của bạn: {avatar.size / (1024 * 1024):.2f}MB"
                )
        return avatar


class CustomUserCreationForm(UserCreationForm):
    """
    Form đăng ký tài khoản mở rộng với email, name
    Tự động set role='member' khi signup
    Validate email không trùng
    """

    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "example@email.com",
                "autocomplete": "email",
            }
        ),
        help_text="Địa chỉ email của bạn (phải duy nhất)",
    )

    name = forms.CharField(
        required=False,
        label="Tên",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Tên của bạn",
                "autocomplete": "given-name",
            }
        ),
    )

    # last_name = forms.CharField(
    #     required=False,
    #     label="Họ",
    #     widget=forms.TextInput(
    #         attrs={
    #             "class": "form-control",
    #             "placeholder": "Họ của bạn",
    #             "autocomplete": "family-name",
    #         }
    #     ),
    # )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "name",
            # "last_name",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap CSS class to all fields
        for field_name, field in self.fields.items():
            if field_name not in ["email", "name"]:
                field.widget.attrs.update({"class": "form-control"})

        # Add help text cho username
        if "username" in self.fields:
            self.fields[
                "username"
            ].help_text = "Tối đa 150 ký tự. Chỉ chữ, số và @/./+/-/_"
            self.fields["username"].widget.attrs.update(
                {"placeholder": "Username của bạn", "autocomplete": "username"}
            )

        # Add help text cho password fields
        if "password1" in self.fields:
            self.fields["password1"].widget.attrs.update(
                {"placeholder": "Nhập mật khẩu", "autocomplete": "new-password"}
            )
        if "password2" in self.fields:
            self.fields["password2"].widget.attrs.update(
                {"placeholder": "Xác nhận mật khẩu", "autocomplete": "new-password"}
            )

    def clean_email(self):
        """
        Validate email: kiểm tra xem email đã được sử dụng chưa
        """
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Email này đã được đăng ký. Vui lòng sử dụng email khác hoặc "
                "<a href='/accounts/login/'>đăng nhập</a> nếu bạn đã có tài khoản."
            )
        return email

    def clean_username(self):
        """
        Validate username: thêm kiểm tra xem username đã được sử dụng chưa
        """
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "Username này đã tồn tại. Vui lòng chọn username khác."
            )
        return username

    def save(self, commit=True):
        """
        Save user và tự động set role='member'
        """
        user = super().save(commit=False)
        # Auto-set role to 'member' for new signups
        user.role = User.ROLE_MEMBER
        if commit:
            user.save()
        return user


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Form thay đổi mật khẩu với CSS class tùy chỉnh
    Thừa kế từ Django's PasswordChangeForm
    """

    old_password = forms.CharField(
        label="Mật khẩu hiện tại",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "current-password"}
        ),
    )
    new_password1 = forms.CharField(
        label="Mật khẩu mới",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        help_text="Mật khẩu phải đủ mạnh",
    )
    new_password2 = forms.CharField(
        label="Xác nhận mật khẩu mới",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
    )
