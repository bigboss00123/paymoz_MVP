from django.core.management.base import BaseCommand
from core.models import UserProfile, Transaction, Saque
from decimal import Decimal

class Command(BaseCommand):
    help = 'Recalculates the balance for all user profiles based on transactions and withdrawals.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting balance recalculation...'))

        user_profiles = UserProfile.objects.all()
        for profile in user_profiles:
            total_received = Decimal('0.00')
            total_withdrawn = Decimal('0.00')
            total_fees = Decimal('0.00')

            # Calculate total received from successful transactions
            successful_transactions = Transaction.objects.filter(user_profile=profile, status='SUCCESS')
            for transaction in successful_transactions:
                total_received += transaction.valor
                total_fees += transaction.valor * Decimal('0.10') # Assuming 10% fee
            
            # Calculate total withdrawn from successful saques
            successful_saques = Saque.objects.filter(user_profile=profile, status='CONCLUIDO')
            for saque in successful_saques:
                total_withdrawn += saque.valor

            # Calculate the new balance
            new_balance = total_received - total_fees - total_withdrawn
            
            # Update the user profile balance
            profile.balance = new_balance
            profile.save()

            self.stdout.write(self.style.SUCCESS(
                f'Recalculated balance for {profile.user.username}: '
                f'Received={total_received:.2f}, Fees={total_fees:.2f}, Withdrawn={total_withdrawn:.2f}, '
                f'New Balance={new_balance:.2f}'
            ))
        
        self.stdout.write(self.style.SUCCESS('Balance recalculation completed.'))
