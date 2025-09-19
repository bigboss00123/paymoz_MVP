import os
import django
from decimal import Decimal

# Configure o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paymoz.settings')
django.setup()

# Importe os modelos necessários
from core.models import Package

def add_pro_plan():
    """
    Cria ou atualiza o 'Plano Pro' na base de dados.
    """
    package_details = {
        'name': 'Plano Pro',
        'description': 'Acesso a todos os recursos da plataforma, incluindo API, páginas de produtos ilimitadas e suporte prioritário.',
        'price': Decimal('1500.00'),
        'is_active': True,
        'package_type': 'ONE_TIME'
    }

    # Use get_or_create para evitar duplicados
    package, created = Package.objects.get_or_create(
        name=package_details['name'],
        defaults=package_details
    )

    if created:
        print(f"Pacote '{package.name}' criado com sucesso!")
    else:
        # Se o pacote já existe, verifica se precisa de ser atualizado
        updated = False
        for key, value in package_details.items():
            if getattr(package, key) != value:
                setattr(package, key, value)
                updated = True
        
        if updated:
            package.save()
            print(f"Pacote '{package.name}' atualizado com sucesso!")
        else:
            print(f"Pacote '{package.name}' já existe e está atualizado.")

if __name__ == "__main__":
    add_pro_plan()
