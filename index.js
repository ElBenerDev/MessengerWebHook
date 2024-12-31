import dotenv from 'dotenv';
import express from 'express';
import axios from 'axios';
import cors from 'cors';

dotenv.config();

const app = express();
const port = process.env.PORT || 8080;
const pythonServiceUrl = 'http://localhost:5000';

console.log(`Python service URL: ${pythonServiceUrl}`);
console.log(`Node.js server running on port: ${port}`);

app.use(cors());
app.use(express.json());

// Función para enviar un mensaje a WhatsApp usando la API de WhatsApp de Facebook
async function sendMessageToWhatsApp(recipientId, message, phoneNumberId) {
    const WHATSAPP_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;

    if (!WHATSAPP_ACCESS_TOKEN) {
        console.error("FACEBOOK_PAGE_ACCESS_TOKEN no está configurado en las variables de entorno.");
        return;
    }

    const url = `https://graph.facebook.com/v12.0/${phoneNumberId}/messages`;

    if (typeof message !== 'string') {
        console.warn("El mensaje no es un string. Intentando convertirlo...");
        message = String(message || "");
    }

    const payload = {
        messaging_product: "whatsapp",
        to: recipientId,
        text: { body: message },
    };

    try {
        console.log("Enviando mensaje a WhatsApp:", payload);
        const response = await axios.post(url, payload, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${WHATSAPP_ACCESS_TOKEN}`,
            },
        });
        console.log(`Mensaje enviado a ${recipientId}: ${message}`);
        console.log("Respuesta de WhatsApp:", response.data);
    } catch (error) {
        console.error("Error al enviar mensaje a WhatsApp:", error.response?.data || error.message);
    }
}

// Endpoint webhook que recibe los mensajes de WhatsApp y llama a tu servicio Python
app.post('/webhook', async (req, res) => {
    try {
        console.log('Webhook recibido:', req.body);

        if (!req.body?.entry || !Array.isArray(req.body.entry)) {
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

                if (value?.messages?.[0]?.type === 'text') {
                    const message = value.messages[0];
                    const senderId = message.from;
                    const receivedMessage = message.text.body;
                    const phoneNumberId = value.metadata.phone_number_id;

                    if (!senderId || !phoneNumberId) {
                        console.error("Faltan datos importantes del mensaje.");
                        return res.sendStatus(400);
                    }

                    console.log(`Mensaje recibido de ${senderId}: ${receivedMessage}`);

                    try {
                        const response = await axios.post(`${pythonServiceUrl}/generate-response`, {
                            message: receivedMessage,
                            sender_id: senderId
                        });

                        const assistantMessage = response.data?.response || "Lo siento, no pude procesar tu mensaje.";
                        console.log("Respuesta generada por Python:", assistantMessage);

                        await sendMessageToWhatsApp(senderId, assistantMessage, phoneNumberId);
                    } catch (error) {
                        console.error("Error al interactuar con el servicio Python:", error.message);
                        await sendMessageToWhatsApp(senderId, "Hubo un problema al procesar tu mensaje.", phoneNumberId);
                    }
                } else if (value?.statuses) {
                    console.log("Estado de mensaje recibido, no se requiere acción.");
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

// Ruta para la verificación del webhook de Facebook
app.get('/webhook', (req, res) => {
    const VERIFY_TOKEN = process.env.WHATSAPP_VERIFY_TOKEN;
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    if (mode === 'subscribe' && token === VERIFY_TOKEN) {
        console.log('Webhook verificado');
        res.status(200).send(challenge);
    } else {
        console.error('Token de verificación incorrecto o solicitud inválida');
        res.sendStatus(403);
    }
});

app.get('/', (req, res) => {
    res.send('El servidor está funcionando correctamente');
});

// Iniciar el servidor Node.js
app.listen(port, () => {
    console.log(`Servidor escuchando en puerto ${port}`);
});
