import os
import django
from django.db.models import Sum

# Configure o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paymoz.settings')
django.setup()

from core.models import User, UserProfile, Transaction, Saque
from decimal import Decimal

class Command(django.core.management.base.BaseCommand):
    help = 'Recalculates the balance for the root user based on their own transactions and withdrawals.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting to recalculate root user balance...'))

        try:
            # Get the root user
            root_user = User.objects.get(username='root')
            
            # Get or create the UserProfile for the root user
            root_profile, created = UserProfile.objects.get_or_create(
                user=root_user,
                defaults={'balance': Decimal('0.00'), 'api_key': 'root_default_api_key'} # Provide a default API key if creating
            )
            if created:
                self.stdout.write(self.style.WARNING('Created UserProfile for root user.'))

            total_received = Decimal('0.00')
            total_withdrawn = Decimal('0.00')
            total_fees = Decimal('0.00')

            # Calculate total received from successful transactions for the root user
            successful_transactions = Transaction.objects.filter(user_profile=root_profile, status='SUCCESS')
            for transaction in successful_transactions:
                total_received += transaction.valor
                total_fees += transaction.valor * Decimal('0.10') # Assuming 10% fee
            
            # Calculate total withdrawn from successful saques for the root user
            successful_saques = Saque.objects.filter(user_profile=root_profile, status='CONCLUIDO')
            for saque in successful_saques:
                total_withdrawn += saque.valor

            # Calculate the new balance
            new_balance = total_received - total_fees - total_withdrawn
            
            # Update the root user's balance
            root_profile.balance = new_balance
            root_profile.save()

            self.stdout.write(self.style.SUCCESS(
                f'Successfully recalculated root user balance to: {root_profile.balance:.2f} MZN'
            ))

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Error: Root user does not exist. Please create the root user first.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An unexpected error occurred: {e}'))
