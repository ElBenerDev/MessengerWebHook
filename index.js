require('dotenv').config(); // Cargar variables de entorno desde el archivo .env
const express = require('express');
const bodyParser = require('body-parser');
const assistant = require('./assistant'); // Importar el módulo del asistente

const app = express();
app.use(bodyParser.json());

// Endpoint de verificación de webhook
app.get('/webhook', (req, res) => {
  const mode = req.query['hub.mode'];
  const token = req.query['hub.verify_token'];
  const challenge = req.query['hub.challenge'];

  if (mode && token) {
    if (token === process.env.FACEBOOK_VERIFY_TOKEN) {
      res.status(200).send(challenge); // Verificar el webhook
    } else {
      res.sendStatus(403); // Token de verificación incorrecto
    }
  }
});

// Endpoint para recibir los mensajes
app.post('/webhook', (req, res) => {
  assistant.handleMessage(req, res); // Delegar la lógica del asistente
});

// Iniciar servidor en el puerto 3000
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor corriendo en el puerto ${PORT}`);
});
