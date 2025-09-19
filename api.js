const express = require('express');
const timeout = require('connect-timeout');
const { payMpesa } = require('./m-pesa.js');

const app = express();

// Middleware para parar execução se já passou do timeout
function haltOnTimedout(req, res, next) {
  if (!req.timedout) next();
}

app.use(timeout('60s')); // Timeout global para rota
app.use(express.json());
app.use(haltOnTimedout);

app.post('/pagar', async (req, res) => {
  const { phone, value, reference } = req.body;
  console.log(`[${new Date().toISOString()}] Nova requisição:`, req.body);

  // Validações
  if (!phone || !value || !reference) {
    return res.status(400).json({ error: 'Campos phone, value e reference são obrigatórios.' });
  }
  if (!/^(258)?(8[45])\d{7}$/.test(phone)) {
    return res.status(400).json({ error: 'Número de telefone inválido.' });
  }
  if (typeof value !== 'number' || value <= 0) {
    return res.status(400).json({ error: 'O valor deve ser um número positivo.' });
  }

  try {
    // Chamando payMpesa com timeout e retry
    const result = await payMpesa(phone, value, reference, {
      timeoutMs: 20000, // 20s por tentativa
      attempts: 2,      // tenta no máximo 2 vezes
      backoffBaseMs: 500
    });

    if (req.timedout) return; // evita enviar resposta depois do timeout

    if (result.error) {
      return res.status(500).json(result);
    }

    return res.json(result);
  } catch (error) {
    if (req.timedout) return;
    console.error(`[${new Date().toISOString()}] Erro inesperado:`, error);
    res.status(500).json({ error: 'Erro interno do servidor.' });
  }
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`Servidor rodando na porta ${PORT}`);
});

