import 'dotenv/config';  // Cargar variables de entorno desde el archivo .env
import express from 'express';
import bodyParser from 'body-parser';
import axios from 'axios';
import { OpenAI } from 'openai';  // Importar la clase OpenAI

// Configuración de OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,  // Cargar API Key desde el archivo .env
});

// Configuración de Facebook
const PAGE_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN; // Token de acceso a la página de Facebook
const VERIFY_TOKEN = process.env.FACEBOOK_VERIFY_TOKEN;  // Token de verificación

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

      // Crear un hilo de conversación con el asistente de OpenAI
      try {
        const assistantId = 'asst_Q3M9vDA4aN89qQNH1tDXhjaE';  // Usar el ID de tu asistente
        const thread = await openai.chat.threads.create();

        // Enviar el mensaje del usuario al hilo
        const userMessage = await openai.chat.messages.create({
          thread_id: thread.id,
          role: 'user',
          content: messageText,
        });

        console.log(`Mensaje enviado al hilo: ${userMessage.content}`);

        // Crear y manejar la respuesta del asistente en el flujo
        const responseStream = openai.chat.threads.stream({
          thread_id: thread.id,
          assistant_id: assistantId,
          event_handler: new EventHandler(senderId),  // Pasar el senderId al manejador de eventos
        });

        // Escuchar las respuestas del asistente
        for await (const message of responseStream) {
          // Se procesa la respuesta cuando llega
          if (message.role === 'assistant') {
            console.log(`Asistente: ${message.content}`);
            await sendMessage(senderId, message.content);  // Enviar respuesta al usuario
          }
        }

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

// Clase para manejar los eventos de respuesta del asistente (simula la parte de streaming)
class EventHandler {
  constructor(senderId) {
    this.senderId = senderId;
  }

  // Maneja el texto generado por el asistente
  on_text_created(text) {
    console.log(`Respuesta del asistente: ${text}`);
  }

  // Maneja los cambios en el texto generado por el asistente (streaming)
  on_text_delta(delta) {
    console.log(delta.value);  // Imprime los cambios del texto
  }

  // Enviar un mensaje cuando la respuesta está lista
  on_done() {
    sendMessage(this.senderId, '¡Gracias por esperar! Estoy aquí para ayudarte.');
  }
}

// Iniciar servidor en el puerto 3000
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor corriendo en el puerto ${PORT}`);
});
