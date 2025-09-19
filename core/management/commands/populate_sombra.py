from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from core.models import User, UserProfile, Transaction
from decimal import Decimal

class Command(BaseCommand):
    help = 'Creates a test user "sombra" and populates it with successful transactions.'

    def handle(self, *args, **kwargs):
        # Find or create the user
        user, user_created = User.objects.get_or_create(
            username='sombra',
            defaults={'name': 'Sombra', 'email': 'sombra@example.com'}
        )
        if user_created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created user "{user.username}"'))
        else:
            self.stdout.write(self.style.WARNING(f'User "{user.username}" already exists.'))

        # Find or create the user profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal('0.00'), 'api_key': 'pk_test_sombra12345'}
        )
        if profile_created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created profile for "{user.username}"'))

        # Clear existing transactions for this user to avoid duplicates
        Transaction.objects.filter(user_profile=profile).delete()
        self.stdout.write(self.style.WARNING(f'Cleared existing transactions for "{user.username}".'))

        # Create a series of transactions
        today = timezone.now()
        for i in range(60):  # Create transactions for the last 60 days
            # Create more transactions in the recent period
            if i < 30:
                num_transactions_per_day = random.randint(2, 5)
            else:
                num_transactions_per_day = random.randint(0, 2)

            for _ in range(num_transactions_per_day):
                transaction_date = today - timedelta(days=i)
                amount = Decimal(random.uniform(50.0, 750.0)).quantize(Decimal('0.01'))
                Transaction.objects.create(
                    user_profile=profile,
                    valor=amount,
                    status='SUCCESS',
                    timestamp=transaction_date
                )
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created a new series of transactions for "{user.username}".'))