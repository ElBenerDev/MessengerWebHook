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
  console.log("Solicitud POST recibida en /webhook");
  console.log("Headers:", req.headers); // Esto es para ver los headers, por si hay algo importante
  console.log("Body:", req.body); // Loguea el cuerpo de la solicitud para ver los mensajes

  const body = req.body;

  // Validar que la solicitud provenga de Messenger
  if (body.object === "page") {
    console.log("Evento recibido de una página de Facebook.");

    body.entry.forEach((entry) => {
      const webhookEvent = entry.messaging[0]; // El primer evento de la entrada
      console.log("Evento recibido:", webhookEvent);

      // Aquí deberías asegurarte de que los mensajes estén llegando
      if (webhookEvent.message && webhookEvent.sender) {
        const senderId = webhookEvent.sender.id;
        const messageText = webhookEvent.message.text;
        console.log(`Mensaje recibido de ${senderId}: ${messageText}`);

        // Responde al usuario si es necesario, por ejemplo con un mensaje fijo
        axios.post(`https://graph.facebook.com/v12.0/me/messages?access_token=${process.env.FB_PAGE_ACCESS_TOKEN}`, {
          recipient: { id: senderId },
          message: { text: "Gracias por tu mensaje, te responderé pronto." }
        }).then(response => {
          console.log("Mensaje enviado a usuario:", response.data);
        }).catch(error => {
          console.error("Error al enviar el mensaje:", error);
        });
      }
    });

    // Responder a Facebook para confirmar recepción del evento
    res.status(200).send("EVENT_RECEIVED");
  } else {
    console.error("Objeto no soportado recibido.");
    res.sendStatus(404);
  }
});

// Inicia el servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
