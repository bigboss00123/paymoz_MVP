from django.shortcuts import render
from .logica_mpesa import mpesa, tratmento_erro, mpesa_b2c # Importar a nova função b2c
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required # Importar login_required
from django.contrib.auth import authenticate, login, logout # Importar funções de autenticação
from django.core.cache import cache # Importar o cache
from .models import TransacaoMpesa
from django.db.models import Sum
from decimal import Decimal # Importar Decimal para precisão monetária

MAX_LOGIN_ATTEMPTS = 5
BLOCK_TIME = 300 # 5 minutos em segundos

@csrf_exempt
def pagamento_mpesa(request):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Metodo nao permitido'}, status=405)
    
    try: 
        dados = json.loads(request.body)
        numero_celular = dados.get('numero_celular')
        valor = dados.get('valor')
    except json.JSONDecodeError:
        return JsonResponse({'erro': 'Formato de dados invalido'}, status=400)
    
    if not numero_celular or not valor:
        return JsonResponse({'erro': 'Dados insuficientes'}, status=400)
    
    if not str(numero_celular).isdigit() or len(str(numero_celular)) != 9:
        return JsonResponse({'erro': 'Numero de celular invalido'}, status=400)
   
    if not isinstance(valor, (int, float)) or valor <= 0:
        return JsonResponse({'erro': 'Valor invalido'}, status=400)

    resultado = mpesa(numero_celular, valor)
    resposta_api = resultado.body
    codigo_erro = resposta_api.get('output_ResponseCode')
    mensagem_erro = tratmento_erro(codigo_erro)

    status = 'SUCESSO' if codigo_erro == 'INS-0' else 'FALHA'

    TransacaoMpesa.objects.create(
        tipo_transacao='C2B',
        numero_celular=numero_celular,
        valor=valor,
        status=status,
        resposta_api=resposta_api,
        mensagem_erro=mensagem_erro
    )

    # Retorna a resposta da API original, mas com a mensagem de erro tratada
    resposta_final = resposta_api.copy()
    resposta_final['mensagem_tratada'] = mensagem_erro

    return JsonResponse(resposta_final, status=resultado.status_code)
    


@login_required
def dashborad(request):
    # Calcula o total de ENTRADAS (C2B bem-sucedidas)
    total_entradas = TransacaoMpesa.objects.filter(
        tipo_transacao='C2B', status='SUCESSO'
    ).aggregate(Sum('valor'))['valor__sum'] or 0

    # Calcula o total de SAÍDAS (B2C bem-sucedidas)
    total_saidas = TransacaoMpesa.objects.filter(
        tipo_transacao='B2C', status='SUCESSO'
    ).aggregate(Sum('valor'))['valor__sum'] or 0

    # Calcula o saldo líquido
    saldo_liquido = total_entradas - total_saidas
    # Se o saldo for negativo, exibe 0
    if saldo_liquido < 0:
        saldo_liquido = Decimal('0.00')

    # Conta o número total de transações que falharam
    total_erros = TransacaoMpesa.objects.filter(status='FALHA').count()
    
    # Conta o número total de transações
    total_transacoes = TransacaoMpesa.objects.count()
    
    # Busca as 10 últimas transações para exibir na tabela, ordenadas pela mais recente
    ultimas_transacoes = TransacaoMpesa.objects.order_by('-criado_em')[:10]
    
    # Cria o dicionário de contexto para passar ao template
    contexto = {
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo_liquido': saldo_liquido,
        'total_erros': total_erros,
        'total_transacoes': total_transacoes,
        'ultimas_transacoes': ultimas_transacoes
    }
    
    # Renderiza o template com o contexto
    return render(request, 'dashboard.html', contexto)
    
 

@csrf_exempt
def pagamento_b2c(request):
    """
    View para processar pagamentos B2C.
    """
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)

    try:
        dados = json.loads(request.body)
        numero_celular = dados.get('numero_celular')
        valor = dados.get('valor')
    except json.JSONDecodeError:
        return JsonResponse({'erro': 'Formato de dados inválido'}, status=400)

    if not numero_celular or not valor:
        return JsonResponse({'erro': 'Dados insuficientes'}, status=400)

    if not str(numero_celular).isdigit() or len(str(numero_celular)) != 9:
        return JsonResponse({'erro': 'Número de celular inválido'}, status=400)

    if not isinstance(valor, (int, float)) or valor <= 0:
        return JsonResponse({'erro': 'Valor inválido'}, status=400)

    # --- Validação de Saldo --- #
    try:
        valor_decimal = Decimal(str(valor))
        total_entradas = TransacaoMpesa.objects.filter(tipo_transacao='C2B', status='SUCESSO').aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
        total_saidas = TransacaoMpesa.objects.filter(tipo_transacao='B2C', status='SUCESSO').aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
        saldo_liquido = total_entradas - total_saidas
        # Se o saldo for negativo, trate como 0
        if saldo_liquido < 0:
            saldo_liquido = Decimal('0.00')

        if valor_decimal > saldo_liquido:
            return JsonResponse({'erro': f'Saldo insuficiente para realizar a transferência. Saldo atual: {saldo_liquido} MZN'}, status=400)
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao verificar saldo: {str(e)}'}, status=500)
    # --- Fim da Validação de Saldo --- #

    resposta_dados = {}
    try:
        # Chama a função de lógica B2C
        resultado = mpesa_b2c(numero_celular, valor)
        if resultado is None:
            raise Exception('A chamada à API B2C retornou None')

        resposta_dados = resultado.body
        status = 'SUCESSO' if resultado.status_code in [200, 201] else 'FALHA'

        # Salva a transação no banco de dados
        TransacaoMpesa.objects.create(
            tipo_transacao='B2C',  # Adicionado tipo de transação
            numero_celular=numero_celular,
            valor=valor,
            status=status,
            resposta_api=resposta_dados,
            mensagem_erro=None if status == 'SUCESSO' else str(resposta_dados)
        )

        return JsonResponse(resultado.body, status=resultado.status_code)

    except Exception as e:
        # Salva a transação com o erro
        TransacaoMpesa.objects.create(
            tipo_transacao='B2C',  # Adicionado tipo de transação
            numero_celular=numero_celular,
            valor=valor,
            status='FALHA',
            resposta_api=resposta_dados,
            mensagem_erro=str(e)
        )

        return JsonResponse({'erro': f'Ocorreu um erro interno: {str(e)}'}, status=500)

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        ip_cache_key = f'login_attempts_ip_{ip_address}'
        ip_attempts = cache.get(ip_cache_key, 0)

        if ip_attempts >= MAX_LOGIN_ATTEMPTS:
            return JsonResponse({'erro': 'Muitas tentativas de login do seu IP. Tente novamente mais tarde.'}, status=429)

        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return JsonResponse({'erro': 'Email e senha são obrigatórios'}, status=400)

            email_cache_key = f'login_attempts_email_{email}'
            email_attempts = cache.get(email_cache_key, 0)

            if email_attempts >= MAX_LOGIN_ATTEMPTS:
                return JsonResponse({'erro': 'Muitas tentativas de login para este email. Tente novamente mais tarde.'}, status=429)

            from django.contrib.auth.models import User
            try:
                user = User.objects.get(email=email)
                username = user.username
            except User.DoesNotExist:
                cache.set(ip_cache_key, ip_attempts + 1, BLOCK_TIME)
                cache.set(email_cache_key, email_attempts + 1, BLOCK_TIME)
                return JsonResponse({'erro': 'Credenciais inválidas'}, status=400)

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                cache.delete(ip_cache_key) # Clear IP attempts on successful login
                cache.delete(email_cache_key) # Clear email attempts on successful login
                return JsonResponse({'mensagem': 'Login bem-sucedido'}, status=200)
            else:
                cache.set(ip_cache_key, ip_attempts + 1, BLOCK_TIME)
                cache.set(email_cache_key, email_attempts + 1, BLOCK_TIME)
                return JsonResponse({'erro': 'Credenciais inválidas'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'erro': 'Formato de dados inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'erro': f'Ocorreu um erro interno: {str(e)}'}, status=500)
    return JsonResponse({'erro': 'Método não permitido'}, status=405)

@csrf_exempt
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return JsonResponse({'mensagem': 'Logout bem-sucedido'}, status=200)
    return JsonResponse({'erro': 'Método não permitido'}, status=405)

def render_login_page(request):
    return render(request, 'mpesa_app/login.html')

@login_required
def list_all_transactions(request):
    if request.method == 'GET':
        transactions = TransacaoMpesa.objects.all().order_by('-criado_em')
        data = []
        for t in transactions:
            data.append({
                'tipo_transacao': t.tipo_transacao,
                'numero_celular': t.numero_celular,
                'valor': str(t.valor), # Convert Decimal to string
                'status': t.status,
                'criado_em': t.criado_em.strftime("%d/%m/%Y %H:%M"),
                'mensagem_erro': t.mensagem_erro
            })
        return JsonResponse(data, safe=False)
    return JsonResponse({'erro': 'Método não permitido'}, status=405)