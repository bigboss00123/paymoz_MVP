
import requests
import threading
import time
import uuid

# --- Configurações ---
API_KEY = "neura-0af331f1-0bd2-4b36-ae8e-87e7e7070391"
BASE_URL = "http://5.189.144.249:8000"
ENDPOINT = "/api/v1/payment/mpesa/"
URL = BASE_URL + ENDPOINT

NUMERO_REQUISICOES = 5
VALOR_PAGAMENTO = 1.5  # Usar um valor baixo para teste
NUMERO_CELULAR = "258840000001" # Número de celular de teste

# --- Headers ---
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# --- Função para fazer a requisição ---
def fazer_pagamento(thread_id):
    """Função que será executada por cada thread."""
    payload = {
        "numero_celular": NUMERO_CELULAR,
        "valor": VALOR_PAGAMENTO,
    }
    
    start_time = time.time()
    print(f"Thread {thread_id}: Enviando requisição...")
    
    try:
        response = requests.post(URL, json=payload, headers=HEADERS, timeout=45)
        end_time = time.time()
        
        print(f"Thread {thread_id}: Resposta recebida (Status: {response.status_code}) em {end_time - start_time:.2f}s")
        
        try:
            response_data = response.json()
            print(f"Thread {thread_id}: Dados da Resposta: {response_data}")
        except requests.exceptions.JSONDecodeError:
            print(f"Thread {thread_id}: Erro ao decodificar JSON. Resposta: {response.text}")

    except requests.exceptions.RequestException as e:
        end_time = time.time()
        print(f"Thread {thread_id}: Erro na requisição em {end_time - start_time:.2f}s - {e}")

# --- Execução ---
if __name__ == "__main__":
    threads = []
    print(f"Iniciando {NUMERO_REQUISICOES} requisições simultâneas para: {URL}")

    for i in range(NUMERO_REQUISICOES):
        thread = threading.Thread(target=fazer_pagamento, args=(i+1,)) 
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("\nTeste de concorrência concluído.")
