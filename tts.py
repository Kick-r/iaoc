import edge_tts
import uuid
import os

AUDIO_DIR = "audios"

async def gerar_audio(texto):
    nome = f"{uuid.uuid4()}.wav"
    caminho = os.path.join(AUDIO_DIR, nome)

    communicate = edge_tts.Communicate(
        texto,
        "pt-BR-FranciscaNeural"
    )

    await communicate.save(caminho)
    return nome
