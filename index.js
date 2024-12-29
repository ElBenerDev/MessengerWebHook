import dotenv from 'dotenv';
import express from 'express';
import axios from 'axios';
import fs from 'fs';
import path from 'path';

dotenv.config();

const app = express();
const port = process.env.PORT || 8080;
const pythonServiceUrl = 'http://localhost:5000'; // URL de tu servicio Flask

app.use(express.json());

// Enviar mensaje de texto a WhatsApp
async function sendMessageToWhatsApp(recipientId, message, phoneNumberId) {
    const WHATSAPP_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;

    if (!WHATSAPP_ACCESS_TOKEN) {
        console.error("FACEBOOK_PAGE_ACCESS_TOKEN no está configurado en las variables de entorno.");
        return;
    }

    const url = `https://graph.facebook.com/v12.0/${phoneNumberId}/messages`;

    if (typeof message !== 'string') {
        message = String(message || "");
    }

    const payload = {
        messaging_product: "whatsapp",
        to: recipientId,
        text: { body: message },
    };

    try {
        const response = await axios.post(url, payload, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${WHATSAPP_ACCESS_TOKEN}`,
            },
        });
        console.log(`Mensaje enviado a ${recipientId}: ${message}`);
    } catch (error) {
        console.error("Error al enviar mensaje a WhatsApp:", error.response?.data || error.message);
    }
}

// Enviar audio a WhatsApp
async function sendAudioToWhatsApp(recipientId, audioFilePath, phoneNumberId) {
    const WHATSAPP_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;
    const url = `https://graph.facebook.com/v12.0/${phoneNumberId}/messages`;

    if (!WHATSAPP_ACCESS_TOKEN) {
        console.error("FACEBOOK_PAGE_ACCESS_TOKEN no está configurado en las variables de entorno.");
        return;
    }

    // Subir el archivo de audio a WhatsApp
    const formData = new FormData();
    formData.append('file', fs.createReadStream(audioFilePath));
    formData.append('messaging_product', 'whatsapp');
    formData.append('to', recipientId);

    const headers = {
        ...formData.getHeaders(),
        'Authorization': `Bearer ${WHATSAPP_ACCESS_TOKEN}`,
    };

    try {
        const response = await axios.post(url, formData, { headers });
        console.log(`Audio enviado a ${recipientId}: ${audioFilePath}`);
    } catch (error) {
        console.error("Error al enviar audio a WhatsApp:", error.response?.data || error.message);
    }
}

// Webhook para recibir mensajes de WhatsApp
app.post('/webhook', async (req, res) => {
    try {
        if (!req.body || !req.body.entry || !Array.isArray(req.body.entry)) {
            console.error("Formato de payload inesperado:", JSON.stringify(req.body, null, 2));
            return res.sendStatus(400);
        }

        for (const entry of req.body.entry) {
            if (!entry.changes || !Array.isArray(entry.changes)) {
                console.error("El campo 'changes' no está presente o no es un array:", JSON.stringify(entry, null, 2));
                continue;
            }

            for (const change of entry.changes) {
                const value = change.value;
                if (value && value.messages && Array.isArray(value.messages)) {
                    value.messages.forEach(async (message) => {
                        const senderId = message.from;
                        const phoneNumberId = value.metadata.phone_number_id;

                        if (message.type === 'text') {
                            const receivedMessage = message.text.body;
                            console.log(`Mensaje de texto recibido: ${receivedMessage}`);
                            await handleTextMessage(senderId, receivedMessage, phoneNumberId);
                        } else if (message.type === 'audio') {
                            const audioUrl = message.audio.url;
                            console.log(`Audio recibido: ${audioUrl}`);
                            await handleAudioMessage(senderId, audioUrl, phoneNumberId);
                        }
                    });
                }
            }
        }

        res.sendStatus(200);
    } catch (error) {
        console.error("Error general en el webhook:", error);
        res.sendStatus(500);
    }
});

// Webhook de verificación
app.get('/webhook', (req, res) => {
    const VERIFY_TOKEN = process.env.FACEBOOK_VERIFY_TOKEN;
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    if (mode && token) {
        if (mode === 'subscribe' && token === VERIFY_TOKEN) {
            console.log('Webhook verificado');
            res.status(200).send(challenge);
        } else {
            console.error('Token de verificación incorrecto');
            res.sendStatus(403);
        }
    } else {
        console.error('Solicitud de verificación incorrecta:', req.query);
        res.sendStatus(400);
    }
});

// Función para manejar mensajes de texto y enviar la respuesta
async function handleTextMessage(senderId, receivedMessage, phoneNumberId) {
    try {
        // Enviar el mensaje al servicio de Flask para generar la respuesta
        const response = await axios.post(`${pythonServiceUrl}/generate-response`, {
            message: receivedMessage,
            sender_id: senderId
        });

        const assistantMessage = response.data.response;
        const audioFilePath = response.data.audio_file; // Ruta del archivo de audio generado

        // Enviar el mensaje de texto
        await sendMessageToWhatsApp(senderId, assistantMessage, phoneNumberId);

        // Enviar el archivo de audio (si se generó uno)
        if (audioFilePath) {
            await sendAudioToWhatsApp(senderId, audioFilePath, phoneNumberId);
        }
    } catch (error) {
        console.error("Error al manejar el mensaje de texto:", error.message);
    }
}

// Función para manejar mensajes de audio
async function handleAudioMessage(senderId, audioUrl, phoneNumberId) {
    console.log(`Procesando mensaje de audio recibido: ${audioUrl}`);
    // Aquí puedes agregar la lógica para procesar el audio recibido si es necesario.
    // Enviar una respuesta predeterminada por ahora
    await sendMessageToWhatsApp(senderId, 'Recibí tu mensaje de audio, procesando...', phoneNumberId);
}

app.listen(port, () => {
    console.log(`Servidor escuchando en puerto ${port}`);
});
