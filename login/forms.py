"""
Authentication & User Management Forms
=======================================

Implements user signup, flexible username/email login, and password reset forms
with custom widget styling matching the central theme_config color scheme.

Security Note:
All form field cleaning uses Django's standard sanitization and validation,
enforcing minimum password lengths and character rules.
"""

from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import (
    UserCreationForm,
    PasswordResetForm,
    SetPasswordForm
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """
    User Registration (Signup) Form.
    Enforces unique email address, valid username format, and strong password policies.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'name@example.com',
            'class': 'form-input',
            'autocomplete': 'email',
        }),
        help_text=_("Required. Enter a valid email address.")
    )

    username = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Choose a username',
            'class': 'form-input',
            'autocomplete': 'username',
        })
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply theme-compatible CSS classes to password fields
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({
                'class': 'form-input',
                'placeholder': 'Create a strong password',
            })
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({
                'class': 'form-input',
                'placeholder': 'Confirm password',
            })

    def clean_username(self):
        """
        Allows non-unique usernames (multiple users can share the same username).
        """
        username = self.cleaned_data.get('username', '').strip()
        return username

    def clean_email(self):
        """
        Verifies that email is strictly unique across all users.
        """
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("A user with this email address already exists."))
        return email


class EmailOrUsernameLoginForm(forms.Form):
    """
    User Login Form supporting Username OR Email identification with Password.
    Supports non-unique usernames by checking password across matching username candidates.
    """
    login_identity = forms.CharField(
        label=_("Username or Email"),
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your username or email',
            'class': 'form-input',
            'autocomplete': 'username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'form-input',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label=_("Keep me signed in")
    )

    def clean(self):
        cleaned_data = super().clean()
        identity = cleaned_data.get('login_identity')
        password = cleaned_data.get('password')

        if identity and password:
            identity = identity.strip()
            self.user_cache = None

            # 1. Look up by exact email address
            users_by_email = User.objects.filter(email__iexact=identity)
            for user in users_by_email:
                if user.check_password(password):
                    self.user_cache = user
                    break

            # 2. If not matched by email, look up candidates by username
            if self.user_cache is None:
                users_by_username = User.objects.filter(username__iexact=identity)
                for user in users_by_username:
                    if user.check_password(password):
                        self.user_cache = user
                        break

            # 3. Fallback standard Django authenticate
            if self.user_cache is None:
                self.user_cache = authenticate(username=identity, password=password)

            if self.user_cache is None:
                raise ValidationError(
                    _("Invalid login credentials. Please check your username/email and password."),
                    code='invalid_login'
                )
            elif not self.user_cache.is_active:
                raise ValidationError(
                    _("This account is currently inactive."),
                    code='inactive'
                )

        return cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)


class Admin2FAForm(forms.Form):
    """
    Form for validating 6-digit OTP verification code during Admin 2FA login.
    """
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.HiddenInput(),
        error_messages={
            'required': _("Please enter the 6-digit verification code."),
            'min_length': _("The verification code must be exactly 6 digits."),
            'max_length': _("The verification code must be exactly 6 digits."),
        }
    )

    def clean_otp_code(self):
        code = self.cleaned_data.get('otp_code', '').strip()
        if not code.isdigit() or len(code) != 6:
            raise ValidationError(_("Verification code must consist of exactly 6 numbers."))
        return code


class CustomPasswordResetForm(PasswordResetForm):
    """
    Password Reset Email Request Form.
    """
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your account email address',
            'class': 'form-input',
            'autocomplete': 'email',
        })
    )


class CustomSetPasswordForm(SetPasswordForm):
    """
    Password Reset Confirmation / New Password Form.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['new_password1', 'new_password2']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'form-input',
                    'placeholder': 'Enter new password',
                })


from .models import Testimonial, ConsultationBooking

class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ['name', 'email', 'role', 'location', 'quote', 'rating', 'category', 'linkedin_url', 'avatar_file']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter your full name', 'required': True, 'aria-required': 'true', 'aria-label': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Enter your email address (for notification when published)', 'required': True, 'aria-required': 'true', 'aria-label': 'Email Address'}),
            'role': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Fintech Entrepreneur / Portfolio Manager', 'required': True, 'aria-required': 'true', 'aria-label': 'Professional Role'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Zurich, NY, Mumbai', 'required': True, 'aria-required': 'true', 'aria-label': 'City or Location'}),
            'quote': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Write your testimonial review here...', 'rows': 4, 'required': True, 'aria-required': 'true', 'aria-label': 'Testimonial Review'}),
            'rating': forms.Select(choices=[(5, '⭐⭐⭐⭐⭐ (5/5)'), (4, '⭐⭐⭐⭐ (4/5)'), (3, '⭐⭐⭐ (3/5)'), (2, '⭐⭐ (2/5)'), (1, '⭐ (1/5)')], attrs={'class': 'form-input', 'aria-label': 'Star Rating'}),
            'category': forms.Select(attrs={'class': 'form-input', 'aria-label': 'Category Group'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://linkedin.com/in/username (Optional)', 'aria-label': 'LinkedIn Profile URL'}),
            'avatar_file': forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/*', 'aria-label': 'Profile Photo Image'}),
        }


class ConsultationBookingForm(forms.ModelForm):
    class Meta:
        model = ConsultationBooking
        fields = [
            'client_name', 'email', 'phone', 'service', 
            'duration_minutes', 'consultation_date', 'consultation_time',
            'subject', 'message', 'preferred_comm'
        ]
        widgets = {
            'client_name': forms.TextInput(attrs={'class': 'consult-form-input', 'placeholder': 'e.g. Eleanor Vance', 'required': True, 'aria-required': 'true', 'aria-label': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'consult-form-input', 'placeholder': 'e.g. eleanor.vance@company.com', 'required': True, 'aria-required': 'true', 'aria-label': 'Email Address'}),
            'phone': forms.TextInput(attrs={'class': 'consult-form-input', 'placeholder': '+1 (555) 234-5678', 'required': True, 'aria-required': 'true', 'aria-label': 'Phone Number'}),
            'service': forms.Select(attrs={'class': 'consult-form-select', 'required': True, 'aria-required': 'true', 'aria-label': 'Advisory Service'}),
            'duration_minutes': forms.HiddenInput(),
            'consultation_date': forms.HiddenInput(),
            'consultation_time': forms.HiddenInput(),
            'subject': forms.TextInput(attrs={'class': 'consult-form-input', 'placeholder': 'e.g. Multi-Asset Portfolio Strategy & Trust Structuring', 'aria-label': 'Subject or Purpose of Consultation'}),
            'message': forms.Textarea(attrs={'class': 'consult-form-textarea', 'placeholder': 'Please share your financial objectives, portfolio scope, or specific topics for discussion...', 'rows': 4, 'aria-label': 'Specific Objectives and Requirements'}),
            'preferred_comm': forms.Select(attrs={'class': 'consult-form-select', 'aria-label': 'Preferred Communication Mode'}),
        }

    def clean_consultation_date(self):
        import datetime
        date = self.cleaned_data.get('consultation_date')
        if not date:
            raise ValidationError(_("Please select a consultation date on the calendar."))
        if date < datetime.date.today():
            raise ValidationError(_("Consultations cannot be scheduled on past dates."))
        if date.weekday() in (5, 6):
            raise ValidationError(_("Consultations are available Monday through Friday only."))
        return date

    def clean_consultation_time(self):
        time = self.cleaned_data.get('consultation_time')
        if not time:
            raise ValidationError(_("Please select an available time slot for your consultation."))
        return time

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('consultation_date')
        time = cleaned_data.get('consultation_time')
        duration = cleaned_data.get('duration_minutes') or 45

        if date and time:
            import datetime
            start_dt = datetime.datetime.combine(date, time)
            end_dt = start_dt + datetime.timedelta(minutes=duration)
            close_dt = datetime.datetime.combine(date, datetime.time(18, 0))
            open_dt = datetime.datetime.combine(date, datetime.time(9, 0))

            if start_dt < open_dt:
                raise ValidationError(_("Consultations cannot start before 9:00 AM."))
            if end_dt > close_dt:
                raise ValidationError(_("Consultations must conclude by 6:00 PM. Please select an earlier start time."))

            buffer_min = 15
            existing_bookings = ConsultationBooking.objects.filter(
                consultation_date=date
            ).exclude(status__in=['cancelled'])

            if self.instance and self.instance.pk:
                existing_bookings = existing_bookings.exclude(pk=self.instance.pk)

            for b in existing_bookings:
                b_start = datetime.datetime.combine(date, b.consultation_time)
                b_duration = b.duration_minutes or 45
                b_end = b_start + datetime.timedelta(minutes=b_duration)
                
                # Check for overlap taking 15 min gap into account
                if start_dt < (b_end + datetime.timedelta(minutes=buffer_min)) and (end_dt + datetime.timedelta(minutes=buffer_min)) > b_start:
                    raise ValidationError(_(f"The selected time slot ({time.strftime('%I:%M %p')}) overlaps with a scheduled consultation ({b.consultation_time.strftime('%I:%M %p')} - {b_end.strftime('%I:%M %p')}) or the required 15-minute buffer."))

        return cleaned_data


class BookingTrackingLookupForm(forms.Form):
    reference_key = forms.CharField(
        max_length=10,
        min_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'track-input-field',
            'placeholder': 'Enter 10-Character Key (e.g. GT7K4M9P2X)',
            'maxlength': '10',
            'autocomplete': 'off',
            'style': 'text-transform: uppercase;'
        })
    )

    def clean_reference_key(self):
        key = self.cleaned_data.get('reference_key', '').strip().upper()
        if len(key) != 10:
            raise ValidationError(_("Reference key must be exactly 10 characters."))
        return key



