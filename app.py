from flask import Flask, request, jsonify, send_from_directory, render_template
import asyncio
import os

from ai import responder
from tts import gerar_audio

app = Flask(__name__)
os.makedirs("audios", exist_ok=True)

# 1) Página principal (HTML)
@app.route("/")
def home():
    return render_template("index.html")

# 2) Chat API
@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "")

    if not msg.strip():
        return jsonify({"text": "<i>Escreve alguma coisa aí 😅</i>", "audio": None})

    texto = responder(msg)

    # gerar áudio (Render não toca, só gera)
    audio = asyncio.run(gerar_audio(texto))

    return jsonify({
        "text": texto,
        "audio": f"/audio/{audio}"
    })

# 3) Servir o áudio gerado
@app.route("/audio/<nome>")
def audio(nome):
    return send_from_directory("audios", nome)

# 4) Deletar depois que tocar
@app.route("/audio/<nome>/delete", methods=["DELETE"])
def delete_audio(nome):
    try:
        os.remove(os.path.join("audios", nome))
        return {"ok": True}
    except FileNotFoundError:
        return {"ok": False}, 404
