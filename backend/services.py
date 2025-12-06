import sqlite3
import json
import random
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. CONFIGURARE ROBUSTĂ PENTRU .ENV ---
# Asta rezolvă problema cu "nu găsesc fișierul .env"
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# --- 2. COMPONENTA DE SCRAPING (SIMULATĂ PENTRU HACKATHON) ---
def scrape_social_media():
    """
    În loc să ne chinuim cu API-uri de Twitter/Facebook care necesită aprobări lungi,
    simulăm date care arată EXACT ca niște postări reale.
    """
    print("📡 Scanez sursele de informații...")
    
    # Acestea sunt exemple de texte "raw" pe care le-ar găsi scraper-ul
    raw_posts = [
        "Am fost atacat de o haită de câini în Parcul IOR lângă lac, aveți grijă!",
        "Nu merge iluminatul public pe strada Zidurilor de 3 zile, e beznă totală.",
        "Accident grav la intersecția Unirii, trafic blocat și poliție peste tot.",
        "Grup de indivizi dubioși care sparg semințe și fac scandal la scara blocului pe Bd. Basarabia.",
        "S-a furat o bicicletă din curtea școlii 195, camerele nu merg."
    ]
    return raw_posts

# --- 3. COMPONENTA DE CLASIFICARE AI ---
def analyze_incident_with_ai(text):
    """
    Trimite textul la GPT și primește înapoi un JSON structurat.
    """
    print(f"🤖 Analizez incidentul: '{text}'...")
    
    prompt = f"""
    Ești un expert în siguranță urbană pentru București. Analizează textul: "{text}".
    
    Trebuie să extragi următoarele date în format JSON strict:
    1. "category": alege una din [theft, assault, dogs, lighting, accident, suspicious_group, other]
    2. "risk_score": un număr întreg de la 1 (inofensiv) la 10 (pericol de moarte)
    3. "latitude": estimează o coordonată realistă pentru București (aprox 44.4...)
    4. "longitude": estimează o coordonată realistă pentru București (aprox 26.1...)
    
    Răspunde DOAR cu JSON-ul, fără alte explicații.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Sau "gpt-4o" dacă ai acces
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        # Curățăm eventualele markeri de cod ```json ... ```
        content = content.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(content)
        return data
    except Exception as e:
        print(f"❌ Eroare AI: {e}")
        return None

# --- 4. SALVARE ÎN BAZA DE DATE ---
def save_incident_to_db(description, data):
    conn = sqlite3.connect('saferoute.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO incidents (description, category, risk_score, latitude, longitude, source, verified)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        description, 
        data['category'], 
        data['risk_score'], 
        data['latitude'], 
        data['longitude'], 
        'social_media_scan', 
        1
    ))
    
    conn.commit()
    conn.close()
    print(f"✅ Incident salvat: {data['category']} (Risc: {data['risk_score']})")

# --- FUNCȚIA PRINCIPALĂ CARE LE LEAGĂ PE TOATE ---
def run_data_pipeline():
    posts = scrape_social_media()
    count = 0
    
    for post in posts:
        ai_data = analyze_incident_with_ai(post)
        if ai_data:
            save_incident_to_db(post, ai_data)
            count += 1
            
    return {"status": "success", "new_incidents": count}

# Putem rula fișierul direct ca să testăm: python services.py
if __name__ == "__main__":
    run_data_pipeline()