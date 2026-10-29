"""
SaaS Access Guard & Subscription Security Middleware
====================================================
Provided by: VintushTech & KPRegTech
Client: Sabin Balan (Founder, GuardianTree FP)

Enforces SaaS subscription and 3-month free trial rules:
- Unconditionally preserves all database records.
- Allows public website traffic to proceed with zero disruption.
- Intercepts Django Admin portal when the trial/subscription has expired.
- Displays the luxury SaaS Subscription Renewal Lock Screen with instant activation.
"""

from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from .saas_service import get_saas_status, SUBSCRIPTION_PLANS, unlock_subscription_with_plan, validate_license_key
from .backup_service import get_latest_backups_summary


class AdminSaaSGuardMiddleware:
    """
    Middleware ensuring the Django Admin Panel is strictly governed by
    the active SaaS subscription and 3-Month Free Trial state.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_secret_path = getattr(settings, 'ADMIN_SECRET_PATH', 'x7K9mQp2LrT4').strip('/')

    def __call__(self, request):
        path = request.path_info

        # Skip non-admin paths, static files, and media
        admin_prefix = f"/{self.admin_secret_path}"
        is_admin_route = path.startswith(admin_prefix) or path.startswith('/admin')
        
        # Also allow dedicated SaaS unlock API routes
        is_unlock_route = path.startswith('/admin-saas/unlock') or path.startswith('/saas/unlock')

        if not is_admin_route and not is_unlock_route:
            return self.get_response(request)

        # Allow static files and asset downloads
        if path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)

        # Retrieve current SaaS status
        saas_status = get_saas_status()

        # Handle unlock submission if posted directly or via unlock route
        if request.method == 'POST' and (is_unlock_route or request.POST.get('saas_action') or request.POST.get('action')):
            action = request.POST.get('saas_action') or request.POST.get('action') or 'unlock_license'
            if action in ['unlock_license', 'activate_key']:
                key = request.POST.get('license_key', '').strip()
                is_valid, matched_plan, msg = validate_license_key(key)
                if is_valid:
                    unlock_subscription_with_plan(matched_plan or '1_year', license_key=key)
                    return redirect(f"{admin_prefix}/")
                else:
                    context = {
                        'saas_status': saas_status,
                        'plans': SUBSCRIPTION_PLANS,
                        'backup_summary': get_latest_backups_summary(),
                        'error_message': msg,
                        'admin_url': f"{admin_prefix}/",
                    }
                    return render(request, 'admin/saas_lock.html', context, status=403)

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
                        client_email='example@gmail.com',
                        status='pending'
                    )

                    send_saas_purchase_request_emails(plan_code, plan_info['name'], price_str)
                    return redirect(f"{admin_prefix}/")


        # If locked or expired (0 days left), block admin access and render SaaS Subscription Lock Screen
        if saas_status.get('is_locked') or saas_status.get('days_remaining', 0) <= 0:
            context = {
                'saas_status': saas_status,
                'plans': SUBSCRIPTION_PLANS,
                'backup_summary': get_latest_backups_summary(),
                'admin_url': f"{admin_prefix}/",
            }
            return render(request, 'admin/saas_lock.html', context, status=403)


        return self.get_response(request)
