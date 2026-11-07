"""
Portal Access Control & Dynamic Content Service
===============================================
Centralized business logic governing:
- Dynamic section permissions per user tier and individual client override.
- Real-time navigation tab rendering driven by Django Admin configuration.
- Flash announcements and tier-targeted promotional widgets.
- Strict server-side enforcement (IDOR protection).
"""

from django.utils import timezone
from django.urls import reverse, NoReverseMatch
from .models import (
    PortalSectionConfig,
    ClientPortalAccessOverride,
    PortalWidgetConfig,
    PortalAnnouncement
)


class AccessControlService:
    """
    Evaluates client access rights for any portal module with priority:
    1. Superuser / Staff -> Full access granted unconditionally.
    2. Global switch -> If section disabled globally, blocked for all.
    3. Individual Client Override -> Direct override by Admin (FORCE_ENABLED / FORCE_DISABLED).
    4. Subscription Tier -> Free vs. Active Premium Subscription.
    """

    @classmethod
    def can_access_section(cls, user, section_key):
        """
        Returns (is_allowed: bool, badge_or_reason: str).
        """
        # 1. Staff and Superusers always have full access
        if user and (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)):
            return True, "ADMIN"

        # 2. Lookup section configuration
        try:
            section = PortalSectionConfig.objects.get(section_key=section_key)
        except PortalSectionConfig.DoesNotExist:
            return False, "Section does not exist"

        if not section.is_enabled_globally:
            return False, "This section is currently disabled by administrator."

        # 3. Check Individual Client Override
        if user and user.is_authenticated:
            override = ClientPortalAccessOverride.objects.filter(
                client=user,
                section=section
            ).first()

            if override:
                if override.access_status == 'FORCE_DISABLED':
                    return False, "Access to this section has been restricted for your account."

                if override.access_status == 'FORCE_ENABLED':
                    if not override.is_expired():
                        badge = override.custom_badge or "VIP"
                        return True, badge

        # 4. Standard Subscription Tier Check
        if section.requires_premium:
            if not user or not user.is_authenticated:
                return False, "Authentication required."
            
            is_premium = getattr(user, 'is_premium_active', False)
            if not is_premium:
                # Teaser access allowed for preview, but trade specifics restricted
                return False, "Requires active Premium Subscription."

            return True, "PREMIUM"

        return True, "STANDARD"

    @classmethod
    def get_navigation_tabs_for_user(cls, user, current_key=None):
        """
        Computes dynamic tabs for the portal header sub-navigation bar
        based on active sections and user permissions.
        """
        sections = PortalSectionConfig.objects.filter(
            is_enabled_globally=True,
            is_visible_in_nav=True
        ).order_by('display_order', 'id')

        tabs = []
        is_user_premium = getattr(user, 'is_premium_active', False) if (user and user.is_authenticated) else False
        is_staff = getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)

        for sec in sections:
            # Check individual client override
            override = None
            if user and user.is_authenticated:
                override = ClientPortalAccessOverride.objects.filter(client=user, section=sec).first()

            # If client specifically force-disabled, skip tab
            if override and override.access_status == 'FORCE_DISABLED' and not is_staff:
                continue

            has_force_enabled = override and override.access_status == 'FORCE_ENABLED' and not override.is_expired()
            
            # Resolve URL
            try:
                tab_url = reverse(sec.url_name)
            except NoReverseMatch:
                tab_url = reverse('portal:dashboard')

            # Determine lock / teaser status
            is_locked = False
            badge_text = ""
            badge_class = ""

            if has_force_enabled:
                badge_text = override.custom_badge or "VIP"
                badge_class = "badge-vip"
            elif sec.requires_premium:
                if not is_user_premium and not is_staff:
                    is_locked = True
                    badge_text = "PREMIUM"
                    badge_class = "badge-locked"
                else:
                    badge_text = "PRO"
                    badge_class = "badge-pro"

            tabs.append({
                'key': sec.section_key,
                'title': sec.title,
                'subtitle': sec.subtitle,
                'url': tab_url,
                'icon_name': sec.icon_name,
                'is_active': (sec.section_key == current_key),
                'is_locked': is_locked,
                'badge_text': badge_text,
                'badge_class': badge_class,
            })

        return tabs

    @classmethod
    def get_active_announcements_for_user(cls, user):
        """
        Fetches live announcements targeting this client's tier or user ID.
        """
        now = timezone.now()
        qs = PortalAnnouncement.objects.filter(
            is_active=True,
            start_date__lte=now
        ).filter(
            models_q_filter(user, now)
        ).distinct()

        return qs

    @classmethod
    def get_active_widgets_for_user(cls, user, widget_type=None):
        """
        Fetches widgets (e.g. sidebar promo cards) matching user's tier.
        """
        is_user_premium = getattr(user, 'is_premium_active', False) if (user and user.is_authenticated) else False
        qs = PortalWidgetConfig.objects.filter(is_active=True)

        if widget_type:
            qs = qs.filter(widget_type=widget_type)

        if is_user_premium:
            qs = qs.filter(target_tier__in=['all', 'premium_only'])
        else:
            qs = qs.filter(target_tier__in=['all', 'free_only'])

        return qs.order_by('display_order', '-created_at')


def models_q_filter(user, now):
    from django.db.models import Q
    base_q = Q(end_date__isnull=True) | Q(end_date__gte=now)
    
    if not user or not user.is_authenticated:
        return base_q & Q(target_tier__in=['all', 'free_only'])

    is_user_premium = getattr(user, 'is_premium_active', False)
    
    tier_q = Q(target_tier='all')
    if is_user_premium:
        tier_q |= Q(target_tier='premium_only')
    else:
        tier_q |= Q(target_tier='free_only')

    specific_client_q = Q(target_tier='specific_clients', specific_clients=user)
    
    return base_q & (tier_q | specific_client_q)

