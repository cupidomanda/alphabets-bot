import os
import threading
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# === 1. CONFIGURACIÓN ===
TOKEN = "8636942270:AAE-JyJVhfhTlbCiYixGaF3FLfTkbLWN-f8"

LINKS_STRIPE = {
    "bronce": "https://buy.stripe.com/dRm7sM1aY3Un1ND2Cabo400",
    "plata": "https://buy.stripe.com/00w28s9HugH90Jzgt0bo403",
    "oro": "https://buy.stripe.com/4gM5kEg5ScqTdwlekSbo402",
    "diamante": "https://buy.stripe.com/8x29AU1aYcqT9g52Cabo404"
}

TEXTO_BIENVENIDA = (
    "🏛 *Bienvenido a ALPHABETS | Inversión Deportiva Inteligente*\n\n"
    "No somos un canal de apuestas tradicional. Aquí no verás promesas de hacerte rico de la noche a la mañana.\n\n"
    "Nos basamos en *análisis estadístico, gestión de banca estricta y rentabilidad a largo plazo*. "
    "Nuestra filosofía es clara: priorizamos siempre la calidad sobre la cantidad de picks.\n\n"
    "📊 *¿Qué encontrarás aquí?*\n"
    "• Pronósticos filtrados de alto valor.\n"
    "• Control de riesgo absoluto.\n"
    "• Transparencia total en nuestros resultados.\n\n"
    "👇 *Selecciona una opción abajo para empezar:*"
)

# === 2. LÓGICA DEL BOT (START Y BOTONES) ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    teclado = [
        [InlineKeyboardButton("💎 Ver Planes de Suscripción", callback_data="menu_planes")],
        [InlineKeyboardButton("🤝 Sistema de Afiliados", callback_data="menu_afiliados")]
    ]
    reply_markup = InlineKeyboardMarkup(teclado)
    try:
        with open("bienvenida.png", "rb") as foto:
            await context.bot.send_photo(chat_id=user_id, photo=foto, caption=TEXTO_BIENVENIDA, reply_markup=reply_markup, parse_mode="Markdown")
    except:
        await update.message.reply_text(TEXTO_BIENVENIDA, reply_markup=reply_markup, parse_mode="Markdown")

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_planes":
        texto_planes = "🔥 *OFERTA POR TIEMPO LIMITADO*\n\n🥉 *BRONCE:* ~29,99€~ 👉 *19,99€*\n🥈 *PLATA:* ~59,99€~ 👉 *39,99€*\n🥇 *ORO:* ~89,99€~ 👉 *59,99€*\n💎 *DIAMANTE:* ~149,99€~ 👉 *99,99€*\n\n👇 *Toca un plan para activar:*"
        botones = [
            [InlineKeyboardButton("🥉 Bronce", callback_data="plan_bronce"), InlineKeyboardButton("🥈 Plata", callback_data="plan_plata")],
            [InlineKeyboardButton("🥇 Oro", callback_data="plan_oro"), InlineKeyboardButton("💎 Diamante", callback_data="plan_diamante")],
            [InlineKeyboardButton("🔙 Volver al Inicio", callback_data="menu_inicio")]
        ]
        try:
            with open("detalles_planes.png", "rb") as f:
                await query.edit_message_media(media=InputMediaPhoto(media=f, caption=texto_planes, parse_mode="Markdown"), reply_markup=InlineKeyboardMarkup(botones))
        except: pass

    elif data.startswith("plan_"):
        plan = data.split("_")[1]
        link = f"{LINKS_STRIPE[plan]}?client_reference_id={query.from_user.id}"
        texto = f"💳 *Suscripción {plan.upper()}*\n\nPulsa abajo para completar el pago seguro.\n\n🚀 *Acceso inmediato tras el pago.*"
        botones = [[InlineKeyboardButton("🔥 PAGAR CON DESCUENTO", url=link)], [InlineKeyboardButton("🔙 Volver a Planes", callback_data="menu_planes")]]
        await query.edit_message_caption(caption=texto, reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")

    elif data == "menu_afiliados":
        texto_afi = "🤝 *SISTEMA DE AFILIADOS ALPHABETS*\n\nGana el **30% de cada pago mensual** que realicen tus referidos, de por vida."
        try:
            with open("info_afiliados.jpg", "rb") as f:
                await query.edit_message_media(media=InputMediaPhoto(media=f, caption=texto_afi, parse_mode="Markdown"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Inicio", callback_data="menu_inicio")]]))
        except: pass

    elif data == "menu_inicio":
        botones = [[InlineKeyboardButton("💎 Ver Planes", callback_data="menu_planes")], [InlineKeyboardButton("🤝 Afiliados", callback_data="menu_afiliados")]]
        try:
            with open("bienvenida.png", "rb") as f:
                await query.edit_message_media(media=InputMediaPhoto(media=f, caption=TEXTO_BIENVENIDA, parse_mode="Markdown"), reply_markup=InlineKeyboardMarkup(botones))
        except: pass

# === 3. SERVIDOR WEB PARA STRIPE (FLASK) ===
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot funcionando correctamente"

@app_flask.route('/webhook', methods=['POST'])
def webhook():
    # Aquí es donde Stripe enviará la confirmación (lo configuraremos luego)
    return jsonify(success=True)

def run_flask():
    # CAMBIO PARA RAILWAY: Usar el puerto que nos asigne el servidor
    puerto = int(os.environ.get("PORT", 5000))
    app_flask.run(host='0.0.0.0', port=puerto)

# === 4. ARRANQUE DEL BOT ===
if __name__ == "__main__":
    # Arrancamos el servidor web en un hilo aparte
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Arrancamos Telegram
    print("🚀 Iniciando bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    app.run_polling()