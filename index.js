import express from 'express';
import axios from 'axios';
import fs from 'fs';
import FormData from 'form-data';

const app = express();
const PORT = process.env.PORT || 8080;
const pythonServiceUrl = 'http://localhost:5000'; // Asegúrate de que este sea el URL correcto

app.use(express.json());

// Función para enviar mensajes de texto a WhatsApp
async function sendMessageToWhatsApp(recipientId, message, phoneNumberId) {
    const WHATSAPP_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;

    const url = `https://graph.facebook.com/v12.0/${phoneNumberId}/messages`;

    const payload = {
        messaging_product: 'whatsapp',
        to: recipientId,
        type: 'text',
        text: { body: message }
    };

    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${WHATSAPP_ACCESS_TOKEN}`
    };

    try {
        await axios.post(url, payload, { headers });
        console.log(`Mensaje enviado a ${recipientId}: ${message}`);
    } catch (error) {
        console.error("Error al enviar mensaje de texto a WhatsApp:", error.response?.data || error.message);
    }
}

// Función para enviar archivos de audio a WhatsApp
async function sendAudioToWhatsApp(recipientId, audioFilePath, phoneNumberId) {
    const WHATSAPP_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;
    const url = `https://graph.facebook.com/v12.0/${phoneNumberId}/messages`;

    if (!WHATSAPP_ACCESS_TOKEN) {
        console.error("FACEBOOK_PAGE_ACCESS_TOKEN no está configurado en las variables de entorno.");
        return;
    }

    if (!audioFilePath) {
        console.error("La ruta del archivo de audio es inválida o no está definida.");
        return;
    }

    const formData = new FormData();
    formData.append('messaging_product', 'whatsapp'); // Parámetro requerido
    formData.append('to', recipientId);
    formData.append('type', 'audio');
    formData.append('audio', fs.createReadStream(audioFilePath)); // Archivo de audio

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

// Manejar mensajes entrantes y generar respuestas
app.post('/webhook', async (req, res) => {
    const body = req.body;

    if (body.object) {
        const entry = body.entry[0];
        const changes = entry.changes[0];
        const phoneNumberId = entry.id;
        const from = changes.value.messages[0].from;
        const messageText = changes.value.messages[0].text?.body;

        console.log(`Mensaje recibido: ${messageText}`);

        if (messageText) {
            await handleTextMessage(from, messageText, phoneNumberId);
        }

        res.sendStatus(200);
    } else {
        res.sendStatus(404);
    }
});

// Función para manejar mensajes de texto
async function handleTextMessage(senderId, receivedMessage, phoneNumberId) {
    try {
        const response = await axios.post(`${pythonServiceUrl}/generate-response`, {
            message: receivedMessage,
            sender_id: senderId
        });

        const assistantMessage = response.data.response;
        const audioFilePath = response.data.audio_file;

        console.log(`Ruta del archivo de audio generada: ${audioFilePath}`);

        await sendMessageToWhatsApp(senderId, assistantMessage, phoneNumberId);

        if (audioFilePath) {
            await sendAudioToWhatsApp(senderId, audioFilePath, phoneNumberId);
        }
    } catch (error) {
        console.error("Error al manejar el mensaje de texto:", error.message);
    }
}

// Iniciar el servidor
app.listen(PORT, () => {
    console.log(`Servidor Node.js ejecutándose en el puerto ${PORT}`);
});
