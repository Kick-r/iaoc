# Maggie — Mentora Virtual de Carreira (MVP)

## 1. Visão Geral

**Maggie** é uma aplicação web que implementa uma **mentora virtual de carreira** voltada ao apoio de jovens em processos iniciais de orientação profissional. O sistema foi construído no formato de **MVP** (Produto Mínimo Viável), priorizando funcionalidades essenciais: autenticação, criação e gerenciamento de conversas (chats), persistência de histórico e respostas geradas por IA, além de recurso opcional de síntese de áudio para acessibilidade.

A aplicação foi projetada para funcionar em ambiente local (desenvolvimento) e em produção com hospedagem na plataforma **Render**, utilizando banco **PostgreSQL** para garantir persistência real dos dados.

---

## 2. Objetivo do Projeto

O objetivo do sistema é oferecer um ambiente simples e acessível onde o usuário possa:

- Criar uma conta e autenticar-se com segurança;
- Informar dados básicos que ajudem a personalizar a experiência (ex.: idade, contexto e objetivo);
- Criar múltiplos chats e manter histórico de mensagens;
- Receber respostas da mentora virtual de forma clara e acolhedora;
- (Opcional) Ouvir respostas por síntese de voz.

---

## 3. Funcionalidades Implementadas (MVP)

### 3.1 Autenticação e Sessão
- Cadastro (`/auth/signup`)
- Login (`/auth/login`)
- Logout (`/auth/logout`)
- Verificação de sessão ativa (`/auth/me`)
- Sessão baseada em cookie (Flask session), com configurações de segurança para produção (HTTPS).

### 3.2 Sistema de Chats
- Criar chat (`POST /chats`)
- Listar chats do usuário (`GET /chats`)
- Renomear chat (`PUT /chats/<id>`)
- Deletar chat (`DELETE /chats/<id>`)
- Listar mensagens de um chat (`GET /chats/<id>/messages`)

### 3.3 Conversa com IA
- Envio de mensagem e resposta (`POST /chat`)
- Salvamento automático da mensagem do usuário e da resposta da IA no banco
- Uso de histórico recente (últimas mensagens) para coerência da conversa
- Uso de perfil do usuário (nome, idade, contexto e objetivo) para orientar respostas

### 3.4 Áudio (Opcional)
- Geração de áudio via TTS (quando disponível)
- Endpoint de acesso ao áudio (`GET /audio/<arquivo>`)
- Endpoint para remover arquivo após tocar (`DELETE /audio/<arquivo>/delete`)

---

## 4. Arquitetura e Organização do Projeto  
iaoc/  
├── app.py              # Servidor Flask, rotas e lógica principal  
├── db.py               # ORM SQLAlchemy e modelos do banco de dados  
├── ai.py               # Integração com IA (Groq) e formatação de saída  
├── tts.py              # Síntese de voz (edge-tts)  
├── requirements.txt    # Dependências do projeto  
├── README.md           # Documentação do projeto  
│  
├── templates/  
│   ├── index.html      # Interface principal do chat  
│   └── login.html      # Tela de login e cadastro  
│  
├── static/  
│   └── (opcional)      # Ícones, imagens e arquivos estáticos  
│  
└── audios/  
    └── (runtime)       # Arquivos de áudio gerados dinamicamente  

---

## 5. Tecnologias Utilizadas

### Back-end
- **Python**
- **Flask** (API e renderização das páginas HTML)
- **SQLAlchemy** (ORM e persistência)
- **Gunicorn** (servidor de aplicação para produção)
- **Werkzeug Security** (hash e verificação de senha)

### IA
- **Groq SDK** para comunicação com modelo LLM

### Banco de Dados
- **PostgreSQL** em produção (Render)
- Possibilidade de fallback local (SQLite), dependendo da configuração do `DATABASE_URL`

### TTS (Acessibilidade)
- **edge-tts** para gerar áudio de resposta

---

## 6. Banco de Dados

O sistema utiliza SQLAlchemy para modelagem e persistência.

### Entidades principais:
- **User**: dados do usuário, credenciais e perfil para personalização
- **Chat**: conversas vinculadas a um usuário
- **Message**: mensagens vinculadas a um chat, com papel (`user` ou `assistant`)

Relacionamentos:
- `User 1:N Chat`
- `Chat 1:N Message`

---

## 7. Configuração de Ambiente

### 7.1 Variáveis de Ambiente
O projeto depende das seguintes variáveis (principalmente em produção):

- `FLASK_SECRET_KEY`  
  Chave secreta para sessão (obrigatória em produção).

- `DATABASE_URL`  
  URL do banco. Em produção no Render, normalmente já é fornecida.

- `GROQ_API_KEY`  
  Chave para acesso à API Groq.

> Observação: Em Render, a variável `DATABASE_URL` pode vir como `postgres://...`.  
> O SQLAlchemy requer `postgresql://...`, então o `db.py` faz essa correção automaticamente.

---
Estrutura sugerida (referência):

