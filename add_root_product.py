# -*- coding: utf-8 -*-
import os
import django
from decimal import Decimal

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paymoz.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import UserProfile
from produtos.models import Produto

def add_product_to_root():
    User = get_user_model()
    try:
        # 1. Encontrar o usuário 'root'
        root_user = User.objects.get(username='root')
        print(f"Usuário 'root' encontrado: {root_user}")

        # 2. Obter o UserProfile associado
        user_profile = UserProfile.objects.get(user=root_user)
        print(f"UserProfile para 'root' encontrado: {user_profile}")

        # 3. Definir os dados para o novo produto
        product_data = {
            'user_profile': user_profile,
            'nome': "Curso de Python para Automação",
            'descricao': "Aprenda a automatizar tarefas repetitivas com Python. Este curso cobre desde o básico de scripting até a integração com APIs e web scraping.",
            'preco': Decimal('499.99'),
            'depoimentos': [
                {"autor": "Joana Silva", "texto": "Excelente curso! Consegui automatizar vários relatórios no meu trabalho."},
                {"autor": "Pedro Costa", "texto": "Didática muito clara e exemplos práticos. Recomendo!"}
            ],
            'gatilhos_mentais': {
                "escassez": "Últimas 20 vagas com 50% de desconto!",
                "prova_social": "Junte-se a mais de 500 alunos satisfeitos."
            },
            'ativo': True
        }

        # 4. Criar e salvar o novo produto
        # Usamos update_or_create para evitar duplicatas se o script for executado várias vezes
        novo_produto, created = Produto.objects.update_or_create(
            nome=product_data['nome'],
            user_profile=user_profile,
            defaults=product_data
        )

        if created:
            print(f"\nProduto '___{novo_produto.nome}___' criado com sucesso para o usuário 'root'.")
        else:
            print(f"\nProduto '___{novo_produto.nome}___' já existia e foi atualizado para o usuário 'root'.")
        
        print(f"ID do Produto: {novo_produto.id}")
        print(f"Slug Gerado: {novo_produto.slug}")

    except User.DoesNotExist:
        print("ERRO: O usuário com username 'root' não foi encontrado.")
    except UserProfile.DoesNotExist:
        print("ERRO: O UserProfile para o usuário 'root' não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    add_product_to_root()
