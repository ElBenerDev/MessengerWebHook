import express from 'express';
import bodyParser from 'body-parser';
import axios from 'axios';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

dotenv.config();

const app = express();
const port = process.env.PORT || 10000; // Render expone el puerto 10000
const pythonServiceUrl = 'http://localhost:5000';

app.use(bodyParser.json());

async function sendMessageToWhatsApp(to, message, phoneNumberId) {
    try {
        const response = await axios.post(
            `https://graph.facebook.com/v15.0/${phoneNumberId}/messages`,
            {
                messaging_product: "whatsapp",
                to: to,
                text: { body: message }
            },
            {
                headers: {
                    'Authorization': `Bearer ${process.env.FACEBOOK_PAGE_ACCESS_TOKEN}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        console.log(`Mensaje enviado a ${to}: ${message}`);
        console.log("Respuesta de WhatsApp:", response.data);
        return response.data;
    } catch (error) {
        console.error(`Error al enviar mensaje a ${to}:`, error.message);
        return null;
    }
}

app.post('/webhook', async (req, res) => {
    try {
        const data = req.body;
        console.log("Datos recibidos:", JSON.stringify(data, null, 2));

        if (data.entry && Array.isArray(data.entry)) {
            for (const entry of data.entry) {
                if (entry.changes) {
                    for (const change of entry.changes) {
                        const value = change.value;

                        if (value && value.messages && Array.isArray(value.messages)) {
                            const message = value.messages[0];

                            if (message && message.type === 'text') {
                                const senderId = message.from;
                                const receivedMessage = message.text.body;

                                console.log(`Mensaje recibido de ${senderId}: ${receivedMessage}`);

                                try {
                                    const response = await axios.post(`${pythonServiceUrl}/generate-response`, {
                                        message: receivedMessage,
                                        sender_id: senderId
                                    });

                                    const assistantMessage = response.data.response;
                                    await sendMessageToWhatsApp(
                                        senderId, 
                                        assistantMessage, 
                                        value.metadata.phone_number_id
                                    );
                                } catch (error) {
                                    console.error("Error al interactuar con el servicio Python:", error.message);
                                    await sendMessageToWhatsApp(
                                        senderId,
                                        "Lo siento, hubo un problema al procesar tu mensaje.",
                                        value.metadata.phone_number_id
                                    );
                                }
                            } else {
                                console.log("El mensaje no es de tipo 'text' o tiene un formato no compatible:", 
                                    JSON.stringify(value, null, 2));
                            }
                        }
                    }
                }
            }
        }

        res.status(200).send('OK');
    } catch (error) {
        console.error("Error en webhook:", error);
        res.status(500).send('Error interno del servidor');
    }
});

app.get('/webhook', (req, res) => {
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    if (mode && token) {
        if (mode === 'subscribe' && token === process.env.FACEBOOK_VERIFY_TOKEN) {
            console.log('Webhook verificado!');
            res.status(200).send(challenge);
        } else {
            res.sendStatus(403);
        }
    }
});

app.listen(3000, () => {
    console.log('Servidor escuchando en el puerto 3000');
});