from django.core.management.base import BaseCommand
from core.models import UserProfile
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Checks for expired trial subscriptions and updates user status.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Checking for expired trial subscriptions...")
        
        trial_users = UserProfile.objects.filter(subscription_status='TRIAL')
        
        for profile in trial_users:
            if profile.trial_start_date and (date.today() - profile.trial_start_date).days > 7:
                profile.subscription_status = 'TRIAL_EXPIRED'
                profile.save()
                self.stdout.write(self.style.WARNING(f'Trial expired for user: {profile.user.username}. Status updated to TRIAL_EXPIRED.'))
            else:
                self.stdout.write(f'User {profile.user.username} is still within trial period.')
                
        self.stdout.write(self.style.SUCCESS('Trial status check complete.'))
