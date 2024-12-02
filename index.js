const express = require("express");
const axios = require("axios");
require("dotenv").config();

const app = express();
const PORT = process.env.PORT || 8080;

// Middleware para parsear los cuerpos de las solicitudes
app.use(express.json());

// Ruta de verificación del webhook
// Ruta de verificación del webhook
app.get("/webhook", (req, res) => {
    const mode = req.query["hub.mode"];
    const token = req.query["hub.verify_token"];
    const challenge = req.query["hub.challenge"];
  
    console.log("Token recibido:", token);  // Log para ver el token que Facebook envió
    console.log("Challenge recibido:", challenge);  // Log para ver el challenge que Facebook envió
    console.log("Token esperado:", process.env.VERIFY_TOKEN);  // Log para ver el token que tenemos en el archivo .env
  
    if (mode && token) {
      if (token === process.env.VERIFY_TOKEN) {  // Compara el token recibido con el de .env
        res.status(200).send(challenge);  // Si coinciden, responde con el challenge
      } else {
        console.log("Token de verificación incorrecto");  // Log si los tokens no coinciden
        res.sendStatus(403);  // Responde con Forbidden si los tokens no coinciden
      }
    } else {
      console.log("Parámetros 'mode' o 'token' no encontrados en la solicitud.");
      res.sendStatus(400);  // Bad Request si no se encuentran los parámetros
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
  console.log("Token de verificación esperado:", process.env.VERIFY_TOKEN);

});
