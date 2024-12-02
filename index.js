const express = require("express");
const axios = require("axios");
require("dotenv").config();

const app = express();
const PORT = process.env.PORT || 8080;

// Middleware para parsear los cuerpos de las solicitudes
app.use(express.json());

// Ruta de verificación del webhook
app.get("/webhook", (req, res) => {
  // Extraer los parámetros enviados por Facebook
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];

  // Agregar logs para verificar los valores de los parámetros
  console.log("Modo recibido:", mode);  // Debería ser 'subscribe'
  console.log("Token recibido:", token);  // El token enviado por Facebook
  console.log("Token esperado:", process.env.VERIFY_TOKEN);  // El token que has configurado en .env
  console.log("Challenge recibido:", challenge);  // El challenge que Facebook envía

  // Verificar que el token recibido coincida con el que tenemos en el archivo .env
  if (mode && token && token === process.env.VERIFY_TOKEN) {
    console.log("Token de verificación correcto");  // Si el token es correcto
    res.status(200).send(challenge);  // Enviar el challenge de vuelta a Facebook
  } else {
    console.log("Token de verificación incorrecto");  // Si el token no coincide
    res.sendStatus(403);  // Si el token no coincide, responder con 403 (Forbidden)
  }
});

// Ruta para recibir los mensajes
app.post("/webhook", (req, res) => {
  const messaging_events = req.body.entry[0].messaging;

  // Revisar si los mensajes están llegando correctamente
  console.log("Evento recibido:", messaging_events);

  messaging_events.forEach((event) => {
    if (event.message) {
      const sender = event.sender.id;
      const text = event.message.text;

      // Llamar a OpenAI para obtener una respuesta
      axios
        .post("https://api.openai.com/v1/completions", {
          model: "text-davinci-003",
          prompt: text,
          max_tokens: 150,
        }, {
          headers: {
            "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
            "Content-Type": "application/json",
          }
        })
        .then((response) => {
          // Log para verificar la respuesta de OpenAI
          console.log("Respuesta de OpenAI:", response.data.choices[0].text.trim());

          // Enviar la respuesta de OpenAI al usuario de Messenger
          axios.post(`https://graph.facebook.com/v12.0/me/messages?access_token=${process.env.FB_PAGE_ACCESS_TOKEN}`, {
            recipient: { id: sender },
            message: { text: response.data.choices[0].text.trim() }
          });
        })
        .catch((error) => {
          console.error("Error al contactar con OpenAI:", error);  // Log de error si falla la llamada a OpenAI
        });
    }
  });

  // Responder a Facebook para indicar que hemos recibido el evento
  res.status(200).send("EVENT_RECEIVED");
});

// Iniciar el servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
