import sqlite3

conn = sqlite3.connect('rfid_system.db', check_same_thread=False)
c = conn.cursor()

# Crearea tabelei users
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                tag_id TEXT UNIQUE NOT NULL,
                gpio_pin INTEGER NOT NULL
              )''')

# Crearea tabelei access_log
c.execute('''CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_id TEXT NOT NULL,
                gpio_pin INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
              )''')

conn.commit()
