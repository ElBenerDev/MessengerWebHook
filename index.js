import { interactWithAssistant } from './assistant.js';

async function handleMessage(userMessage, chatId) {
  try {
    // Llamar a interactWithAssistant y obtener la respuesta
    const assistantResponse = await interactWithAssistant(userMessage);
    
    if (assistantResponse && typeof assistantResponse === 'object' && assistantResponse.value) {
      // Asegurarse de obtener solo el valor de 'value' y usar .trim() en caso de ser necesario
      const responseText = assistantResponse.value.trim();

      console.log("Mensaje generado por el asistente:", responseText);

      // Enviar el mensaje generado de vuelta al usuario
      sendMessageToUser(chatId, responseText);
    } else {
      console.log("Respuesta vacía o incorrecta del asistente.");
      sendMessageToUser(chatId, "Lo siento, hubo un problema al procesar tu mensaje.");
    }
  } catch (error) {
    console.error("Error al interactuar con el asistente:", error);
    sendMessageToUser(chatId, "Lo siento, hubo un error al procesar tu mensaje.");
  }
}

function sendMessageToUser(chatId, message) {
  // Aquí colocas la lógica para enviar el mensaje al usuario a través de tu API
  console.log(`Mensaje enviado a ${chatId}: ${message}`);
  // Puedes hacer una llamada a la API de mensajería para enviar el texto
  // api.sendMessage(chatId, message);
}

export { handleMessage };
