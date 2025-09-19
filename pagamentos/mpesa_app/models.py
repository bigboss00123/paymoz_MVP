from django.db import models

class TransacaoMpesa(models.Model):
    TIPO_TRANSACAO_CHOICES = [
        ('C2B', 'Entrada (C2B)'),
        ('B2C', 'Saída (B2C)'),
    ]

    tipo_transacao = models.CharField(max_length=3, choices=TIPO_TRANSACAO_CHOICES, default='C2B')
    numero_celular = models.CharField(max_length=20)
    valor =  models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
    resposta_api = models.JSONField(null=True, blank=True)
    mensagem_erro = models.TextField(null=True, blank=True, help_text="Armazena a mensagem de erro, se houver.")
    criado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.numero_celular} - {self.valor} MZN - {self.status}'
    

