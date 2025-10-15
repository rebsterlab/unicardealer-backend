from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uuid import uuid4
import os, shutil, chromadb
from openai import OpenAI

app = FastAPI(title="Unicardealer Service Tech Assistant")

# ✅ Imposta CORS per tutte le origini
origins = [
    "https://service-assistant-frontend.vercel.app",  # frontend pubblico
    "https://service-admin-frontend.vercel.app",      # admin
    "http://localhost:3000",                          # per test locali
    "*"                                                # fallback
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Middleware di emergenza per aggiungere CORS anche sugli errori
@app.middleware("http")
async def add_cors_on_error(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception as e:
        response = JSONResponse({"detail": str(e)}, status_code=500)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response









# === CARTELLA PDF ===
PDF_FOLDER = "uploaded_pdfs"
os.makedirs(PDF_FOLDER, exist_ok=True)

# === CHROMA DB ===
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("pdf_chunks")

# === OPENAI ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === ENDPOINT DI STATO ===
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# === UPLOAD PDF (solo amministratore) ===
@app.post("/upload")
async def upload_pdf(
    admin_token: str = Form(...),
    file: UploadFile = File(...)
):
    """Carica un PDF se il token amministratore è valido"""
    expected_token = os.getenv("ADMIN_TOKEN", "unicardealer_admin_2025")
    if admin_token != expected_token:
        raise HTTPException(status_code=403, detail="Token amministratore non valido")

    try:
        file_id = str(uuid4())
        file_path = os.path.join(PDF_FOLDER, f"{file_id}_{file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": "PDF caricato con successo", "file_id": file_id, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'upload: {str(e)}")

# === LISTA PDF CARICATI ===
@app.get("/list_pdfs")
async def list_pdfs():
    pdfs = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]
    return {"pdfs": pdfs}

# === CHAT (assistente tecnico) ===
@app.post("/chat")
async def chat(message: str = Form(...)):
    """Risponde alle domande tecniche dell'utente"""
    try:
        prompt = (
            f"L'utente ha chiesto: '{message}'. "
            "Rispondi in modo chiaro, tecnico e professionale, come un esperto meccanico e diagnostico di veicoli. "
            "Se non hai dati sufficienti, chiedi gentilmente maggiori dettagli."
        )

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sei Unicardealer Service Tech Assistant, un esperto di assistenza e diagnostica veicoli."},
                {"role": "user", "content": prompt}
            ]
        )

        response_text = completion.choices[0].message.content
        return {"response": response_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante la generazione della risposta: {str(e)}")
