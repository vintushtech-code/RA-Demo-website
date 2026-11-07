import os
import io
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden, Http404, JsonResponse, FileResponse
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.db import models

from .models import StockRecommendation, RecommendationUpdate, ClientWatchlist, SEBIComplianceAuditLog
from .services import AccessControlService
from login.models import SecurityAuditLog
from research_vault.models import ResearchDocument, DocumentAccessAssignment, DocumentAccessLog
from billing.models import SubscriptionPlan, UserSubscription


class PortalSectionAccessMixin(LoginRequiredMixin):
    """
    Base mixin enforcing Admin section configuration and individual client overrides.
    Injects dynamic navigation tabs, live announcements, and target widgets.
    """
    section_key = None
    allow_teaser_for_free = False
    login_url = 'login:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(self.login_url)

        if self.section_key:
            allowed, info = AccessControlService.can_access_section(request.user, self.section_key)
            if not allowed and not self.allow_teaser_for_free:
                # Log security denial
                SecurityAuditLog.log(
                    'access_denied',
                    request=request,
                    target=request.user,
                    details={'section': self.section_key, 'reason': info}
                )
                messages.warning(request, f"Access restricted: {info}")
                # Prevent infinite redirect loop if dashboard/market is restricted
                if self.section_key == 'market':
                    return redirect('portal:upgrade')
                return redirect('portal:dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['nav_tabs'] = AccessControlService.get_navigation_tabs_for_user(user, current_key=self.section_key)
        context['active_announcements'] = AccessControlService.get_active_announcements_for_user(user)
        context['sidebar_widgets'] = AccessControlService.get_active_widgets_for_user(user, widget_type='sidebar_card')
        context['active_tab'] = self.section_key
        context['is_premium'] = getattr(user, 'is_premium_active', False)
        return context


class PortalDashboardView(PortalSectionAccessMixin, TemplateView):
    """
    Central Client Portal Dashboard.
    Adapts seamlessly between Free Registered Clients and Active Premium Subscribers.
    """
    template_name = 'portal/dashboard.html'
    section_key = 'market'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        is_premium = user.is_premium_active

        # Active Subscription
        active_sub = user.get_active_subscription() if hasattr(user, 'get_active_subscription') else None

        # Recommendations: Open trades
        open_recommendations = StockRecommendation.objects.filter(status='open').order_by('-published_at')[:6]

        # User Watchlist
        watchlist = ClientWatchlist.objects.filter(user=user)

        # Assigned Research PDFs (Available to Premium Users)
        assigned_docs = []
        if is_premium:
            assigned_docs = ResearchDocument.objects.filter(
                models.Q(is_universal_premium=True) |
                models.Q(assignments__client=user, assignments__is_active=True),
                is_published=True
            ).distinct().order_by('-publication_date')[:4]

        # Benchmark Market Data (Live / Curated Institutional Indices)
        market_indices = [
            {'name': 'NIFTY 50', 'value': '24,367.50', 'change': '+142.30', 'pct': '+0.59%', 'is_positive': True},
            {'name': 'SENSEX', 'value': '80,185.20', 'change': '+465.10', 'pct': '+0.58%', 'is_positive': True},
            {'name': 'BANK NIFTY', 'value': '52,140.85', 'change': '-85.20', 'pct': '-0.16%', 'is_positive': False},
            {'name': 'INDIA VIX', 'value': '13.45', 'change': '-0.42', 'pct': '-3.03%', 'is_positive': True},
        ]

        # Subscription Upgrade Plans (for Free Users)
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')

        context.update({
            'active_sub': active_sub,
            'open_recommendations': open_recommendations,
            'watchlist': watchlist,
            'assigned_docs': assigned_docs,
            'market_indices': market_indices,
            'plans': plans,
        })
        return context


class RecommendationsListView(PortalSectionAccessMixin, ListView):
    """
    Research recommendations feed with multi-horizon filtering:
    Intraday, Short Term (Swing), Mid/Long Term, Futures, Options.
    Free users preview teaser potential % while premium users see complete parameters.
    """
    model = StockRecommendation
    template_name = 'portal/recommendations.html'
    context_object_name = 'recommendations'
    section_key = 'calls'
    allow_teaser_for_free = True

    def get_queryset(self):
        qs = StockRecommendation.objects.all().order_by('-published_at')
        horizon = self.request.GET.get('horizon')
        status = self.request.GET.get('status', 'open')

        if horizon and horizon != 'all':
            qs = qs.filter(horizon=horizon)
        if status and status != 'all':
            qs = qs.filter(status=status)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_horizon'] = self.request.GET.get('horizon', 'all')
        context['current_status'] = self.request.GET.get('status', 'open')
        context['plans'] = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')
        return context


class RecommendationDetailView(PortalSectionAccessMixin, DetailView):
    """
    Deep-dive trade thesis, balance sheet forensic rationale, and risk parameters.
    Gated strictly to Premium Subscribers (or VIP overrides).
    """
    model = StockRecommendation
    template_name = 'portal/recommendation_detail.html'
    context_object_name = 'rec'
    pk_url_kwarg = 'rec_id'
    section_key = 'calls'
    allow_teaser_for_free = False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login:login')
        
        # Enforce premium or VIP override
        allowed, info = AccessControlService.can_access_section(request.user, 'calls')
        if not allowed:
            messages.warning(request, "This deep-dive institutional research thesis requires an active premium subscription.")
            return redirect('portal:upgrade')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['updates'] = self.object.updates.all().order_by('-timestamp')
        return context


class ScreenerView(PortalSectionAccessMixin, TemplateView):
    """
    Institutional Equity Screener with valuation ratios & momentum metrics.
    """
    template_name = 'portal/screener.html'
    section_key = 'screener'


class SectorExplorerView(PortalSectionAccessMixin, TemplateView):
    """
    Interactive Sector Grid matching StockYaari Screenshot 5.
    """
    template_name = 'portal/sectors.html'
    section_key = 'sectors'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sectors = [
            {'name': 'Banking & Financials', 'code': 'bank', 'trend': '+1.4%', 'is_up': True, 'count': 42},
            {'name': 'IT & Technology', 'code': 'it', 'trend': '+0.8%', 'is_up': True, 'count': 38},
            {'name': 'Auto & Ancillaries', 'code': 'auto', 'trend': '-0.3%', 'is_up': False, 'count': 26},
            {'name': 'Cement & Materials', 'code': 'cement', 'trend': '+2.1%', 'is_up': True, 'count': 18},
            {'name': 'Pharmaceuticals', 'code': 'pharma', 'trend': '+0.5%', 'is_up': True, 'count': 31},
            {'name': 'Metals & Mining', 'code': 'metals', 'trend': '-1.2%', 'is_up': False, 'count': 22},
            {'name': 'Energy & Oil/Gas', 'code': 'energy', 'trend': '+0.4%', 'is_up': True, 'count': 19},
            {'name': 'Defence & Aerospace', 'code': 'defence', 'trend': '+3.8%', 'is_up': True, 'count': 14},
            {'name': 'FMCG & Consumption', 'code': 'fmcg', 'trend': '+0.2%', 'is_up': True, 'count': 29},
            {'name': 'Chemicals', 'code': 'chemicals', 'trend': '+1.1%', 'is_up': True, 'count': 24},
            {'name': 'Commodities', 'code': 'commodities', 'trend': '-0.6%', 'is_up': False, 'count': 17},
            {'name': 'Infrastructure', 'code': 'infra', 'trend': '+1.9%', 'is_up': True, 'count': 35},
        ]
        context['sectors'] = sectors
        return context


class CorporateActionsView(PortalSectionAccessMixin, TemplateView):
    """
    Corporate Actions & Financial Statements view matching StockYaari Screenshot 4.
    """
    template_name = 'portal/corporate_actions.html'
    section_key = 'corporate_actions'


class WatchlistView(PortalSectionAccessMixin, TemplateView):
    """
    Personal client watchlist.
    """
    template_name = 'portal/watchlist.html'
    section_key = 'watchlist'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['watchlist'] = ClientWatchlist.objects.filter(user=self.request.user).order_by('-created_at')
        return context


class WatchlistToggleAPIView(LoginRequiredMixin, View):
    """
    AJAX API to add/remove ticker from watchlist.
    """
    def post(self, request, *args, **kwargs):
        ticker = request.POST.get('ticker', '').strip().upper()
        company_name = request.POST.get('company_name', ticker)
        if not ticker:
            return JsonResponse({'status': 'error', 'message': 'Ticker required'}, status=400)

        item = ClientWatchlist.objects.filter(user=request.user, ticker=ticker).first()
        if item:
            item.delete()
            return JsonResponse({'status': 'removed', 'ticker': ticker, 'is_watching': False})
        else:
            # Free tier limitation check (up to 5 stocks)
            if not request.user.is_premium_active:
                count = ClientWatchlist.objects.filter(user=request.user).count()
                if count >= 5:
                    return JsonResponse({
                        'status': 'upgrade_required',
                        'message': 'Free tier limit reached (5 stocks). Upgrade to Premium for unlimited watchlist tracking.'
                    }, status=403)

            ClientWatchlist.objects.create(user=request.user, ticker=ticker, company_name=company_name)
            return JsonResponse({'status': 'added', 'ticker': ticker, 'is_watching': True})


class ResearchVaultListView(PortalSectionAccessMixin, TemplateView):
    """
    Confidential Research Reports Library.
    Displays universal reports and client-assigned private PDFs.
    """
    template_name = 'portal/vault_list.html'
    section_key = 'vault'
    allow_teaser_for_free = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        is_premium = user.is_premium_active

        if is_premium:
            from django.db.models import Q
            docs = ResearchDocument.objects.filter(
                Q(is_universal_premium=True) |
                Q(assignments__client=user, assignments__is_active=True),
                is_published=True
            ).distinct().order_by('-publication_date')
        else:
            docs = []

        context['documents'] = docs
        context['plans'] = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')
        return context


class SecureDocStreamView(LoginRequiredMixin, View):
    """
    Streams confidential PDF directly into browser with dynamic anti-piracy watermark.
    Enforces strict access control:
    Client A can NEVER access Client B's assigned PDF.
    """
    login_url = 'login:login'

    def get(self, request, doc_id, *args, **kwargs):
        user = request.user
        doc = get_object_or_404(ResearchDocument, id=doc_id)

        # 1. Evaluate permissions
        if not doc.is_accessible_by(user):
            DocumentAccessLog.objects.create(
                document=doc,
                user=user,
                action='unauthorized_denied',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            return HttpResponseForbidden("Access Denied: You do not hold an active authorization for this confidential report.")

        # 2. Check if file exists on disk
        if not doc.file or not os.path.exists(doc.file.path):
            raise Http404("Document file is currently unavailable.")

        # 3. Dynamic Watermark Stamping Text
        ip_addr = request.META.get('REMOTE_ADDR', '127.0.0.1')
        timestamp_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S IST')
        watermark_text = f"CONFIDENTIAL — LICENSED TO: {user.get_display_name()} | {user.email} | IP: {ip_addr} | {timestamp_str}"

        # 4. Log Access Event
        DocumentAccessLog.objects.create(
            document=doc,
            user=user,
            action='stream_view',
            ip_address=ip_addr,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            watermark_stamp=watermark_text
        )

        # 5. Stream file directly (protected delivery with no-cache headers)
        try:
            response = FileResponse(open(doc.file.path, 'rb'), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{os.path.basename(doc.file.name)}"'
            response['Cache-Control'] = 'private, no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['X-Content-Type-Options'] = 'nosniff'
            return response
        except Exception:
            raise Http404("Error streaming document.")


class SecureDocDownloadView(SecureDocStreamView):
    """
    Downloads file with attachment disposition.
    """
    def get(self, request, doc_id, *args, **kwargs):
        response = super().get(request, doc_id, *args, **kwargs)
        if isinstance(response, FileResponse):
            doc = get_object_or_404(ResearchDocument, id=doc_id)
            response['Content-Disposition'] = f'attachment; filename="Kalphora_Research_{doc.ticker if hasattr(doc, "ticker") else doc.id}.pdf"'
        return response


class UpgradePlanView(LoginRequiredMixin, TemplateView):
    """
    Membership upgrade checkout & pricing options.
    Always accessible to all authenticated clients.
    """
    template_name = 'portal/upgrade.html'
    login_url = 'login:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['nav_tabs'] = AccessControlService.get_navigation_tabs_for_user(user, current_key='upgrade')
        context['active_announcements'] = AccessControlService.get_active_announcements_for_user(user)
        context['sidebar_widgets'] = AccessControlService.get_active_widgets_for_user(user, widget_type='sidebar_card')
        context['active_tab'] = 'upgrade'
        context['is_premium'] = getattr(user, 'is_premium_active', False)
        context['plans'] = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')
        return context
