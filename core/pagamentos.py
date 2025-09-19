from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import json

# Importar modelos relevantes, se necessário
# from .models import Transaction, UserProfile

@login_required
@require_POST
def process_payment_view(request):
    """
    Uma view para processar uma requisição de pagamento.
    Espera um JSON no corpo da requisição com 'amount' e 'description'.
    """
    try:
        # Decodifica o corpo da requisição JSON
        data = json.loads(request.body)
        amount = data.get('amount')
        description = data.get('description')

        # Validação básica
        if not amount or not isinstance(amount, (int, float)) or amount <= 0:
            return JsonResponse({'status': 'error', 'message': 'O valor do pagamento é inválido.'}, status=400)

        if not description:
            return JsonResponse({'status': 'error', 'message': 'A descrição é obrigatória.'}, status=400)

        # --- Lógica de Pagamento (Placeholder) ---
        # Aqui você integraria com um gateway de pagamento (ex: Stripe, M-Pesa, etc.)
        # Por agora, vamos apenas simular que o pagamento foi bem-sucedido.
        
        # Exemplo: Deduzir do saldo do usuário (se aplicável)
        # user_profile = request.user.userprofile
        # if user_profile.balance < amount:
        #     return JsonResponse({'status': 'error', 'message': 'Saldo insuficiente.'}, status=400)
        # user_profile.balance -= amount
        # user_profile.save()

        # Exemplo: Criar um registro da transação
        # Transaction.objects.create(
        #     user=request.user,
        #     amount=amount,
        #     description=description,
        #     status='completed'
        # )

        # Resposta de sucesso
        return JsonResponse({
            'status': 'success',
            'message': 'Pagamento processado com sucesso!',
            'transaction_id': 'simulated_tx_12345' # ID de transação simulado
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Requisição JSON inválida.'}, status=400)
    except Exception as e:
        # Log do erro é uma boa prática
        # logger.error(f"Erro ao processar pagamento para {request.user.username}: {e}")
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)
