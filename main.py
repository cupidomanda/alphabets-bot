import os
import threading
import stripe
import requests
import json
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, ChatJoinRequestHandler

# === 1. CONFIGURACIÓN ===
TOKEN = os.environ.get("TOKEN", "TU_TOKEN")
stripe.api_key = os.environ.get("STRIPE_API_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# Disco duro blindado de Railway para la Base de Datos
DB_FILE = "/data/database.json"

LINKS_STRIPE = {
    "bronce": "https://buy.stripe.com/dRm7sM1aY3Un1ND2Cabo400",
    "plata": "https://buy.stripe.com/00w28s9HugH90Jzgt0bo403",
    "oro": "https://buy.stripe.com/4gM5kEg5ScqTdwlekSbo402",
    "diamante": "https://buy.stripe.com/8x29AU1aYcqT9g52Cabo404"
}

# 👇 AQUÍ ES DONDE TIENES QUE RELLENAR TUS DATOS
CANALES_CONFIG = {
    "bronce": {"id": -1003556020198, "link": "https://t.me/+CebE1h3T3zczNDIx"},
    "plata": {"id": -1003932471723, "link": "https://t.me/+_6jSN2Gfeog2NjRh"},
    "oro": {"id": -1003953909208, "link": "https://t.me/+0EP2r82YeN82NjEx"},
    "diamante": {"id": -1003943835185, "link": "https://t.me/+1Z5xJp134gEyNTIx"}
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

# === 2. BASE DE DATOS SEGURA ===
def guardar_usuario(stripe_cust_id, telegram_id, plan):
    data = {}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: data = json.load(f)
        except: pass
    
    data[stripe_cust_id] = {"telegram_id": str(telegram_id), "plan": plan}
    with open(DB_FILE, "w") as f: json.dump(data, f)

def obtener_usuario(stripe_cust_id):
    if not os.path.exists(DB_FILE): return None
    try:
        with open(DB_FILE, "r") as f: data = json.load(f)
        return data.get(stripe_cust_id)
    except: return None

# === 3. LÓGICA DEL BOT DE TELEGRAM ===
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
        texto_planes = "🔥 *OFERTA POR TIEMPO LIMITADO*\n\n🥉 *BRONCE:* ~29,99€~ 👉 *19,99€*\n🥈 *PLATA:* ~59,99€~ 👉 *39,99€*\n🥇 *ORO:* ~89,99€~ 👉 *59,99€*\n💎 *DIAMANTE:* ~149,99€~ 👉 *99,99€*\n\n👇 *Toca un plan para activar (Recibirás acceso automático a tu canal):*"
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
        link = f"{LINKS_STRIPE[plan]}?client_reference_id={query.from_user.id}_{plan}"
        texto = f"💳 *Suscripción {plan.upper()}*\n\nPulsa abajo para completar el pago seguro.\n\n🚀 *El bot te enviará el enlace a tu Canal VIP tras el pago.*"
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

# === 4. EL "SEGURATA" DE LA PUERTA (Aprobar o Rechazar peticiones) ===
async def manejador_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request_join = update.chat_join_request
    user_id = str(request_join.from_user.id)
    chat_id = str(request_join.chat.id)
    
    tiene_acceso = False
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                for cust_id, info in data.items():
                    if info.get("telegram_id") == user_id:
                        plan_usuario = info.get("plan")
                        chat_id_plan = str(CANALES_CONFIG.get(plan_usuario, {}).get("id"))
                        if chat_id_plan == chat_id:
                            tiene_acceso = True
                            break
        except Exception: pass

    if tiene_acceso:
        await request_join.approve()
        try:
            await context.bot.send_message(chat_id=user_id, text="✅ *Acceso Concedido.*\n\nHe verificado tu suscripción. ¡Bienvenido al Canal VIP!", parse_mode="Markdown")
        except: pass
    else:
        await request_join.decline()
        try:
            await context.bot.send_message(chat_id=user_id, text="❌ *Acceso Denegado.*\n\nTu solicitud de unión ha sido rechazada porque no consta un pago activo para este canal.", parse_mode="Markdown")
        except: pass

# === 5. WEBHOOK (PAGOS Y EXPULSIONES) ===
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot de Alphabets funcionando correctamente"

@app_flask.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception:
        return jsonify(success=False), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        datos_cliente = session.get('client_reference_id') 
        cust_id = session.get('customer')
        
        if datos_cliente and "_" in datos_cliente and cust_id:
            try:
                user_id, plan_comprado = datos_cliente.split('_')
                guardar_usuario(cust_id, user_id, plan_comprado)
                
                link_canal = CANALES_CONFIG.get(plan_comprado, {}).get("link", "Enlace no configurado.")
                texto_exito = f"✅ *¡PAGO CONFIRMADO!*\n\nHas adquirido el plan *{plan_comprado.upper()}*.\n\nÚnete a tu canal VIP exclusivo pulsando el siguiente enlace y el sistema te aprobará automáticamente:\n👉 {link_canal}\n\n¡Mucha suerte!"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": user_id, "text": texto_exito, "parse_mode": "Markdown"})
            except Exception as e: print(e)

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        cust_id = subscription.get('customer')
        user_data = obtener_usuario(cust_id)
        
        if user_data:
            t_id = user_data['telegram_id']
            plan = user_data['plan']
            chat_id = CANALES_CONFIG.get(plan, {}).get("id")
            
            if chat_id:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/banChatMember", json={"chat_id": chat_id, "user_id": t_id})
                requests.post(f"https://api.telegram.org/bot{TOKEN}/unbanChatMember", json={"chat_id": chat_id, "user_id": t_id, "only_if_banned": True})
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": t_id, "text": "❌ *Suscripción Finalizada*\n\nTu suscripción ha terminado y el acceso al Canal VIP ha sido revocado.", "parse_mode": "Markdown"})

    return jsonify(success=True)

def run_flask():
    puerto = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=puerto)

# === 6. ARRANQUE DEL BOT ===
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("🚀 Iniciando bot Aduana...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    app.add_handler(ChatJoinRequestHandler(manejador_solicitudes))
    app.run_polling()