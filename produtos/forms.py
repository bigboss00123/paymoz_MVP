from django import forms
from django.forms import inlineformset_factory
from .models import Produto, ItemIncluido, ProdutoImagem, AvaliacaoProduto
from tinymce.widgets import TinyMCE # Importar TinyMCE

class ProdutoForm(forms.ModelForm):
    """
    Formulário atualizado para criar e editar produtos com a nova interface.
    """
    class Meta:
        model = Produto
        fields = [
            'nome',
            'preco',
            'preco_oferta',
            'categoria',
            'imagem_destaque',
            'descricao_curta',
            'descricao',
            'depoimentos',
            'gatilhos_mentais',
            'titulo_seo',
            'descricao_seo',
            'titulo_cabecalho',
            'slug',
            'permitir_comentarios',
            'mostrar_relacionados',
            'habilitar_analytics',
            'css_customizado',
            'campos_personalizados',
            'mensagem_whatsapp_sucesso',
            'callback_url',
            'arquivo_download',
            'foto_criador',
            'sobre_o_criador',
            'facebook_pixel_id',
            'video_url',
            'faq',
        ]
        widgets = {
            'descricao': TinyMCE(attrs={'cols': 80, 'rows': 30}), # Usar TinyMCE para o campo descricao
            'depoimentos': forms.HiddenInput(),
            'gatilhos_mentais': forms.HiddenInput(),
            'campos_personalizados': forms.HiddenInput(),
            'faq': forms.HiddenInput(),
            'mensagem_whatsapp_sucesso': forms.Textarea(attrs={'rows': 4}),
            'callback_url': forms.URLInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-paymoz-primary', 'placeholder': 'https://seusite.com/sucesso'}),
            'video_url': forms.URLInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-paymoz-primary', 'placeholder': 'https://www.youtube.com/embed/seu_video'}),
        }
        # Os widgets para os outros campos serão aplicados diretamente no template.

class ItemIncluidoForm(forms.ModelForm):
    class Meta:
        model = ItemIncluido
        fields = ['descricao']

class ProdutoImagemForm(forms.ModelForm):
    class Meta:
        model = ProdutoImagem
        fields = ['imagem']
        # Os widgets para os outros campos serão aplicados diretamente no template.

class AvaliacaoForm(forms.ModelForm):
    class Meta:
        model = AvaliacaoProduto
        fields = ['rating', 'comentario']
        widgets = {
            'rating': forms.HiddenInput(), # O rating será controlado por estrelas na UI
        }

ItemIncluidoFormSet = inlineformset_factory(Produto, ItemIncluido, form=ItemIncluidoForm, extra=1, can_delete=True)
ProdutoImagemFormSet = inlineformset_factory(Produto, ProdutoImagem, form=ProdutoImagemForm, extra=1, can_delete=True)
