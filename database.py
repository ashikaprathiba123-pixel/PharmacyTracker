import sqlite3

def create_db():
    conn = sqlite3.connect("pharmacy.db")
    cursor = conn.cursor()
    # This line adds the 'price' column
    cursor.execute("""CREATE TABLE IF NOT EXISTS medicines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        quantity INTEGER,
                        expiry_date TEXT,
                        price REAL)""")
    
    cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)")
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123')")
    conn.commit()
    conn.close()
    print("✅ JIOI Database Reset Complete!")

if __name__ == "__main__":
    create_db()