import requests
import json

# --- Configuração da Requisição ---
# URL do seu endpoint Django
url = "http://127.0.0.1:8005/api/pagamento_mpesa/"

# Dados do pagamento que você quer enviar
dados_pagamento = {
    "numero_celular": "843550143",
    "valor": 10
}

# Cabeçalho da requisição
headers = {
    "Content-Type": "application/json"
}

# --- Envio da Requisição ---
print(f"Enviando requisição POST para: {url}")
print(f"Corpo da requisição: {json.dumps(dados_pagamento)}")

try:
    # Faz a requisição POST
    response = requests.post(url, headers=headers, data=json.dumps(dados_pagamento))

    # Força um erro se a resposta não for bem-sucedida (ex: 404, 500)
    response.raise_for_status()

    # --- Processamento da Resposta ---
    print("\n--- Resposta Recebida ---")
    print(f"Status Code: {response.status_code}")

    # Converte a resposta para JSON e a imprime de forma legível
    resposta_json = response.json()
    print("Corpo da resposta (JSON):")
    print(json.dumps(resposta_json, indent=4, ensure_ascii=False))

except requests.exceptions.HTTPError as http_err:
    print(f"\n[ERRO HTTP]: {http_err}")
    print(f"Corpo da resposta: {response.text}")
except requests.exceptions.ConnectionError as conn_err:
    print(f"\n[ERRO DE CONEXÃO]: {conn_err}")
    print("Não foi possível conectar ao servidor. Verifique se o servidor Django está rodando na porta 8005.")
except Exception as err:
    print(f"\n[ERRO INESPERADO]: {err}")
