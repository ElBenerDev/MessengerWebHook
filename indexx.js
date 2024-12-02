require("dotenv").config();
const express = require("express");
const axios = require("axios");
const { getOpenAiResponse } = require("./openai");  // Importamos la función desde openai.js
const app = express();

const PORT = process.env.PORT || 8080;

// Logs iniciales
console.log("VERIFY_TOKEN desde .env:", process.env.VERIFY_TOKEN);

// Middleware para parsear JSON
app.use(express.json());

// Ruta para verificar que el servidor esté funcionando
app.get("/", (req, res) => {
  console.log("Solicitud recibida en la raíz '/'");
  res.send("Servidor de Messenger Webhook funcionando correctamente.");
});

// Ruta de verificación del webhook
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
    console.error("Parámetros inválidos en la solicitud.");
    res.sendStatus(400);
  }
});

// Ruta para manejar mensajes enviados desde Facebook Messenger
app.post("/webhook", async (req, res) => {  // Aquí agregamos `async` al principio
  console.log("Solicitud POST recibida en /webhook");
  console.log("Headers:", req.headers);
  console.log("Body:", req.body);

  const body = req.body;

  // Validar que la solicitud provenga de Messenger
  if (body.object === "page") {
    body.entry.forEach(async (entry) => {  // Hacemos también que la función de `forEach` sea async
      const webhookEvent = entry.messaging[0];
      console.log("Evento recibido:", webhookEvent);

      // Manejar mensajes aquí
      if (webhookEvent.message && webhookEvent.sender) {
        const senderId = webhookEvent.sender.id;
        const messageText = webhookEvent.message.text;

        console.log(`Mensaje recibido de ${senderId}: ${messageText}`);

        // Llamar a OpenAI para obtener una respuesta
        const openAiResponse = await getOpenAiResponse(messageText);

        // Responder al usuario con la respuesta de OpenAI
        sendMessageToFacebook(senderId, openAiResponse);
      }
    });

    // Responder a Facebook para confirmar recepción del evento
    res.status(200).send("EVENT_RECEIVED");
  } else {
    console.error("Objeto no soportado recibido.");
    res.sendStatus(404);
  }
});


// Función para enviar mensaje a través de la API de Messenger
const sendMessageToFacebook = (senderId, messageText) => {
  const url = `https://graph.facebook.com/v12.0/me/messages?access_token=${process.env.FB_PAGE_ACCESS_TOKEN}`;

  const body = {
    messaging_type: "RESPONSE",
    recipient: { id: senderId },
    message: { text: messageText },
  };

  axios
    .post(url, body)
    .then((response) => {
      console.log("Mensaje enviado a Facebook:", response.data);
    })
    .catch((error) => {
      console.error("Error al enviar mensaje a Facebook:", error);
    });
};

// Iniciar el servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
