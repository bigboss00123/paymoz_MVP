#!/bin/bash
cd /root/projetos_mtevolution/paymoz_MVP

# Ativa o ambiente virtual (se estiver usando)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Inicia o Django
exec python3 manage.py runserver 0.0.0.0:9000
