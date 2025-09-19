from django.db import models, transaction
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
import requests
import json
import base64
import hashlib
import secrets
from urllib.parse import urlencode
import logging
from django.core.mail import send_mail # Importar send_mail
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import User, UserProfile, Saque, Package, Transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import date, timedelta, datetime
from decimal import Decimal
import uuid
from pagamentos.mpesa_app.logica_mpesa import numero_normal, referencia_transacao
from portalsdk import APIContext, APIMethodType, APIRequest

logger = logging.getLogger(__name__)

def normalizar_numero_base(numero: str) -> str:
    """
    Remove caracteres não numéricos do número.
    """
    return ''.join(filter(str.isdigit, numero))

def normalizar_numero_whatsapp(numero: str) -> str:
    """
    Remove caracteres não numéricos e o '+' inicial do número de celular.
    Assume que o número já inclui o código do país, se necessário.
    """
    numero_limpo = normalizar_numero_base(numero)

    if numero_limpo.startswith('+'):
        return numero_limpo[1:]
    else:
        return numero_limpo

def normalizar_numero_mpesa(numero: str) -> str:
    """
    Normaliza o numero de celular para o formato M-Pesa (sem +).
    """
    numero_limpo = normalizar_numero_base(numero)

    if numero_limpo.startswith('258') and len(numero_limpo) == 12:
        return numero_limpo
    elif len(numero_limpo) == 9 and (numero_limpo.startswith('84') or numero_limpo.startswith('85') or numero_limpo.startswith('86') or numero_limpo.startswith('87')):
        return '258' + numero_limpo
    elif numero_limpo.startswith('+'): # Remove o + se tiver
        return numero_limpo[1:]
    else:
        return numero_limpo

def normalizar_numero_emola(numero: str) -> str:
    """
    Normaliza o numero de celular para o formato e-Mola (9 digitos).
    """
    numero_limpo = ''.join(filter(str.isdigit, numero))
    # Retorna os ultimos 9 digitos
    if len(numero_limpo) > 9:
        return numero_limpo[-9:]
    return numero_limpo

def send_whatsapp_message(number, message):
    nodejs_api_url = 'http://5.189.144.249:3002/send-message'
    try:
        response = requests.post(
            nodejs_api_url,
            json={
                'number': number,
                'message': message
            },
            timeout=30
        )
        response.raise_for_status()  # Levanta HTTPError para respostas de erro (4xx ou 5xx)
        logger.info(f"Mensagem WhatsApp enviada com sucesso para {number}")
        return response.json() # Retorna a resposta JSON em caso de sucesso
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 503:
            logger.error(f"Erro 503 (Service Unavailable) ao enviar mensagem WhatsApp para {number}. O serviço externo pode estar temporariamente indisponível. Detalhes: {e.response.text}")
        else:
            logger.error(f"Erro HTTP ({e.response.status_code}) ao enviar mensagem WhatsApp para {number}: {e.response.text}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erro de conexão ao enviar mensagem WhatsApp para {number}: {e}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout ao enviar mensagem WhatsApp para {number}: {e}")
        return None
    except requests.exceptions.RequestException as e: # Captura quaisquer outros erros relacionados a requests
        logger.error(f"Erro desconhecido ao enviar mensagem WhatsApp para {number}: {e}")
        return None

def enviar_notificacao(user_profile, valor_saque, numero_celular):
    """
    Imprime uma mensagem de notificação para o administrador sobre uma nova solicitação de saque.
    """
    user = user_profile.user
    nome_completo = f"{user.name} {user.surname}".strip() if user.name or user.surname else user.username
    
    mensagem = (
        f"Sr. Admin, há uma nova solicitação de saque!\n"
        f"----------------------------------------\n"
        f"Nome do Usuário: {nome_completo}\n"
        f"Email do Usuário: {user.email}\n"
        f"Contato (informado no formulário): {numero_celular}\n"
        f"Valor do Saque: {valor_saque:.2f} MZN\n"
        f"ID do Perfil do Usuário: {user_profile.id}\n"
        f"----------------------------------------"
    )

    send_whatsapp_message(normalizar_numero_whatsapp('258845508884'), mensagem )
    send_whatsapp_message(normalizar_numero_whatsapp('258860614661'), mensagem )
    send_whatsapp_message(normalizar_numero_whatsapp('258878172325'), mensagem )
    send_whatsapp_message(normalizar_numero_whatsapp('258878005941'), mensagem )
    print("DEBUG: Função enviar_notificacao foi chamada.") # Adicione esta linha
    logger.info(mensagem)

def enviar_notificacao_venda(transaction):
    """
    Envia uma mensagem de notificação para o vendedor sobre uma nova venda,
    usando uma mensagem personalizada do produto, se configurada.
    """
    user_profile = transaction.user_profile
    user = user_profile.user
    nome_completo_vendedor = f"{user.name} {user.surname}".strip() if user.name or user.surname else user.username

    nome_produto = transaction.checkout_session.nome_produto if transaction.checkout_session else 'N/A' # Definir nome_produto aqui

    # Tenta obter o produto associado à transação
    produto = None
    nome_produto = transaction.checkout_session.nome_produto if transaction.checkout_session else 'N/A' # Definir nome_produto aqui

    if transaction.checkout_session and transaction.checkout_session.nome_produto:
        try:
            # Assumindo que nome_produto na CheckoutSession corresponde ao nome do Produto
            # Uma abordagem mais robusta seria armazenar o ID do produto na CheckoutSession
            from produtos.models import Produto # Importar aqui para evitar circular dependency
            produto = Produto.objects.get(nome=transaction.checkout_session.nome_produto, user_profile=user_profile)
        except Produto.DoesNotExist:
            logger.warning(f"Produto '{transaction.checkout_session.nome_produto}' não encontrado para o user '{user_profile.user.username}'. Usando mensagem padrão.")

    if produto and produto.mensagem_whatsapp_sucesso:
        mensagem_personalizada = produto.mensagem_whatsapp_sucesso
        # Substituir variáveis na mensagem personalizada
        nome_cliente = transaction.checkout_session.nome_cliente if transaction.checkout_session else 'N/A'
        valor_pago = f"{transaction.valor:.2f} MZN"

        mensagem = mensagem_personalizada.format(
            nome_cliente=nome_cliente,
            nome_produto=nome_produto,
            valor_pago=valor_pago
        )
    else:
        mensagem = (
            f"Nova Venda Realizada!\n"
            f"----------------------------------------\n"
            f"Vendedor: {nome_completo_vendedor}\n"
            f"Produto: {nome_produto}\n"
            f"Valor: {transaction.valor:.2f} MZN\n"
            f"ID da Transação: {transaction.transaction_id}\n"
        )

    if transaction.checkout_session and transaction.checkout_session.dados_cliente_custom:
        mensagem += "\n--- Dados do Cliente ---\n"
        for label, valor in transaction.checkout_session.dados_cliente_custom.items():
            mensagem += f"{label}: {valor}\n"
    
    mensagem += "----------------------------------------"
    
    # Obter o número de WhatsApp do vendedor (assumindo que está no sso_id do User)
    numero_vendedor_whatsapp = user.sso_id # Pega o sso_id do User

    if numero_vendedor_whatsapp:
        numero_vendedor_whatsapp_normalizado = normalizar_numero_whatsapp(numero_vendedor_whatsapp)
        logger.debug(f"Tentando enviar mensagem para o vendedor {user.username} no WhatsApp: {numero_vendedor_whatsapp_normalizado}")
        send_whatsapp_message(numero_vendedor_whatsapp_normalizado, mensagem)
        logger.info(f"Mensagem de sucesso de venda enviada para o vendedor {user.username} ({numero_vendedor_whatsapp}).")
    else:
        logger.warning(f"Número de WhatsApp do vendedor {user.username} (sso_id) não encontrado ou inválido para enviar notificação de venda.")

    # --- Mensagem E-mail para o Vendedor ---
    if user.email:
        assunto_email = f"Nova Venda Realizada: {nome_produto} - Paymoz"
        mensagem_email = (
            f"Prezado(a) {nome_completo_vendedor},\n\n"
            f"Parabéns! Uma nova venda foi realizada na Paymoz.\n\n"
            f"Detalhes da Venda:\n"
            f"- Produto: {nome_produto}\n"
            f"- Valor: {transaction.valor:.2f} MZN\n"
            f"- ID da Transação: {transaction.transaction_id}\n\n"
        )
        if transaction.checkout_session and transaction.checkout_session.dados_cliente_custom:
            mensagem_email += "--- Dados do Cliente ---\n"
            for label, valor in transaction.checkout_session.dados_cliente_custom.items():
                mensagem_email += f"{label}: {valor}\n"
            mensagem_email += "\n"

        mensagem_email += (
            f"Agradecemos a sua parceria.\n\n"
            f"Atenciosamente,\n"
            f"A Equipe Paymoz"
        )

        try:
            send_mail(
                assunto_email,
                mensagem_email,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            logger.info(f"E-mail de sucesso de venda enviado para o vendedor {user.email}.")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de sucesso de venda para {user.email}: {e}")
    else:
        logger.error(f"E-mail do vendedor {user.username} (ID: {user.id}) não encontrado. Notificação de venda não pode ser enviada.")

    logger.info(mensagem)


def enviar_notificacao_cliente(transaction):
    """
    Envia uma mensagem de notificação para o cliente sobre a compra bem-sucedida
    via WhatsApp e e-mail.
    """
    # Extrai o número de WhatsApp e e-mail do cliente da sessão de checkout
    numero_cliente_whatsapp = None
    email_cliente = None

    if transaction.checkout_session:
        email_cliente = transaction.checkout_session.email_cliente
        if transaction.checkout_session.dados_cliente_custom:
            for label, valor in transaction.checkout_session.dados_cliente_custom.items():
                if 'whatsapp' in label.lower():
                    numero_cliente_whatsapp = valor
                    break

    # Tenta obter o produto associado à transação
    produto = None
    if transaction.checkout_session and transaction.checkout_session.nome_produto:
        try:
            from produtos.models import Produto
            produto = Produto.objects.get(nome=transaction.checkout_session.nome_produto, user_profile=transaction.user_profile)
        except Produto.DoesNotExist:
            logger.warning(f"Produto '{transaction.checkout_session.nome_produto}' não encontrado. Usando mensagem padrão para o cliente.")

    # Prepara as variáveis para a mensagem
    nome_produto = transaction.checkout_session.nome_produto if transaction.checkout_session else 'Produto Adquirido'
    valor_pago = f"{transaction.valor:.2f} MZN"
    nome_cliente = transaction.checkout_session.nome_cliente if transaction.checkout_session and transaction.checkout_session.nome_cliente else 'Cliente'
    
    # Adiciona a callback_url do produto, se existir
    callback_url_produto = produto.callback_url if produto and produto.callback_url else None

    # --- Mensagem WhatsApp (tom informal) ---
    if numero_cliente_whatsapp:
        if produto and produto.mensagem_whatsapp_sucesso:
            mensagem_whatsapp = produto.mensagem_whatsapp_sucesso.format(
                nome_cliente=nome_cliente,
                nome_produto=nome_produto,
                valor_pago=valor_pago
            )
        else:
            mensagem_whatsapp = (
                f"Olá {nome_cliente}!\n\n"
                f"Obrigado pela sua compra!\n\n"
                f"Detalhes do seu pedido:\n"
                f"- Produto: {nome_produto}\n"
                f"- Valor Pago: {valor_pago}\n\n"
            )
        
        if callback_url_produto:
            mensagem_whatsapp += f"Acesse seu produto ou conteúdo aqui: {callback_url_produto}\n\n"
        else:
            mensagem_whatsapp += f"Em breve você receberá mais informações sobre o seu produto.\n\n"

        mensagem_whatsapp += f"Atenciosamente,\n"
        mensagem_whatsapp += f"{transaction.user_profile.user.get_full_name() or transaction.user_profile.user.username}"

        logger.debug(f"Tentando enviar mensagem para o cliente no WhatsApp: {numero_cliente_whatsapp}")
        send_whatsapp_message(normalizar_numero_whatsapp(numero_cliente_whatsapp), mensagem_whatsapp)
        logger.info(f"Mensagem de confirmação de compra enviada para o cliente no número {numero_cliente_whatsapp}.")
    else:
        logger.warning("Número de WhatsApp do cliente não encontrado para notificação de sucesso.")

    # --- Mensagem E-mail (tom formal) ---
    if email_cliente:
        assunto_email = f"Confirmação de Compra: {nome_produto} - Paymoz"
        mensagem_email = (
            f"Prezado(a) {nome_cliente},\n\n"
            f"Confirmamos o recebimento do seu pagamento e a conclusão da sua compra na Paymoz.\n\n"
            f"Detalhes do Pedido:\n"
            f"- Produto: {nome_produto}\n"
            f"- Valor Pago: {valor_pago} MZN\n"
            f"- ID da Transação: {transaction.transaction_id}\n\n"
        )
        if callback_url_produto:
            mensagem_email += f"Você pode acessar seu produto ou conteúdo através do seguinte link: {callback_url_produto}\n\n"
        else:
            mensagem_email += f"Em breve, você receberá um e-mail separado com as instruções de acesso ao seu produto.\n\n"
        
        mensagem_email += (
            f"Agradecemos a sua preferência.\n\n"
            f"Atenciosamente,\n"
            f"A Equipe Paymoz"
        )

        try:
            send_mail(
                assunto_email,
                mensagem_email,
                settings.DEFAULT_FROM_EMAIL,
                [email_cliente],
                fail_silently=False,
            )
            logger.info(f"E-mail de confirmação de compra enviado para o cliente {email_cliente}.")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de confirmação para {email_cliente}: {e}")
    else:
        logger.warning("E-mail do cliente não encontrado para notificação de sucesso.")



from .models import User, UserProfile, Saque, Package, Transaction, ContactoSuporte, CheckoutSession, ApiSettings, AdminWithdrawalSettings, AdminWithdrawal
from django.db.models import Case, When

def home(request):
    # Define a ordem explícita dos pacotes
    package_order = Case(
        When(package_type='TRIAL', then=1),
        When(package_type='ONE_TIME', then=2),
        When(package_type='ENTERPRISE', then=3),
        default=4
    )

    packages = Package.objects.filter(is_active=True).order_by(package_order)
    current_package = None
    support_contacts = ContactoSuporte.load() # Carrega os contatos

    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            current_package = user_profile.package
            # Se o usuário for PRO, não mostramos o plano TRIAL
            if user_profile.subscription_status == 'PRO':
                packages = packages.exclude(package_type='TRIAL')
        except UserProfile.DoesNotExist:
            pass # Mantém current_package como None

    context = {
        'packages': packages,
        'current_package': current_package,
        'support_contacts': support_contacts, # Adiciona ao contexto
    }
    return render(request, 'paginas/home.html', context)

from django.db.models import Avg, Count
from produtos.models import Produto  # Importar o modelo Produto

@login_required
def dashboard_view(request):
    try:
        api_settings = ApiSettings.load()
        user_profile = UserProfile.objects.get(user=request.user)
        produtos = Produto.objects.filter(user_profile=user_profile).annotate(
            avg_rating=Avg('avaliacoes__rating'),
            count_rating=Count('avaliacoes')
        ) # Buscar produtos do usuário

        logger.debug(f"User Profile Balance from DB: {user_profile.balance}")
        saques = Saque.objects.filter(user_profile=user_profile).order_by('-data_solicitacao')
        transactions = Transaction.objects.filter(user_profile=user_profile)

        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', 'all')

        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', 'all')

        logger.debug(f"Dashboard View - Search Query: '{search_query}', Status Filter: '{status_filter}'")

        if search_query:
            transactions = transactions.filter(
                models.Q(transaction_id__icontains=search_query) |
                models.Q(valor__icontains=search_query) |
                models.Q(status__icontains=search_query) |
                models.Q(user_profile__user__name__icontains=search_query)
            )

        if status_filter != 'all':
            transactions = transactions.filter(status=status_filter)

        transactions = transactions.order_by('-timestamp')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            transactions_data = []
            for t in transactions:
                client_phone = 'N/A'
                if t.checkout_session and t.checkout_session.dados_cliente_custom:
                    for label, valor in t.checkout_session.dados_cliente_custom.items():
                        if 'whatsapp' in label.lower() or 'telefone' in label.lower() or 'celular' in label.lower():
                            client_phone = valor
                            break

                transactions_data.append({
                    'id': str(t.transaction_id),
                    'valor': f'{t.valor:,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."),
                    'status': t.status,
                    'timestamp': t.timestamp.strftime('%H:%M'),
                    'user_name': t.user_profile.user.name if t.user_profile and t.user_profile.user else 'N/A',
                    'client_phone': client_phone,
                })
            logger.debug(f"Returning {len(transactions_data)} transactions for filter '{status_filter}'")
            return JsonResponse({'transactions': transactions_data})

        packages = Package.objects.all()

        # Calculate total sum of all successful transactions for the user
        total_transactions_sum = Transaction.objects.filter(
            user_profile=user_profile,
            status='SUCCESS'
        ).aggregate(models.Sum('valor'))['valor__sum'] or 0

        # Calculate total sum of all failed transactions for the user
        total_failed_transactions_sum = Transaction.objects.filter(
            user_profile=user_profile,
            status='FAILED'
        ).aggregate(models.Sum('valor'))['valor__sum'] or 0

        # Assign this sum to user_profile.balance for display purposes, deducting 10%
        # user_profile.balance = total_transactions_sum * Decimal('0.90') # REMOVIDO: Não sobrescrever o saldo real do user_profile
        formatted_balance = f"{user_profile.balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        logger.debug(f"Formatted Balance sent to template: {formatted_balance}")

        # Format values for display
        formatted_total_success_value = f"{total_transactions_sum:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        formatted_total_failed_value = f"{total_failed_transactions_sum:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        daily_sales = []
        weekly_sales = []
        monthly_sales = []


  

        # Definição dos períodos
        today = timezone.now()
        current_period_start = today - timedelta(days=30)
        previous_period_start = today - timedelta(days=60)
        previous_period_end = current_period_start

        # Transações do período atual
        current_transactions = Transaction.objects.filter(
            user_profile=user_profile, 
            timestamp__gte=current_period_start
        )
        
        # Transações do período anterior
        previous_transactions = Transaction.objects.filter(
            user_profile=user_profile, 
            timestamp__gte=previous_period_start, 
            timestamp__lt=previous_period_end
        )

        # Total de Vendas
        current_sales = current_transactions.filter(status='SUCCESS').aggregate(models.Sum('valor'))['valor__sum'] or 0
        formatted_current_sales = f"{current_sales:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        previous_sales = previous_transactions.filter(status='SUCCESS').aggregate(models.Sum('valor'))['valor__sum'] or 0
        sales_change = ((current_sales - previous_sales) / previous_sales) * 100 if previous_sales > 0 else 0

        # Novos Clientes (a nível de sistema)
        current_new_customers = User.objects.filter(date_joined__gte=current_period_start).count()
        previous_new_customers = User.objects.filter(date_joined__gte=previous_period_start, date_joined__lt=previous_period_end).count()
        customers_change = ((current_new_customers - previous_new_customers) / previous_new_customers) * 100 if previous_new_customers > 0 else 0

        # Taxa de Conversão
        current_total_trans = current_transactions.count()
        current_success_trans = current_transactions.filter(status='SUCCESS').count()
        current_conversion_rate = (current_success_trans / current_total_trans) * 100 if current_total_trans > 0 else 0
        formatted_conversion_rate = f"{current_conversion_rate:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        previous_total_trans = previous_transactions.count()
        previous_success_trans = previous_transactions.filter(status='SUCCESS').count()
        previous_conversion_rate = (previous_success_trans / previous_total_trans) * 100 if previous_total_trans > 0 else 0
        
        conversion_rate_change = current_conversion_rate - previous_conversion_rate

        # Receita Média
        avg_revenue = current_sales / current_success_trans if current_success_trans > 0 else 0
        formatted_avg_revenue = f"{avg_revenue:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        formatted_avg_revenue = f"{avg_revenue:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        previous_avg_revenue = previous_sales / previous_success_trans if previous_success_trans > 0 else 0
        avg_revenue_change = ((avg_revenue - previous_avg_revenue) / previous_avg_revenue) * 100 if previous_avg_revenue > 0 else 0

        # Dados para os gráficos
        daily_sales_raw = Transaction.objects.filter(user_profile=user_profile, status='SUCCESS', timestamp__gte=today - timedelta(days=7)).annotate(period=TruncDay('timestamp'), total=models.Sum('valor')).values('period', 'total').order_by('period').filter(total__gt=0)
        daily_sales = [{'day': item['period'].strftime('%Y-%m-%d'), 'total': float(item['total'])} for item in daily_sales_raw]

        weekly_sales_raw = Transaction.objects.filter(user_profile=user_profile, status='SUCCESS', timestamp__gte=today - timedelta(weeks=4)).annotate(period=TruncWeek('timestamp'), total=models.Sum('valor')).values('period', 'total').order_by('period').filter(total__gt=0)
        weekly_sales = [{'week': item['period'].strftime('%Y-%m-%d'), 'total': float(item['total'])} for item in weekly_sales_raw]

        monthly_sales_raw = Transaction.objects.filter(user_profile=user_profile, status='SUCCESS', timestamp__gte=today - timedelta(days=365)).annotate(period=TruncMonth('timestamp'), total=models.Sum('valor')).values('period', 'total').order_by('period').filter(total__gt=0)
        monthly_sales = [{'month': item['period'].strftime('%Y-%m-%d'), 'total': float(item['total'])} for item in monthly_sales_raw]

        # Determine the effective withdrawal fee percentage
        if user_profile.custom_withdrawal_fee_percentage is not None:
            effective_withdrawal_fee_percentage = user_profile.custom_withdrawal_fee_percentage
        elif user_profile.package:
            effective_withdrawal_fee_percentage = user_profile.package.withdrawal_fee_percentage
        else:
            effective_withdrawal_fee_percentage = Decimal('0.00') # Default if no custom fee and no package

        context = {
            'user_profile': user_profile,
            'saques': saques,
            'packages': packages,
            'formatted_balance': formatted_balance,
            'formatted_current_sales': formatted_current_sales,
            'total_vendas': formatted_current_sales,
            'sales_change': sales_change,
            'novos_clientes': current_new_customers,
            'customers_change': customers_change,
            'taxa_conversao': formatted_conversion_rate,
            'conversion_rate_change': conversion_rate_change,
            'receita_media': formatted_avg_revenue,
            'avg_revenue_change': avg_revenue_change,
            'daily_sales': daily_sales,
            'weekly_sales': weekly_sales,
            'monthly_sales': monthly_sales,
            'transactions': transactions,
            'formatted_total_success_value': formatted_total_success_value,
            'formatted_total_failed_value': formatted_total_failed_value,
            'withdrawal_fee_percentage': effective_withdrawal_fee_percentage, # Add to context
            'api_base_url': api_settings.base_url,
            'produtos': produtos, # Adicionar produtos ao contexto
        }
        return render(request, 'paginas/dashboard.html', context)
    except UserProfile.DoesNotExist:
        return redirect('home')


def login_sso(request):
    """
    Redireciona o usuário para a página de autorização do SSO.
    """
    next_url = request.GET.get('next')
    if next_url:
        request.session['next_url'] = next_url

    authorize_url = "https://autenticacao.neuratechmz.tech/oauth/authorize/"

    # Gera o code_verifier e o code_challenge para o fluxo PKCE
    code_verifier = secrets.token_urlsafe(64)
    request.session['code_verifier'] = code_verifier
    hashed = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(hashed).decode('utf-8').replace('=', '')

    params = {
        'response_type': 'code',
        'client_id': settings.CLIENT_ID,
        'redirect_uri': settings.SSO_REDIRECT_URI,
        'scope': 'oidc read write',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    redirect_to_sso = f"{authorize_url}?{urlencode(params)}"
    return redirect(redirect_to_sso)

def sso_callback(request):
    """
    Callback do SSO após a autorização do usuário.
    Troca o código de autorização por um token de acesso e obtém os dados do usuário.
    """
    code = request.GET.get('code')
    code_verifier = request.session.pop('code_verifier', None)

    if not code or not code_verifier:
        # Por enquanto, redireciona para a home em caso de erro.
        # Idealmente, teríamos uma página de erro.
        logger.warning("SSO callback sem 'code' ou 'code_verifier'.")
        return redirect('home')

    token_url = "https://autenticacao.neuratechmz.tech/oauth/token/"
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': settings.CLIENT_ID,
        'client_secret': settings.CLIENT_SECRET,
        'redirect_uri': settings.SSO_REDIRECT_URI,
        'code_verifier': code_verifier,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        response = requests.post(token_url, data=data, headers=headers)
        response.raise_for_status()
        tokens = response.json()

        access_token = tokens.get('access_token')
        id_token = tokens.get('id_token')

        if id_token:
            request.session['id_token'] = id_token

        if not access_token:
            logger.error("Access token não recebido do SSO.")
            return redirect('home')

        user_info_url = settings.SSO_USERINFO_URL
        user_headers = {'Authorization': f'Bearer {access_token}'}
        user_response = requests.get(user_info_url, headers=user_headers)
        user_response.raise_for_status()
        user_data = user_response.json()

        sso_id = user_data.get('id') or user_data.get('whatsapp_number')

        if sso_id:
            user, created = User.objects.get_or_create(
                sso_id=sso_id,
                defaults={
                    'username': user_data.get('username', sso_id),
                    'email': user_data.get('email', ''),
                    'name': user_data.get('name', ''),
                    'surname': user_data.get('surname', ''),
                }
            )
            if not created:
                user.username = user_data.get('username', sso_id)
                user.email = user_data.get('email', '')
                user.name = user_data.get('name', '')
                user.surname = user_data.get('surname', '')
                user.save()
            
            # Garante que o UserProfile existe para o usuário
            user_profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'api_key': secrets.token_urlsafe(32)}
            )
            if profile_created:
                user_profile.trial_start_date = date.today()
                user_profile.save()
                logger.info(f"UserProfile criado para o usuário: {user.username} com data de início do trial.")

            login(request, user)
            logger.info(f"Login bem-sucedido para o usuário com sso_id: {sso_id}")
            
            next_url = request.session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            
            return redirect('home')
        else:
            logger.error("ID do usuário (sso_id) não encontrado na resposta do SSO.")
            return redirect('home')

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na comunicação com o SSO: {e}")
        return redirect('home')
    except json.JSONDecodeError:
        logger.error("Resposta inválida (não-JSON) recebida do SSO.")
        return redirect('home')

@require_POST
def sso_logout(request):
    """
    Inicia o fluxo de logout, redirecionando para a URL de logout silencioso.
    """
    return redirect('sso_silent_logout_redirect')

def sso_silent_logout_redirect(request):
    """
    Redireciona para o endpoint de logout do SSO, invalidando a sessão lá.
    """
    id_token = request.session.pop('id_token', None)
    params = {
        "post_logout_redirect_uri": settings.SSO_POST_LOGOUT_REDIRECT_URI,
        "client_id": settings.CLIENT_ID,
    }
    if id_token:
        params["id_token_hint"] = id_token

    sso_logout_url = f"{settings.SSO_END_SESSION_ENDPOINT}?{urlencode(params)}"
    logger.debug(f"Redirecionando para a URL de logout do SSO: {sso_logout_url}")
    return redirect(sso_logout_url)

def logout_success_view(request):
    """
    View para a qual o SSO redireciona após o logout.
    Limpa a sessão local do Django.
    """
    logout(request)
    logger.info("Sessão local do usuário encerrada com sucesso.")
    return redirect('home')

@login_required
@require_POST
@csrf_exempt
def send_verification_email(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        data = json.loads(request.body)
        email = data.get('email')

        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email não fornecido.'}, status=400)

        # Gerar código de 6 dígitos
        code = ''.join(secrets.choice('0123456789') for i in range(6))
        expires_at = timezone.now() + timedelta(minutes=10) # Código expira em 10 minutos

        user_profile.verification_code = code
        user_profile.verification_code_expires_at = expires_at
        user_profile.save()

        subject = 'Seu Código de Verificação Paymoz'
        message = f'Olá {request.user.username},\n\nSeu código de verificação Paymoz é: {code}\n\nEste código expira em 10 minutos.\n\nAtenciosamente,\nA Equipe Paymoz'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]

        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

        return JsonResponse({'status': 'success', 'message': 'Código de verificação enviado para o seu email.'})
    except Exception as e:
        logger.error(f"Erro ao enviar email de verificação: {e}")
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro ao enviar o email: {str(e)}'}, status=500)

@login_required
@require_POST
@csrf_exempt
def verify_email_code(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        data = json.loads(request.body)
        code = data.get('code')
        new_email = data.get('email')

        if not code or not new_email:
            return JsonResponse({'status': 'error', 'message': 'Código e email são obrigatórios.'}, status=400)

        if user_profile.verification_code == code and \
           user_profile.verification_code_expires_at and \
           timezone.now() < user_profile.verification_code_expires_at:
            
            # Atualiza o email do usuário principal
            user = request.user
            user.email = new_email
            user.save()

            user_profile.email_verified = True
            user_profile.verification_code = None
            user_profile.verification_code_expires_at = None
            user_profile.save()

            return JsonResponse({'status': 'success', 'message': 'Email verificado e atualizado com sucesso!'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Código de verificação inválido ou expirado.'}, status=400)
    except Exception as e:
        logger.error(f"Erro ao verificar código de email: {e}")
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro ao verificar o código: {str(e)}'}, status=500)


    try:
        response = requests.post(
            nodejs_api_url,
            json={
                'number': number,
                'message': message
            },
            timeout=30
        )
        response.raise_for_status()  # Levanta HTTPError para respostas de erro (4xx ou 5xx)
        logger.info(f"Mensagem WhatsApp enviada com sucesso para {number}")
        return response.json() # Retorna a resposta JSON em caso de sucesso
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 503:
            logger.error(f"Erro 503 (Service Unavailable) ao enviar mensagem WhatsApp para {number}. O serviço externo pode estar temporariamente indisponível. Detalhes: {e.response.text}")
        else:
            logger.error(f"Erro HTTP ({e.response.status_code}) ao enviar mensagem WhatsApp para {number}: {e.response.text}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erro de conexão ao enviar mensagem WhatsApp para {number}: {e}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout ao enviar mensagem WhatsApp para {number}: {e}")
        return None
    except requests.exceptions.RequestException as e: # Captura quaisquer outros erros relacionados a requests
        logger.error(f"Erro desconhecido ao enviar mensagem WhatsApp para {number}: {e}")
        return None

@csrf_exempt
@require_POST
@transaction.atomic # Adicionado para atomicidade
def pagamento_mpesa_api(request):
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return JsonResponse({'status': 'error', 'message': 'API key não fornecida.'}, status=401)

        try:
            user_profile = UserProfile.objects.select_for_update().get(api_key=api_key) # Adicionado select_for_update

        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'API key inválida.'}, status=401)

        if user_profile.subscription_status == 'TRIAL_EXPIRED':
            return JsonResponse({'status': 'error', 'message': 'O seu período de teste eirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        if user_profile.subscription_status == 'TRIAL':
            if user_profile.trial_start_date and (date.today() - user_profile.trial_start_date).days > 7:
                user_profile.subscription_status = 'TRIAL_EXPIRED'
                user_profile.save()
                return JsonResponse({'status': 'error', 'message': 'O seu período de teste expirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        data = json.loads(request.body)
        numero_celular = data.get('numero_celular')
        valor = Decimal(str(data.get('valor')))

        if not numero_celular or not valor:
            return JsonResponse({'status': 'error', 'message': 'Número de celular e valor são obrigatórios.'}, status=400)

        # Lógica de pagamento M-Pesa (simulada ou real)
        # Supondo que a resposta da API M-Pesa seja um JSON válido
        

        # Configurar o APIContext com as credenciais e detalhes da API M-Pesa
        api_context = APIContext()
        # TODO: Estas chaves devem ser configuráveis (e.g., via settings.py ou ApiSettings model)
        
        api_context.api_key = 'ny2nnixoe5di7ieddm3ixjzex3cjctrz'
        api_context.public_key = 'MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAyrOP7fgXIJgJyp6nP/Vtlu8kW94Qu+gJjfMaTNOSd/mQJChqXiMWsZPH8uOoZGeR/9m7Y8vAU83D96usXUaKoDYiVmxoMBkfmw8DJAtHHt/8LWDdoAS/kpXyZJ5dt19Pv+rTApcjg7AoGczT+yIU7xp4Ku23EqQz70V5Rud+Qgerf6So28Pt3qZ9hxgUA6lgF7OjoYOIAKPqg07pHp2eOp4P6oQW8oXsS+cQkaPVo3nM1f+fctFGQtgLJ0y5VG61ZiWWWFMOjYFkBSbNOyJpQVcMKPcfdDRKq+9r5DFLtFGztPYIAovBm3a1Q6XYDkGYZWtnD8mDJxgEiHWCzog0wZqJtfNREnLf1g2ZOanTDcrEFzsnP2MQwIatV8M6q/fYrh5WejlNm4ujnKUVbnPMYH0wcbXQifSDhg2jcnRLHh9CF9iabkxAzjbYkaG1qa4zG+bCidLCRe0cEQvt0+/lQ40yESvpWF60omTy1dLSd10gl2//0v4IMjLMn9tgxhPp9c+C2Aw7x2Yjx3GquSYhU6IL41lrURwDuCQpg3F30QwIHgy1D8xIfQzno3XywiiUvoq4YfCkN9WiyKz0btD6ZX02RRK6DrXTFefeKjWf0RHREHlfwkhesZ4X168Lxe9iCWjP2d0xUB+lr10835ZUpYYIr4Gon9NTjkoOGwFyS5ECAwEAAQ=='
        api_context.ssl = True
        api_context.method_type = APIMethodType.POST
        api_context.address = 'api.vm.co.mz'
        api_context.port = 18352
        api_context.path = '/ipg/v1x/c2bPayment/singleStage/'
            
        api_context.add_header('Origin', '*')

            # Mapear os parâmetros da requisição para o portalsdk
        api_context.add_parameter('input_TransactionReference', referencia_transacao()) # Usar a função existente
        api_context.add_parameter('input_CustomerMSISDN', numero_celular)
        api_context.add_parameter('input_Amount', str(int(valor))) # O SDK espera string de inteiro
        api_context.add_parameter('input_ThirdPartyReference', referencia_transacao()) # Pode ser configurável
        api_context.add_parameter('input_ServiceProviderCode', '900571') # Pode ser configurável

        api_request = APIRequest(api_context)
        
        try:
            result = api_request.execute()
            
            # Processar o resultado do portalsdk
            if (result.status_code == 200 or result.status_code == 201) and result.body and result.body.get('output_ResponseCode') == 'INS-0':
                resposta_json = result.body
                # Update transaction status to SUCCESS
                nova_transacao.status = 'SUCCESS'
                nova_transacao.external_transaction_id = resposta_json.get('output_TransactionID')
                nova_transacao.save()
            else:
                # Se a resposta não for 200 ou o código de resposta não for INS-0
                error_message = result.body.get('output_ResponseDesc', 'Erro desconhecido na API M-Pesa') if result.body else 'Resposta vazia da API M-Pesa'
                logger.error(f"Erro na API M-Pesa: {result.status_code} - {error_message}")
                resposta_json = {'output_ResponseCode': 'ERR', 'output_ResponseDesc': error_message}
                # Update transaction status to FAILED
                nova_transacao.status = 'FAILED'
                nova_transacao.external_transaction_id = resposta_json.get('output_TransactionID') # Still save if available
                nova_transacao.save()
        except Exception as e:
            logger.error(f"Erro ao executar portalsdk: {e}")
            resposta_json = {'output_ResponseCode': 'ERR', 'output_ResponseDesc': f'Erro ao processar pagamento: {e}'}
            # Update transaction status to FAILED on exception
            nova_transacao.status = 'FAILED'
            nova_transacao.save()

        # Se a transação M-Pesa for bem-sucedida, adicionar o valor e deduzir a taxa
        if nova_transacao.status == 'SUCCESS': # Check the transaction status from the DB
            # Determine the effective transaction fee percentage
            if user_profile.custom_transaction_fee_percentage is not None:
                effective_transaction_fee_percentage = user_profile.custom_transaction_fee_percentage
            elif user_profile.package:
                effective_transaction_fee_percentage = user_profile.package.transaction_fee_percentage
            else:
                effective_transaction_fee_percentage = Decimal('10.00') # Default to 10% if no custom fee and no package

            taxa = valor * (effective_transaction_fee_percentage / 100)
            user_profile.balance += valor  # Adiciona o valor total da transação
            user_profile.balance -= taxa  # Deduz a taxa
            user_profile.save()
            resposta_json['taxa_deduzida'] = taxa
            resposta_json['novo_saldo'] = user_profile.balance

            Transaction.objects.create(
                user_profile=user_profile,
                valor=valor,
                status='SUCCESS'
            )
        else:
            Transaction.objects.create(
                user_profile=user_profile,
                valor=valor,
                status='FAILED'
            )

        return JsonResponse(resposta_json)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Requisição JSON inválida.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)

'''@csrf_exempt
@require_POST
def pagamento_emola_api(request):
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return JsonResponse({'status': 'error', 'message': 'API key não fornecida.'}, status=401)

        try:
            user_profile = UserProfile.objects.get(api_key=api_key)
        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'API key inválida.'}, status=401)

        if user_profile.subscription_status == 'TRIAL_EXPIRED':
            return JsonResponse({'status': 'error', 'message': 'O seu período de teste expirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        if user_profile.subscription_status == 'TRIAL':
            if user_profile.trial_start_date and (date.today() - user_profile.trial_start_date).days > 7:
                user_profile.subscription_status = 'TRIAL_EXPIRED'
                user_profile.save()
                return JsonResponse({'status': 'error', 'message': 'O seu período de teste expirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        data = json.loads(request.body)
        numero_celular = data.get('numero_celular')
        valor = Decimal(str(data.get('valor')))

        if not numero_celular or not valor:
            return JsonResponse({'status': 'error', 'message': 'Número de celular e valor são obrigatórios.'}, status=400)

        # Lógica de pagamento fictícia para Emola
        # Simular uma resposta de sucesso para Emola
        resposta_json = {
            'status': 'success',
            'message': f'Pagamento Emola (fictício) de {valor} para {numero_celular} processado com sucesso para o usuário {user_profile.user.username}.'
        }

        # Deduzir a taxa de 10% do saldo do usuário
        # Determine the effective transaction fee percentage
        if user_profile.custom_transaction_fee_percentage is not None:
            effective_transaction_fee_percentage = user_profile.custom_transaction_fee_percentage
        elif user_profile.package:
            effective_transaction_fee_percentage = user_profile.package.transaction_fee_percentage
        else:
            effective_transaction_fee_percentage = Decimal('0.00') # Default if no custom fee and no package

        taxa = valor * (effective_transaction_fee_percentage / 100)
        user_profile.balance += valor  # Adiciona o valor total da transação
        user_profile.balance -= taxa  # Deduz a taxa
        user_profile.save()
        resposta_json['taxa_deduzida'] = taxa
        resposta_json['novo_saldo'] = user_profile.balance

        Transaction.objects.create(
            user_profile=user_profile,
            valor=valor,
            status='SUCCESS'
        )

        return JsonResponse(resposta_json)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Requisição JSON inválida.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)
'''
@csrf_exempt
@require_POST
def upgrade_to_pro(request):
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return JsonResponse({'status': 'error', 'message': 'API key não fornecida.'}, status=401)

        try:
            user_profile = UserProfile.objects.get(api_key=api_key)
        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'API key inválida.'}, status=401)

        user_profile.subscription_status = 'PRO'
        user_profile.save()

        return JsonResponse({'status': 'success', 'message': 'Upgrade para o plano Pro realizado com sucesso!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def solicitar_saque_api(request):
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return JsonResponse({'status': 'error', 'message': 'API key não fornecida.'}, status=401)

        try:
            user_profile = UserProfile.objects.get(api_key=api_key)
        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'API key inválida.'}, status=401)

        # Validação do Status da Assinatura
        if user_profile.subscription_status == 'TRIAL_EXPIRED':
            return JsonResponse({'status': 'error', 'message': 'O seu período de teste expirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        if user_profile.subscription_status == 'TRIAL':
            if user_profile.trial_start_date and (date.today() - user_profile.trial_start_date).days > 7:
                user_profile.subscription_status = 'TRIAL_EXPIRED'
                user_profile.save()
                return JsonResponse({'status': 'error', 'message': 'O seu período de teste expirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        data = json.loads(request.body)
        valor_saque_str = data.get('valor') # Obter como string primeiro

        try:
            valor_saque = Decimal(str(valor_saque_str)) # Converter para Decimal
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Valor de saque inválido. Deve ser um número.'}, status=400)

        if valor_saque <= 0 or valor_saque < 100:
            return JsonResponse({'status': 'error', 'message': 'Valor de saque inválido. Deve ser maior que zero e no mínimo 100 MZN.'}, status=400)

        if user_profile.balance < valor_saque:
            return JsonResponse({'status': 'error', 'message': 'Saldo insuficiente para o saque.'}, status=400)

        # Determine the effective withdrawal fee percentage
        if user_profile.custom_withdrawal_fee_percentage is not None:
            effective_withdrawal_fee_percentage = user_profile.custom_withdrawal_fee_percentage
        elif user_profile.package:
            effective_withdrawal_fee_percentage = user_profile.package.withdrawal_fee_percentage
        else:
            effective_withdrawal_fee_percentage = Decimal('0.00') # Default if no custom fee and no package

        taxa_saque = valor_saque * (effective_withdrawal_fee_percentage / 100)
        valor_liquido = valor_saque - taxa_saque # Calcular o valor líquido

        # Deduzir o valor do saldo imediatamente (valor do saque + taxa)
        user_profile.balance -= (valor_saque + taxa_saque)
        user_profile.save()

        # Criar o registro de saque pendente
        saque = Saque.objects.create(
            user_profile=user_profile,
            valor=valor_saque,
            valor_liquido=valor_liquido, # Salvar o valor líquido
            numero_celular=data.get('numero_celular'), # Salvar o número de celular
            status='PENDENTE'
        )

        # Chamar a função de notificação após o saque ser criado com sucesso
        # O numero_celular é o que o usuário digitou no formulário, que vem do `data`
        enviar_notificacao(user_profile, valor_saque, data.get('numero_celular'))

        return JsonResponse({
            'status': 'success',
            'message': 'Solicitação de saque recebida e pendente de aprovação.',
            'saque': { # Adicionando os detalhes do saque
                'valor': str(saque.valor), # Converter para string para JSON
                'valor_liquido': str(saque.valor_liquido), # Retornar o valor líquido
                'taxa_saque': str(taxa_saque), # Retornar a taxa de saque
                'status': saque.status,
                'data_solicitacao': saque.data_solicitacao.strftime('%d/%m/%Y, %H:%M'), # Formatar data
                'id_transacao': str(saque.id_transacao),
                'user_profile_username': saque.user_profile.user.username, # Adicionar username
            },
            'novo_saldo': str(user_profile.balance) # Converter para string para JSON
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Requisição JSON inválida.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

@login_required
def checkout_pro_view(request):
    try:
        package = Package.objects.get(package_type='ONE_TIME')
        user_profile = UserProfile.objects.get(user=request.user)

        if request.method == 'POST':
            numero_celular = request.POST.get('numero_celular')
            valor = package.price

            if not numero_celular:
                messages.error(request, 'O número de celular é obrigatório.')
                return redirect('checkout_pro')

            # --- Logica de Pagamento M-Pesa com portalsdk ---
            api_context = APIContext()
            # TODO: Estas chaves devem ser configuraveis (e.g., via settings.py ou ApiSettings model)

            api_context.api_key = 'ny2nnixoe5di7ieddm3ixjzex3cjctrz'
            api_context.public_key = 'MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAyrOP7fgXIJgJyp6nP/Vtlu8kW94Qu+gJjfMaTNOSd/mQJChqXiMWsZPH8uOoZGeR/9m7Y8vAU83D96usXUaKoDYiVmxoMBkfmw8DJAtHHt/8LWDdoAS/kpXyZJ5dt19Pv+rTApcjg7AoGczT+yIU7xp4Ku23EqQz70V5Rud+Qgerf6So28Pt3qZ9hxgUA6lgF7OjoYOIAKPqg07pHp2eOp4P6oQW8oXsS+cQkaPVo3nM1f+fctFGQtgLJ0y5VG61ZiWWWFMOjYFkBSbNOyJpQVcMKPcfdDRKq+9r5DFLtFGztPYIAovBm3a1Q6XYDkGYZWtnD8mDJxgEiHWCzog0wZqJtfNREnLf1g2ZOanTDcrEFzsnP2MQwIatV8M6q/fYrh5WejlNm4ujnKUVbnPMYH0wcbXQifSDhg2jcnRLHh9CF9iabkxAzjbYkaG1qa4zG+bCidLCRe0cEQvt0+/lQ40yESvpWF60omTy1dLSd10gl2//0v4IMjLMn9tgxhPp9c+C2Aw7x2Yjx3GquSYhU6IL41lrURwDuCQpg3F30QwIHgy1D8xIfQzno3XywiiUvoq4YfCkN9WiyKz0btD6ZX02RRK6DrXTFefeKjWf0RHREHlfwkhesZ4X168Lxe9iCWjP2d0xUB+lr10835ZUpYYIr4Gon9NTjkoOGwFyS5ECAwEAAQ=='
            api_context.ssl = True
            api_context.method_type = APIMethodType.POST
            api_context.address = 'api.vm.co.mz'
            api_context.port = 18352
            api_context.path = '/ipg/v1x/c2bPayment/singleStage/'
            
            api_context.add_header('Origin', '*')

            # Mapear os parâmetros da requisição para o portalsdk
            api_context.add_parameter('input_TransactionReference', referencia_transacao()) # Usar a função existente
            api_context.add_parameter('input_CustomerMSISDN', numero_celular)
            api_context.add_parameter('input_Amount', str(int(valor))) # O SDK espera string de inteiro
            api_context.add_parameter('input_ThirdPartyReference', referencia_transacao()) # Pode ser configurável
            api_context.add_parameter('input_ServiceProviderCode', '900571') # Pode ser configurável

            api_request = APIRequest(api_context)

            try:
                result = api_request.execute()
                
                if (result.status_code == 200 or result.status_code == 201) and result.body and result.body.get('output_ResponseCode') == 'INS-0':
                    # Pagamento bem-sucedido
                    user_profile.subscription_status = 'PRO'
                    user_profile.package = package
                    user_profile.save()
                    
                    messages.success(request, 'Pagamento bem-sucedido! Seu plano foi atualizado para Pro.')
                    return redirect('dashboard')
                else:
                    # Pagamento falhou
                    error_message = result.body.get('output_ResponseDesc', 'Ocorreu um erro desconhecido durante o pagamento.') if result.body else 'Resposta vazia da API M-Pesa'
                    messages.error(request, f'O pagamento falhou: {error_message}')

            except Exception as e:
                messages.error(request, f'Erro ao processar pagamento: {e}')
            
            return redirect('checkout_pro')

        context = {
            'package': package
        }
        return render(request, 'paginas/checkout.html', context)
    except Package.DoesNotExist:
        messages.error(request, 'O pacote Pro não foi encontrado.')
        return redirect('home')
    except UserProfile.DoesNotExist:
        # Se o perfil não existir, algo está errado. Redirecionar para home.
        return redirect('home')

def documentacao_view(request):
    api_settings = ApiSettings.load()
    context = {
        'api_base_url': api_settings.base_url
    }
    return render(request, 'paginas/documentacao.html', context)

@login_required
@require_POST
def cancelar_saque(request, saque_id):
    try:
        saque = Saque.objects.get(id_transacao=saque_id, user_profile__user=request.user)

        if saque.status == 'PENDENTE':
            with transaction.atomic():
                saque.status = 'CANCELADO'
                saque.save()

                # Reembolsa o valor total (saque + taxa) para o saldo do usuário
                user_profile = saque.user_profile
                # Determine the effective withdrawal fee percentage
                if user_profile.custom_withdrawal_fee_percentage is not None:
                    effective_withdrawal_fee_percentage = user_profile.custom_withdrawal_fee_percentage
                elif user_profile.package:
                    effective_withdrawal_fee_percentage = user_profile.package.withdrawal_fee_percentage
                else:
                    effective_withdrawal_fee_percentage = Decimal('0.00') # Default if no custom fee and no package

                taxa_saque = saque.valor * (effective_withdrawal_fee_percentage / 100)
                valor_reembolso = saque.valor + taxa_saque
                user_profile.balance += valor_reembolso
                user_profile.save()

                messages.success(request, f'O saque de {saque.valor} MZN foi cancelado com sucesso.')
        else:
            messages.error(request, 'Este saque não pode ser cancelado.')

    except Saque.DoesNotExist:
        messages.error(request, 'Saque não encontrado.')
    
    return redirect('dashboard')


@csrf_exempt
@require_POST
@transaction.atomic
def process_payment(request, method):
    """
    API genérica para processar pagamentos (M-Pesa real,  simulado),
    autenticando via API Key, aplicando taxas dinâmicas e atualizando o saldo.
    """
    try:
        # 1. Autenticação e validações iniciais (comum a todos os métodos)
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return JsonResponse({'status': 'error', 'message': 'API key não fornecida.'}, status=401)

        try:
            user_profile = UserProfile.objects.select_for_update().get(api_key=api_key)
        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'API key inválida.'}, status=401)

        # Validação do Status da Assinatura
        if user_profile.subscription_status == 'TRIAL_EXPIRED':
            return JsonResponse({'status': 'error', 'message': 'O seu período de teste expirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        if user_profile.subscription_status == 'TRIAL':
            if user_profile.trial_start_date and (date.today() - user_profile.trial_start_date).days > 7:
                user_profile.subscription_status = 'TRIAL_EXPIRED'
                user_profile.save()
                return JsonResponse({'status': 'error', 'message': 'O seu período de teste expirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        data = json.loads(request.body)
        numero_celular = data.get('numero_celular')
        valor_str = data.get('valor')

        # Normalizar o numero de celular dependendo do metodo
        if method == 'emola':
            numero_celular = normalizar_numero_emola(numero_celular)
        else: # Assume mpesa ou outros metodos futuros que usem o formato com 258
            numero_celular = numero_normal(numero_celular)

        if not numero_celular or not valor_str:
            return JsonResponse({'status': 'error', 'message': 'Número de celular e valor são obrigatórios.'}, status=400)

        try:
            valor = Decimal(str(valor_str))
            if valor <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Valor inválido.'}, status=400)

        resposta_json = None

        # 2. Lógica de pagamento específica para cada método
        if method == 'mpesa':
            # Create transaction object early to get a stable ID for M-Pesa reference
            # Set status to PENDING initially
            nova_transacao = Transaction.objects.create(
                user_profile=user_profile,
                valor=valor,
                status='PENDING',
                payment_phone_number=numero_celular # Save the payment phone number
            )
            # Configurar o APIContext com as credenciais e detalhes da API M-Pesa
            api_context = APIContext()
            # TODO: Estas chaves devem ser configuraveis (e.g., via settings.py ou ApiSettings model)
            
            api_context.api_key = 'ny2nnixoe5di7ieddm3ixjzex3cjctrz'
            api_context.public_key = 'MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAyrOP7fgXIJgJyp6nP/Vtlu8kW94Qu+gJjfMaTNOSd/mQJChqXiMWsZPH8uOoZGeR/9m7Y8vAU83D96usXUaKoDYiVmxoMBkfmw8DJAtHHt/8LWDdoAS/kpXyZJ5dt19Pv+rTApcjg7AoGczT+yIU7xp4Ku23EqQz70V5Rud+Qgerf6So28Pt3qZ9hxgUA6lgF7OjoYOIAKPqg07pHp2eOp4P6oQW8oXsS+cQkaPVo3nM1f+fctFGQtgLJ0y5VG61ZiWWWFMOjYFkBSbNOyJpQVcMKPcfdDRKq+9r5DFLtFGztPYIAovBm3a1Q6XYDkGYZWtnD8mDJxgEiHWCzog0wZqJtfNREnLf1g2ZOanTDcrEFzsnP2MQwIatV8M6q/fYrh5WejlNm4ujnKUVbnPMYH0wcbXQifSDhg2jcnRLHh9CF9iabkxAzjbYkaG1qa4zG+bCidLCRe0cEQvt0+/lQ40yESvpWF60omTy1dLSd10gl2//0v4IMjLMn9tgxhPp9c+C2Aw7x2Yjx3GquSYhU6IL41lrURwDuCQpg3F30QwIHgy1D8xIfQzno3XywiiUvoq4YfCkN9WiyKz0btD6ZX02RRK6DrXTFefeKjWf0RHREHlfwkhesZ4X168Lxe9iCWjP2d0xUB+lr10835ZUpYYIr4Gon9NTjkoOGwFyS5ECAwEAAQ=='
            api_context.ssl = True
            api_context.method_type = APIMethodType.POST
            api_context.address = 'api.vm.co.mz'
            api_context.port = 18352
            api_context.path = '/ipg/v1x/c2bPayment/singleStage/'
            
            api_context.add_header('Origin', '*')

            # Mapear os parâmetros da requisição para o portalsdk
            api_context.add_parameter('input_TransactionReference', referencia_transacao()) # Usar a função existente
            api_context.add_parameter('input_CustomerMSISDN', numero_celular)
            api_context.add_parameter('input_Amount', str(int(valor))) # O SDK espera string de inteiro
            api_context.add_parameter('input_ThirdPartyReference', referencia_transacao()) # Pode ser configurável
            api_context.add_parameter('input_ServiceProviderCode', '900571') # Pode ser configurável

            api_request = APIRequest(api_context)
            
            try:
                result = api_request.execute()
                
                # Processar o resultado do portalsdk
                if (result.status_code == 200 or result.status_code == 201) and result.body and result.body.get('output_ResponseCode') == 'INS-0':
                    resposta_json = result.body
                else:
                    if result.body:
                        logger.error(f"Corpo completo da resposta de erro da M-Pesa: {json.dumps(result.body)}")
                    error_message = result.body.get('output_ResponseDesc') or result.body.get('output_error', 'Erro desconhecido na API M-Pesa') if result.body else 'Resposta vazia da API M-Pesa'
                    logger.error(f"Erro na API M-Pesa: {result.status_code} - {error_message}")
                    resposta_json = {'output_ResponseCode': 'ERR', 'output_ResponseDesc': error_message}
            except Exception as e:
                logger.error(f"Erro ao executar portalsdk: {e}")
                return JsonResponse({'status': 'error', 'message': f'Erro ao processar pagamento: {e}'}, status=500)

        elif method == 'emola':
            # TODO: Mover credenciais para settings.py ou um modelo de configuracao
            EMOLA_API_URL = 'https://e2payments.explicador.co.mz/v1/c2b/emola-payment/996798'
            EMOLA_CLIENT_ID = '9cd9ab3a-ba3b-4f8e-959c-2092afd76f31'
            EMOLA_BEARER_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5Y2Q5YWIzYS1iYTNiLTRmOGUtOTU5Yy0yMDkyYWZkNzZmMzEiLCJqdGkiOiJiYTM2OWRhZTI3YmZjZjgxZDg2MmZkY2M4MGQ4YmYwNjJlMWYzMjU0YWM5ZWQ3YmU3YzJhNWNiZmJlMWZhNGRkZDY2YjFmODdhYzE3MTYyZCIsImlhdCI6MTc1ODE3NDM5NS44MTU2NDcsIm5iZiI6MTc1ODE3NDM5NS44MTU2NTIsImV4cCI6MTc4OTcxMDM5NS44MTExNzUsInN1YiI6IiIsInNjb3BlcyI6W119.ZOTE7jJgohrFVQUlUxGA48qjeTo_JGI1M32UdwQ2rPxAl7KFo0boqlLvBqDcY0zUG1vXLR8kOv-oOG5s_ivnKM0Gop0hcBiJmAlOurZtnDWXlT3Oy02dzqvtlLaOIdYEsvqZMDYu0uGUhtVrWgHtmDJbc7U0X1526ixe31iV28PkpNAh1iuQ2Petlv74vNlOl3h_QWP_-5c4kR7lWpdTtOJcM56OAFaohyDnuh0LpXLET7rX5h90L5TxFK3nBIib-olVKMiYKwyBukGNzjucgqFV6dEvAJ8gyOlV_UufG3_lo9IJZeNS29y7ke0Zb_ObEO1CxIv7dQ8dxQny2mL63YBny2Iv0kBDKn89Fo7wN40-1HAzPFCnbW5rfRMjfblHkHBJzuhmnCQHYOZtdWbajjHtkNRiCVojwxS0ZwSVKAexIvSSqJ2SmDw1bS8ew_m9cGACJW67GOuBa4ou-JuRVL9HO-PNO8ZP_DRu9OZf53UzmSLkyhNZjuBlTmmu3-c5yOKPnZmVPDMVtCzkZ4q-jLWGmD3fJC2vZwIj_QFxl6J1Rsny95uB8WB-Ewc76YkGMZGXlTmUW_sqpgm5aABoyVsVqVZVekpEBL-A8TyCvueZcLg6KFjd1jPdYT5bbTX3bBHiVqKJjCVWnV4d_bKJWb4L1OFdvZfT8ziCm-GHKiI'

            headers = {
                'Authorization': f'Bearer {EMOLA_BEARER_TOKEN}',
                'X-Requested-With': 'XMLHttpRequest'
            }
            payload = {
                'client_id': EMOLA_CLIENT_ID,
                'amount': str(int(valor)),
                'reference': f"PAYMOZ-{uuid.uuid4().hex[:8]}",
                'phone': numero_celular
            }
            
            try:
                response = requests.post(EMOLA_API_URL, headers=headers, data=payload)

                if response.status_code == 422:
                    logger.error(f"Erro 422 da API e-Mola. Resposta: {response.text}")
                    try:
                        error_details = response.json()
                        error_message = error_details.get('message', 'Erro de validacao.')
                        errors = error_details.get('errors', {})
                        detailed_error = f"{error_message} Detalhes: {json.dumps(errors)}"
                    except json.JSONDecodeError:
                        detailed_error = response.text
                    resposta_json = {'output_ResponseCode': 'ERR', 'output_ResponseDesc': detailed_error}
                else:
                    response.raise_for_status()  # Lanca excecao para outros erros 4xx/5xx
                    emola_response_data = response.json()
                    logger.info(f"Resposta bem-sucedida da API e-Mola: {json.dumps(emola_response_data)}")
                    
                                        # Processar a resposta da API e-Mola
                    if response.status_code in [200, 201] and emola_response_data.get('success'):
                                            # A API e-Mola retorna um sucesso simples.
                                            # Geramos um ID de transacao unico para referencia interna.
                                            resposta_json = {
                                                'output_ResponseCode': 'INS-0',
                                                'output_TransactionID': f"EMOLA-{uuid.uuid4().hex[:12].upper()}",
                                                'output_ResponseDesc': emola_response_data.get('success')
                                            }

                    else:
                                            error_message = emola_response_data.get('message', 'Erro desconhecido na API e-Mola')
                                            logger.error(f"Erro na API e-Mola: {response.status_code} - {error_message}")
                                            resposta_json = {'output_ResponseCode': 'ERR', 'output_ResponseDesc': error_message}
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro de conexao com a API e-Mola: {e}")
                return JsonResponse({'status': 'error', 'message': f'Erro de comunicacao com o gateway de pagamento e-Mola: {e}'}, status=500)

        # elif method == 'emola':
        #     # Simulação para Emola
        #     resposta_json = {
        #         "output_ResponseCode": "INS-0",
        #         "output_ResponseDesc": "Request processed successfully (Simulated)",
        #         "output_TransactionID": f"EMOLA-SIM-{uuid.uuid4().hex[:10]}",
        #     }
        else:
            return JsonResponse({'status': 'error', 'message': 'Método de pagamento não suportado.'}, status=400)

        # 3. Processamento unificado da resposta e atualização do sistema
        if resposta_json and resposta_json.get('output_ResponseCode') == 'INS-0':
            if user_profile.custom_transaction_fee_percentage is not None:
                taxa_percentual = user_profile.custom_transaction_fee_percentage
            elif user_profile.package:
                taxa_percentual = user_profile.package.transaction_fee_percentage
            else:
                taxa_percentual = Decimal('10.00')

            taxa_aplicada = valor * (taxa_percentual / 100)
            valor_liquido = valor - taxa_aplicada

            user_profile.balance += valor_liquido
            user_profile.save()

            nova_transacao = Transaction.objects.create(
                user_profile=user_profile,
                valor=valor,
                status='SUCCESS',
                external_transaction_id=resposta_json.get('output_TransactionID'),
                payment_phone_number=numero_celular # Salva o número de pagamento
            )

            # Enviar notificação de venda para o usuário (vendedor)
            enviar_notificacao_venda(nova_transacao)

            # Retorna a transação criada para ser usada na view chamadora
            return JsonResponse({
                'status': 'success',
                'message': f'Pagamento via {method.capitalize()} processado com sucesso.',
                'transaction_id': resposta_json.get('output_TransactionID'),
                'valor_recebido': str(valor),
                'taxa_aplicada': str(taxa_aplicada),
                'valor_liquido_creditado': str(valor_liquido),
                'internal_transaction_id': str(nova_transacao.id) # Adiciona o ID interno da transação
            })
        else:
            error_message = 'O pagamento falhou.'
            details = 'Resposta inválida do gateway de pagamento.'
            if resposta_json:
                error_message = resposta_json.get('mensagem_tratada', f'O pagamento via {method.capitalize()} falhou.')
                details = resposta_json.get('output_ResponseDesc', 'Sem detalhes adicionais.')

            return JsonResponse({
                'status': 'error',
                'message': error_message,
                'details': details
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Requisição JSON inválida.'}, status=400)
    except Exception as e:
        logger.error(f"Erro inesperado na process_payment: {e}")
        return JsonResponse({'status': 'error', 'message': 'Ocorreu um erro interno inesperado.'}, status=500)
@csrf_exempt
@require_POST
def create_checkout_session(request):
    """
    Cria uma sessão de checkout e retorna uma URL de pagamento hospedada.
    """
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return JsonResponse({'status': 'error', 'message': 'API key não fornecida.'}, status=401)

        try:
            user_profile = UserProfile.objects.get(api_key=api_key)
        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'API key inválida.'}, status=401)

        # Validação do Status da Assinatura
        if user_profile.subscription_status == 'TRIAL_EXPIRED':
            return JsonResponse({'status': 'error', 'message': 'O seu período de teste expirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        if user_profile.subscription_status == 'TRIAL':
            if user_profile.trial_start_date and (date.today() - user_profile.trial_start_date).days > 7:
                user_profile.subscription_status = 'TRIAL_EXPIRED'
                user_profile.save()
                return JsonResponse({'status': 'error', 'message': 'O seu período de teste expirou. Por favor, faça um upgrade para o plano Pro.'}, status=403)

        data = json.loads(request.body)
        valor_str = data.get('valor')
        nome_cliente = data.get('nome_cliente') # Opcional
        nome_produto = data.get('nome_produto', '') # Opcional, inicializa com string vazia se não fornecido

        # Usa a callback_url fornecida ou define uma padrão
        callback_url = data.get('callback_url')

        if not callback_url:
            if nome_produto:
                try:
                    from produtos.models import Produto # Importar aqui para evitar circular dependency
                    produto = Produto.objects.get(nome=nome_produto, user_profile=user_profile)
                    if produto.callback_url:
                        callback_url = produto.callback_url
                        logger.debug(f"create_checkout_session: Usando callback_url do produto: {callback_url}")
                    else:
                        callback_url = request.build_absolute_uri(reverse('dashboard'))
                        logger.debug(f"create_checkout_session: Produto sem callback_url, usando dashboard: {callback_url}")
                except Produto.DoesNotExist:
                    callback_url = request.build_absolute_uri(reverse('dashboard'))
                    logger.warning(f"create_checkout_session: Produto '{nome_produto}' não encontrado, usando dashboard: {callback_url}")
            else:
                callback_url = request.build_absolute_uri(reverse('dashboard'))
                logger.debug(f"create_checkout_session: Nenhuma callback_url ou nome_produto, usando dashboard: {callback_url}")
        
        logger.debug(f"create_checkout_session: callback_url final: {callback_url}")

        if not valor_str:
            return JsonResponse({'status': 'error', 'message': 'O campo \'valor\' é obrigatório.'}, status=400)

        try:
            valor = Decimal(str(valor_str))
            if valor <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Valor inválido.'}, status=400)

        # Cria a sessão de checkout
        session = CheckoutSession.objects.create(
            user_profile=user_profile,
            valor=valor,
            callback_url=callback_url,
            nome_cliente=nome_cliente,
            nome_produto=nome_produto
        )

        # Monta a URL de pagamento
        checkout_url = request.build_absolute_uri(f'/checkout/pay/{session.session_id}/')

        return JsonResponse({
            'status': 'success',
            'checkout_url': checkout_url,
            'session_id': session.session_id,
            'expires_at': session.created_at + timedelta(minutes=30) # Exemplo de expiração
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Requisição JSON inválida.'}, status=400)
    except Exception as e:
        logger.error(f"Erro inesperado em create_checkout_session: {e}")
        return JsonResponse({'status': 'error', 'message': 'Ocorreu um erro interno inesperado.'}, status=500)


from django.views.decorators.csrf import csrf_exempt
from django.db import transaction # Importar transaction

def enviar_notificacao_falha_vendedor(transaction):
    """
    Envia uma notificação para o vendedor quando uma transação falha.
    """
    user_profile = transaction.user_profile
    user = user_profile.user
    nome_completo_vendedor = f"{user.name} {user.surname}".strip() if user.name or user.surname else user.username
    
    # Carrega os contatos de suporte
    suporte = ContactoSuporte.load()
    contato_suporte_whatsapp = suporte.whatsapp if suporte and suporte.whatsapp else "número de suporte não configurado"

    mensagem = (
        f"Atenção: Transação Falhou!\n"
        f"----------------------------------------\n"
        f"Vendedor: {nome_completo_vendedor}\n"
        f"Produto: {transaction.checkout_session.nome_produto if transaction.checkout_session else 'N/A'}\n"
        f"Valor: {transaction.valor:.2f} MZN\n"
        f"ID da Transação: {transaction.transaction_id}\n"
        f"----------------------------------------\n"
        f"Se este problema persistir, por favor, entre em contato com nosso suporte: {contato_suporte_whatsapp}"
    )
    
    numero_vendedor_whatsapp = user.sso_id
    if numero_vendedor_whatsapp:
        numero_vendedor_whatsapp_normalizado = normalizar_numero_whatsapp(numero_vendedor_whatsapp)
        send_whatsapp_message(numero_vendedor_whatsapp_normalizado, mensagem)
        logger.info(f"Notificação de falha enviada para o vendedor {user.username} ({numero_vendedor_whatsapp}).")
    else:
        logger.warning(f"Número de WhatsApp do vendedor {user.username} (sso_id) não encontrado para notificação de falha.")

    # --- Mensagem E-mail para o Vendedor ---
    if user.email:
        assunto_email = f"Atenção: Transação Falhou! - {nome_produto} - Paymoz"
        mensagem_email = (
            f"Prezado(a) {nome_completo_vendedor},\n\n"
            f"Informamos que houve um problema ao processar uma transação em sua conta Paymoz.\n\n"
            f"Detalhes da Transação:\n"
            f"- Produto: {transaction.checkout_session.nome_produto if transaction.checkout_session else 'N/A'}\n"
            f"- Valor: {transaction.valor:.2f} MZN\n"
            f"- ID da Transação: {transaction.transaction_id}\n\n"
            f"Se este problema persistir, por favor, entre em contato com nosso suporte: {contato_suporte_whatsapp}\n\n"
            f"Atenciosamente,\n"
            f"A Equipe Paymoz"
        )

        try:
            send_mail(
                assunto_email,
                mensagem_email,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            logger.info(f"E-mail de notificação de falha enviado para o vendedor {user.email}.")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de falha para {user.email}: {e}")
    else:
        logger.warning(f"E-mail do vendedor {user.username} não encontrado para notificação de falha.")

def enviar_notificacao_falha_cliente(transaction):
    """
    Envia uma notificação para o cliente quando uma transação falha
    via WhatsApp e e-mail.
    """
    # Extrai o número de WhatsApp e e-mail do cliente da sessão de checkout
    numero_cliente_whatsapp = None
    email_cliente = None

    if transaction.checkout_session:
        email_cliente = transaction.checkout_session.email_cliente
        if transaction.checkout_session.dados_cliente_custom:
            for label, valor in transaction.checkout_session.dados_cliente_custom.items():
                if 'whatsapp' in label.lower():
                    numero_cliente_whatsapp = valor
                    break
    
    if not numero_cliente_whatsapp and not email_cliente:
        logger.warning("Número de WhatsApp e e-mail do cliente não encontrados para notificação de falha.")
        return

    # Contato do vendedor
    vendedor_user = transaction.user_profile.user
    contato_vendedor_whatsapp = normalizar_numero_whatsapp(vendedor_user.sso_id) if vendedor_user.sso_id else "N/A"

    nome_cliente = transaction.checkout_session.nome_cliente if transaction.checkout_session else 'Cliente'
    nome_produto = transaction.checkout_session.nome_produto if transaction.checkout_session else 'o produto'

    # --- Mensagem WhatsApp (tom informal) ---
    if numero_cliente_whatsapp:
        mensagem_whatsapp = (
            f"""Olá {nome_cliente}!

"""            f"""Houve um problema ao processar o seu pagamento para {nome_produto}.

"""            f"""Por favor, tente novamente. Se o problema persistir, entre em contato diretamente com o vendedor pelo WhatsApp: {contato_vendedor_whatsapp}

"""            f"""Pedimos desculpas pelo inconveniente."""        )
        send_whatsapp_message(normalizar_numero_whatsapp(numero_cliente_whatsapp), mensagem_whatsapp)
        logger.info(f"Notificação de falha enviada para o cliente no número {numero_cliente_whatsapp}.")

    # --- Mensagem E-mail (tom formal) ---
    if email_cliente:
        assunto_email = f"Problema com seu Pagamento para {nome_produto} - Paymoz"
        mensagem_email = (
            f"""Prezado(a) {nome_cliente},

"""            f"""Informamos que houve um problema ao processar o seu pagamento para o produto: {nome_produto}.

"""            f"""Detalhes da Transação:
"""            f"""- Valor: {transaction.valor:.2f} MZN
"""            f"""- ID da Transação: {transaction.transaction_id}

"""            f"""Por favor, tente realizar o pagamento novamente. Se o problema persistir, recomendamos que entre em contato diretamente com o vendedor para assistência:
"""            f"""WhatsApp do Vendedor: {contato_vendedor_whatsapp}

"""            f"""Pedimos desculpas por qualquer inconveniente causado.

"""            f"""Atenciosamente,
"""            f"""A Equipe Paymoz"""        )

        try:
            send_mail(
                assunto_email,
                mensagem_email,
                settings.DEFAULT_FROM_EMAIL,
                [email_cliente],
                fail_silently=False,
            )
            logger.info(f"E-mail de notificação de falha enviado para o cliente {email_cliente}.")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de falha para {email_cliente}: {e}")



@csrf_exempt
def hosted_checkout_view(request, session_id):
    try:
        session = CheckoutSession.objects.get(session_id=session_id, status='PENDING')
    except CheckoutSession.DoesNotExist:
        return render(request, 'paginas/hosted_checkout.html', {'error': 'Sessão de checkout inválida ou expirada.'})

    if request.method == 'POST':
        try:
            numero_celular = request.POST.get('numero_celular')
            nome_cliente = request.POST.get('nome_cliente')

            logger.info(f"hosted_checkout_view: numero_celular recebido: '{numero_celular}', Tipo: {type(numero_celular)}")
            logger.info(f"hosted_checkout_view: nome_cliente recebido: '{nome_cliente}', Tipo: {type(nome_cliente)}")
            logger.info(f"hosted_checkout_view: callback_url da sessão: {session.callback_url}")

            if not numero_celular:
                # Adicionar mensagem de erro se o número for inválido
                return render(request, 'paginas/hosted_checkout.html', {'session': session, 'error': 'Número de celular inválido.'})

            # Atualiza o nome do cliente na sessão, se não foi fornecido na criação
            if nome_cliente and not session.nome_cliente:
                session.nome_cliente = nome_cliente
                session.save()

            # Logica para determinar o metodo de pagamento
            if numero_celular.startswith(('86', '87')):
                method = 'emola'
            elif numero_celular.startswith(('84', '85')):
                method = 'mpesa'
            else:
                return render(request, 'paginas/hosted_checkout.html', {'session': session, 'error': 'Numero de celular invalido para M-Pesa ou e-Mola.'})

            # Simula a chamada à API interna process_payment
            # Construindo um objeto de request simulado para a API
            from django.http import HttpRequest
            from django.test import RequestFactory

            factory = RequestFactory()
            api_request_data = json.dumps({
                'numero_celular': numero_celular,
                'valor': str(session.valor)
            })
            api_request = factory.post(f'/api/v1/payment/{method}/', 
                                       data=api_request_data, 
                                       content_type='application/json',
                                       HTTP_X_API_KEY=session.user_profile.api_key)

            # Chama a view diretamente
            logger.info(f"Chamando process_payment para método: {method}")
            response = process_payment(api_request, method=method)
            logger.info(f"Resposta de process_payment (status_code): {response.status_code}")
            logger.info(f"Resposta de process_payment (content): {response.content}")
            response_data = json.loads(response.content)

            if response_data.get('status') == 'success':
                session.status = 'COMPLETED'
                session.save()

                # Associa a sessão de checkout à transação
                # Busca a transação pelo ID interno retornado por process_payment
                transaction = Transaction.objects.get(id=response_data.get('internal_transaction_id'))
                transaction.checkout_session = session
                transaction.save()

                # Enviar notificação de venda para o vendedor
                enviar_notificacao_venda(transaction)

                # Enviar notificação de confirmação para o cliente
                enviar_notificacao_cliente(transaction)

                # Obter o produto associado à sessão de checkout
                produto = None
                if session.nome_produto and session.user_profile:
                    try:
                        from produtos.models import Produto # Importar aqui para evitar circular dependency
                        produto = Produto.objects.get(nome=session.nome_produto, user_profile=session.user_profile)
                    except Produto.DoesNotExist:
                        logger.warning(f"Produto '{session.nome_produto}' não encontrado para o user '{session.user_profile.user.username}'. Não será possível redirecionar para download.")

                # Renderiza a página de sucesso com todas as informações
                context = {
                    'session': session,
                    'transaction': transaction,
                    'produto': produto,
                    'callback_url': session.callback_url,
                    'success_message': 'Pagamento realizado com sucesso!'
                }
                logger.debug(f"Redirecionando para callback_url: {session.callback_url}")
                return render(request, 'paginas/pagamento_sucesso.html', context)
            else:
                # Se o pagamento falhar, cria uma transação FAILED e renderiza a página com a mensagem de erro
                failed_transaction = Transaction.objects.create(
                    user_profile=session.user_profile,
                    valor=session.valor,
                    status='FAILED',
                    external_transaction_id=response_data.get('transaction_id'), # Pode ser None
                    checkout_session=session
                )
                
                # Enviar notificações de falha
                enviar_notificacao_falha_vendedor(failed_transaction)
                enviar_notificacao_falha_cliente(failed_transaction)

                return render(request, 'paginas/hosted_checkout.html', {'session': session, 'error': response_data.get('message', 'Ocorreu um erro desconhecido no pagamento.')})
        except Exception as e:
            logger.error(f"Erro no processamento do checkout: {e}")
            return render(request, 'paginas/hosted_checkout.html', {'session': session, 'error': f'Ocorreu um erro: {str(e)}'})

    return render(request, 'paginas/hosted_checkout.html', {'session': session})

def payment_success_page(request):
    valor = request.GET.get('valor')
    transaction_id = request.GET.get('transaction_id')
    session_id = request.GET.get('session_id')

    context = {
        'valor': valor,
        'transaction_id': transaction_id,
        'session_id': session_id
    }
    return render(request, 'paginas/pagamento_sucesso.html', context)

@login_required
def total_transactions_panel_view(request):
    # Apenas superusuários podem acessar este painel
    if not request.user.is_superuser:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('home')

        # Total de transações bem-sucedidas
    total_success_transactions_sum = Transaction.objects.filter(
        status='SUCCESS'
    ).aggregate(models.Sum('valor'))['valor__sum'] or Decimal('0')

    # Total de transações falhas
    total_failed_transactions_sum = Transaction.objects.filter(
        status='FAILED'
    ).aggregate(models.Sum('valor'))['valor__sum'] or 0

    # Total de transações (sucesso + falha)
    total_all_transactions_sum = Transaction.objects.aggregate(models.Sum('valor'))['valor__sum'] or 0

    # Contagem de transações por status
    count_success = Transaction.objects.filter(status='SUCCESS').count()
    count_failed = Transaction.objects.filter(status='FAILED').count()
    count_total = Transaction.objects.count()

    # Calcular Lucro Líquido (10% do total de transações bem-sucedidas)
    lucro_liquido = total_success_transactions_sum * Decimal('0.10')

    # Obter configurações de saque administrativo
    admin_withdrawal_settings = AdminWithdrawalSettings.load()
    available_for_withdrawal = (lucro_liquido * (admin_withdrawal_settings.withdrawal_percentage / 100)) - admin_withdrawal_settings.total_withdrawn_amount
    # Garante que o valor disponível não seja negativo
    if available_for_withdrawal < 0:
        available_for_withdrawal = Decimal('0.00')

    # Transações por usuário
    users_with_transactions = []
    all_user_profiles = UserProfile.objects.select_related('user').all()

    for user_profile in all_user_profiles:
        user_successful_transactions = Transaction.objects.filter(
            user_profile=user_profile,
            status='SUCCESS'
        ).select_related('user_profile__user').order_by('-timestamp')

        user_failed_transactions = Transaction.objects.filter(
            user_profile=user_profile,
            status='FAILED'
        ).select_related('user_profile__user').order_by('-timestamp')

        if user_successful_transactions.exists() or user_failed_transactions.exists():
            users_with_transactions.append({
                'user_profile': user_profile,
                'successful_transactions': user_successful_transactions,
                'failed_transactions': user_failed_transactions,
            })

    context = {
        'total_success_transactions_sum': total_success_transactions_sum,
        'total_failed_transactions_sum': total_failed_transactions_sum,
        'total_all_transactions_sum': total_all_transactions_sum,
        'count_success': count_success,
        'count_failed': count_failed,
        'count_total': count_total,
        'lucro_liquido': lucro_liquido, # Novo contexto
        'available_for_withdrawal': available_for_withdrawal, # Novo contexto
        'admin_withdrawal_settings': admin_withdrawal_settings, # Novo contexto
        'users_with_transactions': users_with_transactions, # Novo contexto
        'admin_withdrawals': AdminWithdrawal.objects.all().order_by('-timestamp'), # Histórico de saques
    }
    return render(request, 'paginas/total_transactions_panel.html', context)

@user_passes_test(lambda u: u.is_superuser)
@login_required
@require_POST
@csrf_exempt
def admin_withdraw_view(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Você não tem permissão para realizar esta operação.'}, status=403)

    try:
        data = json.loads(request.body)
        amount_str = data.get('amount')

        try:
            amount = Decimal(str(amount_str))
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Valor de saque inválido.'}, status=400)

        admin_withdrawal_settings = AdminWithdrawalSettings.load()
        total_success_transactions_sum = Transaction.objects.filter(
            status='SUCCESS'
        ).aggregate(models.Sum('valor'))['valor__sum'] or 0
        lucro_liquido = total_success_transactions_sum * Decimal('0.06')
        available_for_withdrawal = (lucro_liquido * (admin_withdrawal_settings.withdrawal_percentage / 100)) - admin_withdrawal_settings.total_withdrawn_amount

        if amount > available_for_withdrawal:
            return JsonResponse({'status': 'error', 'message': f'Valor solicitado ({amount:.2f} MZN) excede o disponível para saque ({available_for_withdrawal:.2f} MZN).'}, status=400)

        with transaction.atomic():
            # Registrar o saque
            AdminWithdrawal.objects.create(amount=amount)

            # Atualizar o total sacado nas configurações
            admin_withdrawal_settings.total_withdrawn_amount += amount
            admin_withdrawal_settings.save()

        return JsonResponse({'status': 'success', 'message': f'Saque de {amount:.2f} MZN realizado com sucesso!', 'new_available_balance': available_for_withdrawal - amount})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Requisição JSON inválida.'}, status=400)
    except Exception as e:
        logger.error(f"Erro ao processar saque administrativo: {e}")
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)