// Carga las variables de entorno
require("dotenv").config();
const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;
const PAGE_ACCESS_TOKEN = process.env.FB_PAGE_ACCESS_TOKEN;

// Middleware para parsear JSON
app.use(express.json());

// Función para enviar mensajes a Messenger
async function sendMessage(senderId, message) {
    const url = `https://graph.facebook.com/v15.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`;
    const payload = {
        recipient: { id: senderId },
        message: { text: message }
    };

    try {
        await axios.post(url, payload);
        console.log(`Mensaje enviado a ${senderId}: ${message}`);
    } catch (error) {
        console.error("Error al enviar el mensaje:", error.response?.data || error.message);
    }
}

// Ruta para manejar la verificación del webhook
app.get("/webhook", (req, res) => {
    const VERIFY_TOKEN = process.env.VERIFY_TOKEN;
    const mode = req.query["hub.mode"];
    const token = req.query["hub.verify_token"];
    const challenge = req.query["hub.challenge"];

    if (mode && token === VERIFY_TOKEN) {
        res.status(200).send(challenge);
    } else {
        res.sendStatus(403);
    }
});

// Ruta para manejar mensajes desde Messenger
app.post("/webhook", async (req, res) => {
    const body = req.body;

    if (body.object === "page") {
        body.entry.forEach(async (entry) => {
            const webhookEvent = entry.messaging[0];

            if (webhookEvent.message && webhookEvent.sender) {
                const senderId = webhookEvent.sender.id;
                const userMessage = webhookEvent.message.text;

                console.log(`Mensaje recibido de ${senderId}: ${userMessage}`);

                try {
                    // Enviar mensaje al API del asistente
                    const response = await axios.post("http://localhost:5000/process_message", {
                        message: userMessage
                    });

                    const assistantReply = response.data.response;

                    console.log(`Respuesta del asistente: ${assistantReply}`);

                    // Enviar respuesta al usuario en Messenger
                    await sendMessage(senderId, assistantReply);
                } catch (error) {
                    console.error("Error al interactuar con el asistente:", error.message);
                }
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
