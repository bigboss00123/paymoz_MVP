import requests
import json

url = 'http://5.189.144.249:8005/api/pagamento_mpesa/'

dados = {
    'numero_celular': '843550143',
    'valor': 10
}

headers = {
    'Content-Type': 'application/json'
}

resposta = requests.post(url, json=dados, headers=headers)

print(resposta.text)