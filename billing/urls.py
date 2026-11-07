from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Razorpay Test Mode Order & Verification Endpoints
    path('order/create/', views.CreateRazorpayOrderView.as_view(), name='create_order'),
    path('payment/verify/', views.VerifyRazorpayPaymentView.as_view(), name='verify_payment'),
    path('payment/failed/', views.PaymentFailureHandlerView.as_view(), name='payment_failed'),
    path('webhook/', views.RazorpayWebhookView.as_view(), name='webhook'),
]

