import streamlit as st
import sqlite3
import os
import datetime
from openai import OpenAI
from pydantic import BaseModel, Field
from duckduckgo_search import DDGS
from typing import Optional

# --- CONFIGURARE ---
# PUNE CHEIA TA AICI
API_KEY = ""
client = OpenAI(api_key=API_KEY)

DB_NAME = 'travel_advisor_pro.db'

# --- 1. CONFIGURARE BAZA DE DATE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS search_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  user_query TEXT,
                  location_resolved TEXT,
                  worth_visiting_score INTEGER,
                  summary_text TEXT)''')
    conn.commit()
    conn.close()

def save_interaction(query, location, score, summary):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO search_history (timestamp, user_query, location_resolved, worth_visiting_score, summary_text) VALUES (?, ?, ?, ?, ?)",
                  (timestamp, query, location, score, summary))
        conn.commit()
        conn.close()
    except: pass

# --- 2. STRUCTURA DATELOR (PYDANTIC) ---

# A. VALIDATOR DE LOCAȚIE
class LocationValidation(BaseModel):
    is_valid: bool = Field(..., description="True DOAR dacă inputul este un oraș, țară, regiune, insulă sau atracție turistică. False pentru concepte abstracte, persoane, mâncare, gibberish.")
    canonical_name: Optional[str] = Field(None, description="Numele geografic corect (ex: 'Rome, Italy') dacă e valid.")
    refusal_reason: Optional[str] = Field(None, description="Motivul refuzului (ex: 'Acesta este un nume de persoană, nu un oraș').")

# B. RAPORTUL TURISTIC
class TravelAnalysis(BaseModel):
    nume_oficial: str = Field(..., description="Numele canonic al locului")
    
    # INDICI
    scor_siguranta: int = Field(..., description="1-10")
    text_siguranta: str = Field(..., description="Analiză siguranță")
    sursa_siguranta_tip: str = Field(..., description="'WEB' sau 'AI_MEMORY'")

    scor_cultura: int = Field(..., description="1-10")
    text_cultura: str = Field(..., description="Analiză atracții")
    sursa_cultura_tip: str = Field(..., description="'WEB' sau 'AI_MEMORY'")

    scor_costuri: int = Field(..., description="1-10")
    text_costuri: str = Field(..., description="Analiză costuri")
    sursa_costuri_tip: str = Field(..., description="'WEB' sau 'AI_MEMORY'")

    scor_oportunitate: int = Field(..., description="Media ponderată")
    verdict_final: str = Field(..., description="Concluzie")

# --- 3. FUNCȚII ---

def validate_input_step(user_input):
    """
    PASUL 0: Validăm dacă inputul este geografic.
    """
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "Ești un filtru geografic strict. Răspunde cu is_valid=False dacă utilizatorul introduce nume de persoane, mâncare, concepte abstracte sau text fără sens. Răspunde cu is_valid=True doar pentru LOCAȚII FIZICE."},
                {"role": "user", "content": f"Analizează acest text: '{user_input}'"}
            ],
            response_format=LocationValidation,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        # Fallback de siguranță
        return LocationValidation(is_valid=True, canonical_name=user_input)

def search_segment(query, keywords):
    ddgs = DDGS()
    text_blob = ""
    links = []
    full_query = f"{query} {keywords}"
    try:
        results = ddgs.text(full_query, max_results=3)
        if results:
            for r in results:
                text_blob += f"SOURCE: {r['title']} | CONTENT: {r['body']}\n"
                links.append(f"{r['title']} ({r['href']})")
    except: pass
    return text_blob, links

def get_agent_response(location):
    
    # 1. Culegem Date
    raw_safety, links_safety = search_segment(location, "safety crime rates tourist danger scams warning")
    raw_culture, links_culture = search_segment(location, "tourist attractions things to do culture history landmarks")
    raw_cost, links_cost = search_segment(location, "travel prices cost of living transport guide hotel price food")
    
    # 2. Prompt Hibrid
    full_context = f"""
    LOCAȚIA: {location}
    === DATE WEB SIGURANȚĂ ===
    {raw_safety if raw_safety else "LIPSA DATE WEB."}
    === DATE WEB CULTURĂ ===
    {raw_culture if raw_culture else "LIPSA DATE WEB."}
    === DATE WEB COSTURI ===
    {raw_cost if raw_cost else "LIPSA DATE WEB."}
    
    INSTRUCȚIUNI:
    - Analizează datele.
    - Dacă ai date web, folosește-le (sursa='WEB'). Altfel 'AI_MEMORY'.
    - Generează scoruri 1-10.
    """

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "Ești un expert Travel Advisor."},
                {"role": "user", "content": full_context}
            ],
            response_format=TravelAnalysis,
        )
        report = completion.choices[0].message.parsed
        all_links = list(set(links_safety + links_culture + links_cost))
        return report, all_links
    except Exception as e:
        st.error(f"Eroare AI: {e}")
        return None, []

# --- 4. INTERFAȚA ---
def main():
    st.set_page_config(page_title="Travel Index Pro", layout="wide", page_icon="🌍")
    init_db()

    st.title("🌍 Travel Index Pro")
    st.markdown("Sistem Inteligent de Analiză Turistică (cu Validare Geografică)")

    # Istoric Sidebar
    with st.sidebar:
        st.header("🗂️ Istoric")
        if st.button("Refresh"):
            conn = sqlite3.connect(DB_NAME)
            df = conn.execute("SELECT location_resolved, worth_visiting_score FROM search_history ORDER BY id DESC LIMIT 5").fetchall()
            conn.close()
            for r in df:
                st.text(f"{r[0]} ({r[1]}/10)")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("is_error"):
                st.error(msg["content"])
            else:
                st.markdown(msg["content"])

    if prompt := st.chat_input("Introdu destinația (ex: Roma, Tokyo)..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            
            # --- FAZA 1: VALIDARE ---
            with st.spinner("🕵️ Validez locația..."):
                validation = validate_input_step(prompt)
            
            if not validation.is_valid:
                # --- CAZ INVALID: AFIȘĂM EROARE ---
                error_text = f"❌ **Eroare:** Nu s-a identificat o locație de pe glob.\n\n*Motiv:* {validation.refusal_reason}\n\nTe rog introdu un oraș, o țară sau o regiune validă."
                st.error(error_text)
                st.session_state.messages.append({"role": "assistant", "content": error_text, "is_error": True})
            
            else:
                # --- CAZ VALID: CONTINUĂM ---
                real_loc = validation.canonical_name
                st.success(f"✅ Locație confirmată: **{real_loc}**")
                
                with st.spinner(f"🔍 Scanez internetul pentru {real_loc}..."):
                    raport, surse = get_agent_response(real_loc)
                
                if raport:
                    # HEADER
                    st.subheader(f"📍 {raport.nume_oficial}")
                    
                    col_main, col_detail = st.columns([1, 2])
                    with col_main:
                        st.metric("✅ INDICE OPORTUNITATE", f"{raport.scor_oportunitate}/10",
                                  delta="Recomandat" if raport.scor_oportunitate >= 7 else "Grijă Mare")
                    with col_detail:
                        st.info(f"**Verdict:** {raport.verdict_final}")

                    st.divider()

                    # INDICI
                    # A. Siguranță
                    c1, c2 = st.columns([1, 4])
                    c1.metric("🛡️ Siguranță", f"{raport.scor_siguranta}/10", 
                              delta_color="inverse" if raport.scor_siguranta < 6 else "normal", 
                              delta="Risc" if raport.scor_siguranta < 6 else "Ok")
                    c2.markdown("**Analiză Siguranță:**")
                    c2.write(raport.text_siguranta)
                    c2.caption(f"Sursă: {'🌐 Internet Live' if raport.sursa_siguranta_tip == 'WEB' else '🧠 AI Memory'}")
                    st.divider()

                    # B. Cultură
                    c1, c2 = st.columns([1, 4])
                    c1.metric("🎨 Cultură", f"{raport.scor_cultura}/10")
                    c2.markdown("**Analiză Atracții:**")
                    c2.write(raport.text_cultura)
                    # AICI AM SCOS LINIA PROBLEMATICĂ CU IMAGINEA
                    c2.caption(f"Sursă: {'🌐 Internet Live' if raport.sursa_cultura_tip == 'WEB' else '🧠 AI Memory'}")
                    st.divider()

                    # C. Costuri
                    c1, c2 = st.columns([1, 4])
                    c1.metric("💰 Costuri", f"{raport.scor_costuri}/10")
                    c2.markdown("**Analiză Buget:**")
                    c2.write(raport.text_costuri)
                    c2.caption(f"Sursă: {'🌐 Internet Live' if raport.sursa_costuri_tip == 'WEB' else '🧠 AI Memory'}")

                    # Surse
                    if surse:
                        with st.expander("🔗 Vezi Sursele Web Utilizate"):
                            for s in surse: st.markdown(f"- {s}")
                    else:
                        st.caption("⚠️ Nu s-au folosit surse web directe.")

                    # Salvare
                    save_interaction(prompt, real_loc, raport.scor_oportunitate, raport.verdict_final)
                    st.session_state.messages.append({"role": "assistant", "content": raport.verdict_final})

if __name__ == "__main__":
    main()