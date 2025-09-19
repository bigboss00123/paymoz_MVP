import os
import django
from django.db.models import Sum

# Configure o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paymoz.settings')
django.setup()

# Importe o modelo Transaction
from core.models import Transaction

def sum_all_transactions():
    """
    Calcula e imprime o valor total de todas as transações de sucesso na base de dados.
    """
    total_sum = Transaction.objects.filter(status='SUCCESS').aggregate(total_valor=Sum('valor'))['total_valor']
    
    if total_sum is None:
        total_sum = 0.00

    print(f"\nValor total de todas as transações de sucesso: {total_sum:.2f} MZN")

if __name__ == "__main__":
    sum_all_transactions()
