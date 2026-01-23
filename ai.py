from groq import Groq
import os
import re
from typing import List, Optional, Dict

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
"""
}


def formatar_html(texto: str) -> str:
    """
    Formatação simples e segura:
    - Converte quebras de linha em <br>
    - Separa parágrafos com <hr> quando houver linha em branco
    """
    if not isinstance(texto, str):
        return ""

    t = texto.strip()
    t = t.replace("\r\n", "\n").replace("\r", "\n")

    partes = [p.strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
    partes = [p.replace("\n", "<br>") for p in partes]

    return "<hr>".join(partes)


def responder(
    texto: str,
    history: Optional[List[Dict]] = None,
    user_profile: Optional[Dict] = None,
    html: bool = True
) -> str:
    """
    texto: mensagem atual do usuário
    history: histórico do chat
    user_profile: infos do cadastro (SEM email/senha)
    """

    messages = [SYSTEM_MESSAGE]

    # 🔹 CONTEXTO DO USUÁRIO (vem do cadastro)
    if user_profile:
        perfil = f"""
Contexto do usuário (use apenas para orientar melhor suas respostas):
Nome: {user_profile.get("name")}
Idade: {user_profile.get("age")}
Situação atual: {user_profile.get("context")}
Objetivo: {user_profile.get("goal")}
"""
        messages.append({
            "role": "system",
            "content": perfil.strip()
        })

    # 🔹 histórico do chat
    if history:
        for m in history:
            role = m.get("role")
            content = m.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content})

    # 🔹 mensagem atual
    messages.append({"role": "user", "content": texto})

    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages
    )

    reply = res.choices[0].message.content or ""

    return formatar_html(reply) if html else reply
