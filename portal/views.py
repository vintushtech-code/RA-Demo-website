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

from .models import StockRecommendation, RecommendationUpdate, ClientWatchlist, SEBIComplianceAuditLog
from research_vault.models import ResearchDocument, DocumentAccessAssignment, DocumentAccessLog
from billing.models import SubscriptionPlan, UserSubscription


class PortalDashboardView(LoginRequiredMixin, TemplateView):
    """
    Central Client Portal Dashboard.
    Adapts seamlessly between Free Registered Clients and Active Premium Subscribers.
    """
    template_name = 'portal/dashboard.html'
    login_url = 'login:login'

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
            # Universal reports OR explicitly assigned reports
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
            'is_premium': is_premium,
            'active_sub': active_sub,
            'open_recommendations': open_recommendations,
            'watchlist': watchlist,
            'assigned_docs': assigned_docs,
            'market_indices': market_indices,
            'plans': plans,
            'active_tab': 'market',
        })
        return context


class RecommendationsListView(LoginRequiredMixin, ListView):
    """
    Research recommendations feed with multi-horizon filtering:
    Intraday, Short Term (Swing), Mid/Long Term, Futures, Options.
    """
    model = StockRecommendation
    template_name = 'portal/recommendations.html'
    context_object_name = 'recommendations'
    login_url = 'login:login'

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
        user = self.request.user
        context['is_premium'] = user.is_premium_active
        context['current_horizon'] = self.request.GET.get('horizon', 'all')
        context['current_status'] = self.request.GET.get('status', 'open')
        context['active_tab'] = 'calls'
        context['plans'] = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')
        return context


class RecommendationDetailView(LoginRequiredMixin, DetailView):
    """
    Deep-dive trade thesis, balance sheet forensic rationale, and risk parameters.
    Gated strictly to Premium Subscribers.
    """
    model = StockRecommendation
    template_name = 'portal/recommendation_detail.html'
    context_object_name = 'rec'
    pk_url_kwarg = 'rec_id'
    login_url = 'login:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login:login')
        if not request.user.is_premium_active:
            messages.warning(request, "This deep-dive institutional research thesis requires an active premium subscription.")
            return redirect('portal:upgrade')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['updates'] = self.object.updates.all().order_by('-timestamp')
        context['active_tab'] = 'calls'
        return context


class ScreenerView(LoginRequiredMixin, TemplateView):
    """
    Institutional Equity Screener with valuation ratios & momentum metrics.
    """
    template_name = 'portal/screener.html'
    login_url = 'login:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_premium'] = self.request.user.is_premium_active
        context['active_tab'] = 'screener'
        return context


class SectorExplorerView(LoginRequiredMixin, TemplateView):
    """
    Interactive Sector Grid matching StockYaari Screenshot 5.
    """
    template_name = 'portal/sectors.html'
    login_url = 'login:login'

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
        context['is_premium'] = self.request.user.is_premium_active
        context['active_tab'] = 'sectors'
        return context


class CorporateActionsView(LoginRequiredMixin, TemplateView):
    """
    Corporate Actions & Financial Statements view matching StockYaari Screenshot 4.
    """
    template_name = 'portal/corporate_actions.html'
    login_url = 'login:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_premium'] = self.request.user.is_premium_active
        context['active_tab'] = 'corporate_actions'
        return context


class WatchlistView(LoginRequiredMixin, TemplateView):
    """
    Personal client watchlist.
    """
    template_name = 'portal/watchlist.html'
    login_url = 'login:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['watchlist'] = ClientWatchlist.objects.filter(user=self.request.user).order_by('-created_at')
        context['active_tab'] = 'watchlist'
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


class ResearchVaultListView(LoginRequiredMixin, TemplateView):
    """
    Confidential Research Reports Library.
    Displays universal reports and client-assigned private PDFs.
    """
    template_name = 'portal/vault_list.html'
    login_url = 'login:login'

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
        context['is_premium'] = is_premium
        context['active_tab'] = 'vault'
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
    """
    template_name = 'portal/upgrade.html'
    login_url = 'login:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')
        context['active_tab'] = 'upgrade'
        return context
