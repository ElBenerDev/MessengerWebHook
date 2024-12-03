import dotenv from 'dotenv';
import express from 'express';
import axios from 'axios';
import { OpenAI } from 'openai';

// Cargar las variables de entorno desde .env
dotenv.config();

// Inicializamos la app de Express
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

// Configurando el cliente de OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Función para enviar mensaje a Messenger
async function sendMessageToMessenger(recipientId, message) {
  const pageAccessToken = process.env.FACEBOOK_PAGE_ACCESS_TOKEN; // Usamos la nueva variable de entorno
  const pageId = process.env.PAGE_ID; // ID de la página

  const url = `https://graph.facebook.com/v12.0/${pageId}/messages?access_token=${pageAccessToken}`;

  const data = {
    recipient: {
      id: recipientId
    },
    message: {
      text: message
    }
  };

  try {
    const response = await axios.post(url, data);
    console.log("Mensaje enviado:", response.data);
  } catch (error) {
    console.error("Error al enviar mensaje a Messenger:", error.response ? error.response.data : error.message);
  }
}

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

    // Si se recibe un mensaje, procesamos la respuesta con el asistente de OpenAI
    try {
      const completion = await openai.chat.completions.create({
        model: 'gpt-4', // O el modelo que prefieras
        messages: [
          { role: 'user', content: receivedMessage }
        ]
      });

      const assistantMessage = completion.choices[0].message.content;
      console.log("Respuesta del asistente:", assistantMessage);

      // Enviar la respuesta generada al usuario en Messenger
      await sendMessageToMessenger(senderId, assistantMessage);

    } catch (error) {
      console.error("Error al interactuar con OpenAI:", error);
      await sendMessageToMessenger(senderId, "Lo siento, hubo un problema al procesar tu mensaje.");
    }
  }

  res.sendStatus(200); // Confirmamos la recepción del mensaje
});

// Iniciamos el servidor
app.listen(port, () => {
  console.log(`Servidor escuchando en puerto ${port}`);
});
