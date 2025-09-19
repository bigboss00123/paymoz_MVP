from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import UserProfile
from django.conf import settings # Importar settings
import uuid # Importar uuid

class Produto(models.Model):
    """
    Modelo para gerenciar produtos digitais dos usuários, versão aprimorada.
    """
    STATUS_CHOICES = (
        ('ATIVO', 'Ativo'),
        ('RASCUNHO', 'Rascunho'),
        ('INATIVO', 'Inativo'),
    )
    CATEGORIA_CHOICES = (
        ('CURSO_ONLINE', 'Curso Online'),
        ('EBOOK', 'E-book'),
        ('SOFTWARE', 'Software'),
        ('CONSULTORIA', 'Consultoria'),
        ('TEMPLATE', 'Template'),
        ('OUTRO', 'Outro'),
    )

    # --- Campos Principais ---
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='produtos', verbose_name='Dono do Produto')
    nome = models.CharField(max_length=255, verbose_name='Nome do Produto')
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text='URL amigável. Deixe em branco para gerar automaticamente.')
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Preço (MZN)')
    preco_oferta = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Preço de Oferta (MZN)', null=True, blank=True)
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, default='CURSO_ONLINE', verbose_name='Categoria')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='RASCUNHO', verbose_name='Status')

    # --- Conteúdo da Página de Vendas ---
    video_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='URL do Vídeo de Vendas', help_text='Link do vídeo (YouTube, Vimeo). Aparecerá no topo da página. Use o link de incorporação (embed).')
    descricao_curta = models.TextField(blank=True, verbose_name='Descrição Curta', help_text='Aparece nos cards e resumos.')
    descricao = models.TextField(verbose_name='Descrição Completa')
    imagem_destaque = models.ImageField(upload_to='produtos_imagens/', null=True, blank=True, verbose_name='Imagem de Destaque')
    o_que_esta_incluido = models.JSONField(default=list, blank=True, help_text='Lista de itens incluídos no produto. Ex: ["50+ videoaulas", "Material de apoio"]')
    depoimentos = models.JSONField(default=list, blank=True, help_text='Lista de depoimentos. Ex: [{"autor": "João", "profissao": "Estudante", "texto": "Excelente!", "rating": 5}]')
    gatilhos_mentais = models.JSONField(default=dict, blank=True, help_text='Gatilhos mentais. Ex: {"escassez": {"texto": "Apenas 10 vagas!"}, "garantia": {"dias": 30}}')
    campos_personalizados = models.JSONField(default=list, blank=True, help_text='Definição de campos personalizados para o checkout. Ex: [{"label": "Seu WhatsApp", "tipo": "tel", "obrigatorio": true}]')
    faq = models.JSONField(default=list, blank=True, help_text='Lista de Perguntas Frequentes (FAQ). Ex: [{"pergunta": "Como acesso?", "resposta": "Após a compra..."}]')

    # --- Sobre o Criador ---
    foto_criador = models.ImageField(upload_to='criadores_fotos/', null=True, blank=True, verbose_name='Foto do Criador')
    sobre_o_criador = models.TextField(blank=True, verbose_name='Sobre o Criador', help_text='Uma breve biografia que aparecerá na página de vendas para gerar confiança.')

    # --- SEO e Configurações Avançadas ---
    titulo_seo = models.CharField(max_length=60, blank=True, verbose_name='Título SEO', help_text='Título que aparecerá no Google (máx. 60 caracteres).')
    descricao_seo = models.CharField(max_length=160, blank=True, verbose_name='Descrição SEO', help_text='Descrição para o Google (máx. 160 caracteres).')
    permitir_comentarios = models.BooleanField(default=False, verbose_name='Permitir Comentários na Página')
    mostrar_relacionados = models.BooleanField(default=True, verbose_name='Mostrar Produtos Relacionados')
    habilitar_analytics = models.BooleanField(default=True, verbose_name='Habilitar Analytics')
    titulo_cabecalho = models.CharField(max_length=100, blank=True, verbose_name='Título do Cabeçalho', help_text='Título que aparecerá no topo da página de vendas. Se deixado em branco, o nome do produto será usado.')
    css_customizado = models.TextField(blank=True, verbose_name='CSS Personalizado')
    facebook_pixel_id = models.CharField(max_length=100, blank=True, verbose_name='Facebook Pixel ID', help_text='ID do seu Pixel do Facebook para rastreamento de conversões.')

    # --- Métricas e Timestamps ---
    vendidos = models.PositiveIntegerField(default=0, verbose_name='Quantidade Vendida')
    mensagem_whatsapp_sucesso = models.TextField(blank=True, null=True, help_text="Mensagem personalizada para enviar ao comprador no WhatsApp após a compra. Use {nome_cliente}, {nome_produto}, {valor_pago}.")
    callback_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL para onde o cliente será redirecionado após o pagamento bem-sucedido. Se deixado em branco, será usada uma página de sucesso padrão.")
    arquivo_download = models.FileField(upload_to='produtos_downloads/', null=True, blank=True, help_text="Ficheiro digital para download após a compra (ex: PDF, ZIP).")

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('detalhe_produto', kwargs={'slug': self.slug})


class ItemIncluido(models.Model):
    produto = models.ForeignKey(Produto, related_name='itens_incluidos', on_delete=models.CASCADE)
    descricao = models.CharField(max_length=255)

    def __str__(self):
        return self.descricao

class ProdutoImagem(models.Model):
    produto = models.ForeignKey(Produto, related_name='imagens_galeria', on_delete=models.CASCADE)
    imagem = models.ImageField(upload_to='produtos_galeria/')

    def __str__(self):
        return f"Imagem para {self.produto.nome}"

class AvaliacaoProduto(models.Model):
    produto = models.ForeignKey(Produto, related_name='avaliacoes', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True, null=True)
    data_avaliacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('produto', 'user') # Um usuário só pode avaliar um produto uma vez

    def __str__(self):
        return f"Avaliação de {self.user.username} para {self.produto.nome}"
