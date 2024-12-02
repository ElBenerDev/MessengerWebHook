const express = require("express");
const axios = require("axios");
require("dotenv").config();

const app = express();
const PORT = process.env.PORT || 8080;

// Middleware para parsear cuerpos JSON
app.use(express.json());

// Middleware para logs detallados
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  console.log("Headers:", req.headers);
  console.log("Body:", req.body);
  next();
});

// Ruta raíz para verificar que el servidor está funcionando
app.get("/", (req, res) => {
  res.send("Servidor de Messenger Webhook funcionando correctamente.");
});

// Ruta de verificación del webhook de Facebook
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
      res.sendStatus(403); // Forbidden
    }
  } else {
    console.error("Parámetros inválidos en la solicitud de verificación.");
    res.sendStatus(400); // Bad Request
  }
});

// Ruta para recibir mensajes de Facebook
app.post("/webhook", (req, res) => {
  console.log("Evento recibido en /webhook POST");
  const body = req.body;

  // Verifica que la solicitud proviene de Facebook
  if (body.object === "page") {
    body.entry.forEach((entry) => {
      const webhook_event = entry.messaging[0];
      console.log("Evento de mensajería recibido:", webhook_event);

      const sender_psid = webhook_event.sender.id;
      if (webhook_event.message) {
        const userMessage = webhook_event.message.text;
        console.log(`Mensaje recibido del usuario (${sender_psid}): ${userMessage}`);
        handleMessage(sender_psid, userMessage);
      }
    });

    // Devuelve una respuesta '200 OK' para confirmar la recepción del evento
    res.status(200).send("EVENT_RECEIVED");
  } else {
    console.error("Objeto no reconocido:", body.object);
    res.sendStatus(404); // Not Found
  }
});

// Manejo de mensajes del usuario
function handleMessage(sender_psid, received_message) {
  // Respuesta simple de ejemplo
  const response = { text: `¡Hola! Recibí tu mensaje: "${received_message}"` };

  // Llamada para enviar el mensaje de vuelta al usuario
  callSendAPI(sender_psid, response);
}

// Envío de mensajes a través de la API de Facebook
function callSendAPI(sender_psid, response) {
  const PAGE_ACCESS_TOKEN = process.env.FB_PAGE_ACCESS_TOKEN;

  const request_body = {
    recipient: { id: sender_psid },
    message: response,
  };

  axios
    .post(`https://graph.facebook.com/v12.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`, request_body)
    .then(() => {
      console.log(`Mensaje enviado al usuario (${sender_psid}) exitosamente.`);
    })
    .catch((error) => {
      console.error("Error al enviar el mensaje:", error.response?.data || error.message);
    });
}

// Inicia el servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
