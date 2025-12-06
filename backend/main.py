import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI

# 1. Încărcăm variabilele de mediu
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Verificare cheie
if not api_key:
    raise ValueError("❌ NU am găsit cheia API! Verifică fișierul .env")

# 2. Configurare Client OpenAI
client = OpenAI(api_key=api_key)
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "SafeRoute AI Backend is running!"}

@app.get("/test-ai")
def test_ai():
    """Test rapid să vedem dacă AI-ul răspunde"""
    try:
        response = client.chat.completions.create(
            model="gpt-5-nano", # Folosește gpt-4o pentru hackathon dacă ai acces
            messages=[
                {"role": "system", "content": "Ești un expert în siguranță urbană."},
                {"role": "user", "content": "Salut! Dă-mi un sfat scurt de siguranță noaptea."}
            ]
        )
        return {"ai_response": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

# Pentru a rula serverul local: uvicorn main:app --reload