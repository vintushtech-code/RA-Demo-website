"""
Authentication Views & Workflows
=================================

Contains all standard and social OAuth authentication views:
- User Signup
- User Login (Username/Email)
- User Logout
- Password Reset via Email
- Social Auth (Google, GitHub, Facebook)
- Authenticated User Main Home Page (home.html)
- Authenticated User Dashboard
"""

import os
import uuid
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.forms import AdminAuthenticationForm
from django.template.response import TemplateResponse
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import FormView, TemplateView
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY

from .forms import (
    CustomUserCreationForm,
    EmailOrUsernameLoginForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    Admin2FAForm
)
from .security import rate_limit, sanitize_input
from .tokens import password_reset_token_generator
from .two_factor import (
    send_2fa_otp,
    verify_2fa_otp,
    can_resend_otp,
    clear_2fa_session,
    OTP_EXPIRY_SECONDS
)

User = get_user_model()


# --------------------------------------------------------------------------
# 1. User Registration (Signup)
# --------------------------------------------------------------------------
@method_decorator(rate_limit(key_type='ip', limit=10, period=60), name='dispatch')
class SignupView(FormView):
    """
    Handles user signup with automatic login upon success.
    Enforces rate-limiting to prevent automated account creation spam.
    """
    template_name = 'login/signup.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login:home')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('login:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Save user using ORM
        user = form.save(commit=False)
        user.auth_provider = 'email'
        user.save()

        # Log user in immediately
        login(self.request, user)
        return super().form_valid(form)


# --------------------------------------------------------------------------
# 2. User Login & Admin 2-Way Verification Entry
# --------------------------------------------------------------------------
@method_decorator(rate_limit(key_type='ip', limit=8, period=60), name='dispatch')
class LoginView(FormView):
    """
    Handles user authentication via Username or Email + Password.
    For Administrator / Staff accounts, enforces a 2-Way Verification Passcode.
    Rate-limited against brute-force attacks.
    """
    template_name = 'login/login.html'
    form_class = EmailOrUsernameLoginForm
    success_url = reverse_lazy('admin:index')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('admin:index')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        remember_me = form.cleaned_data.get('remember_me')
        raw_next = self.request.GET.get('next')
        admin_index = reverse('admin:index')
        redirect_to = raw_next if (raw_next and raw_next.startswith(admin_index)) else admin_index

        # Check if 2FA is required for Admin / Staff Users
        admin_2fa_enabled = getattr(settings, 'ADMIN_2FA_ENABLED', True)
        if admin_2fa_enabled and (user.is_staff or user.is_superuser):
            # Store pre-2FA state in session (ensure strings for JSON session serializer)
            self.request.session['pre_2fa_remember_me'] = bool(remember_me)
            self.request.session['pre_2fa_next'] = str(redirect_to)
            send_2fa_otp(user, self.request)
            messages.info(self.request, f"2-Way Verification code generated for {user.username}! Check terminal output or email.")
            return redirect('login:admin_2fa_verify')

        # Standard Client Login
        login(self.request, user)

        if not remember_me:
            # Session expires on browser closure if remember_me is not checked
            self.request.session.set_expiry(0)
        else:
            # Session persists for 14 days
            self.request.session.set_expiry(1209600)

        return redirect(redirect_to)


# --------------------------------------------------------------------------
# 2.1 Admin 2-Way Verification (2FA) Workflows
# --------------------------------------------------------------------------
@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
@method_decorator(rate_limit(key_type='ip', limit=10, period=60), name='dispatch')
class Admin2FAVerifyView(FormView):
    """
    Renders 6-digit OTP verification screen for Administrator accounts
    and handles OTP validation to finalize session login.
    """
    template_name = 'login/admin_2fa_verify.html'
    form_class = Admin2FAForm

    def dispatch(self, request, *args, **kwargs):
        pre_user_id = request.session.get('pre_2fa_user_id')
        
        # If there is an active 2FA verification in progress, proceed to 2FA screen
        if pre_user_id:
            return super().dispatch(request, *args, **kwargs)

        # If already fully authenticated as staff/superuser with no pending 2FA, go to admin
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return redirect('admin:index')

        messages.warning(request, "No active 2FA login session found. Please sign in.")
        return redirect('admin:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pre_user_id = self.request.session.get('pre_2fa_user_id')
        target_user = User.objects.filter(pk=pre_user_id).first()

        configured_email = getattr(settings, 'ADMIN_2FA_EMAIL', '').strip()
        target_email = configured_email if configured_email else (target_user.email if target_user else '')

        context['target_user'] = target_user
        context['target_email'] = target_email
        context['expiry_seconds'] = OTP_EXPIRY_SECONDS
        return context

    def form_valid(self, form):
        submitted_code = form.cleaned_data.get('otp_code')
        is_valid, error_msg = verify_2fa_otp(self.request, submitted_code)

        if not is_valid:
            context = self.get_context_data()
            context['error'] = error_msg
            return render(self.request, self.template_name, context)

        # 2FA Verification Successful! Finalize Authentication
        pre_user_id = self.request.session.get('pre_2fa_user_id')
        remember_me = self.request.session.get('pre_2fa_remember_me', False)
        redirect_to = self.request.session.get('pre_2fa_next')

        user = User.objects.filter(pk=pre_user_id).first()
        if not user or not user.is_active:
            clear_2fa_session(self.request)
            messages.error(self.request, "Account is inactive or invalid.")
            return redirect('admin:login')

        login(self.request, user)
        clear_2fa_session(self.request)

        if not remember_me:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(1209600)

        messages.success(self.request, f"Welcome back, Administrator {user.get_display_name()}! 2-Way Verification successful.")
        
        # Enforce that Admin/Staff ALWAYS lands directly on the Django Admin Portal
        admin_index_url = reverse('admin:index')
        if not redirect_to or redirect_to in ['/', '/home/', '/login/', '/admin/', reverse('login:home')] or not str(redirect_to).startswith(admin_index_url):
            redirect_to = admin_index_url

        return redirect(redirect_to)

    def form_invalid(self, form):
        context = self.get_context_data()
        context['error'] = "Please enter a valid 6-digit numeric verification code."
        return render(self.request, self.template_name, context)


@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class Admin2FAResendView(View):
    """
    Handles requests to regenerate and resend the 6-digit OTP code with 30s cooldown protection.
    """
    def post(self, request, *args, **kwargs):
        pre_user_id = request.session.get('pre_2fa_user_id')
        if not pre_user_id:
            messages.error(request, "Session expired. Please sign in again.")
            return redirect('admin:login')

        user = User.objects.filter(pk=pre_user_id).first()
        if not user:
            clear_2fa_session(request)
            return redirect('admin:login')

        can_resend, wait_sec = can_resend_otp(request)
        if not can_resend:
            messages.warning(request, f"Please wait {wait_sec} seconds before requesting a new verification code.")
            return redirect('login:admin_2fa_verify')

        send_2fa_otp(user, request, is_resend=True)
        messages.success(request, "A fresh 2-Way Verification code has been printed to the terminal and dispatched to email!")
        return redirect('login:admin_2fa_verify')


@sensitive_post_parameters()
@csrf_protect
@never_cache
def admin_2fa_login(request, extra_context=None):
    """
    Custom Django Admin login handler that seamlessly enforces 2-Way Verification (2FA).
    
    1. If user is already authenticated as staff, redirects to the Admin Dashboard.
    2. Displays the Executive Admin login portal (templates/admin/login.html).
    3. When valid credentials are submitted:
       - If ADMIN_2FA_ENABLED is True:
         - Clears any previous user session keys safely without CSRF cookie mismatch.
         - Saves destination URL in session ('pre_2fa_next') pointing strictly to Django Admin.
         - Triggers 2FA OTP generation and terminal/email dispatch (send_2fa_otp).
         - Redirects to the 2FA OTP verification screen (/verify-2fa/).
       - If ADMIN_2FA_ENABLED is False:
         - Directly authenticates the user into the Admin Portal.
    """
    from django.contrib import admin
    admin_index_url = reverse('admin:index')
    
    # If already logged in as a valid staff/admin user AND not mid-2FA
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser) and not request.session.get('pre_2fa_user_id'):
        return redirect(admin_index_url)

    raw_next = request.POST.get('next') or request.GET.get('next')
    redirect_to = raw_next if (raw_next and raw_next.startswith(admin_index_url)) else admin_index_url

    if request.method == 'POST':
        form = AdminAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            admin_2fa_enabled = getattr(settings, 'ADMIN_2FA_ENABLED', True)
            if admin_2fa_enabled:
                # Flush existing auth session keys safely without rotating CSRF token
                for k in (SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY):
                    request.session.pop(k, None)

                request.session['pre_2fa_remember_me'] = True
                request.session['pre_2fa_next'] = str(redirect_to)
                send_2fa_otp(user, request)
                messages.info(request, f"2-Way Verification code generated for {user.username}! Check terminal output.")
                return redirect('login:admin_2fa_verify')
            else:
                login(request, user)
                return redirect(redirect_to)
    else:
        form = AdminAuthenticationForm(request)

    context = {
        'title': 'Log in',
        'form': form,
        'app_path': request.get_full_path(),
        'username': request.user.get_username(),
        'next': redirect_to,
        'has_permission': admin.site.has_permission(request),
        **(extra_context or {}),
    }
    return TemplateResponse(request, 'admin/login.html', context)



# --------------------------------------------------------------------------
# 3. User Logout
# --------------------------------------------------------------------------
class LogoutView(View):
    """
    Securely terminates the active staff/admin user session on POST request.
    """
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            messages.info(request, "You have been logged out successfully.")
        return redirect('login:home')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            messages.info(request, "You have been logged out successfully.")
        return redirect('login:home')


# --------------------------------------------------------------------------
# 4. Password Reset Workflow via Email
# --------------------------------------------------------------------------
@method_decorator(rate_limit(key_type='ip', limit=5, period=120), name='dispatch')
class CustomPasswordResetView(PasswordResetView):
    template_name = 'login/password_reset.html'
    form_class = CustomPasswordResetForm
    email_template_name = 'login/password_reset_email.html'
    subject_template_name = 'login/password_reset_subject.txt'
    success_url = reverse_lazy('login:password_reset_done')
    token_generator = password_reset_token_generator


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'login/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'login/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('login:password_reset_complete')
    token_generator = password_reset_token_generator


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'login/password_reset_complete.html'


# --------------------------------------------------------------------------
# 5. Social OAuth Authentication (Google, GitHub, Facebook)
# --------------------------------------------------------------------------
class SocialAuthInitView(View):
    def get(self, request, provider, *args, **kwargs):
        provider = provider.lower()
        if provider not in ['google', 'github', 'facebook']:
            messages.error(request, "Unsupported social authentication provider.")
            return redirect('login:login')

        env_client_id = os.environ.get(f"{provider.upper()}_CLIENT_ID")

        if not env_client_id:
            mock_email = f"user_{provider}_{uuid.uuid4().hex[:6]}@example.com"
            mock_username = f"{provider}_user_{uuid.uuid4().hex[:4]}"
            
            user, created = User.objects.get_or_create(
                email=mock_email,
                defaults={
                    'username': mock_username,
                    'auth_provider': provider,
                    'avatar_url': f"https://api.dicebear.com/7.x/avataaars/svg?seed={mock_username}",
                }
            )
            login(request, user)
            return redirect('login:home')

        oauth_urls = {
            'google': f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={env_client_id}&redirect_uri={request.build_absolute_uri(reverse('login:social_callback', kwargs={'provider': 'google'}))}&scope=openid%20profile%20email",
            'github': f"https://github.com/login/oauth/authorize?client_id={env_client_id}&redirect_uri={request.build_absolute_uri(reverse('login:social_callback', kwargs={'provider': 'github'}))}&scope=user:email",
            'facebook': f"https://www.facebook.com/v18.0/dialog/oauth?client_id={env_client_id}&redirect_uri={request.build_absolute_uri(reverse('login:social_callback', kwargs={'provider': 'facebook'}))}&scope=email,public_profile",
        }
        return redirect(oauth_urls[provider])


class SocialAuthCallbackView(View):
    def get(self, request, provider, *args, **kwargs):
        code = request.GET.get('code')
        if not code:
            messages.error(request, "OAuth authentication failed or was cancelled.")
            return redirect('login:login')

        messages.info(request, f"Social authentication callback processed for {provider.capitalize()}.")
        return redirect('login:home')


# --------------------------------------------------------------------------
# 6. Finance Advisory Landing & Main Home Page (home.html)
# --------------------------------------------------------------------------
class HomeView(TemplateView):
    """
    Public Finance Advisory Landing Page & Member Command Center (home.html).
    Accessible to both visitors (guests) and logged-in members.
    """
    template_name = 'login/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user
        context['page_title'] = "GuardianTree FP — Wealth & Institutional Advisory"
        
        try:
            from contactform.forms import ContactForm
            context['contact_form'] = ContactForm()
        except Exception:
            context['contact_form'] = None

        # Fetch FAQs from database only - NO AUTO-SEEDING
        try:
            from .models import FAQ
            faqs = FAQ.objects.filter(is_active=True).order_by('order', 'created_at')[:6]
            context['faqs'] = faqs
            context['has_faqs'] = faqs.exists()
        except Exception:
            context['faqs'] = []
            context['has_faqs'] = False

        # Fetch Top 3 Active Testimonials from database only
        try:
            from .models import Testimonial, MediaMention, PartnerIntegration, MarketResource
            testimonials = list(Testimonial.objects.filter(is_active=True).order_by('order', '-rating')[:3])
            context['testimonials'] = testimonials
            context['has_testimonials'] = bool(testimonials)
            
            context['media_mentions'] = MediaMention.objects.filter(is_active=True).order_by('order', '-created_at')
            context['partners'] = PartnerIntegration.objects.filter(is_active=True).order_by('order', '-created_at')

            # Seed default MarketResources if table is empty
            if not MarketResource.objects.exists():
                MarketResource.objects.create(
                    title="Q4 Macroeconomic Equity Outlook & Yield Curves",
                    category_badge="Market Insight",
                    description="Explore how changing interest rates impact equity valuations and fixed-income strategies across global markets.",
                    meta_reading_time="📖 12 Min Read",
                    meta_topic="Macro Analysis Q4 2026",
                    image_url_fallback="login/images/market_intel_equity.jpg",
                    is_coming_soon=True,
                    button_text="Coming Soon ⏳",
                    order=1
                )
                MarketResource.objects.create(
                    title="The Blueprint for Tax-Advantaged Corporate Treasury",
                    category_badge="Whitepaper",
                    description="A deep dive into optimizing liquidity buffers while minimizing corporate tax drag and mitigating currency exposure.",
                    meta_reading_time="📄 PDF Whitepaper",
                    meta_topic="Corporate Liquidity",
                    image_url_fallback="login/images/market_intel_treasury.jpg",
                    is_coming_soon=True,
                    button_text="Coming Soon ⏳",
                    order=2
                )
                MarketResource.objects.create(
                    title="Structuring Your Family Office: 2026 Edition",
                    category_badge="Executive Guide",
                    description="Master class on setting up private trusts, legacy planning, and multi-generational wealth transfer architecture.",
                    meta_reading_time="🏛️ Master Guide",
                    meta_topic="Estate & Legacy Planning",
                    image_url_fallback="login/images/market_intel_family_office.jpg",
                    is_coming_soon=True,
                    button_text="Coming Soon ⏳",
                    order=3
                )

            context['market_resources'] = MarketResource.objects.filter(is_published=True).order_by('order', '-created_at')
        except Exception:
            context['testimonials'] = []
            context['has_testimonials'] = False
            context['media_mentions'] = []
            context['partners'] = []
            context['market_resources'] = []



        return context

    def post(self, request, *args, **kwargs):
        """Allows updating profile bio safely for logged in users."""
        if not request.user.is_authenticated:
            return redirect('login:login')

        bio = request.POST.get('bio', '')
        sanitized_bio = sanitize_input(bio)
        
        user = request.user
        user.bio = sanitized_bio
        user.save(update_fields=['bio', 'updated_at'])

        messages.success(request, "Your profile bio has been updated successfully!")
        return redirect('login:home')
# --------------------------------------------------------------------------
# 7. About Us Page
# --------------------------------------------------------------------------
class AboutView(TemplateView):
    """
    Publicly accessible About Us page (about.html).
    """
    template_name = 'login/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "About Us — GuardianTree FP"
        
        # Fetch active team members directly from database (COMMENTED OUT: Team section disabled)
        # try:
        #     from .models import TeamMember
        #     if not TeamMember.objects.exists():
        #         initial_members = [
        #             {
        #                 "name": "Sabin Balan",
        #                 "role": "Founder & Managing Partner",
        #                 "order": 1,
        #                 "image": "sabin_balan_3.png"
        #             },
        #             {
        #                 "name": "Vikram Malhotra",
        #                 "role": "Chief Investment Officer",
        #                 "order": 2,
        #                 "image": "avatar_leader2.png"
        #             },
        #             {
        #                 "name": "Anjali Rao",
        #                 "role": "Head of Wealth Management",
        #                 "order": 3,
        #                 "image": "avatar_leader3.png"
        #             },
        #             {
        #                 "name": "Devendra Singh",
        #                 "role": "Fiduciary Tax Advisor",
        #                 "order": 4,
        #                 "image": "avatar_leader4.png"
        #             },
        #             {
        #                 "name": "Meera Sen",
        #                 "role": "Senior Portfolio Manager",
        #                 "order": 5,
        #                 "image": "avatar_emily.png"
        #             }
        #         ]
        #         for item in initial_members:
        #             TeamMember.objects.create(**item)
        #     
        #     context['team_members'] = TeamMember.objects.filter(is_active=True).order_by('order', 'name')
        # except Exception:
        #     context['team_members'] = []
        context['team_members'] = []

        return context




# --------------------------------------------------------------------------
# 8. Services Page
# --------------------------------------------------------------------------
class ServicesView(TemplateView):
    """
    Publicly accessible Services page (services.html).
    """
    template_name = 'login/services.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Our Advisory Services — GuardianTree FP"
        return context


# --------------------------------------------------------------------------
# 9. Testimonials Page
# --------------------------------------------------------------------------
class TestimonialsView(View):
    """
    Publicly accessible Testimonials page (testimonials.html).
    Renders an interactive leaders community UI and handles user review submissions.
    """
    template_name = 'login/testimonials.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        from .forms import TestimonialForm
        form = TestimonialForm(request.POST, request.FILES)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.is_active = False  # Requires administrator review
            if not testimonial.avatar_file:
                # Set blank so initials template badge is rendered
                testimonial.avatar_image = ""
            testimonial.save()
            try:
                from .emails import send_testimonial_email
                send_testimonial_email(testimonial)
            except Exception as e:
                logger.error(f"Error dispatching testimonial notification: {e}")
            messages.success(request, "Thank you! Your testimonial has been submitted successfully. Our fiduciary desk will review it shortly, and you will receive an email confirmation once it is published live.")
            return redirect('login:testimonials')
        
        context = self.get_context_data()
        context['testimonial_form'] = form
        messages.error(request, "There was an error in your submission. Please check the fields and try again.")
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        context = {}
        context['page_title'] = "Client Testimonials — GuardianTree FP"
        from .forms import TestimonialForm
        context['testimonial_form'] = TestimonialForm()
        
        try:
            from .models import Testimonial
            
            # Get only active testimonials ordered by rating and creation date
            testimonials_list = list(
                Testimonial.objects.filter(is_active=True)
                .order_by('-rating', '-created_at')  # Show highest rated first, then newest
            )
            
            context['testimonials'] = testimonials_list
            
            # Check if there are any testimonials
            if testimonials_list:
                # Distribute testimonials into 9 columns for masonry layout
                cols = [[] for _ in range(9)]
                for idx, item in enumerate(testimonials_list):
                    cols[idx % 9].append(item)
                context['testimonials_cols'] = cols
                context['has_testimonials'] = True
            else:
                # No testimonials available
                context['testimonials_cols'] = [[] for _ in range(9)]
                context['has_testimonials'] = False
                context['no_testimonials_message'] = "No client testimonials available at the moment. Be the first to share your experience!"
                
        except Exception as e:
            context['testimonials'] = []
            context['testimonials_cols'] = [[] for _ in range(9)]
            context['has_testimonials'] = False
            context['no_testimonials_message'] = "Testimonials are currently unavailable. Please check back later."

        return context
# --------------------------------------------------------------------------
# 10. Private Wealth Consultation Booking & Tracking Flow
# --------------------------------------------------------------------------
import datetime
from django.http import JsonResponse
from django.utils import timezone


class ConsultationView(View):
    """
    Dedicated Private Wealth Management Consultation Booking Page (consultation.html).
    Renders luxury two-column scheduling dashboard, handles booking requests,
    generates 10-character alphanumeric reference keys, and supports live tracking lookup.
    """
    template_name = 'login/consultation.html'

    def _seed_sample_bookings(self):
        """Auto-seeds initial sample bookings if empty for immediate tracking demonstrations."""
        try:
            from .models import ConsultationBooking
            if ConsultationBooking.objects.count() == 0:
                today = datetime.date.today()
                # Calculate next Tuesday and Wednesday
                days_ahead = (1 - today.weekday()) % 7  # Next Tuesday
                if days_ahead == 0:
                    days_ahead = 7
                next_tuesday = today + datetime.timedelta(days=days_ahead)
                next_wednesday = next_tuesday + datetime.timedelta(days=1)
                last_week = today - datetime.timedelta(days=7)

                # Sample 1: The flagship reference key from prompt (GT7K4M9P2X)
                ConsultationBooking.objects.create(
                    reference_key="GT7K4M9P2X",
                    client_name="Eleanor Vance",
                    email="eleanor.vance@vancestrategies.com",
                    phone="+1 (555) 782-9014",
                    service="investment",
                    duration_minutes=45,
                    consultation_date=next_tuesday,
                    consultation_time=datetime.time(10, 0),
                    end_time=datetime.time(10, 45),
                    subject="Multi-Asset Strategic Asset Allocation & Family Office Advisory",
                    message="Discussing sovereign bond hedging, direct private equity allocations, and wealth preservation frameworks.",
                    preferred_comm="video_call",
                    status="confirmed",
                    payment_status="completed",
                    admin_notes="Assigned to Vikram Malhotra (CIO). Client portfolio scope > $15M."
                )

                # Sample 2: Rescheduled booking with clear previous vs updated schedule comparison
                ConsultationBooking.objects.create(
                    reference_key="BF3N8Q1Z7Y",
                    client_name="Alexander Morgan",
                    email="a.morgan@morganholdings.co",
                    phone="+44 20 7946 0912",
                    service="wealth_management",
                    duration_minutes=60,
                    consultation_date=next_wednesday,
                    consultation_time=datetime.time(11, 0),
                    end_time=datetime.time(12, 0),
                    previous_date=next_tuesday,
                    previous_time=datetime.time(10, 0),
                    rescheduled_reason="Rescheduled by Managing Partner to incorporate updated Q3 fiscal macroeconomic audit reports.",
                    subject="Global Estate & Cross-Border Wealth Transfer Structuring",
                    message="Structuring revocable trusts and multi-jurisdiction capital shielding.",
                    preferred_comm="in_person",
                    status="rescheduled",
                    payment_status="completed",
                    admin_notes="Rescheduled with client consent. Boardroom 4A booked."
                )

                # Sample 3: Newly received consultation request
                ConsultationBooking.objects.create(
                    reference_key="PW9K2M4X7V",
                    client_name="David Sterling",
                    email="david.sterling@sterlingcap.org",
                    phone="+1 (555) 438-1192",
                    service="financial_planning",
                    duration_minutes=30,
                    consultation_date=next_tuesday,
                    consultation_time=datetime.time(14, 0),
                    end_time=datetime.time(14, 30),
                    subject="Retirement & Fixed Income Liquidity Strategy",
                    message="Evaluating tax-sheltered annuities and sovereign gold allocation limits.",
                    preferred_comm="video_call",
                    status="received",
                    payment_status="pending",
                    admin_notes="Under initial fiduciary suitability review."
                )
        except Exception:
            pass

    def get(self, request, *args, **kwargs):
        self._seed_sample_bookings()
        from .forms import ConsultationBookingForm, BookingTrackingLookupForm
        from .models import ConsultationBooking

        # Determine default consultation date (Next Business Day: Mon-Fri)
        today = datetime.date.today()
        default_date = today + datetime.timedelta(days=1)
        while default_date.weekday() in (5, 6):  # Skip Sat, Sun
            default_date += datetime.timedelta(days=1)

        # Check if reference key was queried via GET parameter
        lookup_key = request.GET.get('key', '').strip().upper()
        confirmed_key = request.GET.get('confirmed_key', '').strip().upper()
        
        tracked_booking = None
        if lookup_key:
            tracked_booking = ConsultationBooking.objects.filter(reference_key=lookup_key).first()
        elif confirmed_key:
            tracked_booking = ConsultationBooking.objects.filter(reference_key=confirmed_key).first()

        effective_key = lookup_key or confirmed_key

        booking_form = ConsultationBookingForm(initial={
            'consultation_date': default_date,
            'duration_minutes': 45,
            'service': 'investment',
            'preferred_comm': 'video_call',
        })
        track_form = BookingTrackingLookupForm(initial={'reference_key': effective_key})

        context = {
            'page_title': 'Book Your Consultation — Private Wealth Advisory | GuardianTree FP',
            'booking_form': booking_form,
            'track_form': track_form,
            'default_date': default_date.strftime('%Y-%m-%d'),
            'default_date_display': default_date.strftime('%A, %d %B %Y'),
            'default_duration': 45,
            'tracked_booking': tracked_booking,
            'lookup_key': effective_key,
            'confirmed_key': confirmed_key,
            'service_choices': ConsultationBooking.SERVICE_CHOICES,
            'duration_choices': ConsultationBooking.DURATION_CHOICES,
            'comm_choices': ConsultationBooking.COMM_CHOICES,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self._seed_sample_bookings()
        from .forms import ConsultationBookingForm, BookingTrackingLookupForm
        from .models import ConsultationBooking

        action = request.POST.get('form_action', 'book')
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'

        if action == 'track':
            key = request.POST.get('reference_key', '').strip().upper()
            tracked_booking = ConsultationBooking.objects.filter(reference_key=key).first()
            if is_ajax:
                if tracked_booking:
                    return JsonResponse({
                        'status': 'success',
                        'data': self._serialize_booking(tracked_booking)
                    })
                return JsonResponse({
                    'status': 'error',
                    'message': f"No consultation found for reference key '{key}'. Please verify your 10-character key."
                }, status=404)
            
            # Non-AJAX fallback
            return redirect(f"{reverse('login:consultation')}?key={key}#track-section")

        # Booking submission flow
        form = ConsultationBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.ip_address = request.META.get('REMOTE_ADDR')
            booking.status = 'received'
            booking.payment_status = 'pending'
            booking.save()

            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'reference_key': booking.reference_key,
                    'client_name': booking.client_name,
                    'email': booking.email,
                    'service': booking.get_service_display(),
                    'duration': booking.duration_minutes,
                    'duration_label': booking.duration_label,
                    'date': booking.consultation_date.strftime("%A, %d %B %Y"),
                    'time': booking.consultation_time.strftime("%I:%M %p"),
                    'end_time': booking.end_time.strftime("%I:%M %p") if booking.end_time else "",
                    'message': f"Your consultation request has been successfully registered under reference key #{booking.reference_key}.",
                    'data': self._serialize_booking(booking)
                })

            messages.success(request, f"Your consultation has been booked! Your reference key is #{booking.reference_key}.")
            return redirect(f"{reverse('login:consultation')}?confirmed_key={booking.reference_key}#confirmation-card")

        # Form Errors
        if is_ajax:
            errors_dict = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            return JsonResponse({
                'status': 'error',
                'errors': errors_dict,
                'message': "Please correct the highlighted fields and select an available time slot."
            }, status=400)

        try:
            default_duration = int(request.POST.get('duration_minutes', 45))
        except (ValueError, TypeError):
            default_duration = 45

        messages.error(request, "There was an error in your consultation booking. Please select a valid date and time slot.")
        context = {
            'page_title': 'Book Your Consultation — Private Wealth Advisory | GuardianTree FP',
            'booking_form': form,
            'track_form': BookingTrackingLookupForm(),
            'default_date': request.POST.get('consultation_date', ''),
            'default_duration': default_duration,
            'lookup_key': '',
            'confirmed_key': None,
            'tracked_booking': None,
            'service_choices': ConsultationBooking.SERVICE_CHOICES,
            'duration_choices': ConsultationBooking.DURATION_CHOICES,
            'comm_choices': ConsultationBooking.COMM_CHOICES,
        }
        return render(request, self.template_name, context)

    def _serialize_booking(self, b):
        return {
            'reference_key': b.reference_key,
            'client_name': b.client_name,
            'email': b.email,
            'phone': b.phone,
            'service': b.get_service_display(),
            'duration_minutes': b.duration_minutes,
            'duration_label': b.duration_label,
            'consultation_date': b.consultation_date.strftime("%A, %d %B %Y"),
            'consultation_time': b.consultation_time.strftime("%I:%M %p"),
            'end_time': b.end_time.strftime("%I:%M %p") if b.end_time else "",
            'preferred_comm': b.get_preferred_comm_display(),
            'fee_amount': float(b.fee_amount or 5000.00),
            'fee_display': f"₹{b.fee_amount:,.2f}",
            'discount_amount': float(b.discount_amount or 0.00),
            'discount_display': f"₹{b.discount_amount:,.2f}",
            'net_amount': float(b.net_amount or 5000.00),
            'net_display': f"₹{b.net_amount:,.2f}",
            'invoice_number': b.invoice_number or f"INV-2026-{b.reference_key[:6]}",
            'payment_status': b.get_payment_status_display(),
            'payment_status_code': b.payment_status,
            'payment_badge': b.payment_badge_class,
            'payment_method': b.payment_method,
            'transaction_id': b.transaction_id,
            'fiduciary_desk': b.fiduciary_desk or "Senior Wealth Advisory & Fiduciary Desk",
            'meeting_link': b.meeting_link,
            'client_instructions': b.client_instructions,
            'status': b.status,
            'status_label': b.get_status_display(),
            'status_badge': b.status_badge_class,
            'is_rescheduled': b.status == 'rescheduled' or bool(b.previous_date),
            'previous_date': b.previous_date.strftime("%A, %d %B %Y") if b.previous_date else "",
            'previous_time': b.previous_time.strftime("%I:%M %p") if b.previous_time else "",
            'previous_schedule': f"{b.previous_date.strftime('%A, %d %B %Y')} — {b.previous_time.strftime('%I:%M %p')}" if b.previous_date and b.previous_time else "",
            'updated_schedule': f"{b.consultation_date.strftime('%A, %d %B %Y')} — {b.consultation_time.strftime('%I:%M %p')}",
            'rescheduled_reason': b.rescheduled_reason,
            'subject': b.subject,
            'message': b.message,
            'created_at': b.created_at.strftime("%d %B %Y at %I:%M %p"),
        }


class ConsultationSlotsAPIView(View):
    """
    Dynamic Time Slot Calculation API.
    Calculates exact available slots between 09:00 AM and 06:00 PM (Monday-Friday)
    respecting:
    - Selected duration (30, 45, 60 minutes)
    - 15-minute mandatory buffer between meetings
    - Existing database bookings
    - Past time cutoff if querying today
    - Hard stop at 6:00 PM (no consultation extends beyond 18:00)
    """
    def get(self, request, *args, **kwargs):
        from .models import ConsultationBooking

        date_str = request.GET.get('date')
        try:
            duration = int(request.GET.get('duration', 45))
            if duration not in (30, 45, 60):
                duration = 45
        except (ValueError, TypeError):
            duration = 45

        if not date_str:
            return JsonResponse({'status': 'error', 'message': 'Date parameter is required.'}, status=400)

        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid date format (expected YYYY-MM-DD).'}, status=400)

        today = datetime.date.today()
        if target_date < today:
            return JsonResponse({
                'status': 'error',
                'date': date_str,
                'message': 'Consultations cannot be scheduled for past dates.',
                'slots': []
            })

        # Weekend Check (Saturday = 5, Sunday = 6)
        if target_date.weekday() in (5, 6):
            return JsonResponse({
                'status': 'weekend',
                'date': date_str,
                'message': 'Private Wealth Advisory is closed on weekends (Monday–Friday, 9:00 AM–6:00 PM).',
                'slots': []
            })

        # Working hours definition (9:00 AM to 6:00 PM)
        # In minutes from 00:00:
        OPEN_MINUTES = 9 * 60   # 540 (09:00 AM)
        CLOSE_MINUTES = 18 * 60 # 1080 (06:00 PM)
        BUFFER_MINUTES = 15     # Required 15-minute transition gap

        # Fetch existing active bookings for this date
        existing_bookings = ConsultationBooking.objects.filter(
            consultation_date=target_date
        ).exclude(status='cancelled')

        existing_intervals = []
        for b in existing_bookings:
            b_start_min = b.consultation_time.hour * 60 + b.consultation_time.minute
            b_dur = b.duration_minutes or 45
            b_end_min = b_start_min + b_dur
            existing_intervals.append({
                'start': b_start_min,
                'end': b_end_min,
                'ref': b.reference_key,
                'name': b.client_name
            })

        # Now generate discrete possible candidate time slots
        # We step by 15 minutes between 09:00 and (18:00 - duration)
        # Note: If duration=30: 9:00, 9:45, 10:30, 11:15... or step by 15m
        step = 15
        now = datetime.datetime.now()
        is_today = (target_date == today)
        current_minute_today = now.hour * 60 + now.minute

        slots = []
        current_start = OPEN_MINUTES

        while current_start + duration <= CLOSE_MINUTES:
            slot_end = current_start + duration
            
            # Check if this slot start time is already in the past (if booking today)
            is_past_time = is_today and (current_start <= current_minute_today + 30)  # 30 min advance notice
            
            # Check conflict with existing bookings (including 15-minute gap)
            # A slot [current_start, slot_end] conflicts with booking [b.start, b.end]
            # if current_start < b.end + 15 AND slot_end + 15 > b.start
            conflict = False
            conflict_reason = ""

            for b_int in existing_intervals:
                blocked_start = b_int['start'] - BUFFER_MINUTES
                blocked_end = b_int['end'] + BUFFER_MINUTES
                
                # Check overlap between [current_start, slot_end] and [blocked_start, blocked_end]
                if current_start < blocked_end and slot_end > blocked_start:
                    conflict = True
                    b_start_str = f"{b_int['start'] // 60:02d}:{b_int['start'] % 60:02d}"
                    conflict_reason = f"Reserved (Advisory buffer)"
                    break

            start_hour = current_start // 60
            start_min = current_start % 60
            end_hour = slot_end // 60
            end_min = slot_end % 60

            start_time_obj = datetime.time(start_hour, start_min)
            end_time_obj = datetime.time(end_hour, end_min)

            time_24 = f"{start_hour:02d}:{start_min:02d}"
            time_display = start_time_obj.strftime("%I:%M %p")
            end_display = end_time_obj.strftime("%I:%M %p")

            is_available = not is_past_time and not conflict

            slots.append({
                'time': time_24,
                'time_display': time_display,
                'end_time': f"{end_hour:02d}:{end_min:02d}",
                'end_time_display': end_display,
                'duration': duration,
                'is_available': is_available,
                'is_past': is_past_time,
                'is_booked': conflict,
                'reason': conflict_reason if conflict else ('Past time' if is_past_time else 'Available')
            })

            # Advance by step (15 minutes) to offer flexible starting intervals
            current_start += step

        return JsonResponse({
            'status': 'success',
            'date': date_str,
            'date_display': target_date.strftime("%A, %d %B %Y"),
            'duration': duration,
            'total_slots': len(slots),
            'available_count': sum(1 for s in slots if s['is_available']),
            'slots': slots
        })


class ConsultationTrackAPIView(View):
    """
    API endpoint for Real-Time Consultation Tracking.
    Returns complete consultation lifecycle, status indicators, and
    previous vs updated scheduling comparison if the booking was rescheduled.
    """
    def get(self, request, *args, **kwargs):
        from .models import ConsultationBooking
        key = request.GET.get('key', '').strip().upper()
        if not key or len(key) != 10:
            return JsonResponse({
                'status': 'error',
                'message': 'Please provide a valid 10-character reference key (e.g., GT7K4M9P2X).'
            }, status=400)

        booking = ConsultationBooking.objects.filter(reference_key=key).first()
        if not booking:
            return JsonResponse({
                'status': 'error',
                'message': f"No consultation record was found matching reference key '{key}'. Please double-check your reference key and try again."
            }, status=404)

        # Build timeline states
        # Possible statuses: received, under_review, confirmed, paid, payment_pending, rescheduled, completed, cancelled
        timeline = [
            {
                'step': 1,
                'code': 'received',
                'title': 'Request Submitted',
                'description': 'Consultation request securely received and queued.',
                'state': 'completed'
            },
            {
                'step': 2,
                'code': 'under_review',
                'title': 'Under Review',
                'description': 'Advisory desk reviewing scope & advisor allocation.',
                'state': 'completed' if booking.status in ('confirmed', 'paid', 'rescheduled', 'completed') else ('active' if booking.status in ('received', 'under_review', 'payment_pending') else 'pending')
            },
            {
                'step': 3,
                'code': 'confirmed',
                'title': 'Confirmed',
                'description': 'Boardroom & Senior Wealth Advisor locked in calendar.',
                'state': 'completed' if booking.status in ('paid', 'completed') else ('active' if booking.status in ('confirmed', 'rescheduled') else 'pending')
            },
            {
                'step': 4,
                'code': 'paid',
                'title': 'Payment Completed',
                'description': 'Retainer/fiduciary fee verified or waived.',
                'state': 'completed' if booking.status == 'completed' or booking.payment_status in ('completed', 'waived') else ('active' if booking.status == 'paid' else 'pending')
            },
            {
                'step': 5,
                'code': 'completed',
                'title': 'Consultation Completed',
                'description': 'Strategic briefing & executive advisory concluded.',
                'state': 'completed' if booking.status == 'completed' else 'pending'
            }
        ]

        if booking.status == 'cancelled':
            for t in timeline:
                if t['code'] != 'received':
                    t['state'] = 'cancelled'

        data = {
            'reference_key': booking.reference_key,
            'client_name': booking.client_name,
            'email': booking.email,
            'phone': booking.phone,
            'service': booking.get_service_display(),
            'duration_minutes': booking.duration_minutes,
            'duration_label': booking.duration_label,
            'consultation_date': booking.consultation_date.strftime("%A, %d %B %Y"),
            'consultation_time': booking.consultation_time.strftime("%I:%M %p"),
            'end_time': booking.end_time.strftime("%I:%M %p") if booking.end_time else "",
            'preferred_comm': booking.get_preferred_comm_display(),
            'fee_amount': float(booking.fee_amount if booking.fee_amount is not None else 5000.00),
            'fee_display': f"₹{booking.fee_amount:,.2f}",
            'discount_amount': float(booking.discount_amount if booking.discount_amount is not None else 0.00),
            'discount_display': f"₹{booking.discount_amount:,.2f}",
            'net_amount': float(booking.net_amount if booking.net_amount is not None else 5000.00),
            'net_display': f"₹{booking.net_amount:,.2f}",
            'invoice_number': booking.invoice_number or f"INV-2026-{booking.reference_key[:6]}",
            'payment_status': booking.get_payment_status_display(),
            'payment_status_code': booking.payment_status,
            'payment_badge': booking.payment_badge_class,
            'payment_method': booking.payment_method,
            'transaction_id': booking.transaction_id,
            'fiduciary_desk': booking.fiduciary_desk or "Senior Wealth Advisory & Fiduciary Desk",
            'meeting_link': booking.meeting_link,
            'client_instructions': booking.client_instructions,
            'status': booking.status,
            'status_label': booking.get_status_display(),
            'status_badge': booking.status_badge_class,
            'is_rescheduled': booking.status == 'rescheduled' or bool(booking.previous_date),
            'previous_date': booking.previous_date.strftime("%A, %d %B %Y") if booking.previous_date else "",
            'previous_time': booking.previous_time.strftime("%I:%M %p") if booking.previous_time else "",
            'previous_schedule': f"{booking.previous_date.strftime('%A, %d %B %Y')} — {booking.previous_time.strftime('%I:%M %p')}" if booking.previous_date and booking.previous_time else "",
            'updated_schedule': f"{booking.consultation_date.strftime('%A, %d %B %Y')} — {booking.consultation_time.strftime('%I:%M %p')}",
            'rescheduled_reason': booking.rescheduled_reason,
            'subject': booking.subject,
            'message': booking.message,
            'admin_notes': booking.admin_notes if request.user.is_staff else "",
            'created_at': booking.created_at.strftime("%d %B %Y at %I:%M %p"),
            'timeline': timeline,
        }
        return JsonResponse({
            'status': 'success',
            'data': data
        })


# Custom HTTP Error Handlers (404 & 500)
# --------------------------------------------------------------------------
def custom_404_view(request, exception=None):
    """
    Renders custom 404 Page Not Found error page with full theme support.
    """
    return render(request, '404.html', status=404)


def custom_500_view(request):
    """
    Renders custom 500 Internal Server Error page with full theme support.
    """
    return render(request, '500.html', status=500)


# --------------------------------------------------------------------------
# 11. Institutional Documentation & Legal Compliance Suite
# --------------------------------------------------------------------------
class PrivacyPolicyView(TemplateView):
    """
    Publicly accessible Privacy Policy & Data Protection page (privacy_policy.html).
    """
    template_name = 'login/legal/privacy_policy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Privacy Policy & Data Protection — GuardianTree FP"
        context['current_doc'] = 'privacy'
        return context


class CookiePolicyView(TemplateView):
    """
    Publicly accessible Cookie Policy & Tracking Preferences page (cookie_policy.html).
    """
    template_name = 'login/legal/cookie_policy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Cookie Policy & Tracking Preferences — GuardianTree FP"
        context['current_doc'] = 'cookie'
        return context


class TermsConditionsView(TemplateView):
    """
    Publicly accessible Terms & Conditions & Fiduciary Agreement page (terms_conditions.html).
    """
    template_name = 'login/legal/terms_conditions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Terms & Conditions — GuardianTree FP"
        context['current_doc'] = 'terms'
        return context


class AMLKYCView(TemplateView):
    """
    Publicly accessible AML / KYC Compliance Policy page (aml_kyc.html).
    """
    template_name = 'login/legal/aml_kyc.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "AML / KYC Compliance Policy — GuardianTree FP"
        context['current_doc'] = 'aml_kyc'
        return context


class DisclaimerView(TemplateView):
    """
    Publicly accessible Regulatory Disclaimer & Risk Warning page (disclaimer.html).
    """
    template_name = 'login/legal/disclaimer.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Regulatory Disclaimer & Risk Disclosure — GuardianTree FP"
        context['current_doc'] = 'disclaimer'

        # Dynamic SEBI Complaint Data & Fiduciary Metrics
        from django.utils import timezone
        now = timezone.now()
        current_month = now.month
        current_year = now.year
        context['current_month_year'] = now.strftime('%B %Y')

        from contactform.models import ContactSubmission
        from login.models import ConsultationBooking

        # Total inquiries / formal grievances received
        grievances_count = ContactSubmission.objects.filter(
            created_at__year=current_year,
            created_at__month=current_month,
            subject__icontains='grievance'
        ).count()

        # Total consultations booked and completed
        total_bookings_month = ConsultationBooking.objects.filter(
            created_at__year=current_year,
            created_at__month=current_month
        ).count()
        completed_bookings = ConsultationBooking.objects.filter(
            status='completed'
        ).count()

        context['complaints_summary'] = {
            'month_name': now.strftime('%B %Y'),
            'direct_investor': {
                'sr': 1,
                'source': 'Directly from Investors',
                'carried_forward': 0,
                'received': grievances_count,
                'resolved': grievances_count,
                'pending': 0,
                'pending_over_3m': 0,
                'avg_resolution_days': 0 if grievances_count == 0 else 1,
            },
            'sebi_scores': {
                'sr': 2,
                'source': 'SEBI (SCORES)',
                'carried_forward': 0,
                'received': 0,
                'resolved': 0,
                'pending': 0,
                'pending_over_3m': 0,
                'avg_resolution_days': 0,
            },
            'other_sources': {
                'sr': 3,
                'source': 'Other Sources (if any)',
                'carried_forward': 0,
                'received': 0,
                'resolved': 0,
                'pending': 0,
                'pending_over_3m': 0,
                'avg_resolution_days': 0,
            },
            'grand_total': {
                'carried_forward': 0,
                'received': grievances_count,
                'resolved': grievances_count,
                'pending': 0,
                'pending_over_3m': 0,
                'avg_resolution_days': 0 if grievances_count == 0 else 1,
            },
            'total_bookings_month': total_bookings_month,
            'completed_bookings': completed_bookings,
        }
        return context


# --------------------------------------------------------------------------
# 12. SaaS Subscription Management & Automated Backup Endpoints
# --------------------------------------------------------------------------
from django.http import JsonResponse
from .saas_service import get_saas_status, unlock_subscription_with_plan, validate_license_key, SUBSCRIPTION_PLANS
from .backup_service import create_live_backup, get_latest_backups_summary


def saas_status_api(request):
    """
    Returns JSON SaaS status, trial countdown, and live backup metrics.
    """
    status = get_saas_status()
    backups = get_latest_backups_summary()
    return JsonResponse({
        'saas': status,
        'backups': backups,
    })


def saas_unlock_view(request):
    """
    POST endpoint to validate a license key or simulate plan renewal.
    """
    if request.method == 'POST':
        action = request.POST.get('saas_action') or request.POST.get('action') or 'unlock_license'
        admin_url = f"/{getattr(settings, 'ADMIN_SECRET_PATH', 'x7K9mQp2LrT4').strip('/')}/"
        
        if action in ['unlock_license', 'activate_key']:
            key = request.POST.get('license_key', '').strip()
            is_valid, matched_plan, msg = validate_license_key(key)
            if is_valid:
                unlock_subscription_with_plan(matched_plan or '1_year', license_key=key)
                messages.success(request, f"🎉 Admin Panel Unlocked! {msg}")
                return redirect(admin_url)
            else:
                messages.error(request, msg)
                return redirect('login:saas_lock_page')

        elif action in ['renew_plan', 'request_plan']:
            plan_code = request.POST.get('plan_code', '3_months')
            if plan_code in SUBSCRIPTION_PLANS:
                from .models import SaaSRequestLog
                from .emails import send_saas_purchase_request_emails
                plan_info = SUBSCRIPTION_PLANS[plan_code]
                price_str = f"₹{plan_info['price_inr']:,} / ${plan_info['price_usd']:,}"
                
                SaaSRequestLog.objects.create(
                    plan_code=plan_code,
                    plan_name=plan_info['name'],
                    client_email='sabin@guardiantreefp.com',
                    status='pending'
                )

                send_saas_purchase_request_emails(plan_code, plan_info['name'], price_str)

                messages.success(
                    request,
                    f"📩 Purchase Request Email Sent to info@kpregtech.com! Thank you for ordering {plan_info['name']} ({price_str}). "
                    f"An automated confirmation has been sent to sabin@guardiantreefp.com. KPRegTech will dispatch your Master License Key & Tax Invoice within 24 hours."
                )
                return redirect('login:saas_lock_page')



    return redirect(f"/{getattr(settings, 'ADMIN_SECRET_PATH', 'x7K9mQp2LrT4').strip('/')}/")


def saas_lock_page_view(request):
    """
    Direct view for the SaaS Subscription & Renewal Desk.
    """
    from .models import SaaSInvoice
    admin_prefix = f"/{getattr(settings, 'ADMIN_SECRET_PATH', 'x7K9mQp2LrT4').strip('/')}"
    latest_invoice = SaaSInvoice.objects.order_by('-issued_at').first()
    context = {
        'saas_status': get_saas_status(),
        'plans': SUBSCRIPTION_PLANS,
        'backup_summary': get_latest_backups_summary(),
        'admin_url': f"{admin_prefix}/",
        'latest_invoice': latest_invoice,
    }
    return render(request, 'admin/saas_lock.html', context)


def get_dashboard_analytics_context(request):
    """
    Computes 100% dynamic, real-time statistics from active database models
    (ConsultationBooking, ContactSubmission, CustomUser, TeamMember, Testimonials, Vault Backups).
    """
    from .models import ConsultationBooking, CustomUser, TeamMember, Testimonial, FAQ, AdminBackupLog, SaaSInvoice
    from contactform.models import ContactSubmission
    from .backup_service import get_latest_backups_summary, get_all_backups
    from .saas_service import get_saas_status
    import datetime

    # 1. Real Model Counts
    total_consultations = ConsultationBooking.objects.count()
    confirmed_consultations = ConsultationBooking.objects.filter(status__in=['confirmed', 'paid', 'completed']).count()
    pending_consultations = ConsultationBooking.objects.filter(status='received').count()
    total_inquiries = ContactSubmission.objects.count()
    total_users = CustomUser.objects.count()
    total_staff = CustomUser.objects.filter(is_staff=True).count()
    total_testimonials = Testimonial.objects.count()
    total_faqs = FAQ.objects.count()

    # Calculate dynamic completion percentage and SVG radial progress offset
    completion_rate = 0
    completion_stroke_offset = 238.76
    if total_consultations > 0:
        completion_rate = min(100, round((confirmed_consultations / total_consultations) * 100))
        completion_stroke_offset = round(238.76 - (238.76 * (completion_rate / 100)), 2)

    # 2. Real Model Querysets
    upcoming_consultations = list(ConsultationBooking.objects.order_by('-consultation_date', '-consultation_time')[:5])
    recent_inquiries = list(ContactSubmission.objects.order_by('-created_at')[:5])
    # Advisory Team disabled in production (Commented out):
    # advisory_team = list(TeamMember.objects.filter(is_active=True).order_by('order')[:6])
    # if not advisory_team:
    #     advisory_team = list(TeamMember.objects.all()[:6])
    advisory_team = []

    # 3. Dynamic Weekly Bar Chart Data (Sunday -> Saturday)
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=(today.weekday() + 1) % 7)  # Sunday
    weekly_chart = []
    day_abbrs = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
    day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    
    max_day_val = 1
    daily_counts = []
    for i in range(7):
        target_day = start_of_week + datetime.timedelta(days=i)
        b_count = ConsultationBooking.objects.filter(created_at__date=target_day).count() if hasattr(ConsultationBooking, 'created_at') else 0
        i_count = ContactSubmission.objects.filter(created_at__date=target_day).count()
        total_day = b_count + i_count
        daily_counts.append((day_abbrs[i], day_names[i], target_day, total_day, target_day == today))
        if total_day > max_day_val:
            max_day_val = total_day

    # Scale bar heights (min 20%, max 95%)
    for abbr, name, d_date, count, is_cur in daily_counts:
        bar_height = 25 if count == 0 else int(30 + (count / max(1, max_day_val)) * 65)
        weekly_chart.append({
            'abbr': abbr,
            'name': name,
            'date': d_date.strftime('%b %d'),
            'count': count,
            'height': bar_height,
            'is_current': is_cur,
            'percentage': int((count / max(1, max_day_val)) * 100) if count > 0 else 20
        })

    # 4. Vault Backups & SaaS (Strictly limited to the last 5 snapshots)
    saas_status = get_saas_status()
    backup_summary = get_latest_backups_summary()
    vault_backups = get_all_backups(max_count=5)
    latest_invoice = SaaSInvoice.objects.order_by('-issued_at').first()

    return {
        'kpi_total_consultations': total_consultations,
        'kpi_confirmed_consultations': confirmed_consultations,
        'kpi_pending_consultations': pending_consultations,
        'kpi_total_inquiries': total_inquiries,
        'kpi_total_users': total_users,
        'kpi_total_staff': total_staff,
        'kpi_total_testimonials': total_testimonials,
        'kpi_total_faqs': total_faqs,
        'kpi_completion_rate': completion_rate,
        'kpi_completion_stroke_offset': completion_stroke_offset,
        'upcoming_consultations': upcoming_consultations,
        'recent_inquiries': recent_inquiries,
        'advisory_team': advisory_team,
        'weekly_chart': weekly_chart,
        'saas_status': saas_status,
        'backup_summary': backup_summary,
        'vault_backups': vault_backups,
        'latest_invoice': latest_invoice,
        'admin_secret_path': getattr(settings, 'ADMIN_SECRET_PATH', 'x7K9mQp2LrT4').strip('/'),
    }


def admin_restore_backup_view(request, filename):
    """
    Restores the SQLite database from a chosen backup snapshot file.
    Only accessible to authenticated superusers/staff, restricted to the last 5 backups.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('admin:index')

    if request.method == 'POST':
        from .backup_service import restore_database_from_snapshot, get_all_backups
        valid_backups = [b['filename'] for b in get_all_backups(max_count=5)]
        if filename not in valid_backups:
            messages.error(request, "Restoration is strictly restricted to the last 5 Data Vault backups.")
            return redirect('admin:index')

        res = restore_database_from_snapshot(filename)
        if res.get('success'):
            messages.success(request, f"✅ Data Vault Restored Successfully! All historical data, bookings, and users recovered from {filename}.")
        else:
            messages.error(request, f"❌ Restoration Error: {res.get('error')}")

    return redirect('admin:index')


def admin_download_backup_view(request, filename):
    """
    Allows the admin to download any database backup snapshot file directly to their local computer.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        raise Http404("Unauthorized")

    from .backup_service import BACKUP_DIR
    import os
    from django.http import FileResponse

    filepath = BACKUP_DIR / filename
    if os.path.exists(filepath) and filename.endswith('.sqlite3'):
        return FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)
    else:
        raise Http404("Backup file not found.")


def admin_upload_backup_view(request):
    """
    Allows the admin to upload an external .sqlite3 backup file and restore it instantly.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('admin:index')

    if request.method == 'POST' and request.FILES.get('backup_file'):
        from .backup_service import handle_uploaded_backup
        uploaded_file = request.FILES['backup_file']
        res = handle_uploaded_backup(uploaded_file)
        if res.get('success'):
            messages.success(request, f"Database Restored from Uploaded File! All data and records have been recovered.")
        else:
            messages.error(request, f"Upload Restoration Failed: {res.get('error')}")
    else:
        messages.error(request, "No backup file was uploaded.")

    return redirect('admin:index')


def trigger_manual_backup_view(request):
    """
    API endpoint for on-demand database snapshots triggered from the Admin Dashboard button.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    from .backup_service import create_live_backup
    res = create_live_backup(event_trigger="Admin Dashboard Manual Trigger")
    if res and res.get('success'):
        return JsonResponse({
            'success': True,
            'file_name': res.get('file_name'),
            'file_size_kb': res.get('file_size_kb'),
            'timestamp': res.get('timestamp')
        })
    return JsonResponse({
        'success': False,
        'error': res.get('error') if res else 'Unknown backup error'
    }, status=500)


def kpregtech_saas_control_view(request):
    """
    Secret KPRegTech & VintushTech Master SaaS Control Portal.
    Protected by provider credentials:
      - Email ID: info@kpregtech.com
      - Password: Year@KP#4757
    Provides high-security, zero-confusion management of Sabin Balan's Admin Panel:
      1. Issue new verifiable Master License Keys (1 Month, 3 Months, 6 Months, 1 Year, or Custom Days).
      2. Lock Sabin's admin panel immediately.
      3. Instant emergency unlock without key entry.
      4. Adjust days remaining directly.
      5. Review and approve client renewal requests.
      6. Audit history of issued keys and official tax invoices.
    """
    from .saas_service import (
        get_saas_status,
        unlock_subscription_with_plan,
        get_or_create_saas_subscription,
        generate_license_key,
        create_saas_invoice,
        SUBSCRIPTION_PLANS
    )
    from .emails import send_saas_locked_alert_email, send_saas_master_key_email
    from .models import SaaSInvoice, SaaSRequestLog
    from django.contrib import messages
    from django.utils import timezone
    import datetime

    # 1. Handle Logout
    if request.method == 'POST' and request.POST.get('action') == 'logout':
        request.session.pop('kpregtech_saas_authed', None)
        messages.success(request, "KPRegTech Provider Session Terminated.")
        return render(request, 'login/kpregtech_saas_login.html')

    # 2. Handle Provider Authentication POST
    if request.method == 'POST' and 'email' in request.POST and 'password' in request.POST:
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        if email == 'info@kpregtech.com' and password == 'Year@KP#4757':
            request.session['kpregtech_saas_authed'] = True
            messages.success(request, "KPRegTech Provider Authenticated Successfully.")
        else:
            return render(request, 'login/kpregtech_saas_login.html', {
                'error_message': 'Invalid KPRegTech Provider Credentials. Please verify your Email ID & Password.'
            })

    # 3. Check Session Auth
    if not request.session.get('kpregtech_saas_authed'):
        return render(request, 'login/kpregtech_saas_login.html')

    # 4. Handle Master Control Actions
    if request.method == 'POST':
        action = request.POST.get('action')

        # ACTION: Issue Master License Key
        if action == 'issue_key':
            plan_code = request.POST.get('plan', '1_year')
            custom_days = request.POST.get('custom_days')
            
            # Determine duration
            if plan_code == 'custom':
                try:
                    duration = max(1, int(custom_days or 30))
                except (ValueError, TypeError):
                    duration = 30
                plan_info = {
                    'code': 'custom',
                    'name': f'Custom Access Plan ({duration} Days)',
                    'duration_days': duration,
                    'price_inr': duration * 100,
                    'price_usd': duration * 2,
                }
            else:
                plan_info = SUBSCRIPTION_PLANS.get(plan_code, SUBSCRIPTION_PLANS['1_year'])
                duration = plan_info['duration_days']

            # Generate Cryptographic Unique Master Key
            key = generate_license_key(plan_code if plan_code != 'custom' else '1_year', 'sabin@guardiantreefp.com', unique=True)
            expiry = timezone.now() + datetime.timedelta(days=duration)

            # Create Official SaaS Tax Invoice & Master Key Audit Log
            invoice = create_saas_invoice(
                plan_code=plan_code if plan_code != 'custom' else '1_year',
                license_key=key,
                valid_until=expiry
            )

            # Send Master Key & Invoice Email to Sabin Balan & KPRegTech
            send_saas_master_key_email(key, plan_info['name'], expiry)

            # Retain Admin Panel LOCKED so admin must enter key on lock screen to unlock
            sub = get_or_create_saas_subscription()
            sub.is_locked = True
            sub.subscription_status = 'locked_expired'
            sub.save(update_fields=['is_locked', 'subscription_status', 'updated_at'])

            # Store in session for prominent display and 1-click copy
            request.session['latest_generated_key'] = key
            request.session['latest_generated_plan_name'] = plan_info['name']
            request.session['latest_generated_expiry'] = expiry.strftime('%d %B %Y')
            request.session['latest_generated_inv'] = invoice.invoice_number

            messages.success(
                request,
                f"🔑 Master License Key Generated: {key}. Invoice #{invoice.invoice_number} emailed to sabin@guardiantreefp.com. "
                f"Admin panel is LOCKED until Sabin enters this key at the lock screen."
            )

        # ACTION: Lock Admin Panel Immediately
        elif action == 'lock_now':
            sub = get_or_create_saas_subscription()
            sub.is_locked = True
            sub.subscription_status = 'locked_expired'
            sub.paid_until = timezone.now()
            sub.save()
            status = get_saas_status()
            send_saas_locked_alert_email(status)
            messages.warning(request, "🔒 Admin Panel HAS BEEN LOCKED. Sabin Balan is now restricted to the renewal lock screen.")

        # ACTION: Instant Emergency Unlock (Without Key Entry)
        elif action == 'instant_unlock':
            plan_code = request.POST.get('plan', '1_year')
            sub, expiry = unlock_subscription_with_plan(plan_code, simulated_payment=True)
            invoice = create_saas_invoice(plan_code, sub.license_key, valid_until=expiry)
            plan_name = SUBSCRIPTION_PLANS.get(plan_code, {}).get('name', '1-Year Enterprise Plan')
            send_saas_master_key_email(sub.license_key, plan_name, expiry)
            messages.success(request, f"🔓 Admin Panel INSTANTLY UNLOCKED for {plan_name}. Valid until {expiry.strftime('%d %B %Y')}.")

        # ACTION: Set Days Remaining Directly
        elif action == 'modify_days_left':
            days_input = request.POST.get('days_count')
            if days_input is not None and days_input != '':
                try:
                    num_days = int(days_input)
                    sub = get_or_create_saas_subscription()
                    if num_days <= 0:
                        sub.is_locked = True
                        sub.subscription_status = 'locked_expired'
                        sub.paid_until = timezone.now()
                        sub.save()
                        messages.warning(request, "⚠️ Days Remaining set to 0. Admin Panel is now IMMEDIATELY LOCKED!")
                    else:
                        dt = timezone.now() + datetime.timedelta(days=num_days)
                        sub.is_locked = False
                        sub.is_free_trial = False
                        sub.subscription_status = 'active_paid'
                        sub.paid_until = dt
                        if not sub.current_plan:
                            sub.current_plan = '1_year'
                        sub.save()
                        messages.success(request, f"⏳ Days Remaining Updated! Set access to {num_days} Days (Valid until {dt.strftime('%d %B %Y')}).")
                except ValueError:
                    messages.error(request, "Invalid number of days entered.")

        # ACTION: Approve Client Renewal Request
        elif action == 'approve_request':
            req_id = request.POST.get('request_id')
            req_obj = SaaSRequestLog.objects.filter(pk=req_id).first()
            if req_obj:
                plan_code = req_obj.plan_code
                plan_info = SUBSCRIPTION_PLANS.get(plan_code, SUBSCRIPTION_PLANS['1_year'])
                key = generate_license_key(plan_code, req_obj.client_email, unique=True)
                expiry = timezone.now() + datetime.timedelta(days=plan_info['duration_days'])
                invoice = create_saas_invoice(plan_code, key, client_email=req_obj.client_email, valid_until=expiry)
                req_obj.status = 'approved'
                req_obj.issued_invoice = invoice
                req_obj.save()
                send_saas_master_key_email(key, plan_info['name'], expiry)

                # Keep Admin Panel LOCKED so admin unlocks using this key
                sub = get_or_create_saas_subscription()
                sub.is_locked = True
                sub.subscription_status = 'locked_expired'
                sub.save(update_fields=['is_locked', 'subscription_status', 'updated_at'])

                request.session['latest_generated_key'] = key
                request.session['latest_generated_plan_name'] = plan_info['name']
                request.session['latest_generated_expiry'] = expiry.strftime('%d %B %Y')
                request.session['latest_generated_inv'] = invoice.invoice_number

                messages.success(request, f"✅ Request Approved! Master Key {key} issued and emailed to {req_obj.client_email}.")

        # ACTION: Dismiss / Delete Request
        elif action == 'delete_request':
            req_id = request.POST.get('request_id')
            SaaSRequestLog.objects.filter(pk=req_id).delete()
            messages.success(request, "🗑️ Subscription Request Log Dismissed.")

        # ACTION: Delete Single Invoice
        elif action == 'delete_invoice':
            inv_id = request.POST.get('invoice_id')
            inv = SaaSInvoice.objects.filter(pk=inv_id).first()
            if inv:
                inv.delete()
                active_invoices = SaaSInvoice.objects.filter(status='paid')
                if not active_invoices.exists():
                    sub = get_or_create_saas_subscription()
                    sub.is_locked = True
                    sub.subscription_status = 'locked_expired'
                    sub.current_plan = ''
                    sub.paid_until = timezone.now()
                    sub.save()
                    messages.warning(request, "🗑️ Invoice Deleted. No active plans remaining — Admin Panel is now LOCKED.")
                else:
                    latest_active = active_invoices.order_by('-valid_until').first()
                    sub = get_or_create_saas_subscription()
                    sub.current_plan = latest_active.plan_code
                    sub.paid_until = latest_active.valid_until
                    sub.license_key = latest_active.master_key
                    sub.save()
                    messages.success(request, f"🗑️ Invoice Deleted. Admin Panel synced to active plan: {latest_active.plan_name}.")

        # ACTION: Resend Key Email
        elif action == 'resend_master_key_email':
            key = request.POST.get('license_key')
            plan_name = request.POST.get('plan_name', 'KPRegTech SaaS Master Enterprise')
            expiry = timezone.now() + datetime.timedelta(days=365)
            send_saas_master_key_email(key, plan_name, expiry)
            messages.success(request, f"📧 Master Key Email for key '{key}' resent to sabin@guardiantreefp.com.")

        return redirect('login:kpregtech_saas_control')

    # Prepare status, history & requests for dashboard
    saas_status = get_saas_status()
    pending_requests = list(SaaSRequestLog.objects.filter(status='pending').order_by('-requested_at'))
    invoices_history = list(SaaSInvoice.objects.all().order_by('-issued_at'))

    latest_generated_key = request.session.pop('latest_generated_key', None)
    latest_generated_plan_name = request.session.pop('latest_generated_plan_name', None)
    latest_generated_expiry = request.session.pop('latest_generated_expiry', None)
    latest_generated_inv = request.session.pop('latest_generated_inv', None)

    return render(request, 'login/kpregtech_saas_control.html', {
        'saas_status': saas_status,
        'pending_requests': pending_requests,
        'invoices_history': invoices_history,
        'latest_generated_key': latest_generated_key,
        'latest_generated_plan_name': latest_generated_plan_name,
        'latest_generated_expiry': latest_generated_expiry,
        'latest_generated_inv': latest_generated_inv,
        'plans': SUBSCRIPTION_PLANS,
    })


# --------------------------------------------------------------------------
# 16. Live Financial Market Streaming & Rate Aggregation API Endpoints
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# 17. SEO & Agentic AI Discovery Endpoints (llms.txt, robots.txt, sitemap.xml)
# --------------------------------------------------------------------------
import os
from django.conf import settings
from django.http import HttpResponse

def llms_txt_view(request):
    """
    Serves the standardized llms.txt file for AI agentic web crawlers.
    """
    filepath = settings.BASE_DIR / 'llms.txt'
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/plain; charset=utf-8')
    return HttpResponse("# GuardianTree FP\n> Fiduciary Wealth Advisory\nWebsite: https://www.guardiantreefp.com", content_type='text/plain')


def llms_full_txt_view(request):
    """
    Serves the comprehensive llms-full.txt file for AI agentic web crawlers.
    """
    filepath = settings.BASE_DIR / 'llms-full.txt'
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/plain; charset=utf-8')
    return HttpResponse("# GuardianTree FP — Institutional Reference Manual", content_type='text/plain')


def robots_txt_view(request):
    """
    Serves robots.txt with crawling guidelines, SEO directives, and agentic AI markers.
    """
    admin_slug = getattr(settings, 'ADMIN_SECRET_PATH', 'x7K9mQp2LrT4').strip('/')
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Disallow: /{admin_slug}/\n"
        "Disallow: /admin/\n"
        "\n"
        "# Agentic AI & LLM Discovery Links\n"
        "Link: </llms.txt>; rel=\"agentic-ai\"\n"
        "Link: </llms-full.txt>; rel=\"agentic-ai-documentation\"\n"
        "Sitemap: " + request.build_absolute_uri('/sitemap.xml') + "\n"
    )
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


def sitemap_xml_view(request):
    """
    Renders XML sitemap indexing all public pages and legal documentation for Google, Bing, and AI search engines.
    """
    domain = request.build_absolute_uri('/')[:-1]
    pages = [
        {'loc': domain + '/', 'changefreq': 'daily', 'priority': '1.0'},
        {'loc': domain + '/about/', 'changefreq': 'weekly', 'priority': '0.9'},
        {'loc': domain + '/services/', 'changefreq': 'weekly', 'priority': '0.9'},
        {'loc': domain + '/testimonials/', 'changefreq': 'weekly', 'priority': '0.8'},
        {'loc': domain + '/consultation/', 'changefreq': 'daily', 'priority': '0.9'},
        {'loc': domain + '/contact/', 'changefreq': 'monthly', 'priority': '0.7'},
        {'loc': domain + '/privacy-policy/', 'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': domain + '/terms-and-conditions/', 'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': domain + '/disclaimer/', 'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': domain + '/aml-kyc/', 'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': domain + '/cookie-policy/', 'changefreq': 'monthly', 'priority': '0.5'},
    ]
    
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for p in pages:
        xml.append('  <url>')
        xml.append(f'    <loc>{p["loc"]}</loc>')
        xml.append(f'    <changefreq>{p["changefreq"]}</changefreq>')
        xml.append(f'    <priority>{p["priority"]}</priority>')
        xml.append('  </url>')
    xml.append('</urlset>')
    
    return HttpResponse("\n".join(xml), content_type='application/xml; charset=utf-8')







