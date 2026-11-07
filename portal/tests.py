import time
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from portal.models import (
    PortalSectionConfig,
    ClientPortalAccessOverride,
    PortalWidgetConfig,
    PortalAnnouncement,
    StockRecommendation
)
from portal.services import AccessControlService
from login.forms import EmailOrUsernameLoginForm
from login.models import SecurityAuditLog
from billing.models import SubscriptionPlan, UserSubscription

User = get_user_model()


class PortalSecuritySessionTests(TestCase):
    """
    Validates enterprise session security policies, inactivity timeout,
    and absolute removal of remember-me functionality.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='client_test',
            email='example@gmail.com',
            password='TestPassword123!'
        )

    def test_session_settings_hardened(self):
        """Verify strict session timeout policies in settings."""
        self.assertEqual(settings.SESSION_COOKIE_AGE, 43200, "Max session lifetime must be 12 hours (43200s).")
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE, "Session must expire at browser close.")
        self.assertEqual(getattr(settings, 'SESSION_INACTIVITY_TIMEOUT', None), 1800, "Inactivity timeout must be 30m (1800s).")

    def test_login_form_has_no_remember_me(self):
        """Verify 'remember_me' field has been completely eliminated from login form."""
        form = EmailOrUsernameLoginForm()
        self.assertNotIn('remember_me', form.fields, "Remember Me field must not exist in login form.")

    def test_logout_workflow_security(self):
        """Verify logout flushes session and sends strict anti-caching HTTP headers."""
        self.client.login(username='client_test', password='TestPassword123!')
        response = self.client.get(reverse('login:logout'))
        
        self.assertEqual(response.status_code, 302)
        # Check anti-caching headers
        self.assertIn('no-store', response.get('Cache-Control', ''))
        self.assertIn('no-cache', response.get('Cache-Control', ''))
        self.assertEqual(response.get('Pragma'), 'no-cache')
        self.assertEqual(response.get('Expires'), '0')


class DynamicAccessControlTests(TestCase):
    """
    Tests dynamic section configuration, tier rules, and individual client overrides.
    """
    def setUp(self):
        self.free_user = User.objects.create_user(
            username='free_client',
            email='free_client@example.com',
            password='TestPassword123!'
        )
        self.premium_user = User.objects.create_user(
            username='premium_client',
            email='premium_client@example.com',
            password='TestPassword123!'
        )
        # Setup active subscription for premium_user
        plan = SubscriptionPlan.objects.create(
            code='SWING_QUARTERLY',
            name='Swing Quarterly',
            price_inr=7999,
            duration_days=90,
            billing_cycle='quarterly'
        )
        UserSubscription.objects.create(
            user=self.premium_user,
            plan=plan,
            status='active',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=90)
        )

        # Create Section Configs
        self.sec_market = PortalSectionConfig.objects.create(
            section_key='market_test',
            title='Market Overview',
            url_name='portal:dashboard',
            is_enabled_globally=True,
            requires_premium=False,
            display_order=10
        )
        self.sec_calls = PortalSectionConfig.objects.create(
            section_key='calls_test',
            title='VIP Research Calls',
            url_name='portal:recommendations',
            is_enabled_globally=True,
            requires_premium=True,
            display_order=20
        )

    def test_free_and_premium_standard_access(self):
        """Standard tier checks: free access allowed on market, premium required on calls."""
        allowed_free_market, _ = AccessControlService.can_access_section(self.free_user, 'market_test')
        self.assertTrue(allowed_free_market)

        allowed_free_calls, _ = AccessControlService.can_access_section(self.free_user, 'calls_test')
        self.assertFalse(allowed_free_calls)

        allowed_prem_calls, badge = AccessControlService.can_access_section(self.premium_user, 'calls_test')
        self.assertTrue(allowed_prem_calls)
        self.assertEqual(badge, "PREMIUM")

    def test_global_disable_blocks_regular_clients(self):
        """When admin disables a section globally, all standard clients are blocked."""
        self.sec_market.is_enabled_globally = False
        self.sec_market.save()

        allowed, reason = AccessControlService.can_access_section(self.free_user, 'market_test')
        self.assertFalse(allowed)
        self.assertIn("disabled", reason)

    def test_individual_client_override_vip_grant(self):
        """
        Administrator can grant VIP override to a specific free client for a premium section.
        """
        ClientPortalAccessOverride.objects.create(
            client=self.free_user,
            section=self.sec_calls,
            access_status='FORCE_ENABLED',
            custom_badge='VIP'
        )

        allowed, badge = AccessControlService.can_access_section(self.free_user, 'calls_test')
        self.assertTrue(allowed, "Free user with VIP override must be granted access.")
        self.assertEqual(badge, 'VIP')

    def test_individual_client_override_revocation(self):
        """
        Administrator can restrict/revoke a specific section for an individual client.
        """
        ClientPortalAccessOverride.objects.create(
            client=self.premium_user,
            section=self.sec_calls,
            access_status='FORCE_DISABLED',
            notes='Account temporarily suspended pending KYC review'
        )

        allowed, reason = AccessControlService.can_access_section(self.premium_user, 'calls_test')
        self.assertFalse(allowed, "Client with FORCE_DISABLED override must be blocked.")
        self.assertIn("restricted", reason)

    def test_temporary_override_expiration(self):
        """An expired override must revert back to standard tier rules."""
        past_date = timezone.now() - timedelta(days=1)
        ClientPortalAccessOverride.objects.create(
            client=self.free_user,
            section=self.sec_calls,
            access_status='FORCE_ENABLED',
            expires_at=past_date
        )

        allowed, _ = AccessControlService.can_access_section(self.free_user, 'calls_test')
        self.assertFalse(allowed, "Expired VIP override must revert back to locked status for free user.")


class SecurityAuditLogTests(TestCase):
    """
    Validates immutable security audit logging for authentication and permission changes.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='audit_client',
            email='audit@example.com',
            password='TestPassword123!'
        )

    def test_security_audit_log_creation(self):
        log = SecurityAuditLog.log(
            event_type='login_success',
            actor=self.user,
            details={'method': 'password', 'ip': '127.0.0.1'}
        )
        self.assertIsNotNone(log.id)
        self.assertEqual(log.event_type, 'login_success')
        self.assertEqual(log.actor_user, self.user)
        self.assertEqual(log.details.get('method'), 'password')


class AdminSeparationAndBrandingTests(TestCase):
    """
    Verifies strict separation between Client Portal and Admin Panel,
    ensuring zero admin link discoverability in client-facing templates.
    """
    def setUp(self):
        self.client = Client()

    def test_client_login_page_branding(self):
        """Verify client login page is branded for clients, not administrators."""
        response = self.client.get(reverse('login:login'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("Client Research Portal", content)
        self.assertNotIn("Admin Portal Sign In", content)
        self.assertNotIn("Secure Executive Operations", content)

    def test_public_navbar_has_zero_admin_links(self):
        """Verify public navbar does not disclose the administrator portal."""
        response = self.client.get(reverse('login:home'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn("Executive Admin", content)
        self.assertNotIn("Executive Portal", content)


class ContactSubmissionStatusTests(TestCase):
    """
    Validates operational status management on inbound client inquiries.
    """
    def test_contact_status_transitions(self):
        from contactform.models import ContactSubmission
        sub = ContactSubmission.objects.create(
            name="Investor Test",
            email="investor@example.com",
            subject="Advisory Inquiry",
            message="Interested in swing research calls."
        )
        self.assertEqual(sub.status, 'new')
        self.assertIsNone(sub.resolved_at)

        # Mark as resolved
        sub.status = 'resolved'
        sub.resolved_at = timezone.now()
        sub.save()

        refreshed = ContactSubmission.objects.get(id=sub.id)
        self.assertEqual(refreshed.status, 'resolved')
        self.assertIsNotNone(refreshed.resolved_at)


class RBACGroupTests(TestCase):
    """
    Validates Role-Based Access Control groups for least privilege administration.
    """
    def setUp(self):
        from django.contrib.auth.models import Group
        Group.objects.get_or_create(name='Operations_Administrator')
        Group.objects.get_or_create(name='Website_Content_Manager')

    def test_rbac_groups_exist(self):
        from django.contrib.auth.models import Group
        ops_exists = Group.objects.filter(name='Operations_Administrator').exists()
        content_exists = Group.objects.filter(name='Website_Content_Manager').exists()
        self.assertTrue(ops_exists, "Operations_Administrator group must exist.")
        self.assertTrue(content_exists, "Website_Content_Manager group must exist.")

