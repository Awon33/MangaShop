from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('stripe-payment/<int:order_id>/', views.stripe_payment, name='stripe_payment'),
    path('paypal-payment/<int:order_id>/', views.paypal_payment, name='paypal_payment'),
    path('paypal-execute/<int:order_id>/', views.paypal_execute, name='paypal_execute'),
    path('paypal-cancel/<int:order_id>/', views.paypal_cancel, name='paypal_cancel'),
    path('payment-success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('payment-cancel/<int:order_id>/', views.payment_cancel, name='payment_cancel'),
]