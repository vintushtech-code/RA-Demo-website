"""Single end-to-end regression suite for the Sabin Balan Finance website."""

import datetime as dt
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sabin_balan_finance_project.settings")

import django

django.setup()

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.test import Client, TestCase, override_settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from contactform.models import ContactSubmission
from login.emails import (
    send_consultation_booking_email,
    send_consultation_status_email,
    send_contact_form_emails,
    send_saas_locked_alert_email,
    send_saas_master_key_email,
    send_saas_purchase_request_emails,
    send_saas_warning_7days_email,
    send_testimonial_email,
    send_testimonial_published_email,
)
from login.models import (
    AdminSaaSSubscription,
    ConsultationBooking,
    CustomUser,
    FAQ,
    TeamMember,
    Testimonial,
)
from login.saas_service import get_saas_status, unlock_subscription_with_plan, validate_license_key
from login.two_factor import send_2fa_otp


CLIENT_EMAIL = "vintushtech@gmail.com"
ADMIN_EMAIL = "example@gmail.com"


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ADMIN_NOTIFICATION_EMAIL=ADMIN_EMAIL,
    CONTACT_FORM_EMAIL_RECIPIENT=ADMIN_EMAIL,
    ADMIN_2FA_EMAIL=ADMIN_EMAIL,
    SABIN_CLIENT_EMAIL=CLIENT_EMAIL,
    PROVIDER_EMAIL="info@kpregtech.com",
)
class WebsitePagesAndUiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_all_public_and_legal_pages_render(self):
        routes = [
            "login:home", "login:about", "login:services", "login:testimonials",
            "login:consultation", "contactform:contact", "login:privacy_policy",
            "login:terms_conditions", "login:cookie_policy", "login:aml_kyc",
            "login:disclaimer", "login:login",
        ]
        for route in routes:
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 200, route)
            self.assertNotIn("{{ booking.consultation_time|time", response.content.decode())

    def test_home_quote_is_docked_right_and_team_mobile_mode_is_single(self):
        home = (settings.BASE_DIR / "login/templates/login/home.html").read_text(encoding="utf-8")
        about_js = (settings.BASE_DIR / "login/static/login/js/about.js").read_text(encoding="utf-8")
        self.assertIn("Kalphora Equity", home)
        self.assertIn("window.innerWidth <= 768 ? 1 : 4", about_js)

    def test_consultation_page_has_no_literal_template_leak_and_real_tracking_date(self):
        booking = ConsultationBooking.objects.create(
            client_name="UI Test Client", email=CLIENT_EMAIL, phone="+15550199",
            consultation_date=dt.date(2026, 9, 21), consultation_time=dt.time(14, 30),
        )
        response = self.client.get(reverse("login:consultation"), {"key": booking.reference_key})
        html = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("{{ booking.", html)
        self.assertIn("Monday, 21 September 2026", html)
        self.assertIn("02:30 PM", html)

    def test_models_and_pricing(self):
        user = CustomUser.objects.create_user(username="website", email=CLIENT_EMAIL, password="Pass1234!")
        self.assertTrue(user.check_password("Pass1234!"))
        self.assertIn("team_sabin.png", TeamMember.objects.create(name="Sabin Balan", role="Founder").avatar_url)
        self.assertEqual(str(FAQ.objects.create(question="Q", answer="A")), "Q")
        self.assertEqual(float(ConsultationBooking.objects.create(
            client_name="Pricing", email="pricing@example.com", phone="1", duration_minutes=60,
            consultation_date=dt.date.today() + dt.timedelta(days=2), consultation_time=dt.time(10),
        ).fee_amount), 8000.0)

    def test_contact_form_and_testimonial_models(self):
        submission = ContactSubmission.objects.create(name="Client", email=CLIENT_EMAIL, subject="Advice", message="Help")
        testimonial = Testimonial.objects.create(name="Reviewer", email=CLIENT_EMAIL, role="Founder", quote="Excellent")
        self.assertIn("Advice", str(submission))
        self.assertIn("Reviewer", str(testimonial))


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ADMIN_NOTIFICATION_EMAIL=ADMIN_EMAIL,
    CONTACT_FORM_EMAIL_RECIPIENT=ADMIN_EMAIL,
    ADMIN_2FA_EMAIL=ADMIN_EMAIL,
    SABIN_CLIENT_EMAIL=CLIENT_EMAIL,
    PROVIDER_EMAIL="info@kpregtech.com",
)
class EveryEmailFeatureTest(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.booking = ConsultationBooking(
            reference_key="GTTEST1234", client_name="Mail Client", email=CLIENT_EMAIL,
            phone="+15550199", service="investment", duration_minutes=45,
            consultation_date=dt.date(2026, 9, 21), consultation_time=dt.time(14, 30),
            status="confirmed", payment_status="paid",
        )
        self.submission = ContactSubmission(
            name="Mail Client", email=CLIENT_EMAIL, subject="Portfolio Advice", message="Review my portfolio."
        )
        self.testimonial = Testimonial(
            name="Mail Client", email=CLIENT_EMAIL, role="Founder", quote="Excellent advisory", rating=5
        )

    def assert_mail(self, count, recipients, subject_text=None, body_text=None):
        self.assertEqual(len(mail.outbox), count)
        actual = [recipient for message in mail.outbox for recipient in message.to]
        for recipient in recipients:
            self.assertIn(recipient, actual)
        if subject_text:
            self.assertTrue(any(subject_text in message.subject for message in mail.outbox))
        if body_text:
            self.assertTrue(any(body_text in message.body for message in mail.outbox))

    def test_consultation_booking_and_status_emails(self):
        send_consultation_booking_email(self.booking, sync=True)
        self.assert_mail(2, [CLIENT_EMAIL, ADMIN_EMAIL], "GTTEST1234", "21 September 2026")
        mail.outbox.clear()
        send_consultation_status_email(self.booking, old_status="received", old_payment_status="unpaid", sync=True)
        self.assert_mail(1, [CLIENT_EMAIL], "Confirmed", "02:30 PM")

    def test_contact_and_testimonial_emails(self):
        send_contact_form_emails(self.submission, sync=True)
        self.assert_mail(2, [CLIENT_EMAIL, ADMIN_EMAIL], "Portfolio Advice")
        mail.outbox.clear()
        send_testimonial_email(self.testimonial, sync=True)
        self.assert_mail(2, [CLIENT_EMAIL, ADMIN_EMAIL], "Review")
        mail.outbox.clear()
        send_testimonial_published_email(self.testimonial, sync=True)
        self.assert_mail(1, [CLIENT_EMAIL], "Now Live")

    def test_saas_warning_lock_master_key_and_purchase_emails(self):
        status = {"plan_name": "Enterprise", "days_remaining": 7, "expires_at": timezone.now() + dt.timedelta(days=7)}
        send_saas_warning_7days_email(status, sync=True)
        self.assert_mail(1, [CLIENT_EMAIL, "info@kpregtech.com"], "7 Days")
        mail.outbox.clear()
        send_saas_locked_alert_email(status, sync=True)
        self.assert_mail(1, [CLIENT_EMAIL, "info@kpregtech.com"], "Locked")
        mail.outbox.clear()
        send_saas_master_key_email("KP-TEST-KEY", "Enterprise", status["expires_at"], sync=True)
        self.assert_mail(1, [CLIENT_EMAIL, "info@kpregtech.com"], "Master License Key", "KP-TEST-KEY")
        mail.outbox.clear()
        send_saas_purchase_request_emails("1_year", "Enterprise", "$1,200", sync=True)
        self.assert_mail(2, [CLIENT_EMAIL, "info@kpregtech.com"], "Enterprise")

    def test_admin_2fa_email_uses_admin_address(self):
        request = type("Request", (), {"session": {}})()
        user = type("User", (), {"pk": 1, "username": "admin", "email": ADMIN_EMAIL, "get_display_name": lambda self: "Admin"})()
        send_2fa_otp(user, request, sync=True)
        self.assert_mail(1, [ADMIN_EMAIL], "2-Way Verification")

    def test_all_email_templates_render_with_real_context(self):
        context = {"booking": self.booking, "submission": self.submission, "testimonial": self.testimonial,
                   "saas_status": {"days_remaining": 7, "expires_at": timezone.now()}, "days_remaining": 7,
                   "plan_name": "Enterprise", "expires_at": timezone.now(), "license_key": "KP-TEST-KEY",
                   "provider_email": "info@kpregtech.com", "site_url": "http://testserver"}
        templates = [
            "emails/consultation_booking_email.html", "emails/consultation_status_update_email.html",
            "emails/contact_confirmation_email.html", "emails/contact_admin_alert_email.html",
            "emails/testimonial_received_email.html", "emails/testimonial_published_email.html",
            "emails/saas_warning_email.html", "emails/saas_locked_email.html", "emails/saas_master_key_email.html",
        ]
        for template in templates:
            html = render_to_string(template, context)
            self.assertGreater(len(html), 100, template)
            self.assertNotIn("{{ booking.consultation_time|time", html, template)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", ADMIN_NOTIFICATION_EMAIL=ADMIN_EMAIL, SABIN_CLIENT_EMAIL=CLIENT_EMAIL)
class WorkflowAndSaaSTest(TestCase):
    def test_booking_status_api_and_reschedule(self):
        booking = ConsultationBooking.objects.create(
            client_name="Workflow", email=CLIENT_EMAIL, phone="1", consultation_date=dt.date.today() + dt.timedelta(days=2), consultation_time=dt.time(10)
        )
        api = self.client.get(reverse("login:consultation_track_api"), {"key": booking.reference_key})
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api.json()["data"]["reference_key"], booking.reference_key)
        booking.consultation_date += dt.timedelta(days=1)
        booking.save()
        booking.refresh_from_db()
        self.assertEqual(booking.status, "rescheduled")
        self.assertEqual(booking.previous_date, dt.date.today() + dt.timedelta(days=2))

    def test_saas_keys_and_lock_lifecycle(self):
        valid, plan, _ = validate_license_key("VINTUSHTECH-KPREGTECH-MASTER-2026")
        self.assertTrue(valid)
        self.assertTrue(plan)
        subscription, _ = unlock_subscription_with_plan(plan, license_key="VINTUSHTECH-KPREGTECH-MASTER-2026")
        self.assertFalse(subscription.is_locked)
        self.assertFalse(get_saas_status()["is_locked"])

    def test_project_assets_and_security_routes(self):
        for path in ["login/static/login/css/home.css", "login/static/login/css/about.css", "login/static/login/css/consultation.css"]:
            self.assertTrue((settings.BASE_DIR / path).exists(), path)
        self.assertIn(self.client.get("/admin/").status_code, [403, 404])
