from pprint import pprint
from portalsdk import APIContext, APIMethodType, APIRequest
import time
import uuid
import random
import string
import os
from dotenv import load_dotenv
import os

load_dotenv()



contexto_api = APIContext

def tratmento_erro (resultado):
    if resultado.status_code == 200:
        return 'Sucesso'
    
    if resultado.status_code == 201:
        return 'Sucesso'
    
    elif resultado.status_code == 400:
        return 'Verifique se os dados estão corretos'
    
    if resultado.status_code == 401:
        return 'O cliente cancelou a transação ou nao esta activo'
    
    if resultado.status_code == 500:
        return 'Verifique se o servidor está funcionando corretamente'
    
    if resultado.status_code == 408:
        return 'Tempo de resposta excedido'
    
    if resultado.status_code == 422:
        return 'Cliente nao tem saldo suficiente'
    





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



def mpesa (numero_celular, valor):
    contexto_api = APIContext()
    refenrenia = referencia_transacao()

    contexto_api.api_key = os.getenv('API_KEY')
    contexto_api.public_key = os.getenv('PUBLIC_KEY')
    contexto_api.ssl = True
    contexto_api.method_type = APIMethodType.POST
    contexto_api.address = 'api.sandbox.vm.co.mz'
    contexto_api.port = 18352
    contexto_api.path = '/ipg/v1x/c2bPayment/singleStage/'
    contexto_api.add_header('Origin', '*')
    contexto_api.add_parameter('input_TransactionReference', 'T12344C')
    contexto_api.add_parameter('input_CustomerMSISDN' ,str(numero_celular))
    contexto_api.add_parameter('input_Amount', str(valor))
    contexto_api.add_parameter('input_ThirdPartyReference', str(refenrenia))
    contexto_api.add_parameter('input_ServiceProviderCode', os.getenv('SERVICE_PROVIDER_CODE'))    

    try:
        resposta_api = APIRequest(contexto_api)
        resultado = resposta_api.execute()
    except Exception as e:
        print('Erro ao processar a transacao', e)
    
    return resultado


numero_celular = input('Digite o numero do celular ')
numero_certo = numero_normal(numero_celular)
print(numero_certo)


valor = input('Digite o valor da transacao ')
refenrenia = referencia_transacao()
print(refenrenia)

resultado = mpesa(numero_certo, valor)

ver_status = tratmento_erro(resultado)
print(ver_status)