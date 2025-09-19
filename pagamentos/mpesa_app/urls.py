from django.urls import path
from .views import pagamento_mpesa, dashborad, pagamento_b2c, login_view, logout_view, render_login_page, list_all_transactions, login_view, logout_view, render_login_page, list_all_transactions

urlpatterns = [
    path('pagamento_mpesa/', pagamento_mpesa, name='pagamento_mpesa'),
    path('dashboard/', dashborad, name='dashboard'),
    path('pagamento_b2c/', pagamento_b2c, name='pagamento_b2c'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('login_page/', render_login_page, name='login_page'),
    path('all_transactions/', list_all_transactions, name='all_transactions'),
]