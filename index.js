import 'dotenv/config';  // Cargar variables de entorno desde el archivo .env
import express from 'express';
import bodyParser from 'body-parser';
import axios from 'axios';
import { OpenAI } from 'openai';  // Importar la clase OpenAI
import { AssistantEventHandler } from 'openai';  // Importar el manejador de eventos

// Configuración de OpenAI
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,  // Cargar API Key desde el archivo .env
});

// Configuración de Facebook
const PAGE_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN; // Token de acceso a la página de Facebook
const VERIFY_TOKEN = process.env.FACEBOOK_VERIFY_TOKEN;  // Token de verificación

// Crear un asistente y un hilo de conversación
const assistant_id = "asst_Q3M9vDA4aN89qQNH1tDXhjaE";  // Usar el ID de tu asistente
let thread;

client.beta.threads.create().then((createdThread) => {
  thread = createdThread;
  console.log("Hilo creado:", thread);
}).catch((err) => {
  console.error("Error al crear el hilo:", err);
});

const app = express();
app.use(bodyParser.json());

// Endpoint de verificación de webhook
app.get('/webhook', (req, res) => {
  const mode = req.query['hub.mode'];
  const token = req.query['hub.verify_token'];
  const challenge = req.query['hub.challenge'];

  if (mode && token) {
    if (token === VERIFY_TOKEN) {
      res.status(200).send(challenge);  // Verificar el webhook
    } else {
      res.sendStatus(403);  // Token de verificación incorrecto
    }
  }
});

// Endpoint para recibir los mensajes
app.post('/webhook', async (req, res) => {
  const data = req.body;
  if (data.object === 'page') {
    data.entry.forEach(async (entry) => {
      const messagingEvent = entry.messaging[0];
      const senderId = messagingEvent.sender.id;
      const messageText = messagingEvent.message.text;

      console.log(`Mensaje recibido de ${senderId}: ${messageText}`);

      // Enviar mensaje al hilo con OpenAI
      try {
        // Crear y manejar la respuesta del asistente
        await sendMessageToAssistant(senderId, messageText);
        
        res.sendStatus(200);  // Responder con éxito
      } catch (error) {
        console.error('Error al interactuar con OpenAI:', error);
        await sendMessage(senderId, 'Lo siento, hubo un problema al procesar tu mensaje.');
        res.sendStatus(500);  // Error en el servidor
      }
    });
  } else {
    res.sendStatus(404);  // No encontrado
  }
});

// Función para interactuar con OpenAI
async function sendMessageToAssistant(senderId, userMessage) {
  // Enviar mensaje del usuario al hilo de OpenAI
  await client.beta.threads.messages.create({
    thread_id: thread.id,
    role: 'user',
    content: userMessage
  });

  // Crear un manejador de eventos para manejar las respuestas
  class EventHandler extends AssistantEventHandler {
    on_text_created(text) {
      // Este evento se dispara cuando se crea texto en el flujo
      console.log(`Asistente: ${text.value}`);
      sendMessage(senderId, text.value);  // Enviar respuesta al usuario
    }

    on_text_delta(delta, snapshot) {
      // Este evento se dispara cuando el texto cambia o se agrega en el flujo
      console.log(delta.value);
      sendMessage(senderId, delta.value);  // Enviar respuesta al usuario
    }
  }

  // Usar el flujo para recibir respuestas del asistente
  const eventHandler = new EventHandler();

  // Crear y manejar la respuesta del asistente
  try {
    const stream = await client.beta.threads.runs.stream({
      thread_id: thread.id,
      assistant_id: assistant_id,
      event_handler: eventHandler
    });
    await stream.until_done();
  } catch (error) {
    console.error("Error al recibir respuesta del asistente:", error);
  }
}

// Función para enviar mensajes a través de Messenger
async function sendMessage(senderId, text) {
  const messageData = {
    recipient: { id: senderId },
    message: { text: text },
  };

  try {
    // Enviar la solicitud a la API de Facebook Messenger
    const response = await axios.post(
      `https://graph.facebook.com/v12.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`,
      messageData
    );
    console.log(`Mensaje enviado a ${senderId}: ${text}`);
  } catch (error) {
    console.error('Error al enviar mensaje a Messenger:', error.response ? error.response.data : error.message);
  }
}

// Iniciar servidor en el puerto 3000
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor corriendo en el puerto ${PORT}`);
});
