import OpenAI from "openai";
import readline from "readline";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const assistantId = "asst_Q3M9vDA4aN89qQNH1tDXhjaE";

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

async function continueConversation(userMessage) {
  try {
    // Crear un hilo para la conversación
    const thread = await openai.beta.threads.create({});
    console.log("Hilo creado:", thread.id);

    // Enviar el mensaje del usuario al hilo
    const message = await openai.beta.threads.messages.create(thread.id, {
      role: "user",
      content: userMessage,
    });
    console.log("Mensaje enviado al hilo:", message);

    // Obtener la respuesta del asistente
    const assistantResponse = await openai.beta.threads.messages.create(thread.id, {
      role: "assistant",
      content: "¡Hola, soy tu asistente! ¿Cómo puedo ayudarte?",
    });

    console.log("Respuesta del asistente:", assistantResponse);

    // Inspeccionar la estructura completa de la respuesta
    if (assistantResponse.content && assistantResponse.content.length > 0) {
      const responseText = assistantResponse.content[0]?.text;
      if (responseText) {
        console.log("Texto de la respuesta del asistente (inspeccionado):", responseText);
        return responseText.content || responseText;  // Acceder al contenido correctamente
      } else {
        console.log("El campo 'text' no contiene un texto válido.");
        return null;
      }
    } else {
      console.log("No se encontró contenido en la respuesta del asistente.");
      return null;
    }
  } catch (error) {
    console.error("Error en la conversación:", error);
    throw error;
  }
}

async function interactWithAssistant(userMessage) {
  console.log("Iniciando conversación con el asistente...");
  const assistantResponse = await continueConversation(userMessage);
  console.log("Conversación completada. Respuesta del asistente:", assistantResponse);
  return assistantResponse;
}

export { interactWithAssistant };
