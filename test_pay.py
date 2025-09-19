import requests
import json

# --- Configurações ---
# Substitua pela URL real do seu servidor quando em produção
BASE_URL = "http://127.0.0.1:8000" 
API_KEY = "neura-224bdcef-9f35-4793-b1a3-ed63a3197761"  # <-- COLOQUE SUA CHAVE DE API AQUI

# --- Dados do Pagamento ---
payment_data = {
    "numero_celular": "867519599",  # Número de celular para o pagamento
    "valor": "1"               # Valor do pagamento
}

# --- Montando a Requisição ---
url = f"{BASE_URL}/api/v1/payment/emola/"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# --- Executando a Requisição ---
print(f"Enviando requisição para: {url}")
print(f"Dados: {json.dumps(payment_data, indent=2)}")

try:
    response = requests.post(url, headers=headers, data=json.dumps(payment_data), timeout=60)

    # --- Processando a Resposta ---
    print(f"\nStatus da Resposta: {response.status_code}")
    
    try:
        # Tenta imprimir a resposta como JSON formatado
        response_json = response.json()
        print("Resposta da API (JSON):")
        print(json.dumps(response_json, indent=2))
    except json.JSONDecodeError:
        # Se não for JSON, imprime como texto
        print("Resposta da API (Texto):")
        print(response.text)

except requests.exceptions.Timeout:
    print("\nErro: A requisição demorou muito para responder (timeout).")
except requests.exceptions.RequestException as e:
    print(f"\nErro na requisição: {e}")
