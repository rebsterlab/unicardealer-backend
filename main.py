from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from openai import OpenAI
from uuid import uuid4
import shutil
import chromadb

# === CONFIG ===
app = FastAPI(title="Unicardealer Service Tech Assistant")

# 👇 Domini autorizzati
origins = [
    "https://frontend-admin-five-psi.vercel.app",
    "https://frontend-user-seven.vercel.app",
    "http://localhost:3000",
]

# 👇 Middleware CORS universale
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# 👇 Gestisce tutte le richieste preflight (OPTIONS)
@app.options("/{path_name:path}")
def preflight_handler(path_name: str):
    return JSONResponse(
        content={"ok": True},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), admin_token: str = Form(...)):
    if admin_token != os.getenv("ADMIN_TOKEN", "unicardealer_admin_2025"):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    file_id = str(uuid4())
    file_path = os.path.join(PDF_FOLDER, f"{file_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return JSONResponse(
        {"message": "PDF caricato con successo", "file_id": file_id},
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.get("/list_pdfs")
def list_pdfs():
    pdfs = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]
    return JSONResponse(
        {"pdfs": pdfs},
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.post("/chat")
async def chat(message: str = Form(...)):
    try:
        prompt = (
            f"L'utente ha chiesto: '{message}'. "
            f"Rispondi in modo professionale e tecnico, come un assistente esperto di assistenza meccanica e diagnostica auto."
        )
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Sei Unicardealer Service Tech Assistant, esperto tecnico meccanico.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        response_text = completion.choices[0].message.content
        return JSONResponse(
            {"response": response_text},
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
