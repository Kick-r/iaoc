# app.py
import asyncio
import os

from flask import Flask, request, jsonify, send_from_directory, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

from ai import responder
from tts import gerar_audio
from db import init_db, SessionLocal, User, Chat, Message

app = Flask(__name__)
os.makedirs("audios", exist_ok=True)

# No Render/Prod: crie env FLASK_SECRET_KEY com algo forte
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-nao-use-em-prod")

# Render/Reverse proxy: garante que Flask entenda HTTPS
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# cookies da sessão
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Se estiver no Render (HTTPS), melhor setar Secure
if os.getenv("RENDER") or os.getenv("RENDER_EXTERNAL_URL"):
    app.config["SESSION_COOKIE_SECURE"] = True

# cria tabelas se não existir
init_db()


def get_db():
    return SessionLocal()


# =========================
# HELPERS
# =========================

def require_login():
    return session.get("user_id")


def get_current_user(db):
    uid = require_login()
    if not uid:
        return None
    return db.query(User).filter(User.id == int(uid)).first()


# =========================
# PÁGINAS
# =========================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/account")
def account_page():
    # página protegida
    if not require_login():
        return render_template("login.html")
    return render_template("account.html")


# =========================
# AUTH
# =========================

@app.route("/auth/me", methods=["GET"])
def auth_me():
    uid = require_login()
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
                "goal": u.goal
            }
        })
    finally:
        db.close()


@app.route("/auth/signup", methods=["POST"])
def auth_signup():
    data = request.json or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    age = data.get("age")
    context = (data.get("context") or "").strip() or None
    goal = (data.get("goal") or "").strip() or None

    if not name or not email or not password:
        return jsonify({"error": "nome, email e senha são obrigatórios"}), 400

    if len(password) < 6:
        return jsonify({"error": "senha muito curta (mín 6 caracteres)"}), 400

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

        session["user_id"] = u.id
        return jsonify({"ok": True, "user_id": u.id, "name": u.name})
    finally:
        db.close()


@app.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.json or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

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
# ACCOUNT (dashboard)
# =========================

@app.route("/account/profile", methods=["PUT"])
def account_update_profile():
    uid = require_login()
    if not uid:
        return jsonify({"error": "não autenticado"}), 401

    data = request.json or {}
    name = (data.get("name") or "").strip() or None
    age = data.get("age")
    context = (data.get("context") or "").strip() or None
    goal = (data.get("goal") or "").strip() or None

    # valida idade (se vier)
    age_val = None
    if str(age).strip():
        try:
            age_val = int(age)
            if age_val < 10 or age_val > 99:
                return jsonify({"error": "idade inválida"}), 400
        except:
            return jsonify({"error": "idade inválida"}), 400

    db = get_db()
    try:
        u = get_current_user(db)
        if not u:
            session.pop("user_id", None)
            return jsonify({"error": "sessão inválida"}), 401

        u.name = name
        u.age = age_val
        u.context = context
        u.goal = goal
        db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/account/password", methods=["PUT"])
def account_change_password():
    uid = require_login()
    if not uid:
        return jsonify({"error": "não autenticado"}), 401

    data = request.json or {}
    current_password = (data.get("current_password") or "").strip()
    new_password = (data.get("new_password") or "").strip()

    if not current_password or not new_password:
        return jsonify({"error": "preencha senha atual e nova senha"}), 400

    if len(new_password) < 6:
        return jsonify({"error": "senha muito curta (mín 6 caracteres)"}), 400

    db = get_db()
    try:
        u = get_current_user(db)
        if not u:
            session.pop("user_id", None)
            return jsonify({"error": "sessão inválida"}), 401

        if not u.password_hash or not check_password_hash(u.password_hash, current_password):
            return jsonify({"error": "senha atual incorreta"}), 401

        u.password_hash = generate_password_hash(new_password)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/account", methods=["DELETE"])
def account_delete():
    uid = require_login()
    if not uid:
        return jsonify({"error": "não autenticado"}), 401

    data = request.json or {}
    password = (data.get("password") or "").strip()
    if not password:
        return jsonify({"error": "senha é obrigatória"}), 400

    db = get_db()
    try:
        u = get_current_user(db)
        if not u:
            session.pop("user_id", None)
            return jsonify({"error": "sessão inválida"}), 401

        if not u.password_hash or not check_password_hash(u.password_hash, password):
            return jsonify({"error": "senha incorreta"}), 401

        # apaga chats + mensagens (cascade já ajuda, mas vamos garantir)
        chats = db.query(Chat).filter(Chat.user_id == int(uid)).all()
        for c in chats:
            db.query(Message).filter(Message.chat_id == c.id).delete()
            db.delete(c)

        db.delete(u)
        db.commit()

        session.pop("user_id", None)
        return jsonify({"ok": True})
    finally:
        db.close()


# =========================
# CHATS (com login)
# =========================

@app.route("/chats", methods=["POST"])
def create_chat():
    uid = require_login()
    if not uid:
        return jsonify({"error": "não autenticado"}), 401

    data = request.json or {}
    title = (data.get("title") or "Novo chat").strip() or "Novo chat"

    db = get_db()
    try:
        c = Chat(user_id=int(uid), title=title)
        db.add(c)
        db.commit()
        db.refresh(c)
        return jsonify({"chat_id": c.id})
    finally:
        db.close()


@app.route("/chats", methods=["GET"])
def list_chats():
    uid = require_login()
    if not uid:
        return jsonify({"error": "não autenticado"}), 401

    db = get_db()
    try:
        chats = (
            db.query(Chat)
            .filter(Chat.user_id == int(uid))
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
    uid = require_login()
    if not uid:
        return jsonify({"error": "não autenticado"}), 401

    db = get_db()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat or chat.user_id != int(uid):
            return jsonify({"error": "chat não encontrado"}), 404

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
    uid = require_login()
    if not uid:
        return jsonify({"error": "não autenticado"}), 401

    data = request.json or {}
    msg = (data.get("message") or "").strip()
    chat_id = data.get("chat_id")

    if not msg:
        return jsonify({"text": "<i>Escreve alguma coisa aí 😅</i>", "audio": None})

    if not chat_id:
        return jsonify({"error": "chat_id é obrigatório"}), 400

    db = get_db()
    try:
        chat_obj = db.query(Chat).filter(Chat.id == int(chat_id)).first()
        if not chat_obj or chat_obj.user_id != int(uid):
            return jsonify({"error": "chat não encontrado"}), 404

        u = db.query(User).filter(User.id == int(uid)).first()
        user_profile = None
        if u:
            user_profile = {
                "name": u.name,
                "age": u.age,
                "context": u.context,
                "goal": u.goal
            }

        # salva msg user
        db.add(Message(chat_id=int(chat_id), role="user", content=msg))
        db.commit()

        # histórico (últimas 30)
        last_msgs = (
            db.query(Message)
            .filter(Message.chat_id == int(chat_id))
            .order_by(Message.created_at.asc())
            .all()
        )[-30:]

        history = [{"role": m.role, "content": m.content} for m in last_msgs[:-1]]

        # IA (com perfil do usuário)
        texto = responder(msg, history=history, user_profile=user_profile, html=True)

        # salva resposta
        db.add(Message(chat_id=int(chat_id), role="assistant", content=texto))
        db.commit()

    finally:
        db.close()

    # áudio (não pode quebrar o chat)
    audio_url = None
    try:
        audio = asyncio.run(gerar_audio(texto))
        audio_url = f"/audio/{audio}"
    except:
        audio_url = None

    return jsonify({"text": texto, "audio": audio_url})


@app.route("/chats/<int:chat_id>", methods=["PUT"])
def rename_chat(chat_id):
    uid = require_login()
    if not uid:
        return jsonify({"error": "não autenticado"}), 401

    data = request.json or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "título inválido"}), 400

    db = get_db()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat or chat.user_id != int(uid):
            return jsonify({"error": "chat não encontrado"}), 404

        chat.title = title
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/chats/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    uid = require_login()
    if not uid:
        return jsonify({"error": "não autenticado"}), 401

    db = get_db()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat or chat.user_id != int(uid):
            return jsonify({"error": "chat não encontrado"}), 404

        db.query(Message).filter(Message.chat_id == chat_id).delete()
        db.delete(chat)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# =========================
# ÁUDIO
# =========================

@app.route("/audio/<nome>")
def audio(nome):
    safe = secure_filename(nome)
    return send_from_directory("audios", safe)


@app.route("/audio/<nome>/delete", methods=["DELETE"])
def delete_audio(nome):
    safe = secure_filename(nome)
    try:
        os.remove(os.path.join("audios", safe))
        return {"ok": True}
    except FileNotFoundError:
        return {"ok": False}, 404
