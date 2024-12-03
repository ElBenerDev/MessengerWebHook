import express from 'express';
import bodyParser from 'body-parser';
import dotenv from 'dotenv';
import { interactWithAssistant } from './assistant.js';

// Cargar las variables de entorno desde el archivo .env
dotenv.config();

const app = express();
app.use(bodyParser.json());

// Endpoint para recibir mensajes
app.post('/webhook', async (req, res) => {
  const data = req.body;

  if (data.object === 'page') {
    data.entry.forEach(async (entry) => {
      const messagingEvent = entry.messaging[0];
      const senderId = messagingEvent.sender.id;
      const messageText = messagingEvent.message.text;

      console.log(`Mensaje recibido de ${senderId}: ${messageText}`);

      try {
        // Llamar a interactWithAssistant para obtener la respuesta del asistente
        const assistantResponse = await interactWithAssistant(messageText);

        // Enviar la respuesta al usuario
        await sendMessage(senderId, assistantResponse);

        res.sendStatus(200); // Responder con éxito
      } catch (error) {
        console.error('Error al interactuar con el asistente:', error);
        await sendMessage(senderId, 'Lo siento, hubo un problema al procesar tu mensaje.');
        res.sendStatus(500); // Error en el servidor
      }
    });
  } else {
    res.sendStatus(404); // No encontrado
  }
});

// Función para enviar mensajes a través de Messenger
async function sendMessage(senderId, text) {
  const PAGE_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;

  const messageData = {
    recipient: { id: senderId },
    message: { text: text },
  };

  try {
    const response = await fetch(`https://graph.facebook.com/v12.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(messageData),
    });

    if (!response.ok) {
      throw new Error(`Error al enviar mensaje: ${response.statusText}`);
    }

    console.log(`Mensaje enviado a ${senderId}: ${text}`);
  } catch (error) {
    console.error('Error al enviar mensaje a Messenger:', error);
  }
}

// Iniciar el servidor
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor corriendo en el puerto ${PORT}`);
});
