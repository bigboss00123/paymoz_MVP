

*   **URL:** `/api/pagamento_mpesa/`
*   **Método:** `POST`
*   **Descrição:** Inicia uma transação C2B (pagamento do consumidor para a empresa).
*   **Parâmetros de Requisição (JSON):**
    *   `numero_celular` (string, obrigatório): O número de celular do consumidor (9 dígitos).
    *   `valor` (número, obrigatório): O valor da transação.
*   **Exemplo de Requisição:**
    ```json
    {
        "numero_celular": "841234567",
        "valor": 100.50
    }
    ```
*   **Exemplo de Resposta (Sucesso - Status 200 OK / 201 Created):**
    ```json
    {
        "output_ConversationID": "ws_CO_26072025123456789",
        "output_ResponseCode": "0",
        "output_ResponseDesc": "Request processed successfully",
        "output_TransactionID": "ABCDEF12345"
    }
    ```
    *(A estrutura exata da resposta pode variar dependendo da API M-Pesa real.)*
*   **Exemplo de Resposta (Falha - Status 400 Bad Request / 500 Internal Server Error):**
    ```json
    {
        "erro": "Mensagem de erro específica"
    }
    ```

### Pagamento B2C (Business-to-Consumer)

*   **URL:** `/api/pagamento_b2c/`
*   **Método:** `POST`
*   **Descrição:** Inicia uma transação B2C (pagamento da empresa para o consumidor). Inclui validação de saldo.
*   **Parâmetros de Requisição (JSON):**
    *   `numero_celular` (string, obrigatório): O número de celular do destinatário (9 dígitos).
    *   `valor` (número, obrigatório): O valor da transação.
*   **Exemplo de Requisição:**
    ```json
    {
        "numero_celular": "849876543",
        "valor": 50.00
    }
    ```
*   **Exemplo de Resposta (Sucesso - Status 200 OK / 201 Created):**
    ```json
    {
        "output_ConversationID": "ws_CO_26072025123456789",
        "output_ResponseCode": "0",
        "output_ResponseDesc": "Request processed successfully",
        "output_TransactionID": "ABCDEF12345"
    }
    ```
    *(A estrutura exata da resposta pode variar dependendo da API M-Pesa real.)*
*   **Exemplo de Resposta (Saldo Insuficiente - Status 400 Bad Request):**
    ```json
    {
        "erro": "Saldo insuficiente para realizar a transferência. Saldo atual: 123.45 MZN"
    }
    ```
*   **Exemplo de Resposta (Falha - Status 400 Bad Request / 500 Internal Server Error):**
    ```json
    {
        "erro": "Mensagem de erro específica"
    }
    ```

## Dashboard

*   **URL:** `/api/dashboard/`
*   **Método:** `GET`
*   **Descrição:** Exibe o dashboard com um resumo das transações (entradas, saídas, saldo, erros, últimas transações). Requer autenticação.
*   **Parâmetros de Requisição:** Nenhum.
*   **Resposta:** Renderiza uma página HTML com os dados do dashboard.

### Listar Todas as Transações

*   **URL:** `/api/all_transactions/`
*   **Método:** `GET`
*   **Descrição:** Retorna uma lista de todas as transações registradas no sistema. Requer autenticação.
*   **Parâmetros de Requisição:** Nenhum.
*   **Exemplo de Resposta (Sucesso - Status 200 OK):**
    ```json
    [
        {
            "tipo_transacao": "C2B",
            "numero_celular": "841234567",
            "valor": "100.50",
            "status": "SUCESSO",
            "criado_em": "26/07/2025 10:30",
            "mensagem_erro": null
        },
        {
            "tipo_transacao": "B2C",
            "numero_celular": "849876543",
            "valor": "50.00",
            "status": "FALHA",
            "criado_em": "26/07/2025 11:00",
            "mensagem_erro": "Saldo insuficiente"
        }
    ]
    ```

## Proteção contra Força Bruta

A API de login (`/api/login/`) implementa um mecanismo de limitação de taxa para proteger contra ataques de força bruta.

*   **Limite:** `MAX_LOGIN_ATTEMPTS` (atualmente 5 tentativas)
*   **Tempo de Bloqueio:** `BLOCK_TIME` (atualmente 300 segundos = 5 minutos)

Se um endereço IP ou um e-mail específico exceder o número máximo de tentativas de login falhas dentro do `BLOCK_TIME`, futuras tentativas desse IP/e-mail serão bloqueadas por esse período, retornando um status `429 Too Many Requests`.
