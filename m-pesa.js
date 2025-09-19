const mpesaConfig = require("./mpesa.json");
const MpesaAPI = require("mpesa-api-nodejs");

// Configuração base
const api_key = mpesaConfig.api_key;
const public_key = mpesaConfig.public_key;
const environment = "production"; // ou "development"
const ssl = true;

// Função fábrica para garantir cliente independente por chamada
function createMpesaClient() {
  return MpesaAPI.init(api_key, public_key, environment, ssl);
}

async function payMpesa(phone, value, reference, options = {}) {
  const {
    timeoutMs = 30000,
    attempts = 3,
    backoffBaseMs = 500
  } = options;

  const data = {
    value,
    client_number: phone,
    agent_id: mpesaConfig.shortcode,
    transaction_reference: reference,
    third_party_reference: reference
  };

  let lastError = null;

  for (let attempt = 1; attempt <= attempts; attempt++) {
    const mpesa = createMpesaClient(); // Cliente novo por tentativa

    try {
      // Timeout controlado por Promise.race
      const result = await Promise.race([
        mpesa.c2b(data),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("timeout")), timeoutMs)
        )
      ]);

      console.log(`[M-Pesa][Tentativa ${attempt}] Sucesso:`, result);
      return result;
    } catch (err) {
      lastError = err;
      console.error(`[M-Pesa][Tentativa ${attempt}] Erro:`, err.message);

      if (err.message !== "timeout" && attempt === attempts) {
        return { error: err.message || "Erro ao processar pagamento", output_ResponseCode: "INS-1" };
      }
    }

    // Espera antes de tentar de novo
    if (attempt < attempts) {
      const delay = backoffBaseMs * Math.pow(2, attempt - 1);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  return { error: lastError?.message || "Erro desconhecido", output_ResponseCode: "INS-9" };
}

module.exports = { payMpesa };

