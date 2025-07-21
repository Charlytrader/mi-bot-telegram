import telebot
import sqlite3
from datetime import datetime

# === CONFIGURACIÓN ===
TOKEN = '8179098179:AAEWcZCyaj0KVfQARZrLj0EkNqp4Z4fTLM8'
ADMIN_ID = 6383544407

# === BASE DE DATOS ===
conn = sqlite3.connect('clientes.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    saldo REAL DEFAULT 0,
    rendimiento REAL DEFAULT 0
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    fecha TEXT,
    tipo TEXT,
    monto REAL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS config (
    clave TEXT PRIMARY KEY,
    valor REAL
)''')

cursor.execute("INSERT OR IGNORE INTO config (clave, valor) VALUES ('porcentaje', 0)")
conn.commit()

# === BOT ===
bot = telebot.TeleBot(TOKEN)

# === FUNCIONES ===
def registrar_usuario(user_id, username):
    cursor.execute("SELECT * FROM clientes WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO clientes (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()

def agregar_historial(user_id, tipo, monto):
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO historial (user_id, fecha, tipo, monto) VALUES (?, ?, ?, ?)", (user_id, fecha, tipo, monto))
    conn.commit()

def aplicar_rendimiento_manual():
    cursor.execute("SELECT valor FROM config WHERE clave = 'porcentaje'")
    porcentaje = cursor.fetchone()[0]
    if porcentaje <= 0:
        return
    cursor.execute("SELECT user_id, saldo FROM clientes")
    clientes = cursor.fetchall()
    for user_id, saldo in clientes:
        ganancia = saldo * (porcentaje / 100)
        cursor.execute("UPDATE clientes SET rendimiento = rendimiento + ? WHERE user_id = ?", (ganancia, user_id))
        agregar_historial(user_id, 'rendimiento', ganancia)
    conn.commit()

# === COMANDOS ===

@bot.message_handler(commands=['start'])
def start(message):
    registrar_usuario(message.from_user.id, message.from_user.username)
    bot.reply_to(message, "¡Bienvenido! Usa /saldo para ver tu inversión y ganancias.")

@bot.message_handler(commands=['saldo'])
def saldo(message):
    user_id = message.from_user.id
    cursor.execute("SELECT saldo, rendimiento FROM clientes WHERE user_id = ?", (user_id,))
    datos = cursor.fetchone()
    if datos:
        saldo, rendimiento = datos
        bot.reply_to(message, f"💰 Tu inversión: {saldo:.2f} USDT\n📈 Rendimiento acumulado: {rendimiento:.2f} USDT")
    else:
        bot.reply_to(message, "No estás registrado. Usa /start.")

@bot.message_handler(commands=['historial'])
def historial(message):
    user_id = message.from_user.id
    cursor.execute("SELECT fecha, tipo, monto FROM historial WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
    movimientos = cursor.fetchall()
    if movimientos:
        texto = "📋 Tus últimos movimientos:\n"
        for mov in movimientos:
            texto += f"{mov[0]} | {mov[1]} | {mov[2]:.2f} USDT\n"
        bot.reply_to(message, texto)
    else:
        bot.reply_to(message, "No tienes historial registrado.")

# === COMANDOS ADMIN ===

@bot.message_handler(commands=['acreditar'])
def acreditar(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        partes = message.text.split()
        username = partes[1].replace('@', '')
        monto = float(partes[2])
        cursor.execute("SELECT user_id FROM clientes WHERE username = ?", (username,))
        cliente = cursor.fetchone()
        if cliente:
            user_id = cliente[0]
            cursor.execute("UPDATE clientes SET saldo = saldo + ? WHERE user_id = ?", (monto, user_id))
            agregar_historial(user_id, 'depósito', monto)
            conn.commit()
            bot.reply_to(message, f"✅ {monto} USDT acreditados a @{username}")
        else:
            bot.reply_to(message, "❌ Usuario no encontrado.")
    except:
        bot.reply_to(message, "❗ Usa el comando así: /acreditar @usuario cantidad")

@bot.message_handler(commands=['setrendimiento'])
def setrendimiento(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        partes = message.text.split()
        porcentaje = float(partes[1])
        cursor.execute("UPDATE config SET valor = ? WHERE clave = 'porcentaje'", (porcentaje,))
        conn.commit()
        bot.reply_to(message, f"✅ Porcentaje de rendimiento mensual establecido a {porcentaje}%")
    except:
        bot.reply_to(message, "❗ Usa el comando así: /setrendimiento porcentaje")

@bot.message_handler(commands=['aplicar'])
def aplicar(message):
    if message.from_user.id != ADMIN_ID:
        return
    aplicar_rendimiento_manual()
    bot.reply_to(message, "✅ Rendimiento aplicado a todos los usuarios.")

# === INICIAR BOT ===
print("Bot activo...")
bot.infinity_polling()
