// Carga las variables de entorno
import dotenv from "dotenv";
dotenv.config();

import express from "express";
import { getOpenAiResponse } from "./openaiClient.js";
import { sendMessageToMessenger } from "./messengerClient.js";

const app = express();
const PORT = process.env.PORT || 8080;

// Middleware para parsear JSON
app.use(express.json());

// Ruta de verificación de que el servidor funciona
app.get("/", (req, res) => {
  console.log("Solicitud recibida en la raíz '/'");
  res.send("Servidor de Messenger Webhook funcionando correctamente.");
});

// Ruta para validar el webhook
app.get("/webhook", (req, res) => {
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];

  console.log("Token recibido:", token);
  console.log("Challenge recibido:", challenge);
  console.log("Token esperado (VERIFY_TOKEN):", process.env.VERIFY_TOKEN);

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

// Ruta para manejar mensajes desde Facebook
app.post("/webhook", async (req, res) => {
  console.log("Solicitud POST recibida en /webhook");
  console.log("Body:", req.body);

  const body = req.body;

  if (body.object === "page") {
    body.entry.forEach(async (entry) => {
      const webhookEvent = entry.messaging[0];
      console.log("Evento recibido:", webhookEvent);

      if (webhookEvent.message && webhookEvent.sender) {
        const senderId = webhookEvent.sender.id;
        const userMessage = webhookEvent.message.text;

        console.log(`Mensaje recibido de ${senderId}: ${userMessage}`);

        // Obtener respuesta de OpenAI
        const assistantResponse = await getOpenAiResponse(userMessage);
        console.log(`Respuesta del asistente: ${assistantResponse}`);

        // Enviar respuesta al usuario en Messenger
        await sendMessageToMessenger(senderId, assistantResponse);
      }
    });

    res.status(200).send("EVENT_RECEIVED");
  } else {
    console.error("Objeto no soportado recibido.");
    res.sendStatus(404);
  }
});

// Iniciar el servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
