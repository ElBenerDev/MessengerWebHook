require('dotenv').config();
const express = require('express');
const axios = require('axios');
const { OpenAI } = require('openai');
const { AssistantEventHandler } = require('openai');  // Usando require
const { override } = require('typing_extensions');  // Usando require

// Inicializamos la app de Express
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

// Configuración del cliente de OpenAI
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Crear un asistente y un hilo de conversación
let thread;
client.beta.threads.create().then((createdThread) => {
  thread = createdThread;
  console.log("Hilo creado:", thread);
}).catch((err) => {
  console.error("Error al crear el hilo:", err);
});

// Función para enviar mensaje a Messenger
async function sendMessageToMessenger(recipientId, message) {
  const pageAccessToken = process.env.PAGE_ACCESS_TOKEN; // Cargado desde .env
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
      // Usamos el método streaming de OpenAI para obtener una respuesta en tiempo real
      class EventHandler extends AssistantEventHandler {
        onTextCreated(text) {
          console.log(`Asistente: ${text.value}`);
        }

        onTextDelta(delta) {
          console.log(delta.value);
        }
      }

      const eventHandler = new EventHandler();

      // Enviar el mensaje del usuario al hilo de OpenAI
      await client.beta.threads.messages.create({
        thread_id: thread.id,
        role: 'user',
        content: receivedMessage,
      });

      // Crear y manejar la respuesta del asistente en tiempo real
      const stream = client.beta.threads.runs.stream({
        thread_id: thread.id,
        assistant_id: 'asst_Q3M9vDA4aN89qQNH1tDXhjaE', // ID del asistente
        event_handler: eventHandler,
      });

      await stream.until_done();

      // Enviar la respuesta generada del asistente a Messenger
      const assistantMessage = stream.messages.join(" ");  // Tomamos las respuestas generadas
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
