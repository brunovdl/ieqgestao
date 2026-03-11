export async function generateAIText(prompt: string, systemPrompt: string = "Você é um assistente útil e amigável."): Promise<string> {
    const apiKey = import.meta.env.VITE_GROQ_API_KEY;
    if (!apiKey) {
        throw new Error('Chave da API (VITE_GROQ_API_KEY) não encontrada no ficheiro .env');
    }

    try {
        const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: "llama-3.3-70b-versatile",
                messages: [
                    { role: "system", content: systemPrompt },
                    { role: "user", content: prompt }
                ],
                temperature: 0.7,
                max_tokens: 300
            })
        });

        const data = await response.json();

        if (data.choices && data.choices.length > 0) {
            return data.choices[0].message.content;
        } else {
            throw new Error('Resposta inválida ou vazia da API.');
        }
    } catch (error) {
        console.error('Erro na geração de IA:', error);
        throw error;
    }
}
