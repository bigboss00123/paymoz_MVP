from flask import Flask, request, jsonify
import requests
import json
import random
import string
import os
import logging

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(filename='flask_output.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app.logger.info("Flask app started.")

# URL do seu servidor Node.js
NODE_JS_API_URL = "http://localhost:3000/pagar"

def gerar_referencia_paymoz(tamanho=8):
    """
    Gera uma referência única começando com 'PAYMOZ' e um sufixo aleatório.
    """
    caracteres = string.ascii_uppercase + string.digits
    sufixo = ''.join(random.choice(caracteres) for _ in range(tamanho))
    return f"PAYMOZ{sufixo}"

def numero_normal(numero: str) -> str:
    """
    Normaliza o número de celular adicionando o prefixo '258' se necessário.
    """
    numero_limpo = numero.strip()
    if not numero_limpo.startswith('258'):
        if numero_limpo.startswith('8'):
            return '258' + numero_limpo
        else:
            return '258' + numero_limpo
    return numero_limpo

@app.route('/api/pagamento_mpesa', methods=['POST'])
def make_payment():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    phone = data.get('numero_celular')
    value = data.get('valor')

    if not phone or not value:
        return jsonify({"error": "Os campos 'numero_celular' e 'valor' são obrigatórios."}), 400

    # Normalizar o número de celular
    phone = numero_normal(phone)

    # Gerar a referência
    referencia = gerar_referencia_paymoz()

    # Preparar o payload para o servidor Node.js
    payload = {
        "phone": phone,
        "value": value,
        "reference": referencia # Usar a referência gerada
    }

    try:
        app.logger.info(f"[Flask Gateway] Enviando requisição para Node.js: {NODE_JS_API_URL} com payload: {payload}")
        response = requests.post(NODE_JS_API_URL, json=payload, timeout=60)
        response.raise_for_status()  # Levanta um HTTPError para códigos de status de erro (4xx ou 5xx)

        node_response = response.json()
        app.logger.info(f"[Flask Gateway] Resposta do Node.js: {node_response}")

        # Determinar o status da transação
        transaction_status = 'FAILED'
        if node_response.get('output_ResponseCode') == 'INS-0':
            transaction_status = 'SUCCESS'

        

        return jsonify(node_response), response.status_code

    except requests.exceptions.HTTPError as http_err:
        app.logger.error(f"[Flask Gateway] Erro HTTP ao chamar Node.js: {http_err}")
        return jsonify({"error": f"Erro na comunicação com o serviço de pagamento: {http_err}", "details": response.text if 'response' in locals() else 'N/A'}), response.status_code if 'response' in locals() else 500
    except requests.exceptions.ConnectionError as conn_err:
        app.logger.error(f"[Flask Gateway] Erro de Conexão ao chamar Node.js: {conn_err}")
        return jsonify({"error": f"Não foi possível conectar ao servidor de pagamento (Node.js): {conn_err}"}), 503
    except requests.exceptions.Timeout as timeout_err:
        app.logger.error(f"[Flask Gateway] Erro de Timeout ao chamar Node.js: {timeout_err}")
        return jsonify({"error": "O serviço de pagamento demorou muito para responder."}), 504
    except requests.exceptions.RequestException as req_err:
        app.logger.error(f"[Flask Gateway] Erro na Requisição ao chamar Node.js: {req_err}")
        return jsonify({"error": f"Erro desconhecido ao chamar o serviço de pagamento: {req_err}"}), 500



if __name__ == '__main__':
    # ATENÇÃO: Rodar com host='0.0.0.0' expõe o servidor a todas as interfaces de rede.
    # Isso é útil para testes em rede local, mas NÃO é recomendado para produção sem segurança.
    app.logger.warning("\n!!! ATENÇÃO: O servidor Flask será exposto em todas as interfaces de rede (0.0.0.0). !!!")
    app.logger.warning("!!! Isso NÃO é seguro para ambientes de produção sem as devidas medidas de segurança. !!!\n")
    app.run(host='0.0.0.0', port=8005)