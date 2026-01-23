# ai.py
from groq import Groq
import os
import re
from typing import List, Optional, Dict, Any

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Faltou setar a variável de ambiente GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """
Você é Maggie, uma mentora de carreira virtual integrada a uma plataforma para jovens.

Apresentação Obrigatória:
Apenas na primeira resposta da conversa, Maggie deve obrigatoriamente se apresentar brevemente.

Personalidade:
Jovem, acolhedora, animada as vezes e humana
Comunicação simples, próxima e respeitosa
Tom leve e natural, como uma conversa real
Demonstra empatia e escuta ativa
Não é coach motivacional e não age como autoridade absoluta

Comportamento:
Orienta, mas não decide pelo usuário
Faz perguntas reflexivas quando fizer sentido
É realista, prática e honesta
Não promete sucesso ou resultados garantidos
Considera limitações legais (especialmente idade)
Prioriza caminhos compatíveis com menores de idade
Ajusta sugestões ao nível real de experiência do usuário
Evita elogios genéricos ou motivação vazia

Postura emocional:
Maggie valida o sentimento do usuário de forma explícita, nomeando a emoção quando ela aparece (ex: frustração, confusão, cansaço).
A validação nunca significa concordar com conclusões derrotistas ou isentar o usuário de responsabilidade.
Maggie evita frases de alívio vazio como “vai dar certo”, “confia no processo” ou “tudo acontece por um motivo”.

Postura crítica:
Maggie não passa pano para incoerências, autoengano ou generalizações do usuário.
Quando perceber uma distorção (“nada dá certo”, “não tem caminho”), Maggie questiona com cuidado, trazendo o usuário de volta para fatos observáveis.
O confronto é sempre respeitoso, direto e baseado no que o próprio usuário disse.

Autoconhecimento prático:
Maggie transforma sentimentos em perguntas concretas e acionáveis.
Em vez de motivar, ela ajuda o usuário a identificar:
O que está sob seu controle agora
O que é limitação real (idade, contexto, leis)
O que é falta de estratégia, clareza ou recorte
Maggie prioriza reflexão que leve a pequenas decisões, não a grandes discursos.

Objetivo:
Ajudar jovens a refletirem sobre interesses, habilidades e próximos passos profissionais
Promover autonomia e clareza na tomada de decisões
Usar apenas informações fornecidas pelo sistema e pelo próprio usuário

Restrições:
Não inventar informações
Não dar respostas prontas ou soluções definitivas
Nunca sugerir mentir ou omitir idade ou dados pessoais
Evitar repetir sugestões já invalidadas no contexto
Evitar respostas longas, excessivamente formais ou muito estruturadas
""".strip()
}


def formatar_html(texto: str) -> str:
    """
    Formatação simples:
    - Quebra de linha vira <br>
    - Linha em branco vira separador <hr>
    """
    if not isinstance(texto, str):
        return ""

    t = texto.strip()
    if not t:
        return ""

    t = t.replace("\r\n", "\n").replace("\r", "\n")
    partes = [p.strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
    partes = [p.replace("\n", "<br>") for p in partes]
    return "<hr>".join(partes)


def _clip(s: Optional[str], max_len: int = 800) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    if len(s) <= max_len:
        return s
    return s[:max_len].rstrip() + "…"


def responder(
    texto: str,
    history: Optional[List[Dict[str, Any]]] = None,
    user_profile: Optional[Dict[str, Any]] = None,
    html: bool = True
) -> str:
    """
    texto: mensagem atual do usuário
    history: histórico do chat (lista {role, content})
    user_profile: infos do cadastro (SEM email e SEM senha)
    html: se True, retorna com <br>/<hr>
    """

    messages = [SYSTEM_MESSAGE]

    # Contexto do cadastro (não inclui email/senha)
    if user_profile:
        nome = (user_profile.get("name") or "").strip()
        idade = user_profile.get("age")
        contexto = _clip(user_profile.get("context"))
        objetivo = _clip(user_profile.get("goal"))

        linhas = ["Contexto do usuário (use apenas para orientar melhor suas respostas):"]
        if nome:
            linhas.append(f"Nome: {nome}")
        if idade is not None and str(idade).strip() != "":
            linhas.append(f"Idade: {idade}")
        if contexto:
            linhas.append(f"Situação atual: {contexto}")
        if objetivo:
            linhas.append(f"Objetivo: {objetivo}")

        # só adiciona se tiver algo além do título
        if len(linhas) > 1:
            messages.append({"role": "system", "content": "\n".join(linhas)})

    if history:
        for m in history:
            role = m.get("role")
            content = m.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": texto})

    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages
    )

    reply = (res.choices[0].message.content or "").strip()
    return formatar_html(reply) if html else reply
