import os
import threading
import stripe
import requests
import json
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, ChatJoinRequestHandler, MessageHandler, filters

# === 1. CONFIGURACIÓN ===
TOKEN = os.environ.get("TOKEN", "TU_TOKEN")
stripe.api_key = os.environ.get("STRIPE_API_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# Tu ID de Jefe (Para los comandos de Admin y recibir datos de retiro)
TU_TELEGRAM_ID = "8000243455"

# Bases de datos
DB_FILE = "/data/database.json"
DB_AFILIADOS = "/data/afiliados.json"
DB_USUARIOS_TOTALES = "/data/users.json"

# Usuario de tu bot
BOT_USERNAME = "alphabetsia_bot"

# Comisiones (30% exacto de los precios base)
COMISIONES = {
    "bronce": 4.50,   
    "plata": 9.00,    
    "oro": 15.00,     
    "diamante": 27.00 
}

# 👇 REVISA QUE ESTOS SEAN TUS LINKS DE PAGO REALES DE STRIPE
LINKS_STRIPE = {
    "bronce": "https://buy.stripe.com/dRm7sM1aY3Un1ND2Cabo400",
    "plata": "https://buy.stripe.com/00w28s9HugH90Jzgt0bo403",
    "oro": "https://buy.stripe.com/4gM5kEg5ScqTdwlekSbo402",
    "diamante": "https://buy.stripe.com/8x29AU1aYcqT9g52Cabo404"
}

# Tus Canales Oficiales Integrados
CANALES_CONFIG = {
    "bronce": {"id": -1003556020198, "link": "https://t.me/+CebE1h3T3zczNDIx"},
    "plata": {"id": -1003932471723, "link": "https://t.me/+_6jSN2Gfeog2NjRh"},
    "oro": {"id": -1003953909208, "link": "https://t.me/+0EP2r82YeN82NjEx"},
    "diamante": {"id": -1003943835185, "link": "https://t.me/+1Z5xJp134gEyNTIx"}
}

# Semáforos de seguridad anti-colapsos
db_lock = threading.Lock()
afi_lock = threading.Lock()
esperando_datos = {}

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

# === 2. FUNCIONES DE BASE DE DATOS BLINDADAS ===
def cargar_json(archivo, defecto):
    if not os.path.exists(archivo): return defecto
    try:
        with open(archivo, "r") as f: return json.load(f)
    except: return defecto

def guardar_json(archivo, data):
    with db_lock:
        try:
            with open(archivo, "w") as f: json.dump(data, f)
        except Exception as e: print(f"Error guardando {archivo}: {e}")

def registrar_usuario_total(user_id):
    users = cargar_json(DB_USUARIOS_TOTALES, [])
    if str(user_id) not in users:
        users.append(str(user_id))
        guardar_json(DB_USUARIOS_TOTALES, users)

def registrar_clic_referido(nuevo_id, referidor_id):
    if str(nuevo_id) == str(referidor_id): return
    with afi_lock:
        data = cargar_json(DB_AFILIADOS, {"referidos_pendientes": {}, "usuarios": {}})
        if str(nuevo_id) not in data["referidos_pendientes"]:
            data["referidos_pendientes"][str(nuevo_id)] = str(referidor_id)
            with open(DB_AFILIADOS, "w") as f: json.dump(data, f)

def procesar_venta_afiliado(comprador_id, plan):
    with afi_lock:
        data = cargar_json(DB_AFILIADOS, {"referidos_pendientes": {}, "usuarios": {}})
        referidor_id = data["referidos_pendientes"].get(str(comprador_id))
        
        if referidor_id:
            if referidor_id not in data["usuarios"]:
                data["usuarios"][referidor_id] = {"ventas": 0, "saldo": 0.0}
            
            comision = COMISIONES.get(plan, 0)
            data["usuarios"][referidor_id]["ventas"] += 1
            data["usuarios"][referidor_id]["saldo"] += comision
            with open(DB_AFILIADOS, "w") as f: json.dump(data, f)
            return referidor_id, comision
        return None, 0

# === 3. COMANDOS DE ADMINISTRADOR (MODO DIOS) ===
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != TU_TELEGRAM_ID: return
    
    vips = cargar_json(DB_FILE, {})
    afiliados = cargar_json(DB_AFILIADOS, {"usuarios": {}})
    total_vips = len(vips)
    
    saldo_pendiente = sum(u.get('saldo', 0) for u in afiliados['usuarios'].values())
    ventas_totales = sum(u.get('ventas', 0) for u in afiliados['usuarios'].values())

    resumen = (
        "📊 *MODO DIOS - ALPHABETS*\n\n"
        f"👥 Clientes VIP activos: *{total_vips}*\n"
        f"🤝 Ventas de afiliados totales: *{ventas_totales}*\n"
        f"💰 Deuda total a afiliados: *{saldo_pendiente:.2f}€*\n\n"
        "🛠 *Tus Herramientas:*\n"
        "• `/db` - Descargar bases de datos\n"
        "• `/mensaje [texto]` - Envía un mensaje masivo a todos\n"
        "• `/pagado [ID]` - Notifica un pago a un afiliado"
    )
    await update.message.reply_text(resumen, parse_mode="Markdown")

async def enviar_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != TU_TELEGRAM_ID: return
    for file in [DB_FILE, DB_AFILIADOS, DB_USUARIOS_TOTALES]:
        if os.path.exists(file):
            try: await context.bot.send_document(chat_id=TU_TELEGRAM_ID, document=open(file, 'rb'))
            except Exception as e: print(f"Error enviando {file}: {e}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != TU_TELEGRAM_ID: return
    mensaje = " ".join(context.args)
    if not mensaje:
        await update.message.reply_text("Uso: `/mensaje Hola a todos los usuarios`")
        return
    
    users = cargar_json(DB_USUARIOS_TOTALES, [])
    exito = 0
    for u_id in users:
        try:
            await context.bot.send_message(chat_id=u_id, text=f"📢 *NOTIFICACIÓN ALPHABETS*\n\n{mensaje}", parse_mode="Markdown")
            exito += 1
        except: pass
    await update.message.reply_text(f"✅ Mensaje masivo enviado correctamente a {exito} usuarios.")

async def confirmar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != TU_TELEGRAM_ID: return
    if not context.args:
        await update.message.reply_text("Uso: `/pagado [ID_DEL_AFILIADO]`")
        return
    target_id = context.args[0]
    try:
        await context.bot.send_message(chat_id=target_id, text="✅ *¡PAGO ENVIADO!*\n\nEl administrador ha procesado tu retiro de afiliado y el dinero está en camino. ¡Gracias por formar parte del equipo Alphabets!", parse_mode="Markdown")
        await update.message.reply_text(f"✅ Notificación de pago enviada al usuario {target_id}.")
    except:
        await update.message.reply_text("❌ No se pudo enviar el mensaje. ¿Es correcta la ID?")

# === 4. LÓGICA DEL BOT PARA CLIENTES ===
async def enviar_menu_principal(chat_id, context, borrar_mensaje=None):
    botones = [[InlineKeyboardButton("💎 Ver Planes de Suscripción", callback_data="menu_planes")],
               [InlineKeyboardButton("🤝 Sistema de Afiliados", callback_data="menu_afiliados")]]
    
    try:
        if borrar_mensaje: await borrar_mensaje.delete()
        with open("bienvenida.png", "rb") as foto:
            await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=TEXTO_BIENVENIDA, reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")
    except:
        await context.bot.send_message(chat_id=chat_id, text=TEXTO_BIENVENIDA, reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    registrar_usuario_total(user_id)
    
    if context.args and context.args[0].startswith("ref_"):
        referidor_id = context.args[0].split("_")[1]
        registrar_clic_referido(user_id, referidor_id)
        
    await enviar_menu_principal(user_id, context)

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data == "menu_afiliados":
        with afi_lock:
            datos_afi = cargar_json(DB_AFILIADOS, {"usuarios": {}})
            stats = datos_afi["usuarios"].get(user_id, {"ventas": 0, "saldo": 0.0})
        
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        texto = (
            "🤝 *PANEL DE AFILIADO ALPHABETS*\n\n"
            f"🔗 *Tu enlace:* `{link}`\n\n"
            f"📊 *Estadísticas:*\n"
            f"• Ventas realizadas: *{stats['ventas']}*\n"
            f"• Saldo acumulado: *{stats['saldo']:.2f}€*\n\n"
            "⚠️ _Mínimo de retiro: 120.00€_"
        )
        
        botones = [[InlineKeyboardButton("💰 SOLICITAR RETIRO", callback_data="solicitar_retiro")]] if stats['saldo'] >= 120 else [[InlineKeyboardButton("⏳ Falta para el retiro", callback_data="falta_saldo")]]
        botones.append([InlineKeyboardButton("🔙 Volver", callback_data="menu_inicio")])
        
        try: await query.message.delete()
        except: pass
        
        try:
            with open("info_afiliados.jpg", "rb") as f:
                await context.bot.send_photo(chat_id=user_id, photo=f, caption=texto, reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")
        except:
            await context.bot.send_message(chat_id=user_id, text=texto, reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")

    elif data == "solicitar_retiro":
        botones = [
            [InlineKeyboardButton("🏦 Transferencia IBAN", callback_data="retiro_banco")],
            [InlineKeyboardButton("📱 Bizum", callback_data="retiro_bizum")],
            [InlineKeyboardButton("💳 PayPal", callback_data="retiro_paypal")],
            [InlineKeyboardButton("🪙 Crypto (USDC BSC)", callback_data="retiro_crypto")],
            [InlineKeyboardButton("🔙 Cancelar", callback_data="menu_afiliados")]
        ]
        await query.edit_message_caption("🏦 *Elige tu método de cobro:*", reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")

    elif data.startswith("retiro_"):
        metodo = data.split("_")[1]
        esperando_datos[user_id] = metodo 
        requisitos = {
            "banco": "tu *Nombre Completo* y tu *IBAN*",
            "bizum": "tu *Nombre Completo* y tu *Número de Teléfono*",
            "paypal": "tu *Nombre Completo* y tu *Correo de PayPal*",
            "crypto": "tu *Nombre Completo* y tu *Dirección USDC (Red BSC)*"
        }
        texto = f"Has elegido retirar por *{metodo.capitalize()}*.\n\n👇 Por favor, **escríbeme ahora mismo en un solo mensaje** {requisitos[metodo]} para procesar tu pago."
        await query.edit_message_caption(caption=texto, parse_mode="Markdown")

    elif data == "falta_saldo":
        await query.answer("Necesitas al menos 120€ para solicitar el retiro.", show_alert=True)

    elif data == "menu_planes":
        texto_planes = "💎 *PLANES DE SUSCRIPCIÓN*\n\n🥉 *BRONCE:* *14,99€/mes*\n🥈 *PLATA:* *29,99€/mes*\n🥇 *ORO:* *49,99€/mes*\n💎 *DIAMANTE:* *89,99€/mes*\n\n👇 *Selecciona un plan:*"
        botones = [[InlineKeyboardButton("🥉 Bronce", callback_data="plan_bronce"), InlineKeyboardButton("🥈 Plata", callback_data="plan_plata")],
                   [InlineKeyboardButton("🥇 Oro", callback_data="plan_oro"), InlineKeyboardButton("💎 Diamante", callback_data="plan_diamante")],
                   [InlineKeyboardButton("🔙 Volver", callback_data="menu_inicio")]]
        
        try: await query.message.delete()
        except: pass

        try:
            with open("detalles_planes.png", "rb") as f:
                await context.bot.send_photo(chat_id=user_id, photo=f, caption=texto_planes, reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")
        except:
            await context.bot.send_message(chat_id=user_id, text=texto_planes, reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")

    elif data.startswith("plan_"):
        plan = query.data.split("_")[1]
        url = f"{LINKS_STRIPE[plan]}?client_reference_id={user_id}_{plan}"
        texto = f"💳 *Suscripción {plan.upper()}*\n\nPulsa abajo para completar el pago seguro."
        await query.edit_message_caption(caption=texto, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 PAGAR AHORA", url=url)], [InlineKeyboardButton("🔙 Volver", callback_data="menu_planes")]]), parse_mode="Markdown")

    elif data == "menu_inicio":
        await enviar_menu_principal(user_id, context, borrar_mensaje=query.message)

# === 5. RECEPTOR DE DATOS DE RETIRO (Solo chat privado) ===
async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in esperando_datos:
        metodo = esperando_datos[user_id]
        datos_enviados = update.message.text
        
        with afi_lock:
            datos_afi = cargar_json(DB_AFILIADOS, {"usuarios": {}})
            saldo_actual = datos_afi["usuarios"].get(user_id, {}).get("saldo", 0.0)
            
            if saldo_actual >= 120:
                msg_jefe = (
                    f"🚨 *NUEVO RETIRO SOLICITADO*\n\n"
                    f"👤 *Afiliado:* `{user_id}` (@{update.effective_user.username})\n"
                    f"💰 *Cantidad a pagar:* {saldo_actual:.2f}€\n"
                    f"🏦 *Método:* {metodo.upper()}\n\n"
                    f"📝 *Datos del usuario:*\n`{datos_enviados}`"
                )
                try: 
                    await context.bot.send_message(chat_id=TU_TELEGRAM_ID, text=msg_jefe, parse_mode="Markdown")
                except Exception as e: 
                    print("Error notificando al jefe:", e)
                
                # Descontamos el saldo
                datos_afi["usuarios"][user_id]["saldo"] = 0.0
                with open(DB_AFILIADOS, "w") as f: json.dump(datos_afi, f)
                
                del esperando_datos[user_id]
                
                await update.message.reply_text("✅ *Datos recibidos con éxito.*\n\nTu solicitud ha sido enviada a nuestro equipo de pagos. Recibirás tu dinero en breve.", parse_mode="Markdown")
                await enviar_menu_principal(user_id, context)
            else:
                del esperando_datos[user_id]
                await update.message.reply_text("❌ Ha ocurrido un error o tu saldo es insuficiente.")

# === 6. EL "SEGURATA" DE LA ADUANA ===
async def manejador_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request_join = update.chat_join_request
    user_id = str(request_join.from_user.id)
    chat_id = str(request_join.chat.id)
    tiene_acceso = False
    
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                for cust_id, info in json.load(f).items():
                    if info.get("telegram_id") == user_id and str(CANALES_CONFIG.get(info.get("plan"), {}).get("id")) == chat_id:
                        tiene_acceso = True
                        break
        except: pass

    if tiene_acceso:
        await request_join.approve()
        try: await context.bot.send_message(chat_id=user_id, text="✅ *Acceso Concedido.*\n\nHe verificado tu suscripción. ¡Bienvenido al Canal VIP!", parse_mode="Markdown")
        except: pass
    else:
        await request_join.decline()
        try: await context.bot.send_message(chat_id=user_id, text="❌ *Acceso Denegado.*\n\nTu solicitud de unión ha sido rechazada porque no consta un pago activo para este canal, o tu suscripción ha expirado.", parse_mode="Markdown")
        except: pass

# === 7. WEBHOOK DE STRIPE ===
app_flask = Flask(__name__)

@app_flask.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    try: 
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception as e: 
        print(f"Webhook error: {e}")
        return jsonify(success=False), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        datos_cliente = session.get('client_reference_id')
        cust_id = session.get('customer')
        
        if datos_cliente and "_" in datos_cliente and cust_id:
            user_id, plan = datos_cliente.split('_')
            
            # Guardar en base de datos con seguro
            with db_lock:
                data_vip = cargar_json(DB_FILE, {})
                data_vip[cust_id] = {"telegram_id": user_id, "plan": plan}
                with open(DB_FILE, "w") as f: json.dump(data_vip, f)

            # Gestión de Afiliado
            referidor_id, comision = procesar_venta_afiliado(user_id, plan)
            if referidor_id:
                msg = f"🎉 *¡NUEVA VENTA!*\n\nHas ganado *{comision:.2f}€* por la venta del plan {plan.upper()} a uno de tus invitados."
                try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": referidor_id, "text": msg, "parse_mode": "Markdown"})
                except: pass

            # Mandar link al comprador
            link = CANALES_CONFIG.get(plan, {}).get('link', 'Enlace no configurado')
            try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": user_id, "text": f"✅ *¡PAGO CONFIRMADO!*\n\nHas adquirido el plan *{plan.upper()}*.\n\nÚnete a tu canal VIP exclusivo pulsando el siguiente enlace y el sistema te aprobará automáticamente:\n👉 {link}\n\n¡Mucha suerte!", "parse_mode": "Markdown"})
            except: pass

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        
        with db_lock:
            user_data = cargar_json(DB_FILE, {}).get(subscription.get('customer'))
        
        if user_data:
            t_id, plan = user_data['telegram_id'], user_data['plan']
            chat_id = CANALES_CONFIG.get(plan, {}).get("id")
            if chat_id:
                try: 
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/banChatMember", json={"chat_id": chat_id, "user_id": t_id})
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/unbanChatMember", json={"chat_id": chat_id, "user_id": t_id, "only_if_banned": True})
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": t_id, "text": "❌ *Suscripción Finalizada*\n\nTu suscripción ha terminado y el acceso al Canal VIP ha sido revocado. ¡Esperamos verte pronto!", "parse_mode": "Markdown"})
                except Exception as e: print(f"Error expulsando usuario: {e}")

    return jsonify(success=True)

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("🚀 Iniciando sistema completo ALPHABETS (Modo Dios Integrado)...")
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("db", enviar_db))
    app.add_handler(CommandHandler("mensaje", broadcast))
    app.add_handler(CommandHandler("pagado", confirmar_pago))
    
    # Botones, Textos y Aduana
    app.add_handler(CallbackQueryHandler(manejar_botones))
    app.add_handler(ChatJoinRequestHandler(manejador_solicitudes))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, manejar_texto))
    
    app.run_polling()