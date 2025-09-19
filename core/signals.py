import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile, Saque
from django.utils import timezone

from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Cria ou atualiza o UserProfile sempre que um User é salvo.
    Garante que cada usuário tenha um perfil, uma chave de API e um status de assinatura.
    """
    if created:
        profile = UserProfile.objects.create(user=instance)
        profile.api_key = f"neura-{uuid.uuid4()}"
        profile.subscription_status = 'TRIAL'
        profile.trial_start_date = timezone.now().date()
        profile.save()
    else:
        # Garante que um perfil exista para usuários antigos que talvez não o tenham
        profile, profile_created = UserProfile.objects.get_or_create(user=instance)
        if profile_created or not profile.api_key:
            profile.api_key = f"neura-{uuid.uuid4()}"
            if profile_created:
                profile.subscription_status = 'TRIAL'
                profile.trial_start_date = timezone.now().date()
            profile.save()

@receiver(post_save, sender=Saque)
def update_balance_on_saque_rejection(sender, instance, created, **kwargs):
    """
    Quando um Saque é salvo e seu status é 'REJEITADO',
    o valor do saque é devolvido ao saldo do UserProfile.
    """
    if not created and instance.status == 'REJEITADO':
        user_profile = instance.user_profile
        user_profile.balance += instance.valor
        user_profile.save()
        
        user = user_profile.user
        nome_completo = f"{user.name} {user.surname}".strip() if user.name or user.surname else user.username
        
        mensagem = (
            f"Olá {nome_completo}, seu saque foi REJEITADO!\n"
            f"----------------------------------------\n"
            f"Valor: {instance.valor:.2f} MZN\n"
            f"O valor foi devolvido ao seu saldo. Novo saldo: {user_profile.balance:.2f} MZN\n"
            f"ID da Transação: {instance.id_transacao}\n"
            f"----------------------------------------"
        )
        print("DEBUG: Função update_balance_on_saque_rejection (rejeição) foi chamada.") # Para depuração
        logger.info(mensagem)

@receiver(post_save, sender=Saque)
def notify_on_saque_completion(sender, instance, created, **kwargs):
    """
    Notifica quando um Saque é salvo e seu status é 'CONCLUIDO'.
    """
    # A notificação só deve ocorrer se o saque não for recém-criado
    # e o status foi alterado para 'CONCLUIDO'.
    # Para verificar a mudança de status, precisamos do valor anterior.
    # Isso é um pouco mais complexo com post_save, mas podemos assumir
    # que se não é 'created' e o status é 'CONCLUIDO', é uma transição.
    if not created and instance.status == 'CONCLUIDO':
        user = instance.user_profile.user
        nome_completo = f"{user.name} {user.surname}".strip() if user.name or user.surname else user.username
        
        mensagem = (
            f"Olá {nome_completo}, seu saque foi processado!\n"
            f"----------------------------------------\n"
            f"Valor: {instance.valor:.2f} MZN\n"
            f"Enviado para o número: {instance.numero_celular}\n"
            f"Status: {instance.status}\n"
            f"ID da Transação: {instance.id_transacao}\n"
            f"----------------------------------------"
        )
        print("DEBUG: Função notify_on_saque_completion foi chamada.") # Para depuração
        logger.info(mensagem)
