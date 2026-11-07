from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Main Client Portal Dashboard
    path('', views.PortalDashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.PortalDashboardView.as_view(), name='dashboard_alt'),
    
    # Research Recommendations (Free Teaser + Premium Unlocked)
    path('recommendations/', views.RecommendationsListView.as_view(), name='recommendations'),
    path('recommendations/<uuid:rec_id>/', views.RecommendationDetailView.as_view(), name='recommendation_detail'),
    
    # Screener & Sector Explorer
    path('screener/', views.ScreenerView.as_view(), name='screener'),
    path('sectors/', views.SectorExplorerView.as_view(), name='sectors'),
    
    # Corporate Actions & Financial Statements
    path('corporate-actions/', views.CorporateActionsView.as_view(), name='corporate_actions'),
    
    # Watchlist Management
    path('watchlist/', views.WatchlistView.as_view(), name='watchlist'),
    path('api/watchlist/toggle/', views.WatchlistToggleAPIView.as_view(), name='watchlist_toggle_api'),
    
    # Secure Research PDF Vault
    path('vault/', views.ResearchVaultListView.as_view(), name='vault_list'),
    path('vault/doc/<uuid:doc_id>/stream/', views.SecureDocStreamView.as_view(), name='vault_stream'),
    path('vault/doc/<uuid:doc_id>/download/', views.SecureDocDownloadView.as_view(), name='vault_download'),
    
    # Membership Upgrade & Plans
    path('upgrade/', views.UpgradePlanView.as_view(), name='upgrade'),
]
