from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from io import BytesIO

from pypdf import PdfReader
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from openai import OpenAI

import json


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="AI Job Application Agent API",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# OPENAI
# =========================================================

client = OpenAI()


# =========================================================
# RESUME EXTRACTION
# =========================================================

def extract_resume_text(
    file_bytes: bytes,
    filename: str,
) -> str:

    filename = filename.lower()

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    if filename.endswith(".pdf"):

        reader = PdfReader(
            BytesIO(file_bytes)
        )

        pages = []

        for page in reader.pages:

            text = page.extract_text() or ""

            if text.strip():
                pages.append(text)

        return "\n".join(pages).strip()

    # -----------------------------------------------------
    # DOCX
    # -----------------------------------------------------

    elif filename.endswith(".docx"):

        document = Document(
            BytesIO(file_bytes)
        )

        paragraphs = []

        for paragraph in document.paragraphs:

            text = paragraph.text.strip()

            if text:
                paragraphs.append(text)

        return "\n".join(paragraphs).strip()

    else:

        raise ValueError(
            "Only PDF and DOCX resumes are supported."
        )


# =========================================================
# ANALYZE APPLICATION
# =========================================================

def analyze_application(
    resume_text: str,
    job_description: str,
):

    instructions = """
You are an expert AI job application analyst.

Compare the candidate resume against the job description.

Return ONLY valid JSON.

Use exactly this structure:

{
  "job_title": "",
  "match_score": 0,
  "match_summary": "",
  "matching_skills": [],
  "skill_gaps": [],
  "preferred_skills": [],
  "experience": {
    "required": "",
    "candidate": "",
    "assessment": ""
  },
  "education": {
    "required": "",
    "candidate": "",
    "assessment": ""
  },
  "keywords": [],
  "resume_issues": [],
  "recommendations": []
}

Rules:

- Never invent candidate experience.
- Never invent technologies.
- Never invent employment.
- Never turn projects into commercial employment.
- If a requirement is not supported by the resume,
  identify it as a gap.
- Match score must be an integer from 0 to 100.
- Be factual and conservative.
- Return JSON only.
"""

    prompt = f"""
CANDIDATE RESUME
================

{resume_text}


JOB DESCRIPTION
===============

{job_description}
"""

    response = client.responses.create(
        model="gpt-5.6",
        instructions=instructions,
        input=prompt,
    )

    result = response.output_text.strip()

    try:

        return json.loads(result)

    except json.JSONDecodeError:

        return {
            "error": "AI returned invalid JSON.",
            "raw_response": result,
        }


# =========================================================
# TAILOR RESUME
# =========================================================

def tailor_resume(
    resume_text: str,
    job_description: str,
    analysis: dict,
):

    instructions = """
You are an expert professional resume writer.

Tailor the candidate's existing resume for
the supplied job description.

The result must remain completely truthful.

IMPORTANT:

- Never invent experience.
- Never invent employment.
- Never invent technologies.
- Never invent achievements.
- Never invent metrics.
- Never invent certifications.
- Never invent education.
- Never change company names.
- Never change employment dates.
- Never turn personal projects into employment.
- Never turn academic projects into employment.
- Do not falsely add missing skills.
- Emphasize relevant existing experience.
- Use ATS-friendly wording naturally.
- Keep the resume professional and concise.

Return ONLY the final resume text.

Use this structure:

NAME

CONTACT INFORMATION

PROFESSIONAL SUMMARY

TECHNICAL SKILLS

PROFESSIONAL EXPERIENCE

PROJECTS

EDUCATION
"""

    prompt = f"""
CANDIDATE RESUME
================

{resume_text}


JOB DESCRIPTION
===============

{job_description}


APPLICATION ANALYSIS
====================

{json.dumps(analysis, indent=2)}
"""

    response = client.responses.create(
        model="gpt-5.6",
        instructions=instructions,
        input=prompt,
    )

    return response.output_text.strip()


# =========================================================
# COVER LETTER
# =========================================================

def generate_cover_letter(
    resume_text: str,
    job_description: str,
    analysis: dict,
    tailored_resume: str,
):

    instructions = """
You are an expert professional cover letter writer.

Write a personalized cover letter for the
candidate applying to the supplied job.

IMPORTANT RULES:

- Never invent experience.
- Never invent employment.
- Never invent technologies.
- Never invent achievements.
- Never invent metrics.
- Only use facts supported by the resume.
- Do not claim missing skills.
- Do not exaggerate qualifications.
- Do not mention the match score.
- Do not mention that AI wrote the letter.
- Do not use generic phrases unnecessarily.
- Keep the tone professional and natural.
- Keep it approximately 300-450 words.

Return ONLY the cover letter.

Structure:

Dear Hiring Manager,

Opening paragraph explaining the role
and candidate interest.

Middle paragraph explaining relevant
experience and technical strengths.

Second middle paragraph connecting
relevant projects/skills to the role.

Closing paragraph expressing interest
in discussing the opportunity.

Kind regards,
Candidate
"""

    prompt = f"""
ORIGINAL RESUME
===============

{resume_text}


JOB DESCRIPTION
===============

{job_description}


APPLICATION ANALYSIS
====================

{json.dumps(analysis, indent=2)}


TAILORED RESUME
===============

{tailored_resume}
"""

    response = client.responses.create(
        model="gpt-5.6",
        instructions=instructions,
        input=prompt,
    )

    return response.output_text.strip()


# =========================================================
# CREATE DOCX - RESUME
# =========================================================

def create_resume_docx(
    resume_text: str,
) -> BytesIO:

    document = Document()

    # Page margins
    section = document.sections[0]

    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    # Default font
    styles = document.styles

    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10.5)

    # -----------------------------------------------------
    # Clean text
    # -----------------------------------------------------

    lines = resume_text.splitlines()

    cleaned_lines = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Remove markdown heading symbols
        if line.startswith("#"):
            line = line.lstrip("#").strip()

        # Remove fake placeholders
        if "[ADD IF TRUE:" in line:
            continue

        cleaned_lines.append(line)

    # -----------------------------------------------------
    # Add paragraphs
    # -----------------------------------------------------

    first_content = True

    section_names = {
        "professional summary",
        "summary",
        "technical skills",
        "skills",
        "professional experience",
        "experience",
        "projects",
        "education",
    }

    for line in cleaned_lines:

        lower = line.lower().strip()

        # Section heading
        if lower in section_names:

            paragraph = document.add_paragraph()

            paragraph.paragraph_format.space_before = Pt(8)
            paragraph.paragraph_format.space_after = Pt(3)

            run = paragraph.add_run(
                line.upper()
            )

            run.bold = True
            run.font.name = "Aptos"
            run.font.size = Pt(11)

            continue

        # Bullet
        if (
            line.startswith("•")
            or line.startswith("- ")
            or line.startswith("* ")
        ):

            bullet_text = line[1:].strip()

            if bullet_text.startswith("-"):
                bullet_text = bullet_text[1:].strip()

            paragraph = document.add_paragraph(
                style="List Bullet"
            )

            paragraph.paragraph_format.space_after = Pt(2)

            run = paragraph.add_run(
                bullet_text
            )

            run.font.name = "Aptos"
            run.font.size = Pt(10.5)

            continue

        # Normal paragraph
        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_after = Pt(3)

        run = paragraph.add_run(line)

        run.font.name = "Aptos"
        run.font.size = Pt(10.5)

        # First line = candidate name
        if first_content:

            paragraph.alignment = (
                WD_ALIGN_PARAGRAPH.CENTER
            )

            run.bold = True
            run.font.size = Pt(16)

            first_content = False

    # Save to memory
    output = BytesIO()

    document.save(output)

    output.seek(0)

    return output


# =========================================================
# CREATE DOCX - COVER LETTER
# =========================================================

def create_cover_letter_docx(
    cover_letter: str,
) -> BytesIO:

    document = Document()

    section = document.sections[0]

    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)

    styles = document.styles

    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(11)

    lines = cover_letter.splitlines()

    for line in lines:

        line = line.strip()

        if not line:
            document.add_paragraph()
            continue

        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_after = Pt(8)
        paragraph.paragraph_format.line_spacing = 1.15

        run = paragraph.add_run(line)

        run.font.name = "Aptos"
        run.font.size = Pt(11)

    output = BytesIO()

    document.save(output)

    output.seek(0)

    return output


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "message": "AI Job Application Agent API is running",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
    }


# =========================================================
# ANALYZE
# =========================================================

@app.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):

    try:

        file_bytes = await resume.read()

        resume_text = extract_resume_text(
            file_bytes,
            resume.filename,
        )

        if not resume_text:

            return {
                "success": False,
                "error": "Could not extract text from the resume.",
            }

        if not job_description.strip():

            return {
                "success": False,
                "error": "Job description is empty.",
            }

        analysis = analyze_application(
            resume_text,
            job_description,
        )

        return {
            "success": True,
            "filename": resume.filename,
            "analysis": analysis,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# TAILOR
# =========================================================

@app.post("/tailor")
async def tailor(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    analysis: str = Form(...),
):

    try:

        file_bytes = await resume.read()

        resume_text = extract_resume_text(
            file_bytes,
            resume.filename,
        )

        if not resume_text:

            return {
                "success": False,
                "error": "Could not extract text from the resume.",
            }

        if not job_description.strip():

            return {
                "success": False,
                "error": "Job description is empty.",
            }

        try:

            analysis_data = json.loads(
                analysis
            )

        except json.JSONDecodeError:

            return {
                "success": False,
                "error": "Invalid analysis data.",
            }

        tailored_resume = tailor_resume(
            resume_text,
            job_description,
            analysis_data,
        )

        return {
            "success": True,
            "tailored_resume": tailored_resume,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# COVER LETTER
# =========================================================

@app.post("/cover-letter")
async def cover_letter(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    analysis: str = Form(...),
    tailored_resume: str = Form(...),
):

    try:

        file_bytes = await resume.read()

        resume_text = extract_resume_text(
            file_bytes,
            resume.filename,
        )

        if not resume_text:

            return {
                "success": False,
                "error": "Could not extract text from the resume.",
            }

        try:

            analysis_data = json.loads(
                analysis
            )

        except json.JSONDecodeError:

            return {
                "success": False,
                "error": "Invalid analysis data.",
            }

        if not tailored_resume.strip():

            return {
                "success": False,
                "error": "Tailored resume is required.",
            }

        cover_letter_text = generate_cover_letter(
            resume_text,
            job_description,
            analysis_data,
            tailored_resume,
        )

        return {
            "success": True,
            "cover_letter": cover_letter_text,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# DOWNLOAD RESUME
# =========================================================

@app.post("/download-resume")
async def download_resume(
    tailored_resume: str = Form(...),
):

    try:

        document = create_resume_docx(
            tailored_resume
        )

        return StreamingResponse(
            document,
            media_type=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
            headers={
                "Content-Disposition":
                    'attachment; filename="Tailored_Resume.docx"'
            },
        )

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# DOWNLOAD COVER LETTER
# =========================================================

@app.post("/download-cover-letter")
async def download_cover_letter(
    cover_letter: str = Form(...),
):

    try:

        document = create_cover_letter_docx(
            cover_letter
        )

        return StreamingResponse(
            document,
            media_type=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
            headers={
                "Content-Disposition":
                    'attachment; filename="Cover_Letter.docx"'
            },
        )

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }