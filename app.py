from flask import Flask, request, jsonify, send_from_directory
import asyncio
import os

from ai import responder
from tts import gerar_audio

app = Flask(__name__)
os.makedirs("audios", exist_ok=True)

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json["message"]

    texto = responder(msg)
    audio = asyncio.run(gerar_audio(texto))

    return jsonify({
        "text": texto,
        "audio": f"/audio/{audio}"
    })

@app.route("/audio/<nome>")
def audio(nome):
    return send_from_directory("audios", nome)

@app.route("/audio/<nome>/delete", methods=["DELETE"])
def delete_audio(nome):
    try:
        os.remove(f"audios/{nome}")
        return {"ok": True}
    except:
        return {"ok": False}, 404
