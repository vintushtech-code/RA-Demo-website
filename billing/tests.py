import hmac
import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from billing.models import SubscriptionPlan, UserSubscription, PaymentTransaction
from billing.services import RazorpayService
from billing.admin import PaymentTransactionAdmin, UserSubscriptionAdmin
from login.models import SecurityAuditLog
from django.contrib.admin.sites import AdminSite

User = get_user_model()


class MockAdminSite(AdminSite):
    pass


class RazorpayServiceUnitTests(TestCase):
    """
    Unit tests for Razorpay cryptographic verification, order generation,
    and anti-tampering logic in RazorpayService.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='trader_alex',
            email='alex@example.com',
            password='TestPassword123!'
        )
        self.plan = SubscriptionPlan.objects.create(
            code='SWING_PRO_TEST',
            name='Swing Pro Test Plan',
            price_inr=Decimal('4999.00'),
            duration_days=30,
            billing_cycle='monthly',
            is_active=True
        )

    def test_create_order_pricing_derived_strictly_from_db(self):
        """Order creation must use plan price from database, ignoring any external manipulation."""
        order_info = RazorpayService.create_order(self.user, 'SWING_PRO_TEST')
        
        self.assertIsNotNone(order_info.get('order_id'))
        self.assertEqual(order_info['amount_inr'], 4999.00)
        self.assertEqual(order_info['amount_paise'], 499900)
        self.assertEqual(order_info['plan_code'], 'SWING_PRO_TEST')

        # Verify DB records created
        tx = PaymentTransaction.objects.get(order_id=order_info['order_id'])
        self.assertEqual(tx.user, self.user)
        self.assertEqual(tx.amount, Decimal('4999.00'))
        self.assertEqual(tx.status, 'created')

        sub = UserSubscription.objects.get(razorpay_order_id=order_info['order_id'])
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.status, 'payment_pending')

    def test_verify_payment_signature_valid_and_invalid(self):
        """HMAC-SHA256 signature verification must validate authentic signatures and reject forged ones."""
        order_id = "order_test_12345"
        payment_id = "pay_test_67890"

        # Compute authentic signature
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        secret = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
        valid_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        # Authentic signature
        self.assertTrue(RazorpayService.verify_payment_signature(order_id, payment_id, valid_signature))

        # Forged / Tampered signature
        forged_signature = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.assertFalse(RazorpayService.verify_payment_signature(order_id, payment_id, forged_signature))

        # Blank parameters
        self.assertFalse(RazorpayService.verify_payment_signature("", payment_id, valid_signature))
        self.assertFalse(RazorpayService.verify_payment_signature(order_id, "", valid_signature))
        self.assertFalse(RazorpayService.verify_payment_signature(order_id, payment_id, ""))

    def test_process_payment_verification_success(self):
        """Valid payment signature activates subscription and records unique invoice."""
        order_info = RazorpayService.create_order(self.user, 'SWING_PRO_TEST')
        order_id = order_info['order_id']
        payment_id = "pay_test_succ_001"

        # Authentic signature
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        sig = hmac.new(settings.RAZORPAY_KEY_SECRET.encode('utf-8'), msg, hashlib.sha256).hexdigest()

        success, message, sub = RazorpayService.process_payment_verification(
            user=self.user,
            order_id=order_id,
            payment_id=payment_id,
            signature=sig
        )

        self.assertTrue(success)
        self.assertIn("subscription is now active", message)
        
        # Reload subscription
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'active')
        self.assertTrue(sub.invoice_number.startswith('INV-KP-'))
        self.assertEqual(sub.razorpay_payment_id, payment_id)

        # Reload transaction
        tx = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(tx.status, 'captured')
        self.assertEqual(tx.payment_id, payment_id)

        # Verify Security Audit Log
        audit = SecurityAuditLog.objects.filter(
            event_type='profile_update',
            actor_user=self.user,
            details__event='SUBSCRIPTION_ACTIVATED_PAID'
        ).first()
        self.assertIsNotNone(audit)

    def test_process_payment_verification_forged_signature_fails(self):
        """Forged signature must fail verification, set transaction to failed, and log access_denied."""
        order_info = RazorpayService.create_order(self.user, 'SWING_PRO_TEST')
        order_id = order_info['order_id']
        payment_id = "pay_test_forged_001"
        forged_sig = "invalid_hash_signature"

        success, message, sub = RazorpayService.process_payment_verification(
            user=self.user,
            order_id=order_id,
            payment_id=payment_id,
            signature=forged_sig
        )

        self.assertFalse(success)
        self.assertIn("Invalid cryptographic payment signature", message)
        
        # Transaction should be marked failed
        tx = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(tx.status, 'failed')
        self.assertEqual(tx.error_code, 'BAD_SIGNATURE')

        # Subscription must NOT be active
        sub_record = UserSubscription.objects.get(razorpay_order_id=order_id)
        self.assertEqual(sub_record.status, 'payment_pending')

    def test_process_payment_verification_idor_tampering_blocked(self):
        """User B cannot verify or claim User A's order (IDOR defense)."""
        order_info = RazorpayService.create_order(self.user, 'SWING_PRO_TEST')
        order_id = order_info['order_id']
        payment_id = "pay_test_idor_001"

        attacker_user = User.objects.create_user(
            username='attacker_bob',
            email='bob@example.com',
            password='TestPassword123!'
        )

        msg = f"{order_id}|{payment_id}".encode('utf-8')
        sig = hmac.new(settings.RAZORPAY_KEY_SECRET.encode('utf-8'), msg, hashlib.sha256).hexdigest()

        # Attacker tries to verify User A's order under their own session
        success, message, sub = RazorpayService.process_payment_verification(
            user=attacker_user,
            order_id=order_id,
            payment_id=payment_id,
            signature=sig
        )

        self.assertFalse(success)
        self.assertIn("ownership mismatch", message)

        # Attacker must have NO active subscription
        self.assertFalse(UserSubscription.objects.filter(user=attacker_user, status='active').exists())

        # Audit log must record IDOR attack attempt
        idor_log = SecurityAuditLog.objects.filter(
            event_type='access_denied',
            actor_user=attacker_user,
            details__attack_type='IDOR_PAYMENT_TAMPERING'
        ).first()
        self.assertIsNotNone(idor_log)

    def test_process_payment_idempotency_prevents_replay(self):
        """Repeated verification of an already captured payment must be idempotent and not extend dates."""
        order_info = RazorpayService.create_order(self.user, 'SWING_PRO_TEST')
        order_id = order_info['order_id']
        payment_id = "pay_test_replay_001"

        msg = f"{order_id}|{payment_id}".encode('utf-8')
        sig = hmac.new(settings.RAZORPAY_KEY_SECRET.encode('utf-8'), msg, hashlib.sha256).hexdigest()

        # First verification
        ok1, msg1, sub1 = RazorpayService.process_payment_verification(self.user, order_id, payment_id, sig)
        self.assertTrue(ok1)
        sub1.refresh_from_db()
        initial_end_date = sub1.end_date

        # Replayed verification call
        ok2, msg2, sub2 = RazorpayService.process_payment_verification(self.user, order_id, payment_id, sig)
        self.assertTrue(ok2)
        self.assertIn("already been verified", msg2)
        sub2.refresh_from_db()
        self.assertEqual(sub2.end_date, initial_end_date, "End date must not be pushed further on replay.")


class RazorpayAPIEndpointTests(TestCase):
    """
    Integration tests for Razorpay HTTP views and API endpoints.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='trader_carol',
            email='carol@example.com',
            password='TestPassword123!'
        )
        self.plan = SubscriptionPlan.objects.create(
            code='ALPHA_ANNUAL',
            name='Alpha Annual Plan',
            price_inr=Decimal('18999.00'),
            duration_days=365,
            billing_cycle='yearly',
            is_active=True
        )

    def test_create_order_unauthenticated_redirects(self):
        """Unauthenticated requests must be redirected to login."""
        response = self.client.post(
            reverse('billing:create_order'),
            data=json.dumps({'plan_code': 'ALPHA_ANNUAL'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)

    def test_create_order_authenticated_success(self):
        """Authenticated client can initialize an order; pricing is derived securely from DB."""
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse('billing:create_order'),
            data=json.dumps({'plan_code': 'ALPHA_ANNUAL', 'tampered_price': 1}),  # Tampered client price must be ignored
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'success')
        self.assertEqual(res_data['data']['amount_inr'], 18999.00)
        self.assertEqual(res_data['data']['amount_paise'], 1899900)

    def test_create_order_invalid_plan_returns_400(self):
        """Invalid plan code returns 400 error."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('billing:create_order'),
            data=json.dumps({'plan_code': 'NON_EXISTENT_PLAN'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

    def test_verify_payment_valid_signature_activates(self):
        """Successful payment verification endpoint activates user and returns redirect URL."""
        self.client.force_login(self.user)
        
        order_info = RazorpayService.create_order(self.user, 'ALPHA_ANNUAL')
        order_id = order_info['order_id']
        payment_id = "pay_test_api_success"

        msg = f"{order_id}|{payment_id}".encode('utf-8')
        sig = hmac.new(settings.RAZORPAY_KEY_SECRET.encode('utf-8'), msg, hashlib.sha256).hexdigest()

        response = self.client.post(
            reverse('billing:verify_payment'),
            data=json.dumps({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': sig
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'success')
        self.assertIn(reverse('portal:dashboard'), res_data['redirect_url'])

        # Verify DB status
        sub = UserSubscription.objects.get(razorpay_order_id=order_id)
        self.assertEqual(sub.status, 'active')

    def test_verify_payment_invalid_signature_rejected(self):
        """Payment verification with bad signature returns 400."""
        self.client.force_login(self.user)
        order_info = RazorpayService.create_order(self.user, 'ALPHA_ANNUAL')
        order_id = order_info['order_id']

        response = self.client.post(
            reverse('billing:verify_payment'),
            data=json.dumps({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': 'pay_test_bad',
                'razorpay_signature': 'bad_signature_string'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

    def test_payment_failure_endpoint_records_state(self):
        """Failure / cancel callback marks transaction and subscription cancelled."""
        self.client.force_login(self.user)
        order_info = RazorpayService.create_order(self.user, 'ALPHA_ANNUAL')
        order_id = order_info['order_id']

        response = self.client.post(
            reverse('billing:payment_failed'),
            data=json.dumps({
                'order_id': order_id,
                'error_code': 'BAD_REQUEST_ERROR',
                'error_description': 'Card declined by issuing bank'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        tx = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(tx.status, 'failed')
        self.assertEqual(tx.error_code, 'BAD_REQUEST_ERROR')


class RazorpayWebhookSecurityTests(TestCase):
    """
    Tests security of asynchronous Razorpay webhook listener.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='webhook_user',
            email='webhook@example.com',
            password='TestPassword123!'
        )
        self.plan = SubscriptionPlan.objects.create(
            code='SWING_MONTHLY',
            name='Swing Monthly',
            price_inr=Decimal('2999.00'),
            duration_days=30,
            billing_cycle='monthly',
            is_active=True
        )

    def test_webhook_unauthorized_signature_returns_403(self):
        """Webhook with invalid or missing signature must be rejected with 403 Forbidden."""
        response = self.client.post(
            reverse('billing:webhook'),
            data=json.dumps({'event': 'payment.captured'}),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='forged_sig'
        )
        self.assertEqual(response.status_code, 403)

    def test_webhook_valid_signature_processes_capture(self):
        """Webhook with valid HMAC signature successfully reconciles payment capture."""
        order_info = RazorpayService.create_order(self.user, 'SWING_MONTHLY')
        order_id = order_info['order_id']
        payment_id = "pay_hook_captured_123"

        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': payment_id,
                        'order_id': order_id,
                        'amount': 299900,
                        'status': 'captured'
                    }
                }
            }
        }
        body_bytes = json.dumps(payload).encode('utf-8')
        secret = settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8')
        valid_signature = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()

        response = self.client.post(
            reverse('billing:webhook'),
            data=body_bytes,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=valid_signature
        )

        self.assertEqual(response.status_code, 200)

        # Verify transaction and subscription are updated
        tx = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(tx.status, 'captured')
        self.assertEqual(tx.payment_id, payment_id)

        sub = UserSubscription.objects.get(razorpay_order_id=order_id)
        self.assertEqual(sub.status, 'active')


class AdminBillingProtectionTests(TestCase):
    """
    Validates administrative payment safeguards:
    - Manual creation of payment transactions is prohibited.
    - Deletion of financial audit trail is prohibited.
    - Admin extension actions are logged to SecurityAuditLog.
    """
    def setUp(self):
        self.site = MockAdminSite()
        self.admin_user = User.objects.create_superuser(
            username='admin_boss',
            email='admin@example.com',
            password='AdminPassword123!'
        )
        self.user = User.objects.create_user(
            username='client_dave',
            email='dave@example.com',
            password='TestPassword123!'
        )
        self.plan = SubscriptionPlan.objects.create(
            code='TEST_PLAN',
            name='Test Plan',
            price_inr=Decimal('1000.00'),
            duration_days=30,
            billing_cycle='monthly'
        )
        self.sub = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status='active',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30)
        )

    def test_payment_transaction_admin_tamper_safeguards(self):
        """PaymentTransactionAdmin must forbid manual additions and deletions."""
        tx_admin = PaymentTransactionAdmin(PaymentTransaction, self.site)
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.admin_user

        self.assertFalse(tx_admin.has_add_permission(request), "Admins cannot manually fabricate payment records.")
        self.assertFalse(tx_admin.has_delete_permission(request), "Admins cannot delete payment audit records.")

    def test_courtesy_extension_action_audited(self):
        """Executing authorized 7-day courtesy extension updates end_date and writes to SecurityAuditLog."""
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware

        sub_admin = UserSubscriptionAdmin(UserSubscription, self.site)
        factory = RequestFactory()
        request = factory.post('/')
        request.user = self.admin_user

        SessionMiddleware(lambda req: None).process_request(request)
        MessageMiddleware(lambda req: None).process_request(request)

        old_end_date = self.sub.end_date
        queryset = UserSubscription.objects.filter(id=self.sub.id)
        
        # Trigger action
        sub_admin.grant_courtesy_extension_7d(request, queryset)

        self.sub.refresh_from_db()
        self.assertGreater(self.sub.end_date, old_end_date)

        # Confirm SecurityAuditLog entry exists
        audit = SecurityAuditLog.objects.filter(
            event_type='permission_override',
            actor_user=self.admin_user,
            details__action='ADMIN_EXTENSION_7D'
        ).first()
        self.assertIsNotNone(audit, "Admin subscription extension must be logged in SecurityAuditLog.")
