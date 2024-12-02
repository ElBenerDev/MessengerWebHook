import OpenAI from "openai";

// Inicializar la librería OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY, // Asegúrate de cargar correctamente el .env
});

/**
 * Función para generar una respuesta usando OpenAI
 * @param {string} userMessage - Mensaje enviado por el usuario
 * @returns {Promise<string>} - Respuesta generada por OpenAI
 */
export async function getOpenAiResponse(userMessage) {
  try {
    const completion = await openai.chat.completions.create({
      model: "gpt-4", // Usa el modelo apropiado, por ejemplo, gpt-4 o gpt-3.5-turbo
      messages: [
        { role: "system", content: "Eres un asistente útil y amigable." },
        { role: "user", content: userMessage },
      ],
    });

    return completion.choices[0].message.content.trim();
  } catch (error) {
    console.error("Error al obtener respuesta de OpenAI:", error.message);
    return "Lo siento, no pude procesar tu mensaje en este momento.";
  }
}
