from fastapi import FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai
import os
import time
import uvicorn

# Load environment
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY missing!")

genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(title="Jain Granthas RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-detect available models at startup
AVAILABLE_MODELS = None

def get_available_models():
    global AVAILABLE_MODELS
    if AVAILABLE_MODELS is not None:
        return AVAILABLE_MODELS
    
    print("🔍 Discovering available models...")
    models = []
    for model in genai.list_models():
        # Fix for list vs value attribute error
        methods = model.supported_generation_methods
        if isinstance(methods, list):
            if 'generateContent' in methods:
                models.append(model.name)
        else:
            if hasattr(methods, 'value') and 'generateContent' in methods.value:
                models.append(model.name)
    
    AVAILABLE_MODELS = models[:3]  # Top 3
    print(f"✅ Found models: {AVAILABLE_MODELS}")
    return AVAILABLE_MODELS

def get_first_working_model():
    models = get_available_models()
    if models:
        print(f"🎯 Using model: {models[0]}")
        return models[0]
    return "gemini-pro"  # Fallback

@app.get("/models")
async def list_models():
    models = get_available_models()
    return {"available_models": models, "recommended": models[0] if models else None}

@app.post("/upload_file/")
async def upload_file(file: UploadFile = File(...)):
    try:
        os.makedirs("tmp_uploads", exist_ok=True)
        tmp_path = f"tmp_uploads/{file.filename}"
        contents = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(contents)
        
        uploaded_file = genai.upload_file(path=tmp_path, display_name=file.filename)
        
        # Wait for processing
        for _ in range(30):
            if uploaded_file.state.name == "ACTIVE":
                break
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)
        
        os.remove(tmp_path)
        return {
            "message": f"✅ {file.filename} uploaded!",
            "file_name": uploaded_file.name,
            "state": uploaded_file.state.name
        }
    except Exception as e:
        return {"error": f"Upload failed: {str(e)}"}

@app.post("/invoke/tool/travel_agent_prompt")
async def travel_agent_prompt(request: Request):
    body = await request.json()
    user_input = body.get("input", {}).get("input", "")
    
    if not user_input:
        return {"result": {"output": "Please ask a question about Jain granthas!"}}
    
    try:
        # DYNAMIC MODEL - No more 404 errors!
        model_name = get_first_working_model()
        model = genai.GenerativeModel(model_name)
        
        # File context
        files = list(genai.list_files())[:3]
        file_names = [f.display_name for f in files]
        file_context = f"Files: {', '.join(file_names)}" if files else "No files"
        
        prompt = f"""
You are a Jain granthas expert.
{file_context}

Q: {user_input}
Answer concisely.
"""
        
        response = model.generate_content(prompt)
        answer = response.text
        
    except Exception as e:
        answer = f"Error: {str(e)}"
    
    return {
        "result": {
            "output": answer,
            "model_used": model_name,
            "files": [f.display_name for f in files]
        }
    }

@app.get("/")
async def root():
    model = get_first_working_model()
    files = list(genai.list_files())[:3]
    return {
        "message": "✅ Jain Granthas RAG LIVE!",
        "model": model,
        "files": [f.display_name for f in files],
        "status": "healthy"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000, reload=True)
