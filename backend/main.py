import io
import json
import os
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pypdf import PdfReader
from docx import Document


# ============================================================
# APP SETUP
# ============================================================

app = FastAPI(
    title="AI Job Application Agent",
    description="AI-powered job application assistant",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

frontend_url = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
)

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

if frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# OPENAI
# ============================================================

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

MODEL = "gpt-5.6"


# ============================================================
# BASIC ROUTES
# ============================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "AI Job Application Agent API is running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


# ============================================================
# RESUME EXTRACTION
# ============================================================

async def extract_resume_text(file: UploadFile) -> str:
    """
    Extract text from a PDF or DOCX resume.
    """

    filename = (file.filename or "").lower()

    file_bytes = await file.read()

    if filename.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))

        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)

        return "\n".join(text_parts).strip()

    if filename.endswith(".docx"):
        document = Document(io.BytesIO(file_bytes))

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        return "\n".join(paragraphs).strip()

    raise ValueError(
        "Unsupported resume format. Please upload a PDF or DOCX file."
    )


# ============================================================
# OPENAI HELPER
# ============================================================

def call_ai(prompt: str) -> str:
    """
    Send a prompt to OpenAI and return the response text.
    """

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not configured on the server."
        )

    response = client.responses.create(
        model=MODEL,
        input=prompt,
    )

    return response.output_text


def extract_json(text: str) -> dict[str, Any]:
    """
    Convert an AI response into a Python dictionary.
    Handles responses wrapped in Markdown code fences.
    """

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1)
        cleaned = cleaned.replace("```", "")
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start != -1 and end != -1:
            return json.loads(cleaned[start:end + 1])

        raise ValueError("AI returned invalid JSON.")


# ============================================================
# JOB ANALYSIS
# ============================================================

def analyze_application(
    resume_text: str,
    job_description: str,
) -> dict[str, Any]:

    prompt = f"""
You are an expert technical recruiter and resume analyst.

Analyze the candidate's resume against the job description.

Return ONLY valid JSON.

The JSON must use exactly this structure:

{{
  "match_score": 0,
  "job_title": "",
  "summary": "",
  "matching_skills": [],
  "skill_gaps": [],
  "experience_match": "",
  "keywords": []
}}

Rules:

- match_score must be an integer from 0 to 100.
- job_title should be the likely job title from the job description.
- summary should briefly explain the overall match.
- matching_skills should contain skills clearly supported by the resume.
- skill_gaps should contain important job requirements not clearly demonstrated in the resume.
- experience_match should compare the candidate's experience with the role requirements.
- keywords should contain important ATS/job-description keywords.
- Do not invent experience, education, certifications, or skills.
- Base the analysis only on the supplied resume and job description.

RESUME:
----------------
{resume_text}
----------------

JOB DESCRIPTION:
----------------
{job_description}
----------------
"""

    result = call_ai(prompt)

    return extract_json(result)


# ============================================================
# ANALYZE ENDPOINT
# ============================================================

@app.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    try:
        resume_text = await extract_resume_text(resume)

        if not resume_text:
            return {
                "error": "Could not extract text from the resume."
            }

        if not job_description.strip():
            return {
                "error": "Please provide a job description."
            }

        analysis = analyze_application(
            resume_text,
            job_description,
        )

        return analysis

    except Exception as exc:
        return {
            "error": str(exc)
        }


# ============================================================
# RESUME TAILORING
# ============================================================

def tailor_resume(
    resume_text: str,
    job_description: str,
) -> str:

    prompt = f"""
You are an expert resume writer.

Tailor the candidate's resume for the supplied job description.

IMPORTANT:
- Never invent experience.
- Never invent technologies.
- Never invent certifications.
- Never invent education.
- Never claim the candidate did something that is not supported by the original resume.
- You may improve wording and organization.
- You may emphasize relevant existing experience.
- Preserve factual accuracy.
- Optimize naturally for ATS keywords from the job description.

Return ONLY the tailored resume text.

ORIGINAL RESUME:
----------------
{resume_text}
----------------

JOB DESCRIPTION:
----------------
{job_description}
----------------
"""

    return call_ai(prompt)


# ============================================================
# TAILOR ENDPOINT
# ============================================================

@app.post("/tailor")
async def tailor(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    try:
        resume_text = await extract_resume_text(resume)

        if not resume_text:
            return {
                "error": "Could not extract text from the resume."
            }

        tailored_resume = tailor_resume(
            resume_text,
            job_description,
        )

        return {
            "tailored_resume": tailored_resume
        }

    except Exception as exc:
        return {
            "error": str(exc)
        }


# ============================================================
# COVER LETTER
# ============================================================

def generate_cover_letter(
    resume_text: str,
    job_description: str,
) -> str:

    prompt = f"""
You are an expert professional cover-letter writer.

Write a concise, professional cover letter for the candidate
based on the resume and job description.

Rules:
- Do not invent qualifications.
- Do not invent experience.
- Do not invent company facts.
- Use information supported by the resume.
- Connect relevant experience to the job requirements.
- Avoid generic filler.
- Keep the tone professional and natural.
- Do not include placeholders such as [Company Name].
- Do not include a fake address or phone number.
- Do not include Markdown formatting.

Return ONLY the cover letter.

RESUME:
----------------
{resume_text}
----------------

JOB DESCRIPTION:
----------------
{job_description}
----------------
"""

    return call_ai(prompt)


# ============================================================
# COVER LETTER ENDPOINT
# ============================================================

@app.post("/cover-letter")
async def cover_letter(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    try:
        resume_text = await extract_resume_text(resume)

        if not resume_text:
            return {
                "error": "Could not extract text from the resume."
            }

        letter = generate_cover_letter(
            resume_text,
            job_description,
        )

        return {
            "cover_letter": letter
        }

    except Exception as exc:
        return {
            "error": str(exc)
        }


# ============================================================
# DOCX - RESUME
# ============================================================

def create_resume_docx(resume_text: str) -> io.BytesIO:
    document = Document()

    document.add_heading(
        "Tailored Resume",
        level=1,
    )

    for line in resume_text.splitlines():

        line = line.strip()

        if not line:
            continue

        document.add_paragraph(line)

    output = io.BytesIO()

    document.save(output)

    output.seek(0)

    return output


# ============================================================
# DOCX - COVER LETTER
# ============================================================

def create_cover_letter_docx(
    cover_letter_text: str,
) -> io.BytesIO:

    document = Document()

    document.add_heading(
        "Cover Letter",
        level=1,
    )

    for line in cover_letter_text.splitlines():

        line = line.strip()

        if not line:
            continue

        document.add_paragraph(line)

    output = io.BytesIO()

    document.save(output)

    output.seek(0)

    return output


# ============================================================
# DOWNLOAD TAILORED RESUME
# ============================================================

@app.post("/download-resume")
async def download_resume(
    resume_text: str = Form(...),
):

    document = create_resume_docx(resume_text)

    return StreamingResponse(
        document,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                'attachment; filename="tailored_resume.docx"'
            )
        },
    )


# ============================================================
# DOWNLOAD COVER LETTER
# ============================================================

@app.post("/download-cover-letter")
async def download_cover_letter(
    cover_letter_text: str = Form(...),
):

    document = create_cover_letter_docx(
        cover_letter_text
    )

    return StreamingResponse(
        document,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                'attachment; filename="cover_letter.docx"'
            )
        },
    )