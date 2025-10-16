from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from openai import OpenAI
from uuid import uuid4
import shutil
import chromadb

# === CONFIG ===
app = FastAPI(title="Unicardealer Service Tech Assistant")

# Dominio del frontend admin e user (aggiungili qui)
origins = [
    "https://frontend-admin-five-psi.vercel.app",
    "https://frontend-user-seven.vercel.app",  # se hai anche quello
    "http://localhost:3000",                   # utile per test locale
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],     # <-- Importante
    allow_headers=["*"],     # <-- Importante
)

# === INIZIALIZZA CHROMA ===
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("pdf_chunks")

# === INIZIALIZZA OPENAI ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === CARTELLA PDF ===
PDF_FOLDER = "uploaded_pdfs"
os.makedirs(PDF_FOLDER, exist_ok=True)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.options("/{rest_of_path:path}")
def preflight_handler(rest_of_path: str):
    """Gestisce manualmente le richieste OPTIONS per i CORS"""
    return JSONResponse({"ok": True})

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), admin_token: str = Form(...)):
    if admin_token != os.getenv("ADMIN_TOKEN", "unicardealer_admin_2025"):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    file_id = str(uuid4())
    file_path = os.path.join(PDF_FOLDER, f"{file_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"message": "PDF caricato con successo", "file_id": file_id}

@app.get("/list_pdfs")
def list_pdfs():
    pdfs = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]
    return {"pdfs": pdfs}

@app.post("/chat")
async def chat(message: str = Form(...)):
    try:
        prompt = f"L'utente ha chiesto: '{message}'. Rispondi in modo professionale e tecnico, come un assistente esperto di assistenza meccanica e diagnostica auto."
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sei Unicardealer Service Tech Assistant, esperto tecnico meccanico."},
                {"role": "user", "content": prompt}
            ]
        )
        response_text = completion.choices[0].message.content
        return {"response": response_text}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
