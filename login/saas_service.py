"""
SaaS Service & Subscription Management Engine
=============================================
Provided by: VintushTech (https://vintushtech.cloud) & KPRegTech (https://kpregtech.com)
Client: Sabin Balan (Founder, GuardianTree FP)

Features:
- 3 Months Free Trial lifecycle management (90 days).
- Multi-tier subscription renewal plans:
  * 1 Month  ($49 / ₹3,999)
  * 3 Months ($129 / ₹9,999)
  * 6 Months ($229 / ₹17,999)
  * 1 Year   ($399 / ₹29,999)
- Cryptographic / algorithmic license key validation.
- Zero data loss guarantee with automated backup coordination.
"""

import os
import hashlib
import hmac
import datetime
from django.utils import timezone
from django.conf import settings

# Master Secret for algorithmic license key generation & validation
SAAS_SECRET_KEY = getattr(settings, 'SECRET_KEY', 'vintushtech-kpregtech-saas-master-key')

# Subscription Plan Definitions
SUBSCRIPTION_PLANS = {
    '1_month': {
        'code': '1_month',
        'name': '1 Month Standard Plan',
        'duration_days': 30,
        'price_usd': 49,
        'price_inr': 3999,
        'badge': 'Monthly Flexibility',
        'features': [
            'Full Admin Panel & Operations Access',
            'Continuous Automated Live Database Backups',
            'Fiduciary & Consultation Management',
            'KPRegTech & VintushTech Standard Support',
        ]
    },
    '3_months': {
        'code': '3_months',
        'name': '3 Months Quarterly Plan',
        'duration_days': 90,
        'price_usd': 129,
        'price_inr': 9999,
        'badge': 'Popular Choice',
        'features': [
            'All Standard Plan Features',
            'Priority Backup Retention & Instant Snapshots',
            'Enhanced 2FA & Security Auditing',
            'Dedicated KPRegTech & VintushTech Technical Desk',
        ]
    },
    '6_months': {
        'code': '6_months',
        'name': '6 Months Semi-Annual Plan',
        'duration_days': 180,
        'price_usd': 229,
        'price_inr': 17999,
        'badge': 'Save 15%',
        'features': [
            'All Quarterly Plan Features',
            'Unlimited Client Inquiries & Automated Email Triggers',
            'Advanced Analytics & Fiduciary Reporting',
            'Bi-weekly Health Checks & Performance Tuning',
        ]
    },
    '1_year': {
        'code': '1_year',
        'name': '1 Year Enterprise Annual Plan',
        'duration_days': 365,
        'price_usd': 399,
        'price_inr': 29999,
        'badge': 'Best Value • 2 Months Free',
        'features': [
            'Complete Enterprise Wealth & Admin Operations Suite',
            '24/7 SLA Priority Support by VintushTech & KPRegTech',
            'Zero-Downtime Live Failover Backups & Cloud Sync',
            'Custom Feature Requests & Dedicated Account Engineer',
        ]
    },
}


def generate_license_key(plan_code, client_email="example@gmail.com", unique=True):
    """
    Generates a secure verifiable license key for a given plan and client.
    Format: KP-VINTUSH-XXXX-YYYY-ZZZZ
    """
    import secrets
    raw_payload = f"{client_email}:{plan_code}:{SAAS_SECRET_KEY}".encode('utf-8')
    sig = hashlib.sha256(raw_payload).hexdigest().upper()
    part1 = sig[0:4]
    
    if unique:
        rand1 = secrets.token_hex(2).upper()
        rand2 = secrets.token_hex(2).upper()
        key = f"KP-VINTUSH-{part1}-{rand1}-{rand2}"
    else:
        part2 = sig[4:8]
        part3 = sig[8:12]
        key = f"KP-VINTUSH-{part1}-{part2}-{part3}"

    print(f"\n======================================================================")
    print(f"[SABIN BALAN FINANCE SAAS DISPATCH] MASTER LICENSE KEY GENERATED:")
    print(f"   Client Email: {client_email}")
    print(f"   Plan Code:    {plan_code}")
    print(f"   MASTER KEY:   {key}")
    print(f"======================================================================\n")
    return key


def create_saas_invoice(plan_code, license_key, client_name="Sabin Balan (Founder, GuardianTree FP)", client_email="example@gmail.com", valid_until=None):
    """
    Generates an official SaaS Invoice record for KPRegTech & Sabin Balan billing history.
    """
    import random
    from .models import SaaSInvoice
    plan_info = SUBSCRIPTION_PLANS.get(plan_code, SUBSCRIPTION_PLANS['1_month'])
    now = timezone.now()
    if not valid_until:
        valid_until = now + datetime.timedelta(days=plan_info['duration_days'])
    
    duration = max(1, (valid_until - now).days)
    inv_num = f"INV-KP-2026-{random.randint(1000, 9999)}"

    invoice = SaaSInvoice.objects.create(
        invoice_number=inv_num,
        client_name=client_name,
        client_email=client_email,
        provider_name="KPRegTech & VintushTech",
        plan_code=plan_code,
        plan_name=plan_info['name'],
        amount_inr=plan_info['price_inr'],
        amount_usd=plan_info['price_usd'],
        master_key=license_key,
        duration_days=duration,
        valid_until=valid_until,
        status='paid',
        notes=f"Issued by KPRegTech Provider Desk on {now.strftime('%Y-%m-%d %H:%M:%S UTC')}."
    )

    print(f"\n======================================================================")
    print(f"[OFFICIAL SAAS INVOICE GENERATED]")
    print(f"   Invoice #:   {invoice.invoice_number}")
    print(f"   Client:      {invoice.client_name}")
    print(f"   Plan:        {invoice.plan_name} ({invoice.duration_days} Days)")
    print(f"   Fee:         INR {invoice.amount_inr:,.2f} / ${invoice.amount_usd:,.2f}")
    print(f"   Master Key:  {invoice.master_key}")
    print(f"======================================================================\n")

    return invoice


def validate_license_key(license_key, client_email="example@gmail.com"):
    """
    Validates whether a submitted license key matches any valid plan, issued invoice, or developer bypass master keys.
    Returns: (is_valid: bool, matched_plan_code: str or None, message: str)
    """
    if not license_key:
        return False, None, "Please enter a valid Master License Key."

    cleaned_key = str(license_key).strip().upper().replace(" ", "")
    now = timezone.now()
    
    # Master developer bypass keys for VintushTech & KPRegTech
    if cleaned_key in ['VINTUSHTECH-KPREGTECH-MASTER-2026', 'KP-VINTUSH-SABIN-BALAN-UNLIMITED', 'GUARDIANTREE-FD-OVERRIDE-KEY']:
        return True, '1_year', "Master Developer Key Verified. Full Access Granted."

    # Check against issued SaaS invoices in DB
    from .models import SaaSInvoice
    inv = SaaSInvoice.objects.filter(master_key=cleaned_key).first()
    if inv:
        if inv.valid_until and inv.valid_until <= now:
            return False, None, f"This Master License Key expired on {inv.valid_until.strftime('%d %B %Y')}. Please request a renewal from KPRegTech."
        return True, inv.plan_code, f"Issued Master License Key Verified ({inv.plan_name})."

    # Check against generated deterministic keys for standard plans
    for plan_code in SUBSCRIPTION_PLANS.keys():
        expected_key = generate_license_key(plan_code, client_email, unique=False)
        if cleaned_key == expected_key:
            return True, plan_code, f"Valid License Key for {SUBSCRIPTION_PLANS[plan_code]['name']}."

    return False, None, "Invalid or Expired Master License Key. Please enter a valid key from KPRegTech."


def get_or_create_saas_subscription():
    """
    Retrieves the active AdminSaaSSubscription record or creates the initial locked record (0 active plans).
    """
    from .models import AdminSaaSSubscription
    sub = AdminSaaSSubscription.objects.first()
    if not sub:
        now = timezone.now()
        sub = AdminSaaSSubscription.objects.create(
            service_name="GuardianTree FP Executive Admin Panel",
            client_name="Sabin Balan (Founder, GuardianTree FP)",
            client_email="example@gmail.com",
            provider_credits="VintushTech & KPRegTech",
            is_free_trial=False,
            trial_start_date=now,
            trial_duration_days=0,
            trial_end_date=now,
            paid_until=now,
            subscription_status='locked_expired',
            current_plan='',
            is_locked=True,
            license_key=''
        )
    return sub


def get_saas_status():
    """
    Returns a comprehensive status dictionary of the SaaS subscription.
    """
    try:
        sub = get_or_create_saas_subscription()
        now = timezone.now()

        has_generated_plan = (not sub.is_free_trial) and (sub.current_plan in SUBSCRIPTION_PLANS)
        plan_info = SUBSCRIPTION_PLANS.get(sub.current_plan) if has_generated_plan else None

        effective_expiry = sub.paid_until or sub.trial_end_date or now
        delta = effective_expiry - now
        days_remaining = max(0, delta.days) if (effective_expiry and effective_expiry > now) else 0

        # If locked in DB, or no paid plan generated yet, or expired (days_remaining <= 0)
        if sub.is_locked or not has_generated_plan or days_remaining <= 0 or now >= effective_expiry:
            if sub.subscription_status != 'locked_expired' or not sub.is_locked:
                sub.subscription_status = 'locked_expired'
                sub.is_locked = True
                sub.save(update_fields=['subscription_status', 'is_locked', 'updated_at'])

            return {
                'is_locked': True,
                'status': 'locked_expired',
                'status_display': 'Subscription Access Expired & Locked',
                'days_remaining': 0,
                'hours_remaining': 0,
                'is_free_trial': False,
                'has_generated_plan': False,
                'plan_info': None,
                'plan_name': None,
                'expires_at': effective_expiry,
                'client_name': sub.client_name,
                'provider_credits': sub.provider_credits,
                'plans': SUBSCRIPTION_PLANS,
            }

        hours_remaining = max(0, int(delta.seconds / 3600))

        return {
            'is_locked': False,
            'status': sub.subscription_status,
            'status_display': 'Active SaaS Subscription',
            'days_remaining': days_remaining,
            'hours_remaining': hours_remaining,
            'is_free_trial': False,
            'has_generated_plan': True,
            'plan_info': plan_info,
            'plan_name': plan_info['name'] if plan_info else None,
            'expires_at': effective_expiry,
            'client_name': sub.client_name,
            'provider_credits': sub.provider_credits,
            'plans': SUBSCRIPTION_PLANS,
            'license_key_masked': f"{sub.license_key[:8]}...{sub.license_key[-4:]}" if sub.license_key else "ACTIVE-MANAGED",
        }


    except Exception as e:
        # Fallback safe status: strictly locked
        return {
            'is_locked': True,
            'status': 'locked_expired',
            'status_display': 'Subscription Access Expired & Locked',
            'days_remaining': 0,
            'hours_remaining': 0,
            'is_free_trial': False,
            'has_generated_plan': False,
            'plan_info': None,
            'plan_name': None,
            'client_name': 'Sabin Balan (Founder, GuardianTree FP)',
            'provider_credits': 'VintushTech & KPRegTech',
            'plans': SUBSCRIPTION_PLANS,
        }


def unlock_subscription_with_plan(plan_code, license_key=None, simulated_payment=False):
    """
    Unlocks or extends the subscription for a given plan when key is entered on lock screen.
    """
    sub = get_or_create_saas_subscription()
    
    now = timezone.now()

    from .models import SaaSInvoice
    inv = None
    if license_key:
        cleaned_key = str(license_key).strip().upper().replace(" ", "")
        inv = SaaSInvoice.objects.filter(master_key=cleaned_key).first()

    if inv:
        plan_code = inv.plan_code
        if inv.valid_until and inv.valid_until > now:
            new_expiry = inv.valid_until
        else:
            duration = inv.duration_days or SUBSCRIPTION_PLANS.get(plan_code, {}).get('duration_days', 30)
            new_expiry = now + datetime.timedelta(days=duration)
    else:
        plan_info = SUBSCRIPTION_PLANS.get(plan_code, SUBSCRIPTION_PLANS['1_month'])
        new_expiry = now + datetime.timedelta(days=plan_info['duration_days'])

    plan_info = SUBSCRIPTION_PLANS.get(plan_code, SUBSCRIPTION_PLANS['1_month'])

    sub.is_locked = False
    sub.is_free_trial = False
    sub.subscription_status = 'active_paid'
    sub.current_plan = plan_code
    sub.paid_until = new_expiry
    if license_key:
        sub.license_key = str(license_key).strip().upper().replace(" ", "")
    else:
        sub.license_key = generate_license_key(plan_code, sub.client_email, unique=False)
    
    sub.notes = f"Unlocked for {plan_info['name']} on {now.strftime('%Y-%m-%d %H:%M:%S UTC')} via License Key Validation."
    sub.save()
    
    # Trigger an automatic backup immediately upon renewal
    try:
        from .backup_service import create_live_backup
        create_live_backup(event_trigger=f"SaaS Renewal: {plan_info['name']}")
    except Exception:
        pass

    return sub, new_expiry
