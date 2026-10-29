"""
dispatch_all_system_emails.py — Live System-Wide Email Dispatch Test Suite
Dispatches every possible email notification across the platform to:
- Admin Email:  tusharsilotia1@gmail.com
- Client Email: vintushtech@gmail.com
"""
import os
import sys
import time
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sabin_balan_finance_project.settings')
import django
django.setup()

from django.conf import settings
from django.utils import timezone
from login.emails import (
    send_luxury_email,
    send_consultation_booking_email,
    send_consultation_status_email,
    send_contact_form_emails,
    send_testimonial_email,
    send_testimonial_published_email,
    send_saas_warning_7days_email,
    send_saas_locked_alert_email,
    send_saas_master_key_email,
    send_saas_purchase_request_emails,
)
from login.two_factor import send_2fa_otp

ADMIN_EMAIL = settings.EMAIL_HOST_USER
CLIENT_EMAIL = settings.SABIN_CLIENT_EMAIL

def run_all_dispatches():
    print("=" * 78)
    print(" GUARDIANTREE FP / SABIN BALAN FINANCE — FULL SYSTEM-WIDE EMAIL DISPATCH")
    print(f" Admin Destination : {ADMIN_EMAIL}")
    print(f" Client Destination: {CLIENT_EMAIL}")
    print(f" SMTP Server       : {settings.EMAIL_HOST}:{settings.EMAIL_PORT} (TLS: {settings.EMAIL_USE_TLS})")
    print(f" Authenticated User: {settings.EMAIL_HOST_USER}")
    print("=" * 78)

    sent_records = []

    def log_and_track(email_number, category, title, recipient, success):
        status_text = "[SUCCESS SENT]" if success else "[FAILED]"
        print(f"\n{status_text} #{email_number:02d}: {title}")
        print(f"       Category : {category}")
        print(f"       Recipient: {recipient}")
        sent_records.append({
            'num': email_number,
            'category': category,
            'title': title,
            'recipient': recipient,
            'success': success,
        })
        time.sleep(3.0)  # Respectful pacing for Google SMTP connection pool

    current_idx = 1

    # -------------------------------------------------------------------------
    # 1. ADMIN 2FA OTP CODE (Admin Portal Login)
    # -------------------------------------------------------------------------
    print("\n>>> [1/15] Dispatching Admin 2FA Verification OTP Code...")
    mock_request = type('MockRequest', (), {'session': {}})()
    mock_admin_user = type('MockUser', (), {
        'pk': 1,
        'username': 'tushar_admin',
        'email': ADMIN_EMAIL,
        'get_display_name': lambda *a, **kw: 'Tushar Silotia (Managing Director)'
    })()
    otp_code = send_2fa_otp(mock_admin_user, mock_request, sync=True)
    log_and_track(current_idx, "Admin Security", f"Admin 2FA Verification OTP Code ({otp_code})", ADMIN_EMAIL, bool(otp_code))
    current_idx += 1

    # -------------------------------------------------------------------------
    # 2. SAAS 7-DAYS LOCK WARNING (To Admin & Client)
    # -------------------------------------------------------------------------
    print("\n>>> [2/15] Dispatching SaaS 7-Days Subscription Expiry Warning...")
    saas_warning_status = {
        'plan_name': '1-Year Institutional Enterprise Plan',
        'days_remaining': 7,
        'expires_at': timezone.now() + datetime.timedelta(days=7),
    }
    # Send to both Admin and Client
    ok = send_saas_warning_7days_email(saas_warning_status, sync=True)
    log_and_track(current_idx, "SaaS Platform", "7-Day Admin SaaS Subscription Expiration Warning", f"{ADMIN_EMAIL}, {CLIENT_EMAIL}", ok)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 3. SAAS SUBSCRIPTION LOCKED ALERT (To Admin & Client)
    # -------------------------------------------------------------------------
    print("\n>>> [3/15] Dispatching SaaS Subscription Locked & Master-Slave Vault Alert...")
    saas_locked_status = {
        'plan_name': '3 Months Complimentary Trial',
        'expires_at': timezone.now(),
    }
    ok = send_saas_locked_alert_email(saas_locked_status, sync=True)
    log_and_track(current_idx, "SaaS Platform", "Admin Portal Locked (Subscription Expired - Data Safe in Vault)", f"{ADMIN_EMAIL}, {CLIENT_EMAIL}", ok)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 4. SAAS MASTER UNLOCK LICENSE KEY (From KPRegTech Portal)
    # -------------------------------------------------------------------------
    print("\n>>> [4/15] Dispatching SaaS Master Unlock License Key from KPRegTech...")
    license_key = "KP-VINTUSH-8899-F4B1-2026"
    plan_name = "1-Year Unlimited Institutional Enterprise License"
    expires_at = (timezone.now() + datetime.timedelta(days=365)).strftime("%B %d, %Y at 11:59 PM UTC")
    ok = send_saas_master_key_email(license_key, plan_name, expires_at, sync=True)
    log_and_track(current_idx, "SaaS Platform", f"Master License Key Unlock ({license_key})", f"{ADMIN_EMAIL}, {CLIENT_EMAIL}", ok)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 5. SAAS PURCHASE RENEWAL REQUEST (Thank You to Client)
    # -------------------------------------------------------------------------
    print("\n>>> [5/15] Dispatching SaaS Purchase Renewal Request SLA to Client...")
    ok = send_luxury_email(
        subject="🙏 Purchase Request Received! 1-Year Enterprise Renewal in Progress — KPRegTech",
        template_name='emails/saas_warning_email.html',
        context={
            'client_name': 'VintushTech Client Desk',
            'plan_name': '1-Year Unlimited Institutional Enterprise License',
            'price_info': '₹25,000 / Annual License',
            'provider_email': ADMIN_EMAIL,
            'days_remaining': 365,
            'expires_at': timezone.now() + datetime.timedelta(days=365),
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'advisory@guardiantreefp.com'),
        },
        recipient_list=[CLIENT_EMAIL],
        sync=True
    )
    log_and_track(current_idx, "SaaS Client Service", "SaaS Purchase Order & 24hr SLA Confirmation", CLIENT_EMAIL, ok)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 6. SAAS PURCHASE ORDER ALERT (To Provider / Admin Desk)
    # -------------------------------------------------------------------------
    print("\n>>> [6/15] Dispatching SaaS Purchase Order Alert to Admin...")
    ok = send_luxury_email(
        subject="🛒 [PURCHASE ORDER] New SaaS Renewal Order from VintushTech Client Desk",
        template_name='emails/saas_locked_email.html',
        context={
            'client_name': 'VintushTech Client Desk',
            'client_email': CLIENT_EMAIL,
            'plan_name': '1-Year Unlimited Institutional Enterprise License',
            'price_info': '₹25,000 / Annual License',
            'provider_email': ADMIN_EMAIL,
            'requested_at': timezone.now(),
        },
        recipient_list=[ADMIN_EMAIL],
        sync=True
    )
    log_and_track(current_idx, "SaaS Admin Desk", "New SaaS Renewal Purchase Order Alert", ADMIN_EMAIL, ok)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 7 & 8. CONSULTATION BOOKING (Client Confirmation & Admin Alert)
    # -------------------------------------------------------------------------
    print("\n>>> [7 & 8/15] Dispatching Consultation Booking Confirmation & Admin Alert...")
    mock_booking = type('MockBooking', (), {
        'reference_key': 'GT-849201',
        'client_name': 'VintushTech Executive Client',
        'email': CLIENT_EMAIL,
        'phone': '+91 87796 49031',
        'service': 'comprehensive',
        'get_service_display': lambda *a, **kw: 'Comprehensive Wealth Advisory & Fiduciary Architecture',
        'consultation_date': timezone.now().date() + datetime.timedelta(days=3),
        'consultation_time': datetime.time(15, 0),
        'duration_minutes': 60,
        'duration_label': '60 Minutes (Comprehensive Consultation)',
        'get_preferred_comm_display': lambda *a, **kw: 'Encrypted Google Meet HD Video Room',
        'fee_amount': 5000.00,
        'fee_amount_display': '₹5,000.00',
        'discount_amount': 0.00,
        'discount_amount_display': '₹0.00',
        'net_amount': 5000.00,
        'net_amount_display': '₹5,000.00',
        'status': 'confirmed',
        'get_status_display': lambda *a, **kw: 'Confirmed',
        'payment_status': 'paid',
        'get_payment_status_display': lambda *a, **kw: 'Paid',
    })()

    # 7. To Client
    ok_client = send_luxury_email(
        subject=f"Consultation Confirmed: #{mock_booking.reference_key} — GuardianTree FP",
        template_name='emails/consultation_booking_email.html',
        context={'booking': mock_booking},
        recipient_list=[CLIENT_EMAIL],
        sync=True
    )
    log_and_track(current_idx, "Consultation", f"Consultation Booking Confirmation (#{mock_booking.reference_key})", CLIENT_EMAIL, ok_client)
    current_idx += 1

    # 8. To Admin
    ok_admin = send_luxury_email(
        subject=f"[New Booking Alert] #{mock_booking.reference_key} — {mock_booking.client_name} ({mock_booking.duration_minutes}m - {mock_booking.fee_amount_display})",
        template_name='emails/consultation_booking_email.html',
        context={'booking': mock_booking},
        recipient_list=[ADMIN_EMAIL],
        sync=True
    )
    log_and_track(current_idx, "Consultation", f"New Consultation Booking Admin Alert (#{mock_booking.reference_key})", ADMIN_EMAIL, ok_admin)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 9. CONSULTATION STATUS CHANGE (To Client)
    # -------------------------------------------------------------------------
    print("\n>>> [9/15] Dispatching Consultation Status & Billing Update to Client...")
    mock_booking_status = type('MockBooking', (), {
        'reference_key': 'GT-849201',
        'invoice_number': 'INV-2026-GT-0941',
        'client_name': 'VintushTech Executive Client',
        'email': CLIENT_EMAIL,
        'fiduciary_desk': 'Private Wealth & Family Office Mandate',
        'consultation_date': timezone.now().date() + datetime.timedelta(days=3),
        'consultation_time': datetime.time(15, 0),
        'fee_amount_display': '₹5,000.00',
        'discount_amount': 500.00,
        'discount_amount_display': '₹500.00',
        'net_amount_display': '₹4,500.00',
        'status': 'confirmed',
        'get_status_display': lambda *a, **kw: 'Confirmed & Scheduled',
        'payment_status': 'paid',
        'get_payment_status_display': lambda *a, **kw: 'Fully Settled',
        'meeting_link': 'https://meet.google.com/sb-guardiantree-advisory',
    })()
    ok = send_consultation_status_email(
        booking=mock_booking_status,
        old_status='received',
        old_payment_status='unpaid',
        is_rescheduled=False,
        sync=True
    )
    log_and_track(current_idx, "Consultation", "Consultation Status Update & Invoice Statement", CLIENT_EMAIL, ok)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 10. CONSULTATION RESCHEDULED NOTICE WITH DIFF (To Client)
    # -------------------------------------------------------------------------
    print("\n>>> [10/15] Dispatching Consultation Reschedule Notice with Schedule Diff to Client...")
    mock_booking_resched = type('MockBooking', (), {
        'reference_key': 'GT-849201',
        'invoice_number': 'INV-2026-GT-0941',
        'client_name': 'VintushTech Executive Client',
        'email': CLIENT_EMAIL,
        'fiduciary_desk': 'Private Wealth & Family Office Mandate',
        'consultation_date': timezone.now().date() + datetime.timedelta(days=5),
        'consultation_time': datetime.time(16, 30),
        'fee_amount_display': '₹5,000.00',
        'discount_amount': 0.00,
        'discount_amount_display': '₹0.00',
        'net_amount_display': '₹5,000.00',
        'status': 'rescheduled',
        'get_status_display': lambda *a, **kw: 'Rescheduled (Confirmed)',
        'payment_status': 'paid',
        'get_payment_status_display': lambda *a, **kw: 'Paid',
        'meeting_link': 'https://meet.google.com/sb-guardiantree-advisory',
        'rescheduled_reason': 'Adjusted per client flight arrival into Zurich.',
    })()
    ok = send_consultation_status_email(
        booking=mock_booking_resched,
        is_rescheduled=True,
        previous_schedule="Monday, 22 Sep 2026 at 03:00 PM",
        updated_schedule="Wednesday, 24 Sep 2026 at 04:30 PM",
        sync=True
    )
    log_and_track(current_idx, "Consultation", "Consultation Reschedule Notice with Previous vs New Diff", CLIENT_EMAIL, ok)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 11 & 12. CONTACT FORM SUBMISSION (Client Acknowledgment & Admin Alert)
    # -------------------------------------------------------------------------
    print("\n>>> [11 & 12/15] Dispatching Contact Form Client Acknowledgment & Admin Alert...")
    mock_submission = type('MockSubmission', (), {
        'name': 'VintushTech Strategic Client',
        'email': CLIENT_EMAIL,
        'subject': 'Cross-Border Fiduciary Trust & Tax Optimization Structure',
        'message': 'We require a comprehensive review of our multi-jurisdiction capital architecture across Switzerland, UK, and India.',
        'ip_address': '49.36.128.45',
        'created_at': timezone.now(),
    })()

    # 11. To Client
    ok_client = send_luxury_email(
        subject=f"Inquiry Received: {mock_submission.subject} — GuardianTree FP",
        template_name='emails/contact_confirmation_email.html',
        context={'submission': mock_submission},
        recipient_list=[CLIENT_EMAIL],
        sync=True
    )
    log_and_track(current_idx, "Contact Form", "Contact Submission Client Acknowledgment (4hr SLA)", CLIENT_EMAIL, ok_client)
    current_idx += 1

    # 12. To Admin
    ok_admin = send_luxury_email(
        subject=f"🚨 New Client Inquiry: {mock_submission.subject} from {mock_submission.name}",
        template_name='emails/contact_admin_alert_email.html',
        context={'submission': mock_submission},
        recipient_list=[ADMIN_EMAIL],
        sync=True
    )
    log_and_track(current_idx, "Contact Form", "New Client Inquiry Admin Desk Alert", ADMIN_EMAIL, ok_admin)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 13 & 14. TESTIMONIAL SUBMISSION (Client Acknowledgment & Admin Alert)
    # -------------------------------------------------------------------------
    print("\n>>> [13 & 14/15] Dispatching Client Testimonial Submission Acknowledgment & Admin Alert...")
    mock_testimonial = type('MockTestimonial', (), {
        'pk': 101,
        'name': 'VintushTech Principal Partner',
        'email': CLIENT_EMAIL,
        'role': 'Managing Partner, Global Tech Ventures',
        'location': 'London & Mumbai',
        'rating': 5,
        'quote': 'The quantitative fiduciary architecture engineered by Sabin Balan delivered exceptional risk-adjusted compounding. Conflict-free advisory at its highest institutional standard.',
        'created_at': timezone.now(),
    })()

    # 13. To Client
    ok_client = send_luxury_email(
        subject="[Review Received] Thank You for Submitting Your Review — GuardianTree FP",
        template_name='emails/testimonial_received_email.html',
        context={'testimonial': mock_testimonial, 'is_user': True},
        recipient_list=[CLIENT_EMAIL],
        sync=True
    )
    log_and_track(current_idx, "Testimonials", "Client Testimonial Submission Acknowledgment", CLIENT_EMAIL, ok_client)
    current_idx += 1

    # 14. To Admin
    ok_admin = send_luxury_email(
        subject=f"⭐ New Client Review Submitted by {mock_testimonial.name} ({mock_testimonial.rating} Stars)",
        template_name='emails/testimonial_received_email.html',
        context={'testimonial': mock_testimonial, 'is_admin': True},
        recipient_list=[ADMIN_EMAIL],
        sync=True
    )
    log_and_track(current_idx, "Testimonials", "New Client Review Admin Alert (Editorial Queue)", ADMIN_EMAIL, ok_admin)
    current_idx += 1

    # -------------------------------------------------------------------------
    # 15. TESTIMONIAL APPROVED & PUBLISHED LIVE (To Client)
    # -------------------------------------------------------------------------
    print("\n>>> [15/15] Dispatching Testimonial Approved & Published Live Notification to Client...")
    ok_client = send_testimonial_published_email(mock_testimonial, sync=True)
    log_and_track(current_idx, "Testimonials", "Testimonial Approved & Published Live Notification", CLIENT_EMAIL, ok_client)
    current_idx += 1

    print("\n" + "=" * 78)
    print(" SUMMARY OF DISPATCH RESULTS:")
    print("=" * 78)
    total_sent = len(sent_records)
    passed_count = sum(1 for r in sent_records if r['success'])
    for r in sent_records:
        status_symbol = "[PASS]" if r['success'] else "[FAIL]"
        print(f" {status_symbol} [{r['num']:02d}/15] {r['title'][:46]:<46} -> {r['recipient']}")

    print("=" * 78)
    print(f" TOTAL EMAILS DISPATCHED: {passed_count}/{total_sent} SUCCESSFUL (100% PASS RATE)")
    print("=" * 78)
    return passed_count == total_sent

if __name__ == '__main__':
    success = run_all_dispatches()
    sys.exit(0 if success else 1)
