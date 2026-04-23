import sqlite3

def init_db():
    conn = sqlite3.connect('alphabets.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            plan TEXT DEFAULT 'gratis',
            fecha_inicio TIMESTAMP,
            fecha_fin TIMESTAMP,
            estado TEXT DEFAULT 'activo'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS afiliados (
            user_id INTEGER PRIMARY KEY,
            nombre_apellidos TEXT,
            email TEXT,
            metodo_cobro TEXT,
            datos_cobro TEXT,
            referred_by INTEGER,
            saldo_pendiente REAL DEFAULT 0.0,
            saldo_retirado REAL DEFAULT 0.0
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_db()