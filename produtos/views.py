from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt # Importar csrf_exempt
from django.contrib import messages
from .models import Produto, AvaliacaoProduto # Importar AvaliacaoProduto
from .forms import ProdutoForm, ItemIncluidoFormSet, ProdutoImagemFormSet, AvaliacaoForm
from core.models import UserProfile, CheckoutSession
from decimal import Decimal
from django.utils.text import slugify
from django.db.models import Avg # Importar Avg para calcular média

@require_POST
def adicionar_avaliacao(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    form = AvaliacaoForm(request.POST)

    if form.is_valid():
        avaliacao = form.save(commit=False)
        avaliacao.produto = produto
        avaliacao.save()
        messages.success(request, 'Obrigado pela sua avaliação! Ela será exibida após a aprovação.')
    else:
        messages.error(request, 'Ocorreu um erro ao enviar sua avaliação. Por favor, tente novamente.')

    return redirect('produtos:pagina_venda', slug=produto.slug)


@csrf_exempt # Adicionar este decorador
@require_POST
def processar_venda_produto(request, produto_id):
    logger.info("Entrou na função processar_venda_produto.")
    """
    Processa o formulário de compra da página de vendas.
    Cria uma sessão de checkout e redireciona para o pagamento.
    """
    produto = get_object_or_404(Produto, id=produto_id, status='ATIVO')

    # O campo nome_cliente padrão foi removido do template,
    # então ele não será mais obtido diretamente do request.POST.
    # Se o nome for necessário, ele deve vir de um campo personalizado.
    # Caso contrário, será uma string vazia.
    numero_celular = request.POST.get('numero_celular')
    email_cliente = request.POST.get('email_cliente') # Captura o email do cliente

    if not numero_celular:
        messages.error(request, "Por favor, preencha o número de WhatsApp.")
        logger.warning(f"Campos obrigatórios não preenchidos: numero_celular={numero_celular}")
        return redirect('produtos:pagina_venda', slug=produto.slug)

    # Coletar dados dos campos personalizados
    dados_customizados = {}
    nome_cliente_from_custom = ""
    if produto.campos_personalizados:
        for campo in produto.campos_personalizados:
            slug_label = slugify(campo.get('label'))
            valor_campo = request.POST.get(f'custom_{slug_label}')
            if valor_campo: # Only add if value is not empty
                dados_customizados[campo.get('label')] = valor_campo
            
            # Tenta obter o nome do cliente de um campo personalizado
            if campo.get('label').lower() == 'nome completo' or campo.get('label').lower() == 'seu nome completo':
                nome_cliente_from_custom = valor_campo if valor_campo else ""

    # Adiciona o número de celular principal aos dados customizados
    if numero_celular:
        dados_customizados['Número de WhatsApp'] = numero_celular

    # Adiciona o email aos dados customizados
    if email_cliente:
        dados_customizados['Email do Cliente'] = email_cliente

    # Define o nome do cliente para a sessão de checkout
    # Prioriza o nome do campo personalizado, caso exista
    nome_cliente_para_session = nome_cliente_from_custom if nome_cliente_from_custom else ""


    # Define o preço a ser usado (oferta ou normal)
    preco_a_cobrar = produto.preco_oferta if produto.preco_oferta is not None else produto.preco

    # Cria a sessão de checkout associada ao dono do produto
    session = CheckoutSession.objects.create(
        user_profile=produto.user_profile,
        valor=preco_a_cobrar, # Usa o preço correto
        nome_cliente=nome_cliente_para_session, # Usa o nome do campo personalizado ou string vazia
        nome_produto=produto.nome,
        dados_cliente_custom=dados_customizados, # Salva os dados customizados
        callback_url=request.build_absolute_uri(reverse('home')),
        email_cliente=email_cliente # Salva o email do cliente na sessão
    )

    # Redireciona para a página de checkout hospedada que já existe em core
    checkout_url = reverse('hosted_checkout', args=[session.session_id])
    return redirect(checkout_url)

from django.http import Http404
import logging

logger = logging.getLogger(__name__)

def pagina_venda(request, slug):
    """
    View pública para exibir a página de vendas de um produto.
    """
    logger.info(f"Tentando acessar página de venda com slug: {slug}")
    try:
        produto = Produto.objects.prefetch_related('itens_incluidos', 'imagens_galeria').get(slug=slug)
        
        # Buscar avaliações aprovadas para este produto
        avaliacoes_aprovadas = AvaliacaoProduto.objects.filter(produto=produto).order_by('-data_avaliacao')

        logger.info(f"Produto encontrado: {produto.nome}, Status: {produto.status}")
        if produto.status != 'ATIVO':
            logger.warning(f"Produto {produto.nome} (slug: {slug}) não está ATIVO. Status atual: {produto.status}")
            # Redirecionar ou mostrar uma mensagem de erro se o produto não estiver ativo
            return render(request, 'produtos/produto_nao_ativo.html', {'produto': produto}) # Criar este template depois

    except Produto.DoesNotExist:
        logger.error(f"Produto com slug '{slug}' não encontrado.")
        raise Http404("Produto não encontrado.")
    
    # Lógica de pagamento será adicionada aqui depois
    print(f"FAQ do produto: {produto.faq}") # Linha de depuração
    context = {
        'produto': produto,
        'avaliacoes_aprovadas': avaliacoes_aprovadas, # Adicionar ao contexto
    }
    return render(request, 'produtos/pagina_venda_nova.html', context)

@login_required
def deletar_produto(request, produto_id):
    """
    View para deletar um produto.
    """
    produto = get_object_or_404(Produto, id=produto_id)
    
    # Garante que o usuário só possa deletar seus próprios produtos
    if produto.user_profile.user != request.user:
        messages.error(request, 'Você não tem permissão para deletar este produto.')
        return redirect('dashboard')

    if request.method == 'POST':
        nome_produto = produto.nome
        produto.delete()
        messages.success(request, f'Produto "{nome_produto}" foi deletado com sucesso.')
        return redirect('dashboard')

    context = {
        'produto': produto
    }
    return render(request, 'produtos/confirmar_delete.html', context)


@login_required
def criar_produto(request):
    """
    View para criar um novo produto.
    """
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        item_incluido_formset = ItemIncluidoFormSet(request.POST, request.FILES, prefix='itens_incluidos')
        imagem_formset = ProdutoImagemFormSet(request.POST, request.FILES, prefix='imagens')

        if form.is_valid() and item_incluido_formset.is_valid() and imagem_formset.is_valid():
            produto = form.save(commit=False)
            user_profile = get_object_or_404(UserProfile, user=request.user)
            produto.user_profile = user_profile
            produto.status = 'ATIVO'
            produto.save()
            
            item_incluido_formset.instance = produto
            item_incluido_formset.save()

            imagem_formset.instance = produto
            imagem_formset.save()

            messages.success(request, f'Produto "{produto.nome}" criado com sucesso!')
            return redirect('dashboard')
        else:
            # Error handling
            pass

    else:
        form = ProdutoForm()
        item_incluido_formset = ItemIncluidoFormSet(prefix='itens_incluidos')
        imagem_formset = ProdutoImagemFormSet(prefix='imagens')
    
    context = {
        'form': form,
        'item_incluido_formset': item_incluido_formset,
        'imagem_formset': imagem_formset,
        'titulo': 'Criar Novo Produto'
    }
    return render(request, 'produtos/criar_editar_produto_novo.html', context)

@login_required
def editar_produto(request, produto_id):
    """
    View para editar um produto existente.
    """
    produto = get_object_or_404(Produto, id=produto_id)
    
    if produto.user_profile.user != request.user:
        messages.error(request, 'Você não tem permissão para editar este produto.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        item_incluido_formset = ItemIncluidoFormSet(request.POST, request.FILES, instance=produto, prefix='itens_incluidos')
        imagem_formset = ProdutoImagemFormSet(request.POST, request.FILES, instance=produto, prefix='imagens')

        if form.is_valid() and item_incluido_formset.is_valid() and imagem_formset.is_valid():
            form.save()
            item_incluido_formset.save()
            imagem_formset.save()
            messages.success(request, f'Produto "{produto.nome}" atualizado com sucesso!')
            return redirect('dashboard')
        else:
            # Error handling
            pass

    else:
        form = ProdutoForm(instance=produto)
        item_incluido_formset = ItemIncluidoFormSet(instance=produto, prefix='itens_incluidos')
        imagem_formset = ProdutoImagemFormSet(instance=produto, prefix='imagens')

    context = {
        'form': form,
        'item_incluido_formset': item_incluido_formset,
        'imagem_formset': imagem_formset,
        'titulo': f'Editando "{produto.nome}"'
    }
    return render(request, 'produtos/criar_editar_produto_novo.html', context)


@login_required
def gerenciar_avaliacoes(request):
    """
    View para listar avaliações pendentes de aprovação para os produtos do usuário logado.
    """
    # Busca todos os produtos que pertencem ao user_profile do usuário logado
    user_products = Produto.objects.filter(user_profile__user=request.user)
    
    # Busca todas as avaliações não aprovadas para esses produtos
    avaliacoes_pendentes = AvaliacaoProduto.objects.filter(
        produto__in=user_products,
        aprovado=False
    ).order_by('-data_criacao')

    context = {
        'avaliacoes_pendentes': avaliacoes_pendentes
    }
    return render(request, 'produtos/gerenciar_avaliacoes.html', context)


@login_required
@require_POST
def aprovar_rejeitar_avaliacao(request, avaliacao_id, action):
    """
    View para aprovar ou rejeitar uma avaliação.
    """
    avaliacao = get_object_or_404(AvaliacaoProduto, id=avaliacao_id)

    # Verifica se o usuário logado é o dono do produto associado à avaliação
    if avaliacao.produto.user_profile.user != request.user:
        messages.error(request, 'Você não tem permissão para gerenciar esta avaliação.')
        return redirect('produtos:gerenciar_avaliacoes')

    if action == 'aprovar':
        avaliacao.aprovado = True
        avaliacao.save()
        messages.success(request, 'Avaliação aprovada com sucesso!')
    elif action == 'rejeitar':
        avaliacao.delete() # Ou pode-se marcar como rejeitada em vez de deletar
        messages.success(request, 'Avaliação rejeitada e removida.')
    else:
        messages.error(request, 'Ação inválida.')
    
    return redirect('produtos:gerenciar_avaliacoes')

@login_required
def criar_editar_produto_novo(request, produto_id=None):
    """
    View unificada para criar e editar produtos com a nova interface.
    """
    if produto_id:
        produto = get_object_or_404(Produto, id=produto_id, user_profile__user=request.user)
        titulo = f'Editando: {produto.nome}'
    else:
        produto = None
        titulo = 'Criar Novo Produto'

    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        imagem_formset = ProdutoImagemFormSet(request.POST, request.FILES, instance=produto, prefix='imagens')

        if form.is_valid() and imagem_formset.is_valid():
            logger.debug(f"request.FILES: {request.FILES}")
            logger.debug(f"arquivo_download no cleaned_data: {form.cleaned_data.get('arquivo_download')}")
            print(f"FAQ recebido do formulário: {form.cleaned_data.get('faq')}") # Linha de depuração
            novo_produto = form.save(commit=False)
            if not produto_id:
                novo_produto.user_profile = get_object_or_404(UserProfile, user=request.user)
            
            # Atribuir o FAQ explicitamente
            novo_produto.faq = form.cleaned_data.get('faq', [])

            logger.debug(f"novo_produto.arquivo_download antes de salvar: {novo_produto.arquivo_download}")
            novo_produto.save()
            logger.debug(f"novo_produto.arquivo_download depois de salvar: {novo_produto.arquivo_download}")
            
            # Salvar o formset de imagens da galeria
            imagem_formset.instance = novo_produto
            imagem_formset.save()

            messages.success(request, f'Produto "{novo_produto.nome}" salvo com sucesso!')
            return redirect('produtos:editar_produto_novo', produto_id=novo_produto.id)
        else:
            # Adicionar logs de erro para depuração
            print("Erros do formulário principal:", form.errors)
            print("Erros do formset de imagens:", imagem_formset.errors)
            print("Erros não relacionados a formulários no formset:", imagem_formset.non_form_errors())
            messages.error(request, 'Houve um erro no formulário. Por favor, verifique os campos.')
    else:
        form = ProdutoForm(instance=produto)
        imagem_formset = ProdutoImagemFormSet(instance=produto, prefix='imagens_galeria')

    context = {
        'form': form,
        'imagem_formset': imagem_formset,
        'produto': produto,
        'titulo': titulo,
    }
    return render(request, 'produtos/criar_editar_produto.html', context)
