import dotenv from 'dotenv';
import express from 'express';
import axios from 'axios';

dotenv.config();

const app = express();
const port = process.env.PORT || 8080;
const pythonServiceUrl = 'http://localhost:5000';

app.use(express.json());

async function sendMessageToWhatsApp(recipientId, message, phoneNumberId) {
    const WHATSAPP_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;

    if (!WHATSAPP_ACCESS_TOKEN) {
        console.error("FACEBOOK_PAGE_ACCESS_TOKEN no está configurado.");
        return;
    }

    const url = `https://graph.facebook.com/v12.0/${phoneNumberId}/messages`;

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

app.post('/webhook', async (req, res) => {
    try {
        for (const entry of req.body.entry || []) {
            for (const change of entry.changes || []) {
                const value = change.value;
                if (value?.messages?.[0]?.type === 'text') {
                    const message = value.messages[0];
                    const senderId = message.from;
                    const receivedMessage = message.text.body;
                    const phoneNumberId = value.metadata.phone_number_id;

                    try {
                        const response = await axios.post(`${pythonServiceUrl}/generate-response`, {
                            message: receivedMessage,
                            sender_id: senderId
                        });

                        const assistantMessage = response.data.response;
                        await sendMessageToWhatsApp(senderId, assistantMessage, phoneNumberId);
                    } catch (error) {
                        console.error("Error al interactuar con el servicio Python:", error.message);
                        await sendMessageToWhatsApp(senderId, "Lo siento, hubo un problema al procesar tu mensaje.", phoneNumberId);
                    }
                }
            }
        }
        res.sendStatus(200);
    } catch (error) {
        console.error("Error general en el webhook:", error);
        res.sendStatus(500);
    }
});

app.listen(port, () => {
    console.log(`Servidor escuchando en puerto ${port}`);
});