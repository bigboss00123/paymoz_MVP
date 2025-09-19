from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Transaction
from .models import Produto

@receiver(post_save, sender=Transaction)
def incrementar_contador_vendas(sender, instance, created, **kwargs):
    """
    Quando uma transação de sucesso é criada e está associada a uma sessão de checkout
    que tem um nome de produto, incrementa o contador de vendas desse produto.
    """
    if created and instance.status == 'SUCCESS' and instance.checkout_session:
        session = instance.checkout_session
        if session.nome_produto:
            try:
                # Encontra o produto pelo nome e pelo dono (usuário da sessão)
                produto = Produto.objects.get(
                    nome=session.nome_produto,
                    user_profile=session.user_profile
                )
                produto.vendidos += 1
                produto.save()
            except Produto.DoesNotExist:
                # Opcional: logar se o produto mencionado na sessão não for encontrado
                print(f"Produto não encontrado para a venda: {session.nome_produto}")
            except Exception as e:
                print(f"Erro ao incrementar vendas: {e}")
