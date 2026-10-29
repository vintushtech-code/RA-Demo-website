"""
Sabin Balan Finance — Centralized Luxury Email & Terminal Dispatch Service.
Handles HTML email rendering, fallback generation, context injection, and console/SMTP routing.

To switch from Terminal (Console) Mode to Real SMTP:
1. Open sabin_balan_finance_project/settings.py
2. Set EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
3. Provide EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS = True
"""

import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

import threading

def _async_send(subject, message, sender, recipient_list, html_message, fail_silently, connection=None):
    try:
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=sender,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=fail_silently,
            connection=connection
        )
        logger.info("[Email Engine] Dispatched async email '%s' to %s (Sent: %s)", subject, recipient_list, sent_count)
    except Exception as e:
        logger.error("[Email Engine] Failed to dispatch async email '%s' to %s: %s", subject, recipient_list, e)

def send_luxury_email(subject, template_name, context, recipient_list, from_email=None, fail_silently=True, sync=False, connection=None):
    """
    Renders and sends a premium branded HTML email with automatic plain-text fallback.
    Dispatches via non-blocking asynchronous background thread for instant HTTP response speed,
    or synchronously if sync=True.
    """
    if not recipient_list:
        logger.warning("[Email Engine] No recipients specified for email: %s", subject)
        return False

    # Default branding context
    default_context = {
        'site_name': getattr(settings, 'SITE_NAME', 'GuardianTree FP'),
        'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
        'contact_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'advisory@guardiantreefp.com'),
    }
    merged_context = {**default_context, **context}

    sender = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'advisory@guardiantreefp.com')

    try:
        html_message = render_to_string(template_name, merged_context)
        plain_message = strip_tags(html_message).strip()
    except Exception as e:
        logger.error("[Email Engine] Error rendering email template %s: %s", template_name, e)
        plain_message = f"GuardianTree FP Notification: {subject}"
        html_message = None

    recipients_str = ", ".join(recipient_list)
    try:
        print("\n" + "=" * 70)
        print(f"[GUARDIANTREE FP {'SYNC' if sync else 'ASYNC'} EMAIL DISPATCH]")
        print(f"   To:      {recipients_str}")
        print(f"   From:    {sender}")
        print(f"   Subject: {subject}")
        print("=" * 70 + "\n")
    except Exception:
        pass

    if sync:
        try:
            sent_count = send_mail(
                subject=subject,
                message=plain_message,
                from_email=sender,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=fail_silently,
                connection=connection
            )
            return sent_count > 0
        except Exception as e:
            logger.error("[Email Engine] Failed to dispatch sync email '%s' to %s: %s", subject, recipient_list, e)
            if not fail_silently:
                raise
            return False

    try:
        thread = threading.Thread(
            target=_async_send,
            args=(subject, plain_message, sender, recipient_list, html_message, fail_silently, connection)
        )
        thread.daemon = True
        thread.start()
        return True
    except Exception as e:
        logger.error("[Email Engine] Error launching email thread for '%s': %s", subject, e)
        return False


# ------------------------------------------------------------------------------
# Specialized Domain Email Dispatchers
# ------------------------------------------------------------------------------

def send_consultation_booking_email(booking, **kwargs):
    """
    Sends consultation booking confirmation to client and admin notification.
    """
    subject = f"Consultation Confirmed: #{booking.reference_key} — GuardianTree FP"
    context = {
        'booking': booking,
    }
    # 1. Send confirmation to Client
    send_luxury_email(
        subject=subject,
        template_name='emails/consultation_booking_email.html',
        context=context,
        recipient_list=[booking.email],
        **kwargs
    )

    # 2. Send notification to Admin Desk
    admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', 'tusharsilotia1@gmail.com')
    if admin_email and admin_email != booking.email:
        admin_subject = f"[New Booking] #{booking.reference_key} — {booking.client_name} ({booking.duration_minutes}m - {booking.fee_amount_display})"
        send_luxury_email(
            subject=admin_subject,
            template_name='emails/consultation_booking_email.html',
            context=context,
            recipient_list=[admin_email],
            **kwargs
        )


def send_consultation_status_email(booking, old_status=None, old_payment_status=None, is_rescheduled=False, previous_schedule=None, updated_schedule=None, **kwargs):
    """
    Dispatches dynamic status change and schedule revision notification to client.
    """
    status_label = booking.get_status_display()
    payment_label = booking.get_payment_status_display()
    subject = f"Update on Consultation #{booking.reference_key}: {status_label} ({payment_label})"
    
    context = {
        'booking': booking,
        'old_status': old_status,
        'old_payment_status': old_payment_status,
        'is_rescheduled': is_rescheduled,
        'previous_schedule': previous_schedule,
        'updated_schedule': updated_schedule,
    }
    
    return send_luxury_email(
        subject=subject,
        template_name='emails/consultation_status_update_email.html',
        context=context,
        recipient_list=[booking.email],
        **kwargs
    )


def send_contact_form_emails(submission, **kwargs):
    """
    Sends client acknowledgement and admin alert on contact form submissions.
    """
    # 1. Confirmation to Client
    client_subject = f"Inquiry Received: {submission.subject} — GuardianTree FP"
    send_luxury_email(
        subject=client_subject,
        template_name='emails/contact_confirmation_email.html',
        context={'submission': submission},
        recipient_list=[submission.email],
        **kwargs
    )

    # 2. Alert to Admin
    admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', getattr(settings, 'CONTACT_FORM_EMAIL_RECIPIENT', 'tusharsilotia1@gmail.com'))
    admin_subject = f"🚨 New Client Inquiry: {submission.subject} from {submission.name}"
    send_luxury_email(
        subject=admin_subject,
        template_name='emails/contact_admin_alert_email.html',
        context={'submission': submission},
        recipient_list=[admin_email],
        **kwargs
    )
    return True


def send_testimonial_email(testimonial, **kwargs):
    """
    Sends acknowledgement to user and admin notification on new review submission.
    """
    # 1. User Acknowledgement
    if testimonial.email:
        user_subject = f"[Review Received] Thank You for Submitting Your Review — GuardianTree FP"
        send_luxury_email(
            subject=user_subject,
            template_name='emails/testimonial_received_email.html',
            context={'testimonial': testimonial, 'is_user': True},
            recipient_list=[testimonial.email],
            **kwargs
        )

    # 2. Admin Alert
    admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', 'tusharsilotia1@gmail.com')
    admin_subject = f"⭐ New Client Review Submitted by {testimonial.name} ({testimonial.rating} Stars)"
    return send_luxury_email(
        subject=admin_subject,
        template_name='emails/testimonial_received_email.html',
        context={'testimonial': testimonial, 'is_admin': True},
        recipient_list=[admin_email],
        **kwargs
    )


def send_testimonial_published_email(testimonial, **kwargs):
    """
    Sends congratulations email to reviewer when their testimonial is published live on the platform.
    """
    if not testimonial.email:
        logger.warning("[Email Engine] No email associated with testimonial #%s", testimonial.pk)
        return False

    subject = f"🎉 Congratulations! Your Review is Now Live & Verified — GuardianTree FP"
    context = {
        'testimonial': testimonial,
    }
    return send_luxury_email(
        subject=subject,
        template_name='emails/testimonial_published_email.html',
        context=context,
        recipient_list=[testimonial.email],
        **kwargs
    )


def send_saas_warning_7days_email(saas_status, **kwargs):
    """
    Dispatches 7-day expiration warning email to both Sabin Balan and KPRegTech.
    """
    sabin_email = getattr(settings, 'SABIN_CLIENT_EMAIL', 'vintushtech@gmail.com')
    provider_email = getattr(settings, 'PROVIDER_EMAIL', 'info@kpregtech.com')
    recipients = [sabin_email, provider_email]
    subject = "⚠️ Action Required: 7 Days Remaining on GuardianTree FP Admin SaaS Subscription"
    context = {
        'saas_status': saas_status,
        'days_remaining': saas_status.get('days_remaining', 7),
        'expires_at': saas_status.get('expires_at'),
        'plan_name': saas_status.get('plan_name'),
        'provider_email': provider_email,
    }
    return send_luxury_email(
        subject=subject,
        template_name='emails/saas_warning_email.html',
        context=context,
        recipient_list=recipients,
        **kwargs
    )


def send_saas_locked_alert_email(saas_status, **kwargs):
    """
    Dispatches immediate Lock Alert email to both Sabin Balan and KPRegTech.
    """
    sabin_email = getattr(settings, 'SABIN_CLIENT_EMAIL', 'vintushtech@gmail.com')
    provider_email = getattr(settings, 'PROVIDER_EMAIL', 'info@kpregtech.com')
    recipients = [sabin_email, provider_email]
    subject = "🔒 Alert: GuardianTree FP Admin Panel Has Been Locked (Subscription Expired)"
    context = {
        'saas_status': saas_status,
        'expires_at': saas_status.get('expires_at'),
        'plan_name': saas_status.get('plan_name'),
        'provider_email': provider_email,
    }
    return send_luxury_email(
        subject=subject,
        template_name='emails/saas_locked_email.html',
        context=context,
        recipient_list=recipients,
        **kwargs
    )


def send_saas_master_key_email(license_key, plan_name, expires_at, **kwargs):
    """
    Dispatches Master License Key & Unlock notification email to Sabin Balan and KPRegTech.
    """
    sabin_email = getattr(settings, 'SABIN_CLIENT_EMAIL', 'vintushtech@gmail.com')
    provider_email = getattr(settings, 'PROVIDER_EMAIL', 'info@kpregtech.com')
    recipients = [sabin_email, provider_email]
    subject = "🎉 Congratulations! Here is Your Master License Key — GuardianTree FP"
    context = {
        'license_key': license_key,
        'plan_name': plan_name,
        'expires_at': expires_at,
        'provider_email': provider_email,
    }
    return send_luxury_email(
        subject=subject,
        template_name='emails/saas_master_key_email.html',
        context=context,
        recipient_list=recipients,
        **kwargs
    )


def send_saas_purchase_request_emails(plan_code, plan_name, price_info, **kwargs):
    """
    1. Dispatches automated Purchase Request email to provider (KPRegTech).
    2. Dispatch automated Thank You & 24hr SLA confirmation email to Sabin Balan.
    """
    from django.utils import timezone

    sabin_email = getattr(settings, 'SABIN_CLIENT_EMAIL', 'vintushtech@gmail.com')
    provider_email = getattr(settings, 'PROVIDER_EMAIL', 'info@kpregtech.com')

    # 1. Dispatch Request Email to Provider (KPRegTech)
    subject_provider = f"🛒 [PURCHASE REQUEST] SaaS Order: {plan_name} — Sabin Balan (GuardianTree FP)"
    context_provider = {
        'client_name': 'Sabin Balan (Founder, GuardianTree FP)',
        'client_email': sabin_email,
        'plan_name': plan_name,
        'price_info': price_info,
        'provider_email': provider_email,
        'requested_at': timezone.now(),
    }
    send_luxury_email(
        subject=subject_provider,
        template_name='emails/saas_locked_email.html',
        context=context_provider,
        recipient_list=[provider_email],
        **kwargs
    )

    # 2. Dispatch Thank You & SLA Acknowledgement Email to Client (Sabin Balan)
    subject_client = f"🙏 Purchase Request Received! {plan_name} Renewal in Progress — KPRegTech"
    context_client = {
        'client_name': 'Sabin Balan',
        'plan_name': plan_name,
        'price_info': price_info,
        'provider_email': provider_email,
        'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'advisory@guardiantreefp.com'),
    }
    send_luxury_email(
        subject=subject_client,
        template_name='emails/saas_warning_email.html',
        context=context_client,
        recipient_list=[sabin_email],
        **kwargs
    )




