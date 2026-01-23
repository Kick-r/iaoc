from flask import Flask, request, jsonify, send_from_directory, render_template, session
import asyncio
import os

from werkzeug.security import generate_password_hash, check_password_hash

from ai import responder
from tts import gerar_audio
from db import init_db, SessionLocal, User, Chat, Message

app = Flask(__name__)
os.makedirs("audios", exist_ok=True)

# IMPORTANTÍSSIMO: sessão (cookie)
# No Render, crie env FLASK_SECRET_KEY com um valor aleatório forte
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-nao-use-em-prod")

# inicia o banco (cria tabelas se não existir)
init_db()


def get_db():
    return SessionLocal()


# =========================
# PÁGINAS
# =========================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


# =========================
# AUTH (LOGIN / CADASTRO)
# =========================

@app.route("/auth/me", methods=["GET"])
def auth_me():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"logged": False}), 401

    db = get_db()
    try:
        u = db.query(User).filter(User.id == int(uid)).first()
        if not u:
            session.pop("user_id", None)
            return jsonify({"logged": False}), 401

        return jsonify({
            "logged": True,
            "user": {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "age": u.age,
                "context": u.context,
                "goal": u.goal,
            }
        })
    finally:
        db.close()


@app.route("/auth/signup", methods=["POST"])
def auth_signup():
    data = request.json or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "")
    age = data.get("age")
    context = data.get("context")
    goal = data.get("goal")

    if not name or not email or not password:
        return jsonify({"error": "nome, email e senha são obrigatórios"}), 400

    db = get_db()
    try:
        exists = db.query(User).filter(User.email == email).first()
        if exists:
            return jsonify({"error": "email já cadastrado"}), 409

        u = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            age=int(age) if str(age).strip() else None,
            context=context,
            goal=goal,
        )
        db.add(u)
        db.commit()
        db.refresh(u)

        # cria sessão
        session["user_id"] = u.id

        return jsonify({"ok": True, "user_id": u.id})
    finally:
        db.close()


@app.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.json or {}

    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "")

    if not email or not password:
        return jsonify({"error": "email e senha são obrigatórios"}), 400

    db = get_db()
    try:
        u = db.query(User).filter(User.email == email).first()
        if (not u) or (not u.password_hash) or (not check_password_hash(u.password_hash, password)):
            return jsonify({"error": "email ou senha inválidos"}), 401

        session["user_id"] = u.id
        return jsonify({"ok": True, "user_id": u.id, "name": u.name})
    finally:
        db.close()


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


# =========================
# MVP ANTIGO (ainda funciona)
# =========================

@app.route("/users", methods=["POST"])
def create_user():
    """
    MVP antigo: cria user “anônimo” rápido.
    Continua existindo pra não quebrar o que você já fez.
    Depois a gente desativa quando o login virar obrigatório.
    """
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

        # histórico (últimas 30 mensagens pra não explodir token)
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


@app.route("/audio/<nome>")
def audio(nome):
    return send_from_directory("audios", nome)


@app.route("/audio/<nome>/delete", methods=["DELETE"])
def delete_audio(nome):
    try:
        os.remove(os.path.join("audios", nome))
        return {"ok": True}
    except FileNotFoundError:
        return {"ok": False}, 404


@app.route("/chats/<int:chat_id>", methods=["PUT"])
def rename_chat(chat_id):
    data = request.json or {}
    title = data.get("title", "").strip()

    if not title:
        return {"error": "Título inválido"}, 400

    db = get_db()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            return {"error": "Chat não encontrado"}, 404

        chat.title = title
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.route("/chats/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    db = get_db()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            return {"error": "Chat não encontrado"}, 404

        db.query(Message).filter(Message.chat_id == chat_id).delete()
        db.delete(chat)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
