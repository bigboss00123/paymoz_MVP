import os
import django
import random
from datetime import datetime
from django.utils import timezone
from decimal import Decimal

# Configure o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paymoz.settings')
django.setup()

# Importe os modelos necessários
from core.models import User, UserProfile, Transaction

def add_transactions_for_specific_date(target_date, num_transactions=5):
    
    #Adiciona um número especificado de transações ao usuário 'Sombra' para uma data específica.
    
    try:
        # Encontra o usuário e o perfil
        user = User.objects.get(username='sombra')
        user_profile = UserProfile.objects.get(user=user)
        
        print(f"Adicionando {num_transactions} transações para o usuário '{user.username}' em {target_date.strftime('%Y-%m-%d')}...")

        # Cria as transações
        for i in range(num_transactions):
            valor_aleatorio = Decimal(random.uniform(100.0, 1000.0)).quantize(Decimal('0.01'))
            
            # Define o timestamp para a data alvo, com hora aleatória para simular transações ao longo do dia
            transaction_datetime = target_date.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                microsecond=random.randint(0, 999999)
            )
            # Garante que o datetime é timezone-aware se o seu Django estiver configurado para isso
            if timezone.is_naive(transaction_datetime):
                transaction_datetime = timezone.make_aware(transaction_datetime)

            # Cria a transação
            Transaction.objects.create(
                user_profile=user_profile,
                valor=valor_aleatorio,
                status='SUCCESS',
                timestamp=transaction_datetime
            )
            print(f"  ({i+1}/{num_transactions}) Transação de {valor_aleatorio} MZN criada em {transaction_datetime.strftime('%Y-%m-%d %H:%M:%S')}.")

        print(f"\n{num_transactions} transações adicionadas com sucesso para {target_date.strftime('%Y-%m-%d')}!")

    except User.DoesNotExist:
        print("Erro: Usuário 'sombra' não encontrado. Execute o script para popular os dados de teste primeiro.")
    except UserProfile.DoesNotExist:
        print("Erro: Perfil para o usuário 'sombra' não encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    # Defina a data alvo aqui
    target_date = datetime(2025, 7, 29) # 30 de Julho de 2025
    add_transactions_for_specific_date(target_date, 5)
