from flask import Flask, request, jsonify, send_from_directory, render_template
import asyncio
import os

from ai import responder
from tts import gerar_audio

from db import init_db, SessionLocal, User, Chat, Message

app = Flask(__name__)
os.makedirs("audios", exist_ok=True)

# inicia o banco (cria tabelas se não existir)
init_db()


def get_db():
    return SessionLocal()


# 1) Página principal (HTML)
@app.route("/")
def home():
    return render_template("index.html")


# (NOVO) criar usuário rápido (MVP)
@app.route("/users", methods=["POST"])
def create_user():
    data = request.json or {}
    name = data.get("name")

    db = get_db()
    try:
        u = User(name=name)
        db.add(u)
        db.commit()
        db.refresh(u)
        return jsonify({"user_id": u.id})
    finally:
        db.close()


# (NOVO) criar chat
@app.route("/chats", methods=["POST"])
def create_chat():
    data = request.json or {}
    user_id = data.get("user_id")
    title = data.get("title")

    if not user_id:
        return jsonify({"error": "user_id obrigatório"}), 400

    db = get_db()
    try:
        c = Chat(user_id=int(user_id), title=title)
        db.add(c)
        db.commit()
        db.refresh(c)
        return jsonify({"chat_id": c.id})
    finally:
        db.close()


# (NOVO) listar chats do usuário
@app.route("/chats", methods=["GET"])
def list_chats():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id obrigatório"}), 400

    db = get_db()
    try:
        chats = (
            db.query(Chat)
            .filter(Chat.user_id == int(user_id))
            .order_by(Chat.created_at.desc())
            .all()
        )
        return jsonify([
            {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
            for c in chats
        ])
    finally:
        db.close()


# (NOVO) pegar mensagens do chat
@app.route("/chats/<int:chat_id>/messages", methods=["GET"])
def chat_messages(chat_id: int):
    db = get_db()
    try:
        msgs = (
            db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return jsonify([
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in msgs
        ])
    finally:
        db.close()


# 2) Chat API (AGORA com DB)
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}

    msg = data.get("message", "")
    user_id = data.get("user_id")
    chat_id = data.get("chat_id")

    if not msg.strip():
        return jsonify({"text": "<i>Escreve alguma coisa aí 😅</i>", "audio": None})

    if not user_id or not chat_id:
        return jsonify({"error": "user_id e chat_id são obrigatórios"}), 400

    db = get_db()
    try:
        # salva mensagem do usuário
        db.add(Message(chat_id=int(chat_id), role="user", content=msg))
        db.commit()

        # pega histórico do chat (últimas 30 mensagens pra não explodir token)
        last_msgs = (
            db.query(Message)
            .filter(Message.chat_id == int(chat_id))
            .order_by(Message.created_at.asc())
            .all()
        )[-30:]

        history = [{"role": m.role, "content": m.content} for m in last_msgs[:-1]]
        texto = responder(msg, history=history)

        # salva resposta da IA
        db.add(Message(chat_id=int(chat_id), role="assistant", content=texto))
        db.commit()

    finally:
        db.close()

    # gerar áudio (se falhar, não quebra o chat)
    audio_url = None
    try:
        audio = asyncio.run(gerar_audio(texto))
        audio_url = f"/audio/{audio}"
    except:
        audio_url = None

    return jsonify({
        "text": texto,
        "audio": audio_url
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
