from __future__ import annotations

import io
import json
import os
import re
from datetime import datetime
from typing import Any, Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, BeforeValidator, Field
from pypdf import PdfReader
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from backend.ats import build_ats_audit

load_dotenv()


# ============================================================
# CONFIG
# ============================================================

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173,http://127.0.0.1:5173",
)

MAX_RESUME_SIZE = 8 * 1024 * 1024


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="JobPilot AI",
    version="2.0.0",
    description="AI-powered job application builder",
)


allowed_origins = [
    origin.strip()
    for origin in FRONTEND_URL.split(",")
    if origin.strip()
]

allowed_origins.extend(
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
)

allowed_origins = list(dict.fromkeys(allowed_origins))


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=(
        r"^https://ai-job-application-agent"
        r"(?:-[a-zA-Z0-9-]+)?"
        r"\.vercel\.app$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PYDANTIC HELPERS
# ============================================================

def none_to_empty(value: Any) -> Any:
    return "" if value is None else value


def none_to_list(value: Any) -> Any:
    return [] if value is None else value


SafeString = Annotated[
    str,
    BeforeValidator(none_to_empty),
]

SafeStringList = Annotated[
    list[str],
    BeforeValidator(none_to_list),
]


# ============================================================
# DATA MODELS
# ============================================================

class JobIntelligence(BaseModel):
    job_title: SafeString = ""
    company: SafeString = ""
    location: SafeString = ""
    summary: SafeString = ""

    hard_skills: SafeStringList = Field(
        default_factory=list
    )

    soft_skills: SafeStringList = Field(
        default_factory=list
    )

    keywords: SafeStringList = Field(
        default_factory=list
    )

    responsibilities: SafeStringList = Field(
        default_factory=list
    )

    qualifications: SafeStringList = Field(
        default_factory=list
    )


class ExperienceItem(BaseModel):
    company: SafeString = ""
    title: SafeString = ""
    location: SafeString = ""
    dates: SafeString = ""

    bullets: SafeStringList = Field(
        default_factory=list
    )


class ProjectItem(BaseModel):
    name: SafeString = ""
    dates: SafeString = ""

    bullets: SafeStringList = Field(
        default_factory=list
    )


class EducationItem(BaseModel):
    school: SafeString = ""
    degree: SafeString = ""
    dates: SafeString = ""

    details: SafeStringList = Field(
        default_factory=list
    )


class StructuredResume(BaseModel):
    name: SafeString = ""
    email: SafeString = ""
    phone: SafeString = ""
    location: SafeString = ""
    linkedin: SafeString = ""
    github: SafeString = ""
    portfolio: SafeString = ""

    summary: SafeString = ""

    skills: SafeStringList = Field(
        default_factory=list
    )

    experience: list[ExperienceItem] = Field(
        default_factory=list
    )

    projects: list[ProjectItem] = Field(
        default_factory=list
    )

    education: list[EducationItem] = Field(
        default_factory=list
    )

    certifications: SafeStringList = Field(
        default_factory=list
    )


class BuildResult(BaseModel):
    job: JobIntelligence
    resume: StructuredResume
    cover_letter: SafeString = ""
    notes: SafeStringList = Field(
        default_factory=list
    )


class CoverLetterDownload(BaseModel):
    resume: StructuredResume
    job: JobIntelligence
    cover_letter: str


# ============================================================
# OPENAI
# ============================================================

SYSTEM_PROMPT = """
You are JobPilot AI, a professional job application assistant.

Your task is to analyze a job description and tailor a candidate's resume.

IMPORTANT FACTUAL RULES:

1. NEVER invent experience.
2. NEVER invent companies.
3. NEVER invent job titles.
4. NEVER invent dates.
5. NEVER invent degrees.
6. NEVER invent certifications.
7. NEVER invent technologies.
8. NEVER invent metrics.
9. NEVER claim a skill simply because it appears in the job description.
10. Resume claims must be supported by the source resume.
11. Existing resume facts should be preserved.
12. You may rewrite existing bullets to make them clearer and more relevant.
13. Do not fabricate achievements.
14. Do not fabricate numbers.
15. Never return null. Use "" or [].

For the job analysis:

Extract:
- job title
- company
- location
- summary
- hard skills
- soft skills
- keywords
- responsibilities
- qualifications

For the tailored resume:

- preserve the candidate's identity
- preserve companies
- preserve job titles
- preserve employment dates
- preserve projects
- preserve education
- preserve certifications
- prioritize relevant existing skills
- rewrite existing bullets only when supported by the source resume

For the cover letter:

- make it professional
- make it specific to the job
- use only facts supported by the resume
- do not invent experience
- do not invent metrics

Return ONLY valid JSON.

Required JSON:

{
  "job": {
    "job_title": "",
    "company": "",
    "location": "",
    "summary": "",
    "hard_skills": [],
    "soft_skills": [],
    "keywords": [],
    "responsibilities": [],
    "qualifications": []
  },

  "resume": {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "portfolio": "",
    "summary": "",
    "skills": [],
    "experience": [
      {
        "company": "",
        "title": "",
        "location": "",
        "dates": "",
        "bullets": []
      }
    ],
    "projects": [
      {
        "name": "",
        "dates": "",
        "bullets": []
      }
    ],
    "education": [
      {
        "school": "",
        "degree": "",
        "dates": "",
        "details": []
      }
    ],
    "certifications": []
  },

  "cover_letter": "",

  "notes": []
}
"""


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured.",
        )

    return OpenAI(
        api_key=api_key,
        timeout=60.0,
        max_retries=1,
    )


def call_openai(
    resume_text: str,
    job_description: str,
) -> BuildResult:

    client = get_openai_client()

    prompt = f"""
SOURCE RESUME
=============

{resume_text[:35000]}


JOB DESCRIPTION
===============

{job_description[:30000]}


Build the complete application.

Use the resume as the source of truth for candidate information.

The job description is the source of truth for job requirements.

Do not invent candidate experience.
Do not invent missing skills.
Do not invent metrics.

Return JSON only.
"""

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": SYSTEM_PROMPT,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                },
            ],
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI service request failed: {exc}",
        )

    output = (response.output_text or "").strip()

    if not output:
        raise HTTPException(
            status_code=502,
            detail="AI service returned an empty response.",
        )

    try:
        data = json.loads(output)

    except json.JSONDecodeError:

        match = re.search(
            r"\{.*\}",
            output,
            flags=re.DOTALL,
        )

        if not match:
            raise HTTPException(
                status_code=502,
                detail="AI returned invalid JSON.",
            )

        try:
            data = json.loads(match.group(0))

        except json.JSONDecodeError:
            raise HTTPException(
                status_code=502,
                detail="AI returned invalid application data.",
            )

    try:
        return BuildResult.model_validate(data)

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI output validation failed: {exc}",
        )


# ============================================================
# RESUME EXTRACTION
# ============================================================

def extract_pdf(data: bytes) -> str:

    try:
        reader = PdfReader(
            io.BytesIO(data)
        )

        pages = []

        for page in reader.pages:
            pages.append(
                page.extract_text() or ""
            )

        return "\n".join(pages).strip()

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF: {exc}",
        )


def extract_docx(data: bytes) -> str:

    try:
        document = Document(
            io.BytesIO(data)
        )

        parts = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()

            if text:
                parts.append(text)

        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text.strip()

                    if text:
                        parts.append(text)

        return "\n".join(parts).strip()

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read DOCX: {exc}",
        )


def extract_resume_text(
    filename: str,
    data: bytes,
) -> str:

    name = filename.lower()

    if name.endswith(".pdf"):
        return extract_pdf(data)

    if name.endswith(".docx"):
        return extract_docx(data)

    raise HTTPException(
        status_code=400,
        detail="Please upload a PDF or DOCX resume.",
    )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(value: str) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(value or "").lower(),
    ).strip()


def source_contains(
    value: str,
    source: str,
) -> bool:

    value = normalize(value)

    if not value:
        return True

    return value in normalize(source)


# ============================================================
# SAFETY / FACT PRESERVATION
# ============================================================

def preserve_source_metadata(
    result: BuildResult,
    source_text: str,
) -> BuildResult:

    resume = result.resume

    # These are allowed only if they actually appeared
    # in the source resume.
    identity_fields = [
        "name",
        "email",
        "phone",
        "location",
        "linkedin",
        "github",
        "portfolio",
    ]

    for field in identity_fields:

        value = getattr(resume, field)

        if value and not source_contains(
            value,
            source_text,
        ):
            setattr(
                resume,
                field,
                "",
            )

    # Employment metadata.
    for experience in resume.experience:

        if experience.company and not source_contains(
            experience.company,
            source_text,
        ):
            experience.company = ""

        if experience.title and not source_contains(
            experience.title,
            source_text,
        ):
            experience.title = ""

        if experience.location and not source_contains(
            experience.location,
            source_text,
        ):
            experience.location = ""

        if experience.dates and not source_contains(
            experience.dates,
            source_text,
        ):
            experience.dates = ""

    # Projects.
    for project in resume.projects:

        if project.name and not source_contains(
            project.name,
            source_text,
        ):
            project.name = ""

        if project.dates and not source_contains(
            project.dates,
            source_text,
        ):
            project.dates = ""

    # Education.
    for education in resume.education:

        if education.school and not source_contains(
            education.school,
            source_text,
        ):
            education.school = ""

        if education.degree and not source_contains(
            education.degree,
            source_text,
        ):
            education.degree = ""

        if education.dates and not source_contains(
            education.dates,
            source_text,
        ):
            education.dates = ""

    # Certifications.
    resume.certifications = [
        certification
        for certification in resume.certifications
        if not certification
        or source_contains(
            certification,
            source_text,
        )
    ]

    return result


# ============================================================
# DOCX RESUME
# ============================================================

def set_run_font(
    run,
    size: float = 9.5,
    bold: bool = False,
    italic: bool = False,
):

    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic

    rpr = run._element.get_or_add_rPr()

    fonts = rpr.rFonts

    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)

    fonts.set(
        qn("w:ascii"),
        "Times New Roman",
    )

    fonts.set(
        qn("w:hAnsi"),
        "Times New Roman",
    )

    fonts.set(
        qn("w:eastAsia"),
        "Times New Roman",
    )


def add_section_heading(
    document,
    title: str,
):

    paragraph = document.add_paragraph()

    paragraph.paragraph_format.space_before = Pt(7)
    paragraph.paragraph_format.space_after = Pt(3)

    run = paragraph.add_run(
        title.upper()
    )

    set_run_font(
        run,
        size=10,
        bold=True,
    )

    ppr = paragraph._p.get_or_add_pPr()

    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")

    bottom.set(
        qn("w:val"),
        "single",
    )

    bottom.set(
        qn("w:sz"),
        "6",
    )

    bottom.set(
        qn("w:space"),
        "3",
    )

    bottom.set(
        qn("w:color"),
        "808080",
    )

    border.append(bottom)
    ppr.append(border)


def add_bullet(
    document,
    text: str,
):

    paragraph = document.add_paragraph()

    paragraph.paragraph_format.left_indent = Inches(
        0.18
    )

    paragraph.paragraph_format.first_line_indent = Inches(
        -0.12
    )

    paragraph.paragraph_format.space_after = Pt(
        1.5
    )

    run = paragraph.add_run(
        "• " + text
    )

    set_run_font(run)


def add_title_date_row(
    document,
    title: str,
    dates: str = "",
    title_size: float = 10,
):
    """
    Creates a reliable one-paragraph title/date row.

    The title is left aligned and the dates use a right-aligned
    Word tab stop. This avoids the spacing and wrapping problems
    caused by manually inserting spaces or using a narrow table.
    """

    paragraph = document.add_paragraph()

    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(1)
    paragraph.paragraph_format.keep_with_next = True

    # A4 page width minus the 0.68 inch left/right margins.
    # The right-aligned tab sits at the right edge of the text area.
    paragraph.paragraph_format.tab_stops.add_tab_stop(
        Inches(6.9),
        WD_TAB_ALIGNMENT.RIGHT,
    )

    if title:
        run = paragraph.add_run(
            title.strip()
        )

        set_run_font(
            run,
            size=title_size,
            bold=True,
        )

    if dates:
        # A tab stop aligns the complete date range to the right
        # without relying on spaces.
        paragraph.add_run("\t")

        run = paragraph.add_run(
            dates.strip()
        )

        set_run_font(
            run,
            size=9,
        )

    return paragraph

def clean_resume_text_for_docx(value: str) -> str:
    """Apply small, deterministic resume-formatting corrections.

    These changes are limited to obvious compound-word formatting and
    do not add or invent candidate facts.
    """

    text = str(value or "")

    replacements = {
        "Cloud Based Event Driven": "Cloud-Based Event-Driven",
        "cloud based event driven": "cloud-based event-driven",
        "problem solving": "problem-solving",
        "Problem solving": "Problem-solving",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def make_resume_docx(
    resume: StructuredResume,
) -> bytes:

    document = Document()

    section = document.sections[0]

    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.68)
    section.right_margin = Inches(0.68)

    normal = document.styles["Normal"]

    normal.font.name = "Times New Roman"
    normal.font.size = Pt(9.5)

    # NAME
    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    paragraph.paragraph_format.space_after = Pt(2)

    run = paragraph.add_run(
        resume.name or "Resume"
    )

    set_run_font(
        run,
        size=17,
        bold=True,
    )

    # CONTACT
    contact = " | ".join(
        item
        for item in [
            resume.email,
            resume.phone,
            resume.location,
            resume.linkedin,
            resume.github,
            resume.portfolio,
        ]
        if item
    )

    if contact:

        paragraph = document.add_paragraph()

        paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        paragraph.paragraph_format.space_after = Pt(4)

        run = paragraph.add_run(contact)

        set_run_font(
            run,
            size=8.5,
        )

    # SUMMARY
    if resume.summary:

        add_section_heading(
            document,
            "Professional Summary",
        )

        paragraph = document.add_paragraph(
            resume.summary
        )

        paragraph.paragraph_format.space_after = Pt(
            2
        )

        for run in paragraph.runs:
            set_run_font(run)

    # SKILLS
    if resume.skills:

        add_section_heading(
            document,
            "Skills",
        )

        paragraph = document.add_paragraph(
            ", ".join(resume.skills)
        )

        paragraph.paragraph_format.space_after = Pt(
            2
        )

        for run in paragraph.runs:
            set_run_font(run)

    # EXPERIENCE
    if resume.experience:

        add_section_heading(
            document,
            "Professional Experience",
        )

        for item in resume.experience:

            add_title_date_row(
                document,
                title=item.title,
                dates=item.dates,
                title_size=10,
            )

            company_text = " | ".join(
                value
                for value in [item.company, item.location]
                if value
            )

            if company_text:
                paragraph = document.add_paragraph()
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(1)
                paragraph.paragraph_format.keep_with_next = True
                run = paragraph.add_run(company_text)
                set_run_font(run, size=9, bold=True)

            for bullet in item.bullets:
                add_bullet(
                    document,
                    clean_resume_text_for_docx(bullet),
                )

    # PROJECTS
    if resume.projects:

        add_section_heading(
            document,
            "Projects",
        )

        for project in resume.projects:

            add_title_date_row(
                document,
                title=clean_resume_text_for_docx(project.name),
                dates=project.dates,
                title_size=10,
            )

            for bullet in project.bullets:
                add_bullet(
                    document,
                    clean_resume_text_for_docx(bullet),
                )

    # EDUCATION
    if resume.education:

        add_section_heading(
            document,
            "Education",
        )

        for education in resume.education:

            add_title_date_row(
                document,
                title=education.degree,
                dates=education.dates,
                title_size=10,
            )

            if education.school:
                paragraph = document.add_paragraph()
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(1)
                paragraph.paragraph_format.keep_with_next = True
                run = paragraph.add_run(education.school)
                set_run_font(run, size=9, bold=True)

            for detail in education.details:
                add_bullet(
                    document,
                    clean_resume_text_for_docx(detail),
                )

    # CERTIFICATIONS
    if resume.certifications:

        add_section_heading(
            document,
            "Certifications",
        )

        for certification in resume.certifications:

            add_bullet(
                document,
                clean_resume_text_for_docx(certification),
            )

    output = io.BytesIO()

    document.save(output)

    return output.getvalue()


# ============================================================
# DOCX COVER LETTER
# ============================================================

def make_cover_letter_docx(
    resume: StructuredResume,
    job: JobIntelligence,
    cover_letter: str,
) -> bytes:

    document = Document()

    section = document.sections[0]

    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    normal = document.styles["Normal"]

    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = paragraph.add_run(
        resume.name or "Candidate"
    )

    set_run_font(
        run,
        size=16,
        bold=True,
    )

    contact = " | ".join(
        item
        for item in [
            resume.email,
            resume.phone,
            resume.linkedin,
        ]
        if item
    )

    if contact:

        paragraph = document.add_paragraph()

        paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        run = paragraph.add_run(contact)

        set_run_font(
            run,
            size=9,
        )

    paragraph = document.add_paragraph()

    run = paragraph.add_run(
        datetime.now().strftime(
            "%B %d, %Y"
        )
    )

    set_run_font(run)

    paragraph = document.add_paragraph()

    subject = (
        f"Re: {job.job_title}"
        if job.job_title
        else "Re: Application"
    )

    if job.company:
        subject += f" at {job.company}"

    run = paragraph.add_run(subject)

    set_run_font(
        run,
        bold=True,
    )

    for section_text in cover_letter.split(
        "\n\n"
    ):

        if not section_text.strip():
            continue

        paragraph = document.add_paragraph(
            section_text.strip()
        )

        paragraph.paragraph_format.space_after = Pt(
            9
        )

        for run in paragraph.runs:

            set_run_font(
                run,
                size=11,
            )

    output = io.BytesIO()

    document.save(output)

    return output.getvalue()


# ============================================================
# ROUTES
# ============================================================

@app.get("/")
def root():

    return {
        "name": "JobPilot AI",
        "version": "2.0.0",
        "status": "ok",
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "openai_configured": bool(
            os.getenv("OPENAI_API_KEY")
        ),
        "model": OPENAI_MODEL,
    }


# ============================================================
# MAIN V2 ENDPOINT
# ============================================================

@app.post("/build-application")
async def build_application(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):

    started = datetime.now()

    # -----------------------------
    # Validate resume
    # -----------------------------

    if not resume.filename:

        raise HTTPException(
            status_code=400,
            detail="Please upload your resume.",
        )

    filename = resume.filename

    if not filename.lower().endswith(
        (".pdf", ".docx")
    ):

        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF or DOCX resume.",
        )

    # -----------------------------
    # Validate job description
    # -----------------------------

    if not job_description.strip():

        raise HTTPException(
            status_code=400,
            detail="Please paste the job description.",
        )

    # -----------------------------
    # Read file
    # -----------------------------

    file_data = await resume.read()

    if len(file_data) > MAX_RESUME_SIZE:

        raise HTTPException(
            status_code=400,
            detail="Resume must be smaller than 8 MB.",
        )

    # -----------------------------
    # Extract resume
    # -----------------------------

    resume_text = extract_resume_text(
        filename,
        file_data,
    )

    if len(resume_text.strip()) < 80:

        raise HTTPException(
            status_code=400,
            detail=(
                "We could not read enough text from "
                "your resume. Please use a text-based "
                "PDF or DOCX."
            ),
        )

    # -----------------------------
    # ONE AI REQUEST
    # -----------------------------

    result = call_openai(
        resume_text=resume_text,
        job_description=job_description.strip(),
    )

    # -----------------------------
    # Protect source facts
    # -----------------------------

    result = preserve_source_metadata(
        result,
        resume_text,
    )

    # -----------------------------
    # LOCAL ATS CALCULATION
    # -----------------------------

    ats = build_ats_audit(
        resume=result.resume.model_dump(),
        job_intelligence=result.job.model_dump(),
        filename=filename,
        file_type=filename.rsplit(
            ".",
            1,
        )[-1].upper(),
    )

    elapsed = (
        datetime.now() - started
    ).total_seconds()

    # -----------------------------
    # RESPONSE
    # -----------------------------

    return {
        "success": True,
        "processing_seconds": round(
            elapsed,
            2,
        ),
        "application": {
            "job": result.job.model_dump(),
            "resume": result.resume.model_dump(),
            "cover_letter": result.cover_letter,
            "ats": ats,
            "notes": result.notes,
        },
    }


# ============================================================
# DOWNLOAD RESUME
# ============================================================

@app.post("/download-resume")
def download_resume(
    resume: StructuredResume,
):

    document = make_resume_docx(
        resume
    )

    return StreamingResponse(
        io.BytesIO(document),
        media_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="JobPilot_Tailored_Resume.docx"'
        },
    )


# ============================================================
# DOWNLOAD COVER LETTER
# ============================================================

@app.post("/download-cover-letter")
def download_cover_letter(
    payload: CoverLetterDownload,
):

    document = make_cover_letter_docx(
        payload.resume,
        payload.job,
        payload.cover_letter,
    )

    return StreamingResponse(
        io.BytesIO(document),
        media_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="JobPilot_Cover_Letter.docx"'
        },
    )


# ============================================================
# ERROR HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request,
    exc,
):

    if isinstance(
        exc,
        HTTPException,
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail
            },
        )

    print(
        f"Unhandled server error: {exc}"
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Something went wrong while "
                "building your application."
            )
        },
    )