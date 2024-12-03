const axios = require('axios');
const { OpenAI } = require('openai');

// Configuración de OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY, // Cargar API Key desde el archivo .env
});

// Token de acceso a la página de Facebook
const PAGE_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;

// Función para manejar mensajes entrantes
async function handleMessage(req, res) {
  const data = req.body;

  if (data.object === 'page') {
    data.entry.forEach(async (entry) => {
      const messagingEvent = entry.messaging[0];
      const senderId = messagingEvent.sender.id;
      const messageText = messagingEvent.message.text;

      console.log(`Mensaje recibido de ${senderId}: ${messageText}`);

      try {
        // Crear un hilo de conversación con OpenAI
        const thread = await openai.chat.completions.create({
          model: 'gpt-4', // Usar el modelo correcto
          messages: [{ role: 'user', content: messageText }],
        });

        const assistantResponse = thread.choices[0].message.content;
        console.log(`Respuesta del asistente: ${assistantResponse}`);

        // Enviar la respuesta al usuario a través de Messenger
        await sendMessage(senderId, assistantResponse);

        res.sendStatus(200); // Responder con éxito
      } catch (error) {
        console.error('Error al interactuar con OpenAI:', error);
        await sendMessage(senderId, 'Lo siento, hubo un problema al procesar tu mensaje.');
        res.sendStatus(500); // Error en el servidor
      }
    });
  } else {
    res.sendStatus(404); // No encontrado
  }
}

// Función para enviar mensajes a través de Messenger
async function sendMessage(senderId, text) {
  const messageData = {
    recipient: { id: senderId },
    message: { text: text },
  };

  try {
    const response = await axios.post(
      `https://graph.facebook.com/v12.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`,
      messageData
    );
    console.log(`Mensaje enviado a ${senderId}: ${text}`);
  } catch (error) {
    console.error('Error al enviar mensaje a Messenger:', error.response ? error.response.data : error.message);
  }
}

module.exports = { handleMessage };
