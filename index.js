import("dotenv").then(dotenv => dotenv.config());


// Carga las variables de entorno
console.log("Contenido del archivo .env:", process.env);


const express = require("express");
const app = express();

// Puerto configurado desde las variables de entorno o el predeterminado
const PORT = process.env.PORT || 8080;

// Logs iniciales para confirmar la carga de las variables de entorno
console.log("Configurando servidor...");
console.log("VERIFY_TOKEN desde .env:", process.env.VERIFY_TOKEN);
console.log("FB_PAGE_ACCESS_TOKEN desde .env:", process.env.FB_PAGE_ACCESS_TOKEN);

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

// Ruta para manejar mensajes enviados desde Facebook Messenger
app.post("/webhook", (req, res) => {
  console.log("Solicitud POST recibida en /webhook");
  console.log("Headers:", req.headers);
  console.log("Body:", req.body);

  const body = req.body;

  // Validar que la solicitud provenga de Messenger
  if (body.object === "page") {
    body.entry.forEach((entry) => {
      const webhookEvent = entry.messaging[0];
      console.log("Evento recibido:", webhookEvent);

      // Manejar mensajes aquí
      if (webhookEvent.message && webhookEvent.sender) {
        const senderId = webhookEvent.sender.id;
        const messageText = webhookEvent.message.text;

        console.log(`Mensaje recibido de ${senderId}: ${messageText}`);

        // Responder al usuario
        // Aquí podrías integrar OpenAI o alguna lógica para respuestas automatizadas
      }
    });

    // Responder a Facebook para confirmar recepción del evento
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
