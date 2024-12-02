import axios from "axios";

/**
 * Envía un mensaje a través de la API de Messenger.
 * @param {string} senderId - ID del usuario al que se enviará el mensaje.
 * @param {string} messageText - Texto del mensaje que se enviará.
 */
export async function sendMessageToMessenger(senderId, messageText) {
  const url = `https://graph.facebook.com/v16.0/me/messages`;
  const params = {
    access_token: process.env.FB_PAGE_ACCESS_TOKEN,
  };
  const body = {
    recipient: { id: senderId },
    message: { text: messageText },
  };

  try {
    const response = await axios.post(url, body, { params });
    console.log(`Mensaje enviado a ${senderId}:`, response.data);
  } catch (error) {
    console.error("Error al enviar el mensaje a Messenger:", error.message);
  }
}
