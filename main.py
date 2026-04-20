from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8636942270:AAEj5XLPITknRVCpVliTT4HaoL1MGoIPHM4"

# Usuarios premium
usuarios_premium = set()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "📊 BIENVENIDO A ALPHABETS\n\n"

        "🚀 Sistema profesional de pronósticos deportivos basado en datos reales, análisis avanzado y gestión de riesgo.\n\n"

        "Aquí no vendemos humo ni promesas irreales.\n"
        "Trabajamos con metodología, disciplina y visión a largo plazo.\n\n"

        "📈 RESULTADOS DESTACADOS:\n"
        "✔️ Alto porcentaje de acierto sostenido\n"
        "✔️ Picks filtrados y seleccionados\n"
        "✔️ Estrategia enfocada en rentabilidad\n\n"

        "🧠 ¿Qué obtienes como usuario premium?\n"
        "• Picks diarios de alto valor\n"
        "• Análisis claros y directos\n"
        "• Gestión de banca profesional\n"
        "• Acceso a estrategia completa\n\n"

        "⚠️ Esto NO es para todo el mundo.\n"
        "Solo para personas que buscan consistencia y toman esto en serio.\n\n"

        "👇 Empieza ahora:\n"
        "/picks → prueba gratuita\n"
        "/planes → acceso premium"
    )

    with open("bienvenida.png", "rb") as foto:
        await update.message.reply_photo(photo=foto, caption=texto)

# /picks
async def picks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎁 PICK GRATUITO\n\n"
        "Partido: X vs Y\n"
        "Apuesta: Ambos marcan\n"
        "Cuota: 1.75\n\n"
        "👉 Para más picks accede a premium\n"
        "/planes"
    )

# /planes
async def planes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 PLANES\n\n"

        "🥉 Bronce\n"
        "• 1 pick diario\n\n"

        "🥈 Plata\n"
        "• 2-3 picks diarios\n\n"

        "🥇 Oro ⭐ MÁS POPULAR\n"
        "• 4-5 picks diarios\n\n"

        "💎 Diamante\n"
        "• todos los picks\n\n"

        "👉 /suscripcion"
    )

# /suscripcion
async def suscripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 PLANES DISPONIBLES\n\n"

        "📆 MENSUAL:\n"
        "🥉 Bronce — 14,99€\n"
        "🥈 Plata — 29,99€\n"
        "🥇 Oro — 49,99€ ⭐\n"
        "💎 Diamante — 89,99€\n\n"

        "🏆 ANUAL:\n"
        "🥉 Bronce — 99€\n"
        "🥈 Plata — 199€\n"
        "🥇 Oro — 349€\n"
        "💎 Diamante — 599€\n\n"

        "💬 Escribe el plan (ej: oro mensual)"
    )

# ENVIAR LINKS DE PAGO
async def elegir_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.lower()
    user_id = update.effective_user.id

    # MENSUAL
    if "bronce mensual" in texto:
        link = f"https://buy.stripe.com/dRm7sM1aY3Un1ND2Cabo400?client_reference_id={user_id}"
        await update.message.reply_text(f"💳 Pago seguro:\n{link}")

    elif "plata mensual" in texto:
        link = f"https://buy.stripe.com/00w28s9HugH90Jzgt0bo403?client_reference_id={user_id}"
        await update.message.reply_text(f"💳 Pago seguro:\n{link}")

    elif "oro mensual" in texto:
        link = f"https://buy.stripe.com/4gM5kEg5ScqTdwlekSbo402?client_reference_id={user_id}"
        await update.message.reply_text(f"💳 Pago seguro:\n{link}")

    elif "diamante mensual" in texto:
        link = f"https://buy.stripe.com/8x29AU1aYcqT9g52Cabo404?client_reference_id={user_id}"
        await update.message.reply_text(f"💳 Pago seguro:\n{link}")

    # ANUAL
    elif "bronce anual" in texto:
        link = f"https://buy.stripe.com/eVq9AU2f24YrfEt6Sqbo405?client_reference_id={user_id}"
        await update.message.reply_text(f"💳 Pago seguro:\n{link}")

    elif "plata anual" in texto:
        link = f"https://buy.stripe.com/28E14o5reaiL1ND5Ombo406?client_reference_id={user_id}"
        await update.message.reply_text(f"💳 Pago seguro:\n{link}")

    elif "oro anual" in texto:
        link = f"https://buy.stripe.com/dRm8wQ9HubmPeAp4Kibo407?client_reference_id={user_id}"
        await update.message.reply_text(f"💳 Pago seguro:\n{link}")

    elif "diamante anual" in texto:
        link = f"https://buy.stripe.com/eVqfZi06UcqTbod2Cabo408?client_reference_id={user_id}"
        await update.message.reply_text(f"💳 Pago seguro:\n{link}")
# ACTIVAR PREMIUM (MANUAL)
async def activar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    usuarios_premium.add(user_id)

    await update.message.reply_text("✅ Acceso premium activado")

# ENVIAR PICK A PREMIUM
async def enviarpick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "🔥 PICK PREMIUM\n\n"
        "Partido: X vs Y\n"
        "Apuesta: Over 2.5\n"
        "Cuota: 1.80\n\n"
        "📊 Confianza: Alta"
    )

    for user_id in usuarios_premium:
        try:
            await context.bot.send_message(chat_id=user_id, text=mensaje)
        except:
            pass

    await update.message.reply_text("📤 Pick enviado")

# INICIAR BOT
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("picks", picks))
app.add_handler(CommandHandler("planes", planes))
app.add_handler(CommandHandler("suscripcion", suscripcion))

app.add_handler(CommandHandler("activar", activar))
app.add_handler(CommandHandler("enviarpick", enviarpick))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_plan))

from flask import Flask, request
import stripe
from telegram import Bot
import threading

STRIPE_SECRET = "STRIPE_SECRET_KEY"

bot_flask = Bot(token=TOKEN)
app_flask = Flask(__name__)

stripe.api_key = STRIPE_SECRET

@app_flask.route('/webhook', methods=['POST'])
def webhook():
    event = request.json

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        user_id = session.get("client_reference_id")

        if user_id:
            user_id = int(user_id)
            usuarios_premium.add(user_id)

            bot_flask.send_message(
                chat_id=user_id,
                text="✅ Pago confirmado. Ya eres PREMIUM."
            )

    return "OK"

def run_flask():
    app_flask.run(port=5000)

threading.Thread(target=run_flask).start()


