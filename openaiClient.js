import axios from "axios";

/**
 * Obtiene una respuesta de OpenAI para un mensaje del usuario.
 * @param {string} userMessage - Mensaje recibido del usuario.
 * @returns {Promise<string>} - Respuesta generada por OpenAI.
 */
export async function getOpenAiResponse(userMessage) {
  const url = "https://api.openai.com/v1/chat/completions";
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
  };
  const body = {
    model: "gpt-4",
    messages: [{ role: "user", content: userMessage }],
  };

  try {
    const response = await axios.post(url, body, { headers });
    const assistantMessage = response.data.choices[0].message.content.trim();
    return assistantMessage;
  } catch (error) {
    console.error("Error al obtener respuesta de OpenAI:", error.message);
    return "Lo siento, ocurrió un error al procesar tu mensaje.";
  }
}
