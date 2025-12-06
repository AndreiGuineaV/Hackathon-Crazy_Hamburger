import sqlite3

def init_db():
    conn = sqlite3.connect('saferoute.db')
    cursor = conn.cursor()
    
    # Ștergem tabelele vechi dacă există (pentru a putea da reset ușor)
    cursor.execute('DROP TABLE IF EXISTS incidents')
    cursor.execute('DROP TABLE IF EXISTS safe_zones')

    # 1. Tabela Incidente
    cursor.execute('''
    CREATE TABLE incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        category TEXT,
        risk_score INTEGER,
        latitude REAL,
        longitude REAL,
        source TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        verified BOOLEAN DEFAULT 0
    )
    ''')

    # 2. Tabela Zone Sigure (Ex: Secții poliție)
    cursor.execute('''
    CREATE TABLE safe_zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        latitude REAL,
        longitude REAL,
        type TEXT
    )
    ''')
    
    # Adăugăm câteva date de test (Mock Data pentru demo)
    mock_incidents = [
        ("Grup suspect raportat în parc", "suspicious_group", 7, 44.4268, 26.1025, "user_report"),
        ("Iluminat stradal defect de 3 zile", "lighting", 4, 44.4300, 26.0900, "social_media"),
        ("Câini agresivi lângă școală", "dogs", 8, 44.4400, 26.1100, "news")
    ]
    
    cursor.executemany('''
    INSERT INTO incidents (description, category, risk_score, latitude, longitude, source)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', mock_incidents)

    conn.commit()
    conn.close()
    print("✅ Baza de date 'saferoute.db' a fost creată și populată cu date de test!")

if __name__ == "__main__":
    init_db()