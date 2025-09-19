import os
import django
import random
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

# Configure o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paymoz.settings')
django.setup()

# Importe os modelos necessários
from core.models import User, UserProfile, Transaction

def add_transactions_to_sombra(num_transactions=10):
    """
    Adiciona um número especificado de transações ao usuário 'Sombra'.
    """
    try:
        # Encontra o usuário e o perfil
        user = User.objects.get(username='sombra')
        user_profile = UserProfile.objects.get(user=user)
        
        print(f"Adicionando {num_transactions} transações para o usuário '{user.username}'...")

        # Cria as transações
        for i in range(num_transactions):
            # Gera dados aleatórios
            valor_aleatorio = Decimal(random.uniform(50.0, 800.0)).quantize(Decimal('0.01'))
            dias_atras = random.randint(0, 7)
            data_transacao = timezone.now() - timedelta(days=dias_atras)
            
            # Cria a transação
            Transaction.objects.create(
                user_profile=user_profile,
                valor=valor_aleatorio,
                status='SUCCESS',
                timestamp=data_transacao
            )
            print(f"  ({i+1}/{num_transactions}) Transação de {valor_aleatorio} MZN criada em {data_transacao.strftime('%Y-%m-%d')}.")

        print(f"\n{num_transactions} transações adicionadas com sucesso!")

    except User.DoesNotExist:
        print("Erro: Usuário 'sombra' não encontrado. Execute o script para popular os dados de teste primeiro.")
    except UserProfile.DoesNotExist:
        print("Erro: Perfil para o usuário 'sombra' não encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    add_transactions_to_sombra(10)
