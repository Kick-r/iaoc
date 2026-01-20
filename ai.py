from groq import Groq

client = Groq(api_key="SUA_CHAVE_VAI_PRA ENV")

messages = [
    {
        "role": "system",
        "content": """TODO O TEXTO DA MAGGIE AQUI"""
    }
]

def responder(texto):
    messages.append({"role": "user", "content": texto})

    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages
    )

    reply = res.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    return reply
