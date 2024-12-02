const axios = require("axios");

// Función para obtener una respuesta de OpenAI
const getOpenAiResponse = async (userMessage) => {
  const prompt = `Responde de manera amigable y profesional a la siguiente consulta: ${userMessage}`;

  try {
    const response = await axios.post(
      "https://api.openai.com/v1/completions",
      {
        model: "text-davinci-003",
        prompt: prompt,
        max_tokens: 150,
        temperature: 0.7,
      },
      {
        headers: {
          "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
          "Content-Type": "application/json",
        },
      }
    );

    const answer = response.data.choices[0].text.trim();
    return answer;
  } catch (error) {
    console.error("Error al obtener respuesta de OpenAI:", error);
    return "Lo siento, algo salió mal al procesar tu solicitud.";
  }
};

module.exports = { getOpenAiResponse };
