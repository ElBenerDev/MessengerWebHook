require('dotenv').config(); // Cargar variables de entorno
const { OpenAI } = require('openai');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Configurar OpenAI con la API Key desde el archivo .env
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// ID del asistente existente
const ASSISTANT_ID = "asst_Q3M9vDA4aN89qQNH1tDXhjaE";

/**
 * Interactúa con el asistente OpenAI.
 * @param {string} userMessage - Mensaje enviado por el usuario.
 * @returns {Promise<string>} Respuesta generada por el asistente.
 */
async function interactWithAssistant(userMessage) {
  try {
    console.log("Recuperando el asistente...");
    const assistant = await openai.beta.assistants.retrieve(ASSISTANT_ID);
    console.log("Asistente recuperado:", assistant);

    console.log("Creando un nuevo hilo de conversación...");
    const thread = await openai.beta.threads.create();
    console.log("Hilo creado con ID:", thread.id);

    console.log(`Enviando mensaje del usuario: "${userMessage}"`);
    await openai.beta.threads.messages.create({
      thread_id: thread.id,
      role: "user",
      content: userMessage,
    });

    console.log("Ejecutando el asistente en el hilo...");
    let response = await openai.beta.threads.runs.create({
      thread_id: thread.id,
      assistant_id: ASSISTANT_ID,
    });

    // Esperar a que el asistente complete el procesamiento
    while (response.status !== "completed") {
      console.log(`Esperando respuesta... Estado actual: ${response.status}`);
      await sleep(2000); // Esperar 2 segundos
      response = await openai.beta.threads.runs.retrieve({
        thread_id: thread.id,
        run_id: response.id,
      });
    }

    // Obtener la respuesta generada por el asistente
    const assistantResponse = response.result.messages.at(-1).content;
    console.log("Respuesta del asistente:", assistantResponse);
    return assistantResponse;

  } catch (error) {
    console.error("Error al interactuar con el asistente:", error.message);
    return "Lo siento, ocurrió un error al procesar tu solicitud.";
  }
}

// Exportar la función para usarla en otros archivos
module.exports = { interactWithAssistant };

// Ejemplo de uso
if (require.main === module) {
  const readline = require("readline").createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  readline.question("Escribe tu mensaje para el asistente: ", async (message) => {
    const response = await interactWithAssistant(message);
    console.log("Respuesta del asistente:", response);
    readline.close();
  });
}
