import sqlite3

def agregar_columna_timestamp():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE pdfs ADD COLUMN timestamp TEXT;")
        conn.commit()
        print("✅ Columna 'timestamp' agregada correctamente (sin default).")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️  La columna 'timestamp' ya existe.")
        else:
            print("❌ Error:", e)

    conn.close()

if __name__ == "__main__":
    agregar_columna_timestamp()
