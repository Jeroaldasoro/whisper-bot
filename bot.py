import tempfile
import os
from faster_whisper import WhisperModel
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

TOKEN = os.environ["BOT_TOKEN"]
ALLOWED_USERS = {237456436, 770149239}

print("Cargando modelo Whisper...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Listo.")

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
        segments, _ = model.transcribe(tmp_path, language="es")
        texto = " ".join([s.text for s in segments]).strip()
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
            parser = PlaintextParser.from_string(texto, Tokenizer("spanish"))
            summarizer = LsaSummarizer()
            sentences = summarizer(parser.document, 3)
            resumen = " ".join([str(s) for s in sentences])
            if not resumen.strip():
                resumen = texto[:500] + ("..." if len(texto) > 500 else "")
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
