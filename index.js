import express from "express";
import dotenv from "dotenv";
import { getOpenAiResponse } from "./openaiClient.js";

dotenv.config();
const app = express();
const PORT = process.env.PORT || 8080;

// Middleware para parsear JSON
app.use(express.json());

// Ruta para manejar mensajes enviados desde Facebook Messenger
app.post("/webhook", async (req, res) => {
  console.log("Solicitud POST recibida en /webhook");
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

        // Aquí puedes implementar la lógica para enviar la respuesta de vuelta al usuario en Messenger
      }
    });

    res.status(200).send("EVENT_RECEIVED");
  } else {
    res.sendStatus(404);
  }
});

// Iniciar el servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
