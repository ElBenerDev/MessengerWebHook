require('dotenv').config();  // Cargar variables de entorno desde el archivo .env
const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const OpenAI = require('openai');  // Para interactuar con OpenAI

// Configuración de OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
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

      // Interactuar con OpenAI usando el código que proporcionaste
      try {
        // Crear un hilo con el asistente
        const assistantId = 'asst_Q3M9vDA4aN89qQNH1tDXhjaE';  // Usar el ID de tu asistente
        const thread = await openai.chat.completions.create({
          model: 'gpt-4',  // Usar el modelo correcto
          messages: [
            { role: 'user', content: messageText },
          ],
        });

        const assistantResponse = thread.choices[0].message.content;

        console.log(`Respuesta del asistente: ${assistantResponse}`);

        // Enviar la respuesta al usuario a través de Messenger
        await sendMessage(senderId, assistantResponse);

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
    await axios.post(`https://graph.facebook.com/v12.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`, messageData);
    console.log(`Mensaje enviado a ${senderId}: ${text}`);
  } catch (error) {
    console.error('Error al enviar mensaje a Messenger:', error);
  }
}

// Iniciar servidor en el puerto 3000
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor corriendo en el puerto ${PORT}`);
});
