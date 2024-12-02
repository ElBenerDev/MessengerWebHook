const express = require("express");
const axios = require("axios");
require("dotenv").config();

const app = express();
const PORT = process.env.PORT || 8080;

// Middleware para parsear los cuerpos de las solicitudes
app.use(express.json());

// Ruta de verificación del webhook
app.get("/webhook", (req, res) => {
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];

  if (mode && token) {
    if (token === process.env.VERIFY_TOKEN) {
      res.status(200).send(challenge);
    } else {
      res.sendStatus(403);
    }
  }
});

// Ruta para recibir los mensajes
app.post("/webhook", (req, res) => {
  const messaging_events = req.body.entry[0].messaging;

  messaging_events.forEach((event) => {
    if (event.message) {
      const sender = event.sender.id;
      const text = event.message.text;

      // Llama a OpenAI para obtener la respuesta
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
          // Envía la respuesta de OpenAI al usuario de Messenger
          axios.post(`https://graph.facebook.com/v12.0/me/messages?access_token=${process.env.FB_PAGE_ACCESS_TOKEN}`, {
            recipient: { id: sender },
            message: { text: response.data.choices[0].text.trim() }
          });
        })
        .catch((error) => console.error("Error al contactar con OpenAI:", error));
    }
  });

  res.status(200).send("EVENT_RECEIVED");
});

// Ruta para manejar la autenticación de Google OAuth
app.get("/callback", (req, res) => {
  // Aquí puedes manejar el intercambio del código de Google OAuth por un token de acceso
  const code = req.query.code;
  
  if (code) {
    axios.post('https://oauth2.googleapis.com/token', {
      code: code,
      client_id: process.env.GOOGLE_CLIENT_ID,
      client_secret: process.env.GOOGLE_CLIENT_SECRET,
      redirect_uri: process.env.REDIRECT_URI,
      grant_type: 'authorization_code',
    })
    .then(response => {
      // Aquí puedes guardar el token y usarlo para acceder a la API de Google
      console.log('Token de acceso:', response.data.access_token);
      res.send('Autenticación exitosa');
    })
    .catch(error => {
      console.error('Error al intercambiar el código de Google:', error);
      res.send('Error en la autenticación');
    });
  } else {
    res.send('Falta el código de autenticación');
  }
});

// Inicia el servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
