from pprint import pprint
import time
import uuid
import random
import string
import os
import requests

class MockApiResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body

CODIGOS_ERRO_MPESA = {
    "INS-0": "Requisição processada com sucesso",
    "INS-1": "Erro interno",
    "INS-2": "Chave de API inválida",
    "INS-4": "Utilizador não está ativo",
    "INS-5": "Transação cancelada pelo cliente",
    "INS-6": "Transação falhou",
    "INS-9": "Tempo de requisição esgotado",
    "INS-10": "Transação duplicada",
    "INS-13": "Shortcode inválido",
    "INS-14": "Referência inválida",
    "INS-15": "Valor inválido",
    "INS-16": "Não foi possível processar a requisição devido a uma sobrecarga temporária",
    "INS-17": "Referência de transação inválida. O comprimento deve ser entre 1 e 20.",
    "INS-18": "ID de transação inválido",
    "INS-19": "Referência de terceiro inválida",
    "INS-20": "Nem todos os parâmetros foram fornecidos. Por favor, tente novamente.",
    "INS-21": "Falha na validação dos parâmetros. Por favor, tente novamente.",
    "INS-22": "Tipo de operação inválido",
    "INS-23": "Status desconhecido. Contacte o suporte M-Pesa",
    "INS-24": "Identificador do iniciador inválido",
    "INS-25": "Credencial de segurança inválida",
    "INS-26": "Não autorizado",
    "INS-993": "Débito direto em falta",
    "INS-994": "Débito direto já existe",
    "INS-995": "O perfil do cliente tem problemas",
    "INS-996": "O estado da conta do cliente não está ativo",
    "INS-997": "Transação de ligação não encontrada",
    "INS-998": "Mercado inválido",
    "INS-2001": "Erro de autenticação do iniciador.",
    "INS-2002": "Destinatário inválido.",
    "INS-2006": "Saldo insuficiente",
    "INS-2051": "MSISDN inválido.",
    "INS-2057": "Código de idioma inválido."
}

def tratmento_erro(codigo_erro):
    """
    Traduz um código de erro da API M-Pesa para uma mensagem descritiva.
    """
    return CODIGOS_ERRO_MPESA.get(codigo_erro, "Ocorreu um erro desconhecido.")

def referencia_transacao (tamanho=6, prefixo='paymoz'):

     caracteres = string.ascii_uppercase + string.digits
     parte_aleatoria = ''.join(random.choice(caracteres) for _ in range(tamanho))
     return prefixo + parte_aleatoria

def numero_normal (numero: str) -> str:
    numero_limpo = numero.strip()

    if not numero_limpo.startswith('258'):
        if numero_limpo.startswith('8'):
            return '258' + numero_limpo

        else:
            return '258' + numero_limpo 
    
    return numero_limpo

def mpesa(numero_celular, valor):
    referencia = referencia_transacao()
    numero_celular_certo = numero_normal(numero_celular)

    # URL da sua API Node.js
    url = "http://localhost:3000/pagar"

    # Dados para a requisição
    payload = {
        "phone": numero_celular_certo,
        "value": valor,
        "reference": referencia
    }

    try:
        # Fazendo a requisição POST para a API Node.js
        response = requests.post(url, json=payload, timeout=60)
        print(f"[DEBUG - logica_mpesa] Resposta do Node.js - Status Code: {response.status_code}")
        print(f"[DEBUG - logica_mpesa] Resposta do Node.js - Texto: {response.text}")
        response.raise_for_status()  # Lança um erro para respostas com status 4xx ou 5xx

        # Resposta da API Node.js
        resposta_node = response.json()

        # --- ADAPTADOR ---
        # Traduz a resposta do Node.js para o formato que a view espera.
        if resposta_node.get('output_ResponseCode') == 'INS-0':
            # Se o Node.js disse que foi sucesso, montamos uma resposta de sucesso no formato M-Pesa.
            corpo_resposta_formatado = {
                'output_ResponseCode': 'INS-0', # Código de sucesso
                'output_ResponseDesc': 'Request processed successfully',
                'output_TransactionID': resposta_node.get('transactionId', 'N/A'), # Pega o ID se existir
                'output_ConversationID': resposta_node.get('conversationId', 'N/A'),
                'output_ThirdPartyReference': referencia
            }
        else:
            # Se o Node.js disse que falhou, tentamos usar o código e descrição de erro do Node.js
            corpo_resposta_formatado = {
                'output_ResponseCode': resposta_node.get('output_ResponseCode', 'INS-6'), # Usa o código do Node.js ou INS-6
                'output_ResponseDesc': resposta_node.get('output_ResponseDesc', resposta_node.get('error', 'A transação falhou.')), # Usa a descrição do Node.js ou a mensagem de erro
                'error': resposta_node.get('error') # Mantém o campo 'error' original
            }
        
        return MockApiResponse(response.status_code, corpo_resposta_formatado)

    except requests.exceptions.Timeout:
        print(f'Erro de tempo limite ao conectar com a API Node.js: {{e}}')
        error_body = {{'error': 'O serviço de pagamento demorou muito para responder.', 'output_ResponseCode': 'INS-9'}}
        return MockApiResponse(504, error_body)
    except requests.exceptions.RequestException as e:
        print(f'Erro ao conectar com a API Node.js: {{e}}')
        error_body = {{'error': f'Falha na comunicação com o serviço de pagamento: {{e}}', 'output_ResponseCode': 'INS-1'}}
        return MockApiResponse(502, error_body)