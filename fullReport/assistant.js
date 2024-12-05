import { OpenAI } from 'openai';
import axios from 'axios';

// Configurando el cliente de OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Función para enviar mensaje a Messenger
export async function sendMessageToMessenger(recipientId, message) {
  const pageAccessToken = process.env.FACEBOOK_PAGE_ACCESS_TOKEN;
  const pageId = process.env.PAGE_ID;

  const url = `https://graph.facebook.com/v12.0/${pageId}/messages?access_token=${pageAccessToken}`;

  const data = {
    recipient: {
      id: recipientId
    },
    message: {
      text: message
    }
  };

  try {
    const response = await axios.post(url, data);
    console.log("Mensaje enviado:", response.data);
  } catch (error) {
    console.error("Error al enviar mensaje a Messenger:", error.response ? error.response.data : error.message);
  }
}

// Función para obtener la respuesta del asistente de OpenAI
export async function getAssistantResponse(userMessage) {
  try {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4', // O el modelo que prefieras
      messages: [
        { role: 'user', content: userMessage }
      ]
    });

    const assistantMessage = completion.choices[0].message.content;
    return assistantMessage;
  } catch (error) {
    throw new Error("Error al interactuar con OpenAI: " + error.message);
  }
}
