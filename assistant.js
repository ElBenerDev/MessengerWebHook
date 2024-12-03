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
    // Crear un hilo para la conversación (si aún no existe uno)
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

    // Retornar la respuesta generada
    return assistantResponse;
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
