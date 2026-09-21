from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from src.pipeline.match_pipeline import MatchPipeline

app = FastAPI(title="ResuMatch Advanced NLP Resume-JD Analyzer", version="2.1.0")
templates = Jinja2Templates(directory="app/templates")
pipeline = MatchPipeline()

class SimulateRequest(BaseModel):
    base_resume_text: str = Field(min_length=30)
    added_skills: list[str] = Field(default_factory=list)
    job_description: str = Field(min_length=30)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze")
async def analyze(resume: UploadFile = File(...), job_description: str = Form(...)):
    try:
        allowed = {".pdf", ".docx", ".txt"}
        filename = resume.filename or "resume"
        if not any(filename.lower().endswith(ext) for ext in allowed):
            return JSONResponse({"error": "Unsupported file type. Use PDF, DOCX, or TXT."}, status_code=415)
        data = await resume.read()
        if len(data) > 10 * 1024 * 1024:
            return JSONResponse({"error": "Resume file is larger than 10 MB."}, status_code=413)
        return JSONResponse(pipeline.run(data, filename, job_description))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.post("/simulate")
async def simulate(payload: SimulateRequest):
    try:
        return JSONResponse(pipeline.simulate_addition(payload.base_resume_text, payload.added_skills, payload.job_description))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.1.0"}
