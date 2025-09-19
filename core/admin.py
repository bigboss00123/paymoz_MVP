
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, Saque, Package, Transaction, ContactoSuporte, CheckoutSession, ApiSettings
from django.utils.html import format_html
from django.urls import reverse

import json

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'name', 'surname', 'is_staff', 'user_profile_link')
    search_fields = ('username', 'email', 'name', 'surname')

    def user_profile_link(self, obj):
        if hasattr(obj, 'userprofile'):
            url = reverse("admin:core_userprofile_change", args=[obj.userprofile.id])
            return format_html('<a href="{}">Ver Perfil</a>', url)
        return "Sem Perfil"
    user_profile_link.short_description = 'Perfil de Usuário'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'subscription_status', 'package', 'api_key')
    search_fields = ('user__username', 'user__email', 'api_key')
    list_filter = ('subscription_status', 'package')
    readonly_fields = ('api_key', 'balance')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user_profile_link', 'valor', 'status', 'timestamp', 'external_transaction_id')
    search_fields = ('transaction_id', 'user_profile__user__username', 'external_transaction_id')
    list_filter = ('status', 'timestamp')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    def user_profile_link(self, obj):
        url = reverse("admin:core_userprofile_change", args=[obj.user_profile.id])
        return format_html('<a href="{}">{}</a>', url, obj.user_profile.user.username)
    user_profile_link.short_description = 'User Profile'

@admin.register(Saque)
class SaqueAdmin(admin.ModelAdmin):
    list_display = ('id_transacao', 'user_profile_link', 'valor', 'status', 'data_solicitacao', 'numero_celular')
    search_fields = ('id_transacao', 'user_profile__user__username', 'numero_celular')
    list_filter = ('status', 'data_solicitacao')
    date_hierarchy = 'data_solicitacao'
    ordering = ('-data_solicitacao',)
    actions = ['marcar_como_concluido', 'marcar_como_rejeitado']

    def user_profile_link(self, obj):
        url = reverse("admin:core_userprofile_change", args=[obj.user_profile.id])
        return format_html('<a href="{}">{}</a>', url, obj.user_profile.user.username)
    user_profile_link.short_description = 'User Profile'

    def marcar_como_concluido(self, request, queryset):
        queryset.update(status='CONCLUIDO')
    marcar_como_concluido.short_description = "Marcar saques selecionados como Concluídos"

    def marcar_como_rejeitado(self, request, queryset):
        for saque in queryset:
            if saque.status == 'PENDENTE':
                saque.user_profile.balance += saque.valor 
                saque.user_profile.save()
        queryset.update(status='REJEITADO')
    marcar_como_rejeitado.short_description = "Marcar saques selecionados como Rejeitados (e reverter saldo)"


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'package_type', 'price', 'transaction_fee_percentage', 'withdrawal_fee_percentage', 'is_active')
    list_filter = ('package_type', 'is_active')
    search_fields = ('name',)

@admin.register(ContactoSuporte)
class ContactoSuporteAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return ContactoSuporte.objects.count() == 0

@admin.register(CheckoutSession)
class CheckoutSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user_profile_link', 'valor', 'status', 'created_at', 'nome_produto')
    search_fields = ('session_id', 'user_profile__user__username', 'nome_produto')
    list_filter = ('status', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('session_id', 'user_profile', 'valor', 'callback_url', 'nome_cliente', 'nome_produto', 'display_dados_cliente_custom')
    
    def display_dados_cliente_custom(self, obj):
        """Exibe o JSON de forma formatada e legível."""
        if obj.dados_cliente_custom:
            # Formata o dicionário JSON para uma string bonita
            formatted_json = json.dumps(obj.dados_cliente_custom, indent=4, ensure_ascii=False)
            return format_html("<pre>{}</pre>", formatted_json)
        return "Nenhum dado personalizado."
    display_dados_cliente_custom.short_description = 'Dados Personalizados do Cliente'


    def user_profile_link(self, obj):
        url = reverse("admin:core_userprofile_change", args=[obj.user_profile.id])
        return format_html('<a href="{}">{}</a>', url, obj.user_profile.user.username)
    user_profile_link.short_description = 'User Profile'

@admin.register(ApiSettings)
class ApiSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return ApiSettings.objects.count() == 0
