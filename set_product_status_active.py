# -*- coding: utf-8 -*-
import os
import django

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paymoz.settings')
django.setup()

from produtos.models import Produto

def set_product_status_active(product_name):
    try:
        produto = Produto.objects.get(nome=product_name)
        if produto.status != 'ATIVO':
            produto.status = 'ATIVO'
            produto.save()
            print(f"Status do produto '{product_name}' alterado para ATIVO com sucesso.")
        else:
            print(f"Produto '{product_name}' já está ATIVO.")
    except Produto.DoesNotExist:
        print(f"ERRO: Produto '{product_name}' não encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    # Altere o nome do produto conforme necessário
    set_product_status_active("Curso de Python para Automação")
