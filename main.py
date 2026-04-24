import os
import threading
import stripe
import requests
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# === 1. CONFIGURACIÓN ===
TOKEN = os.environ.get("TOKEN", "TU_TOKEN_POR_SI_ACASO")
stripe.api_key = os.environ.get("STRIPE_API_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# Tu ID de administrador ya puesto
ADMIN_ID = 8000243455 

# Archivo donde guardaremos a los clientes VIP
VIP_FILE = "usuarios_vip.txt"

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

# === 2. GESTIÓN DE USUARIOS VIP ===
def agregar_vip(user_id):
    user_id = str(user_id)
    if not os.path.exists(VIP_FILE):
        open(VIP_FILE, "w").close()
    
    with open(VIP_FILE, "r") as f:
        vips = f.read().splitlines()
    
    if user_id not in vips:
        with open(VIP_FILE, "a") as f:
            f.write(user_id + "\n")
        return True
    return False

def obtener_vips():
    if not os.path.exists(VIP_FILE):
        return []
    with open(VIP_FILE, "r") as f:
        return f.read().splitlines()

# === 3. LÓGICA DEL BOT ===
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

async def enviar_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Solo el admin puede usar esto: /enviar_pick MENSAJE
    if update.effective_user.id != ADMIN_ID:
        return

    mensaje = " ".join(context.args)
    if not mensaje:
        await update.message.reply_text("❌ Escribe algo: `/enviar_pick Gana Madrid...`", parse_mode="Markdown")
        return

    vips = obtener_vips()
    enviados = 0
    for uid in vips:
        try:
            await context.bot.send_message(chat_id=uid, text=f"🚀 *NUEVO PRONÓSTICO VIP*\n\n{mensaje}", parse_mode="Markdown")
            enviados += 1
        except: pass
    
    await update.message.reply_text(f"✅ Pick enviado a {enviados} usuarios VIP.")

async def ver_vips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Solo tú (el admin) puedes ver la lista
    if update.effective_user.id != ADMIN_ID:
        return

    vips = obtener_vips()
    if not vips:
        await update.message.reply_text("📭 Aún no tienes ningún usuario VIP.")
        return

    texto = f"👥 *Tienes {len(vips)} clientes VIP activos:*\n\n"
    for uid in vips:
        texto += f"• ID: `{uid}`\n"
    
    await update.message.reply_text(texto, parse_mode="Markdown")

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_planes":
        texto_planes = "🔥 *OFERTA POR TIEMPO LIMITADO*\n\n🥉 *BRONCE:* ~29,99€~ 👉 *19,99€*\n🥈 *PLATA:* ~59,99€~ 👉 *39,99€*\n🥇 *ORO:* ~89,99€~ 👉 *59,99€*\n💎 *DIAMANTE:* ~149,99€~ 👉 *99,99€*\n\n👇 *Toca un plan para activar (Recibirás los picks por privado):*"
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
        botones = [[InlineKeyboardButton("💎 Ver Planes de Suscripción", callback_data="menu_planes")], [InlineKeyboardButton("🤝 Sistema de Afiliados", callback_data="menu_afiliados")]]
        try:
            with open("bienvenida.png", "rb") as f:
                await query.edit_message_media(media=InputMediaPhoto(media=f, caption=TEXTO_BIENVENIDA, parse_mode="Markdown"), reply_markup=InlineKeyboardMarkup(botones))
        except: pass

# === 4. SERVIDOR WEB PARA RECIBIR PAGOS DE STRIPE ===
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot funcionando correctamente en Railway"

@app_flask.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception as e:
        return jsonify(success=False), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        user_id = session.get('client_reference_id') 
        
        if user_id:
            agregar_vip(user_id)
            texto_exito = "✅ *¡PAGO CONFIRMADO!*\n\nYa estás en la lista VIP. A partir de ahora recibirás todos nuestros pronósticos por este chat privado. ¡Mucha suerte!"
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": user_id, "text": texto_exito, "parse_mode": "Markdown"})

    return jsonify(success=True)

def run_flask():
    puerto = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=puerto)

# === 5. ARRANQUE DEL BOT ===
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("🚀 Iniciando bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("enviar_pick", enviar_pick))
    app.add_handler(CommandHandler("ver_vips", ver_vips)) # <-- ¡AQUÍ ESTÁ EL COMANDO QUE FALTABA!
    app.add_handler(CallbackQueryHandler(manejar_botones))
    app.run_polling()