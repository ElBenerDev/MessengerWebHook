require('dotenv').config(); // Cargar las variables del archivo .env
const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');

const app = express();
const port = process.env.PORT || 5000;

// Configurar middleware para procesar JSON
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Ruta de verificación del webhook
app.get('/webhook', (req, res) => {
    const VERIFY_TOKEN = process.env.VERIFY_TOKEN;

    // Verificar el token de la solicitud de verificación de Messenger
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    if (mode && token) {
        if (token === VERIFY_TOKEN) {
            res.status(200).send(challenge);
        } else {
            res.sendStatus(403);
        }
    }
});

// Ruta para manejar mensajes entrantes de Messenger
app.post('/webhook', async (req, res) => {
    const data = req.body;

    // Verificar que la solicitud contiene eventos de mensajes
    if (data.object === 'page') {
        data.entry.forEach(entry => {
            const messagingEvent = entry.messaging[0];
            const senderId = messagingEvent.sender.id;
            const messageText = messagingEvent.message.text;

            // Llamar a la función para procesar el mensaje con OpenAI
            handleUserMessage(senderId, messageText);
        });

        res.status(200).send('EVENT_RECEIVED');
    } else {
        res.sendStatus(404);
    }
});

// Función para interactuar con OpenAI
async function handleUserMessage(senderId, message) {
    try {
        const responseMessage = await interactuarConAsistente(message);

        // Enviar la respuesta de OpenAI al usuario de Messenger
        await enviarMensaje(senderId, responseMessage);
    } catch (error) {
        console.error('Error al interactuar con OpenAI:', error);
        await enviarMensaje(senderId, 'Lo siento, hubo un problema al procesar tu mensaje.');
    }
}

// Función para interactuar con OpenAI
async function interactuarConAsistente(mensaje) {
    const openaiApiKey = process.env.OPENAI_API_KEY;

    try {
        const response = await axios.post(
            'https://api.openai.com/v1/chat/completions',
            {
                model: 'gpt-4', // Asegúrate de usar el modelo correcto
                messages: [
                    { role: 'user', content: mensaje }
                ]
            },
            {
                headers: {
                    Authorization: `Bearer ${openaiApiKey}`,
                    'Content-Type': 'application/json'
                }
            }
        );

        const responseMessage = response.data.choices[0].message.content;
        return responseMessage;
    } catch (error) {
        console.error('Error al interactuar con OpenAI:', error.response ? error.response.data : error.message);
        throw new Error('Error al procesar el mensaje');
    }
}

// Función para enviar mensajes a Messenger
async function enviarMensaje(senderId, text) {
    const PAGE_ACCESS_TOKEN = process.env.PAGE_ACCESS_TOKEN;
    
    try {
        const response = await axios.post(
            `https://graph.facebook.com/v12.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`,
            {
                recipient: { id: senderId },
                message: { text }
            }
        );
        console.log('Mensaje enviado:', response.data);
    } catch (error) {
        console.error('Error al enviar mensaje a Messenger:', error.response ? error.response.data : error.message);
    }
}

// Iniciar el servidor
app.listen(port, () => {
    console.log(`Servidor en ejecución en http://localhost:${port}`);
});
