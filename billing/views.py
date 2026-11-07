import json
import logging
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import SubscriptionPlan, UserSubscription, PaymentTransaction
from .services import RazorpayService
from login.security import rate_limit
from login.models import SecurityAuditLog

logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


@method_decorator(rate_limit(key_type='ip', limit=15, period=60), name='dispatch')
class CreateRazorpayOrderView(LoginRequiredMixin, View):
    """
    API endpoint: Initializes a Razorpay TEST MODE order.
    The client selects a plan; the backend calculates the exact price from the DB.
    """
    login_url = 'login:login'

    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST

            plan_code = data.get('plan_code', '').strip()
            if not plan_code:
                return JsonResponse({'status': 'error', 'message': 'Plan code is required.'}, status=400)

            ip = get_client_ip(request)
            order_details = RazorpayService.create_order(request.user, plan_code, ip_address=ip)

            return JsonResponse({
                'status': 'success',
                'data': order_details
            })

        except ValidationError as ve:
            return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
        except Exception as e:
            logger.error(f"[Razorpay] Error creating order: {e}")
            return JsonResponse({'status': 'error', 'message': 'Failed to initialize payment gateway order.'}, status=500)


@method_decorator(rate_limit(key_type='ip', limit=15, period=60), name='dispatch')
class VerifyRazorpayPaymentView(LoginRequiredMixin, View):
    """
    API endpoint: Verifies Razorpay payment signature cryptographically.
    Zero Trust: Subscriptions are only activated on HMAC-SHA256 validation.
    """
    login_url = 'login:login'

    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST

            order_id = data.get('razorpay_order_id', '').strip()
            payment_id = data.get('razorpay_payment_id', '').strip()
            signature = data.get('razorpay_signature', '').strip()

            if not order_id or not payment_id or not signature:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing mandatory payment verification parameters (order_id, payment_id, signature).'
                }, status=400)

            ip = get_client_ip(request)
            success, message, subscription = RazorpayService.process_payment_verification(
                user=request.user,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
                ip_address=ip
            )

            if success:
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'redirect_url': reverse('portal:dashboard'),
                    'subscription_id': str(subscription.id) if subscription else None
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': message
                }, status=400)

        except Exception as e:
            logger.error(f"[Razorpay] Verification error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Internal payment verification error.'}, status=500)


@method_decorator(rate_limit(key_type='ip', limit=20, period=60), name='dispatch')
class PaymentFailureHandlerView(LoginRequiredMixin, View):
    """
    Handles payment failure or cancellation callbacks from Razorpay checkout.
    """
    login_url = 'login:login'

    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST

            order_id = data.get('order_id', '').strip()
            error_code = data.get('error_code', 'PAYMENT_CANCELLED')
            error_description = data.get('error_description', 'User cancelled checkout or bank declined transaction.')

            transaction = PaymentTransaction.objects.filter(order_id=order_id, user=request.user).first()
            if transaction:
                transaction.status = 'failed'
                transaction.error_code = error_code
                transaction.error_description = error_description
                transaction.save(update_fields=['status', 'error_code', 'error_description'])

                if transaction.subscription:
                    transaction.subscription.status = 'cancelled'
                    transaction.subscription.save(update_fields=['status'])

            return JsonResponse({'status': 'recorded', 'message': 'Payment failure logged.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(View):
    """
    Enterprise Webhook Handler for asynchronous payment capture and order reconciliation.
    Guarantees idempotency and verifies X-Razorpay-Signature header.
    """
    def post(self, request, *args, **kwargs):
        signature_header = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')
        raw_body = request.body

        # 1. Cryptographically verify webhook signature
        is_valid = RazorpayService.verify_webhook_signature(raw_body, signature_header)
        if not is_valid:
            logger.warning("[Razorpay Webhook] Invalid webhook signature detected!")
            return HttpResponseForbidden("Invalid Webhook Signature")

        # 2. Parse payload
        try:
            payload = json.loads(raw_body.decode('utf-8'))
            event = payload.get('event')
            payload_data = payload.get('payload', {})

            logger.info(f"[Razorpay Webhook] Processing event: {event}")

            # 3. Process captured payments
            if event in ('payment.captured', 'order.paid'):
                payment_entity = payload_data.get('payment', {}).get('entity', {})
                order_id = payment_entity.get('order_id')
                payment_id = payment_entity.get('id')
                amount_paise = payment_entity.get('amount')

                transaction = PaymentTransaction.objects.filter(order_id=order_id).first()
                if transaction and transaction.status != 'captured':
                    transaction.status = 'captured'
                    transaction.payment_id = payment_id
                    transaction.gateway_response = payload_data
                    transaction.save(update_fields=['status', 'payment_id', 'gateway_response'])

                    sub = transaction.subscription
                    if sub and sub.status != 'active':
                        duration = sub.plan.duration_days if sub.plan else 30
                        now = timezone.now()
                        sub.status = 'active'
                        sub.start_date = now
                        sub.end_date = now + timedelta(days=duration)
                        sub.razorpay_payment_id = payment_id
                        sub.save()

            elif event == 'payment.failed':
                payment_entity = payload_data.get('payment', {}).get('entity', {})
                order_id = payment_entity.get('order_id')
                transaction = PaymentTransaction.objects.filter(order_id=order_id).first()
                if transaction:
                    transaction.status = 'failed'
                    transaction.error_code = payment_entity.get('error_code', 'WEBHOOK_FAILED')
                    transaction.error_description = payment_entity.get('error_description', 'Payment failed')
                    transaction.save(update_fields=['status', 'error_code', 'error_description'])

            return HttpResponse(json.dumps({'status': 'webhook processed'}), content_type='application/json', status=200)

        except Exception as e:
            logger.error(f"[Razorpay Webhook] Error: {e}")
            return HttpResponse(json.dumps({'status': 'error', 'message': str(e)}), content_type='application/json', status=500)
