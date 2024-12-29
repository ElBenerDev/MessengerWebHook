import dotenv from 'dotenv';
import express from 'express';
import axios from 'axios';
import fs from 'fs';
import FormData from 'form-data';

dotenv.config();

const app = express();
const port = process.env.PORT || 8080;
const pythonServiceUrl = 'http://localhost:5000';

app.use(express.json());

// Función para subir el archivo de audio a WhatsApp
async function uploadAudioToWhatsApp(audioFilePath, phoneNumberId) {
    const WHATSAPP_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;

    const formData = new FormData();
    formData.append("file", fs.createReadStream(audioFilePath));  // Archivo de audio
    formData.append("messaging_product", "whatsapp");

    try {
        const response = await axios.post(`https://graph.facebook.com/v12.0/${phoneNumberId}/media`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                'Authorization': `Bearer ${WHATSAPP_ACCESS_TOKEN}`,
            },
        });

        return response.data.id;  // Retorna el ID del archivo subido
    } catch (error) {
        console.error("Error al subir el archivo de audio a WhatsApp:", error.response?.data || error.message);
        return null;
    }
}

// Función para enviar el mensaje de audio a WhatsApp
async function sendAudioMessageToWhatsApp(recipientId, audioFileId, phoneNumberId) {
    const WHATSAPP_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;

    const payload = {
        messaging_product: "whatsapp",
        to: recipientId,
        audio: {
            id: audioFileId,
        },
    };

    try {
        const response = await axios.post(`https://graph.facebook.com/v12.0/${phoneNumberId}/messages`, payload, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${WHATSAPP_ACCESS_TOKEN}`,
            },
        });
        console.log(`Mensaje de audio enviado a ${recipientId}`);
        console.log("Respuesta de WhatsApp:", response.data);
    } catch (error) {
        console.error("Error al enviar mensaje de audio a WhatsApp:", error.response?.data || error.message);
    }
}

// Endpoint para manejar el webhook
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
                if (
                    value &&
                    value.messages &&
                    Array.isArray(value.messages) &&
                    value.messages[0].type === 'text'
                ) {
                    const message = value.messages[0];
                    const senderId = message.from;
                    const receivedMessage = message.text.body;
                    const phoneNumberId = value.metadata.phone_number_id;

                    console.log(`Mensaje recibido de ${senderId}: ${receivedMessage}`);

                    try {
                        const response = await axios.post(`${pythonServiceUrl}/generate-response`, {
                            message: receivedMessage,
                            sender_id: senderId
                        });

                        const assistantMessage = response.data.response;
                        const audioFilePath = response.data.audio_file;  // Ruta del archivo de audio generado

                        // Subir el archivo de audio a WhatsApp
                        const audioFileId = await uploadAudioToWhatsApp(audioFilePath, phoneNumberId);
                        if (audioFileId) {
                            await sendAudioMessageToWhatsApp(senderId, audioFileId, phoneNumberId);
                        } else {
                            await sendAudioMessageToWhatsApp(senderId, assistantMessage, phoneNumberId);
                        }
                    } catch (error) {
                        console.error("Error al interactuar con el servicio Python:", error.message);
                        if (senderId && phoneNumberId) {
                            await sendAudioMessageToWhatsApp(
                                senderId,
                                "Lo siento, hubo un problema al procesar tu mensaje.",
                                phoneNumberId
                            );
                        }
                    }
                } else {
                    console.log("Mensaje no procesable:", JSON.stringify(value, null, 2));
                }
            }
        }

        res.sendStatus(200);
    } catch (error) {
        console.error("Error general en el webhook:", error);
        res.sendStatus(500);
    }
});

// Endpoint de verificación del webhook
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

app.listen(port, () => {
    console.log(`Servidor escuchando en puerto ${port}`);
});
