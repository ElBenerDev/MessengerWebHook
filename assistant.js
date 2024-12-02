const axios = require("axios");

// Configuración de tu cliente con la API de OpenAI
const client = axios.create({
  baseURL: 'https://api.openai.com/v1',
  headers: {
    'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
    'Content-Type': 'application/json'
  }
});

// Crear un asistente y un hilo de conversación
let threadId = null;
const assistantId = "asst_Q3M9vDA4aN89qQNH1tDXhjaE";

// Crear un nuevo hilo de conversación
async function createThread() {
  try {
    const response = await client.post('/beta/threads/create');
    threadId = response.data.id;
    console.log("Hilo creado:", threadId);
  } catch (error) {
    console.error("Error al crear hilo:", error.message);
  }
}

// Función para obtener respuesta del asistente personalizado
async function getAssistantResponse(userMessage) {
  try {
    // Crear el hilo si no se ha creado aún
    if (!threadId) {
      await createThread();
    }

    // Enviar mensaje del usuario al asistente
    await client.post(`/beta/threads/messages.create`, {
      thread_id: threadId,
      role: 'user',
      content: userMessage
    });

    // Obtener la respuesta del asistente (streaming)
    const response = await client.post(`/beta/threads/runs.stream`, {
      thread_id: threadId,
      assistant_id: assistantId,
    });

    // Extraer el texto de la respuesta
    const assistantText = response.data.choices[0].message.content;
    return assistantText;
  } catch (error) {
    console.error("Error al interactuar con OpenAI:", error.message);
    return "Lo siento, hubo un problema al procesar tu mensaje.";
  }
}

module.exports = {
  getAssistantResponse
};
