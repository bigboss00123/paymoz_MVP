

import requests
import json

# --- Configurações ---
# Certifique-se de que seu servidor Django esteja rodando
BASE_URL = 'http://127.0.0.1:8000' 
# Substitua pela chave de API de um usuário de teste
API_KEY = 'neura-224bdcef-9f35-4793-b1a3-ed63a3197761' 
# O endpoint para criar a sessão de checkout
ENDPOINT = '/api/v1/checkout/session/'

# --- Dados para a Sessão de Checkout ---
checkout_data = {
    "valor": "1",
    "callback_url": "https://meusite.com/obrigado",
    "nome_produto": "Curso de Django Avançado",
    "nome_cliente": "José Mussá" # Este campo é opcional
}

# --- Montando a Requisição ---
url = BASE_URL + ENDPOINT
headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
}

# --- Executando a Chamada ---
print(f"Enviando requisição para: {url}")
print("---")

try:
    response = requests.post(url, headers=headers, data=json.dumps(checkout_data))

    # --- Exibindo a Resposta ---
    print(f"Status Code: {response.status_code}")
    print("Headers da Resposta:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    print("\nCorpo da Resposta (JSON):")
    try:
        response_json = response.json()
        print(json.dumps(response_json, indent=2))

        if response.status_code == 200 and response_json.get('status') == 'success':
            print("\n--- TESTE BEM-SUCEDIDO ---")
            print("Sessão de checkout criada com sucesso!")
            print(f"URL de Pagamento: {response_json.get('checkout_url')}")
            print("Abra a URL acima em um navegador para continuar o pagamento.")
        else:
            print("\n--- TESTE FALHOU ---")
            print("Não foi possível criar a sessão de checkout.")
            print(f"Mensagem de erro: {response_json.get('message', 'N/A')}")

    except json.JSONDecodeError:
        print("Erro: A resposta não é um JSON válido.")
        print(f"Conteúdo da resposta:\n{response.text}")

except requests.exceptions.RequestException as e:
    print(f"\n--- ERRO DE CONEXÃO ---")
    print(f"Não foi possível conectar ao servidor: {e}")
    print("Verifique se o seu servidor Django está rodando no endereço e porta corretos.")



