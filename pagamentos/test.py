import requests
import json

url = 'http://127.0.0.1:8000/api/pagamento_mpesa/'

dados = {
    'numero_celular': '847519599',
    'valor': 1
}

headers = {
    'Content-Type': 'application/json'
}

resposta = requests.post(url, json=dados, headers=headers)

print(resposta.text)
