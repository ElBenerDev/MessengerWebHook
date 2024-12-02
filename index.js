require("dotenv").config();
const express = require("express");
const axios = require("axios");
const { getAssistantResponse } = require("./assistant"); // Importar la lógica de OpenAI
const app = express();

const PORT = process.env.PORT || 8080;

console.log("VERIFY_TOKEN desde .env:", process.env.VERIFY_TOKEN);

app.use(express.json());

// Ruta raíz para probar que el servidor está funcionando
app.get("/", (req, res) => {
  console.log("Solicitud recibida en la raíz '/'");
  res.send("Servidor de Messenger Webhook funcionando correctamente.");
});

// Ruta para verificar el webhook de Facebook
app.get("/webhook", (req, res) => {
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];

  console.log("Token recibido:", token);
  console.log("Challenge recibido:", challenge);
  console.log("Token esperado:", process.env.VERIFY_TOKEN);

  if (mode && token) {
    if (token === process.env.VERIFY_TOKEN) {
      console.log("Token de verificación correcto.");
      res.status(200).send(challenge);
    } else {
      console.error("Token de verificación incorrecto.");
      res.sendStatus(403);
    }
  } else {
    console.error("Parámetros inválidos.");
    res.sendStatus(400);
  }
});

// Ruta para manejar los mensajes recibidos desde Messenger
app.post("/webhook", async (req, res) => {
  console.log("Solicitud POST recibida en /webhook");
  const body = req.body;

  if (body.object === "page") {
    body.entry.forEach(async (entry) => {
      const webhookEvent = entry.messaging[0];
      console.log("Evento recibido:", webhookEvent);

      if (webhookEvent.message && webhookEvent.sender) {
        const senderId = webhookEvent.sender.id;
        const messageText = webhookEvent.message.text;

        console.log(`Mensaje recibido de ${senderId}: ${messageText}`);

        // Obtener respuesta del asistente personalizado
        const assistantResponse = await getAssistantResponse(messageText);
        console.log("Respuesta del asistente:", assistantResponse);

        // Enviar la respuesta al usuario de Messenger
        await sendMessageToMessenger(senderId, assistantResponse);
      }
    });

    res.status(200).send("EVENT_RECEIVED");
  } else {
    console.error("Objeto no soportado recibido.");
    res.sendStatus(404);
  }
});

// Función para enviar un mensaje a Messenger
async function sendMessageToMessenger(senderId, messageText) {
  const requestBody = {
    recipient: { id: senderId },
    message: { text: messageText },
  };

  try {
    await axios.post(`https://graph.facebook.com/v15.0/me/messages?access_token=${process.env.FB_PAGE_ACCESS_TOKEN}`, requestBody);
    console.log(`Mensaje enviado a ${senderId}: ${messageText}`);
  } catch (error) {
    console.error("Error al enviar mensaje a Messenger:", error.message);
  }
}

app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
