from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_sso, name='login_sso'),
    path('sso/callback/', views.sso_callback, name='sso_callback'),
    path('logout/', views.sso_logout, name='logout'),
    path('logout/silent/', views.sso_silent_logout_redirect, name='sso_silent_logout_redirect'),
    path('logout-success/', views.logout_success_view, name='logout_success'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('api/saque/', views.solicitar_saque_api, name='solicitar_saque_api'),
    path('checkout/pro/', views.checkout_pro_view, name='checkout_pro'),
    path('documentacao/', views.documentacao_view, name='documentacao'),
    path('api/v1/payment/<str:method>/', views.process_payment, name='process_payment'),
    path('api/v1/checkout/session/', views.create_checkout_session, name='create_checkout_session'),
    path('checkout/pay/<uuid:session_id>/', views.hosted_checkout_view, name='hosted_checkout'),
    path('saques/cancelar/<uuid:saque_id>/', views.cancelar_saque, name='cancelar_saque'),
    path('pagamento/sucesso/', views.payment_success_page, name='payment_success_page'),
    path('api/send-verification-email/', views.send_verification_email, name='send_verification_email'),
    path('api/verify-email-code/', views.verify_email_code, name='verify_email_code'),
    path('membros_admin_paymoz/', views.total_transactions_panel_view, name='membros_admin_paymoz'),
    path('admin/withdraw/', views.admin_withdraw_view, name='admin_withdraw'),
]
