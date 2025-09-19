import requests
import json

def make_payment_request(phone, value, reference):
    """
    Faz uma requisição POST para o endpoint /pagar do servidor local.

    Args:
        phone (str): O número de telefone para a transação.
        value (float or int): O valor da transação.
        reference (str): A referência da transação.

    Returns:
        dict or None: A resposta JSON do servidor, ou None em caso de erro.
    """
    url = "http://localhost:8005/api/pagamento_mpesa"
    payload = {
        "numero_celular": phone,
        "valor": value
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        print(f"Enviando requisição POST para {url} com payload: {payload}")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Levanta um HTTPError para códigos de status de erro (4xx ou 5xx)
        print(f"Requisição bem-sucedida! Status Code: {response.status_code}")
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP: {http_err}")
        print(f"Resposta do servidor (se disponível): {response.text if 'response' in locals() else 'N/A'}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Erro de Conexão: {conn_err}. Certifique-se de que o servidor Node.js está rodando em {url}.")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Erro de Timeout: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Erro na Requisição: {req_err}")
    return None

if __name__ == "__main__":
    # Exemplo de uso:
    # Certifique-se de que o servidor Node.js está rodando antes de executar este script.
    
    # Substitua pelos dados reais que você deseja enviar
    telefone_exemplo = "258847519599" # Exemplo de número de telefone
    valor_exemplo = 1
    import random
    referencia_exemplo = f"TEST_REF_{random.randint(10000, 99999)}"

    print("\n--- Testando a requisição de pagamento ---")
    result = make_payment_request(telefone_exemplo, valor_exemplo, referencia_exemplo)

    if result:
        print("\nResposta do servidor:")
        print(json.dumps(result, indent=2))
    else:
        print("\nFalha ao fazer a requisição de pagamento.")
