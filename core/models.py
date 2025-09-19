from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):
    sso_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    surname = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.username

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    api_key = models.CharField(max_length=255, unique=True, blank=True, null=True)
    subscription_status = models.CharField(max_length=20, choices=[('TRIAL', 'Trial'), ('PRO', 'Pro'), ('TRIAL_EXPIRED', 'Trial Expired')], default='TRIAL')
    trial_start_date = models.DateField(null=True, blank=True)
    package = models.ForeignKey('Package', on_delete=models.SET_NULL, null=True, blank=True)
    custom_withdrawal_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    custom_transaction_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_expires_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"

class CheckoutSession(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='checkout_sessions')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    nome_cliente = models.CharField(max_length=255, blank=True, null=True)
    nome_produto = models.CharField(max_length=255, blank=True, null=True)
    email_cliente = models.EmailField(max_length=255, blank=True, null=True)
    callback_url = models.URLField(max_length=2048)
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('EXPIRED', 'Expired')], default='PENDING')
    dados_cliente_custom = models.JSONField(default=dict, blank=True, help_text='Dados customizados preenchidos pelo cliente no checkout.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Checkout {self.session_id} for {self.user_profile.user.username}"

class Transaction(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='transactions')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed')])
    timestamp = models.DateTimeField(auto_now_add=True)
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    external_transaction_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    checkout_session = models.ForeignKey(CheckoutSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='checkout_transactions')
    payment_phone_number = models.CharField(max_length=20, blank=True, null=True)

    @property
    def client_contact_number(self):
        if self.payment_phone_number:
            return self.payment_phone_number
        if self.checkout_session and self.checkout_session.dados_cliente_custom:
            for label, valor in self.checkout_session.dados_cliente_custom.items():
                if 'whatsapp' in label.lower() or 'telefone' in label.lower() or 'celular' in label.lower():
                    return valor
        return 'N/A'

    def __str__(self):
        return f"Transaction of {self.valor} for {self.user_profile.user.username} - {self.status}"

class Saque(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('CONCLUIDO', 'Concluído'),
        ('REJEITADO', 'Rejeitado'),
        ('CANCELADO', 'Cancelado'),
    ]

    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='saques')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    valor_liquido = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    numero_celular = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    id_transacao = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"Saque de {self.valor} para {self.user_profile.user.username} - {self.status}"

class Package(models.Model):
    PACKAGE_TYPES = [
        ('TRIAL', 'Trial'),
        ('ONE_TIME', 'One-Time Payment'),
        ('ENTERPRISE', 'Enterprise'),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPES, unique=True)
    withdrawal_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    transaction_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name

class ContactoSuporte(models.Model):
    email = models.EmailField(max_length=255, blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    facebook_link = models.URLField(max_length=255, blank=True, null=True)
    linkedin_link = models.URLField(max_length=255, blank=True, null=True)
    youtube_link = models.URLField(max_length=255, blank=True, null=True)
    instagram_link = models.URLField(max_length=255, blank=True, null=True)
    github_link = models.URLField(max_length=255, blank=True, null=True)
    x_link = models.URLField(max_length=255, blank=True, null=True)
    pinterest_link = models.URLField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "Informações de Contato"

    class Meta:
        verbose_name = "Informação de Contato"
        verbose_name_plural = "Informações de Contato"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(ContactoSuporte, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class ApiSettings(models.Model):
    base_url = models.URLField(max_length=255, default='https://paymoz.co.mz/api/v1')

    def __str__(self):
        return "Configurações da API"

    class Meta:
        verbose_name = "Configuração da API"
        verbose_name_plural = "Configurações da API"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(ApiSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class AdminWithdrawalSettings(models.Model):
    withdrawal_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, help_text="Porcentagem do lucro líquido que é considerado o saldo disponível para saque administrativo.")
    total_withdrawn_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Valor total já sacado do lucro líquido.")

    class Meta:
        verbose_name = "Configuração de Saque Administrativo"
        verbose_name_plural = "Configurações de Saque Administrativo"

    def save(self, *args, **kwargs):
        self.pk = 1  # Garante que haverá apenas uma instância
        super(AdminWithdrawalSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class AdminWithdrawal(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    # Opcional: Adicionar um campo para o usuário admin que realizou o saque
    # admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Saque Administrativo"
        verbose_name_plural = "Saques Administrativos"
        ordering = ['-timestamp']

    def __str__(self):
        return f"Saque de {self.amount} em {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
