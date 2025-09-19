from django.contrib import admin
from .models import TransacaoMpesa

@admin.register(TransacaoMpesa)
class TransacaoMpesaAdmin(admin.ModelAdmin):
    list_display = ('numero_celular', 'valor', 'status', 'criado_em')
    list_filter = ('status', 'criado_em')
    search_fields = ('numero_celular',)