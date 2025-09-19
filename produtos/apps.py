from django.apps import AppConfig


class ProdutosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'produtos'

    def ready(self):
        # Importa os sinais para que eles sejam registrados quando o app estiver pronto
        import produtos.signals