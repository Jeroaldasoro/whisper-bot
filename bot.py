import tempfile
import os
import httpx
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TOKEN = os.environ["BOT_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
ALLOWED_USERS = {237456436, 770149239}

ultima_transcripcion = {}


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return

    await update.message.reply_text("Transcribiendo...")

    voice = update.message.voice or update.message.audio
    file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    await file.download_to_drive(tmp_path)

    try:
        with open(tmp_path, "rb") as audio_file:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    files={"file": ("audio.ogg", audio_file, "audio/ogg")},
                    data={"model": "whisper-large-v3", "language": "es"},
                    timeout=60,
                )
        response.raise_for_status()
        texto = response.json()["text"].strip()
        ultima_transcripcion[update.effective_user.id] = texto
        await update.message.reply_text(f"Transcripcion:\n\n{texto}\n\nEscribi RESUMIR para obtener un resumen.")
    except Exception as e:
        await update.message.reply_text(f"Error al transcribir: {e}")
    finally:
        os.unlink(tmp_path)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return

    mensaje = update.message.text.strip().upper()

    if mensaje == "RESUMIR":
        texto = ultima_transcripcion.get(update.effective_user.id)
        if not texto:
            await update.message.reply_text("No hay ninguna transcripcion reciente para resumir.")
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    json={
                        "model": "llama3-8b-8192",
                        "messages": [
                            {"role": "user", "content": f"Resume este texto en 3 oraciones cortas en español:\n\n{texto}"}
                        ],
                    },
                    timeout=30,
                )
            response.raise_for_status()
            resumen = response.json()["choices"][0]["message"]["content"].strip()
            await update.message.reply_text(f"Resumen:\n\n{resumen}")
        except Exception as e:
            await update.message.reply_text(f"Error al resumir: {e}")
    else:
        await update.message.reply_text("Manda un audio para transcribir, o escribe RESUMIR despues de una transcripcion.")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot corriendo...")
    app.run_polling()


if __name__ == "__main__":
    main()
