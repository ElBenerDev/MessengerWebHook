import dotenv from 'dotenv';
import express from 'express';
import axios from 'axios';

// Cargar las variables de entorno desde .env
dotenv.config();

const app = express();
const port = process.env.PORT || 10000; // Render expone el puerto 10000
const pythonServiceUrl = 'http://localhost:5000'; // Usar localhost para el servicio Python

app.use(express.json());

// Webhook de verificación de Messenger
app.get('/webhook', (req, res) => {
  const VERIFY_TOKEN = process.env.VERIFY_TOKEN;
  const mode = req.query['hub.mode'];
  const token = req.query['hub.verify_token'];
  const challenge = req.query['hub.challenge'];

  if (mode && token) {
    if (mode === 'subscribe' && token === VERIFY_TOKEN) {
      console.log('Webhook verificado');
      res.status(200).send(challenge);
    } else {
      console.error('Token de verificación incorrecto');
      res.sendStatus(403);
    }
  }
});

// Webhook para recibir mensajes
app.post('/webhook', async (req, res) => {
  const messagingEvents = req.body.entry[0].messaging;

  for (let i = 0; i < messagingEvents.length; i++) {
    const event = messagingEvents[i];
    const senderId = event.sender.id;
    const receivedMessage = event.message.text;

    console.log(`Mensaje recibido de ${senderId}: ${receivedMessage}`);

    try {
      const response = await axios.post(`${pythonServiceUrl}/generate-response`, {
        message: receivedMessage
      });

      const assistantMessage = response.data.response;
      await sendMessageToMessenger(senderId, assistantMessage);
    } catch (error) {
      console.error("Error al interactuar con OpenAI:", error);
      await sendMessageToMessenger(senderId, "Lo siento, hubo un problema al procesar tu mensaje.");
    }
  }

  res.sendStatus(200);
});

// Define la función sendMessageToMessenger
async function sendMessageToMessenger(recipientId, message) {
    console.log(`Enviando mensaje a ${recipientId}: ${message}`);
    // Aquí deberías implementar la llamada a la API de Messenger
}

// Iniciamos el servidor
app.listen(port, () => {
  console.log(`Servidor escuchando en puerto ${port}`);
});