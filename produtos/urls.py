from django.urls import path
from . import views

app_name = 'produtos'

urlpatterns = [
    path('criar/', views.criar_produto, name='criar_produto'),
    path('editar/<uuid:produto_id>/', views.editar_produto, name='editar_produto'),
    path('deletar/<uuid:produto_id>/', views.deletar_produto, name='deletar_produto'),
    path('<slug:slug>/', views.pagina_venda, name='pagina_venda'),
    path('processar-venda/<uuid:produto_id>/', views.processar_venda_produto, name='processar_venda_produto'),
    path('avaliar/<uuid:produto_id>/', views.adicionar_avaliacao, name='adicionar_avaliacao'),
    path('gerenciar-avaliacoes/', views.gerenciar_avaliacoes, name='gerenciar_avaliacoes'),
    path('avaliacoes/<uuid:avaliacao_id>/<str:action>/', views.aprovar_rejeitar_avaliacao, name='aprovar_rejeitar_avaliacao'),
]
