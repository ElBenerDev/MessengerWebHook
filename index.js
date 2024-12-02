require("dotenv").config();
const express = require("express");
const app = express();

const PORT = process.env.PORT || 8080;
console.log("VERIFY_TOKEN desde .env:", process.env.VERIFY_TOKEN);

// Middleware para parsear JSON
app.use(express.json());

// Ruta raíz para verificar que el servidor funciona
app.get("/", (req, res) => {
  res.send("Servidor de Messenger Webhook funcionando correctamente.");
});

// Ruta del webhook (verificación y recepción de eventos)
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
    console.error("Solicitud inválida. Faltan parámetros.");
    res.sendStatus(400);
  }
});

// Ruta para manejar eventos entrantes desde Facebook
app.post("/webhook", (req, res) => {
  const body = req.body;
  console.log("Evento recibido:", body);

  if (body.object === "page") {
    body.entry.forEach((entry) => {
      const webhookEvent = entry.messaging[0];
      console.log("Evento de mensajería:", webhookEvent);

      if (webhookEvent.message) {
        console.log("Mensaje recibido:", webhookEvent.message.text);
      }
    });

    res.status(200).send("EVENT_RECEIVED");
  } else {
    res.sendStatus(404);
  }
});

// Inicia el servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
