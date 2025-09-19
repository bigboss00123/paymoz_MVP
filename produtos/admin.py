from django.contrib import admin
from .models import Produto, ProdutoImagem, AvaliacaoProduto

class ProdutoImagemInline(admin.TabularInline):
    model = ProdutoImagem
    extra = 1

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'user_profile', 'preco', 'status', 'categoria', 'vendidos')
    list_filter = ('status', 'categoria', 'user_profile__user__username')
    search_fields = ('nome', 'descricao', 'descricao_curta', 'user_profile__user__username')
    prepopulated_fields = {'slug': ('nome',)}
    list_editable = ('status', 'preco', 'categoria')
    ordering = ('-id',)
    inlines = [ProdutoImagemInline]

    fieldsets = (
        ('Informações Principais', {
            'fields': ('user_profile', 'nome', 'slug', 'preco', 'status', 'categoria')
        }),
        ('Conteúdo da Página de Vendas', {
            'classes': ('collapse',),
            'fields': ('imagem_destaque', 'descricao_curta', 'descricao', 'o_que_esta_incluido', 'depoimentos', 'gatilhos_mentais')
        }),
        ('SEO e Avançado', {
            'classes': ('collapse',),
            'fields': ('titulo_seo', 'descricao_seo', 'permitir_comentarios', 'mostrar_relacionados', 'habilitar_analytics', 'css_customizado', 'callback_url')
        }),
        ('Métricas', {
            'fields': ('vendidos',)
        }),
    )

@admin.register(AvaliacaoProduto)
class AvaliacaoProdutoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'user', 'rating', 'data_avaliacao')
    list_filter = ('produto', 'rating')
    search_fields = ('produto__nome', 'comentario', 'user__username')
