from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pypdf import PdfReader

from backend.ats import build_ats_audit


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

load_dotenv(
    PROJECT_ROOT / ".env"
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "",
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
)

if not OPENAI_API_KEY:

    raise RuntimeError(
        "OPENAI_API_KEY is not configured."
    )

client = OpenAI(
    api_key=OPENAI_API_KEY,
    timeout=90.0,
    max_retries=0,
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="JobPilot AI",
    version="6.0.0",
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

allowed_origins = list(
    dict.fromkeys(
        allowed_origins
    )
)

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
# BASIC ENDPOINTS
# ============================================================

@app.get("/")
def root():

    return {
        "name": "JobPilot AI",
        "status": "online",
        "version": "6.0.0",
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "JobPilot AI",
        "version": "6.0.0",
    }


# ============================================================
# FILE VALIDATION
# ============================================================

async def read_upload(
    file: UploadFile,
) -> bytes:

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="A resume file is required.",
        )

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in {
        ".pdf",
        ".docx",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF and DOCX files are supported."
            ),
        )

    data = await file.read()

    if not data:

        raise HTTPException(
            status_code=400,
            detail="The uploaded resume is empty.",
        )

    if len(data) > (
        8 * 1024 * 1024
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Resume must be smaller than 8 MB."
            ),
        )

    return data


# ============================================================
# RESUME EXTRACTION
# ============================================================

def extract_pdf_text(
    data: bytes,
) -> str:

    reader = PdfReader(
        io.BytesIO(data)
    )

    pages = []

    for page in reader.pages:

        text = (
            page.extract_text()
            or ""
        ).strip()

        if text:
            pages.append(
                text
            )

    return "\n".join(
        pages
    ).strip()


def extract_docx_text(
    data: bytes,
) -> str:

    document = Document(
        io.BytesIO(data)
    )

    parts = []

    for paragraph in document.paragraphs:

        text = (
            paragraph.text
            or ""
        ).strip()

        if text:
            parts.append(
                text
            )

    for table in document.tables:

        for row in table.rows:

            for cell in row.cells:

                text = (
                    cell.text
                    or ""
                ).strip()

                if text:
                    parts.append(
                        text
                    )

    return "\n".join(
        parts
    ).strip()


def extract_resume_text(
    filename: str,
    data: bytes,
) -> str:

    extension = Path(
        filename
    ).suffix.lower()

    if extension == ".pdf":

        text = extract_pdf_text(
            data
        )

    elif extension == ".docx":

        text = extract_docx_text(
            data
        )

    else:

        raise HTTPException(
            status_code=400,
            detail="Unsupported resume format.",
        )

    if not text:

        raise HTTPException(
            status_code=400,
            detail=(
                "No readable text was found in the resume."
            ),
        )

    return text


# ============================================================
# OPENAI JSON
# ============================================================

def parse_json_response(
    raw: str,
) -> dict[str, Any]:

    text = (
        raw
        .strip()
        .replace(
            "```json",
            "",
        )
        .replace(
            "```",
            "",
        )
        .strip()
    )

    try:

        parsed = json.loads(
            text
        )

        if isinstance(
            parsed,
            dict,
        ):

            return parsed

    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if (
        start >= 0
        and end > start
    ):

        candidate = text[
            start:end + 1
        ]

        try:

            parsed = json.loads(
                candidate
            )

            if isinstance(
                parsed,
                dict,
            ):

                return parsed

        except json.JSONDecodeError:
            pass

    raise ValueError(
        "The AI returned invalid JSON."
    )


def call_json_model(
    instructions: str,
    user_input: str,
) -> dict[str, Any]:

    response = client.responses.create(
        model="gpt-5.6",
        instructions=instructions,
        input=user_input,
    )

    return parse_json_response(
        response.output_text
    )


# ============================================================
# RESUME STRUCTURING
# ============================================================

def structure_resume(
    resume_text: str,
) -> dict[str, Any]:

    instructions = """
You are an expert resume parser.

Convert the resume into structured JSON.

IMPORTANT:
Do not invent facts.

Preserve the candidate's actual:
- name
- contact information
- summary
- skills
- employers
- titles
- dates
- projects
- education
- certifications
- achievements

Return ONLY valid JSON:

{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "linkedin": "",
  "github": "",
  "summary": "",
  "skills": [],
  "experience": [
    {
      "title": "",
      "company": "",
      "location": "",
      "dates": "",
      "bullets": []
    }
  ],
  "projects": [
    {
      "name": "",
      "technologies": [],
      "description": "",
      "bullets": []
    }
  ],
  "education": [
    {
      "degree": "",
      "institution": "",
      "location": "",
      "dates": ""
    }
  ],
  "certifications": []
}
"""

    return call_json_model(
        instructions,
        resume_text,
    )


# ============================================================
# ASHBY
# ============================================================

def extract_ashby_job(
    ashby_url: str,
) -> str:

    url = ashby_url.strip()

    match = re.match(
        r"^https?://jobs\.ashbyhq\.com/"
        r"([^/?#]+)"
        r"(?:/([^/?#]+))?",
        url,
        flags=re.IGNORECASE,
    )

    if not match:

        raise HTTPException(
            status_code=400,
            detail=(
                "Please provide a valid Ashby job URL."
            ),
        )

    board_name = match.group(1)
    posting_id = match.group(2)

    api_url = (
        "https://api.ashbyhq.com/"
        f"posting-api/job-board/{board_name}"
    )

    try:

        response = requests.get(
            api_url,
            timeout=20,
        )

        response.raise_for_status()

        payload = response.json()

    except requests.RequestException as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to retrieve the Ashby job posting."
            ),
        ) from exc

    jobs = (
        payload.get(
            "jobs"
        )
        or []
    )

    if not jobs:

        raise HTTPException(
            status_code=404,
            detail=(
                "No public jobs were found "
                "for this Ashby board."
            ),
        )

    selected = None

    if posting_id:

        for job in jobs:

            job_id = str(
                job.get(
                    "id"
                )
                or ""
            )

            job_url = str(
                job.get(
                    "jobUrl"
                )
                or ""
            )

            if (
                job_id.lower()
                == posting_id.lower()
            ):

                selected = job
                break

            if (
                posting_id.lower()
                in job_url.lower()
            ):

                selected = job
                break

    if selected is None:

        selected = jobs[0]

    title = (
        selected.get(
            "title"
        )
        or ""
    )

    description = (
        selected.get(
            "descriptionPlain"
        )
        or selected.get(
            "description"
        )
        or ""
    )

    if not description:

        description = json.dumps(
            selected,
            indent=2,
        )

    return (
        f"Job Title: {title}\n\n"
        f"{description}"
    ).strip()


# ============================================================
# JOB RESOLUTION
# ============================================================

def resolve_job_description(
    job_description: str,
    ashby_url: str,
) -> str:

    jd = (
        job_description
        or ""
    ).strip()

    ashby = (
        ashby_url
        or ""
    ).strip()

    if jd:
        return jd

    if ashby:
        return extract_ashby_job(
            ashby
        )

    raise HTTPException(
        status_code=400,
        detail=(
            "Add a job description or Ashby URL."
        ),
    )


# ============================================================
# JOB INTELLIGENCE
# ============================================================

def extract_job_intelligence(
    job_description: str,
) -> dict[str, Any]:

    instructions = """
You are an expert technical recruiter and ATS analyst.

Analyze ONE specific job posting.

Your job is to identify meaningful requirements that
should be used for resume matching.

IGNORE:
- privacy notices
- EEO statements
- legal text
- benefits
- footer text
- navigation
- company boilerplate
- generic wording
- repeated phrases
- unrelated jobs

IMPORTANT:
Do NOT split one technical concept into tiny words.

BAD:
[
  "database",
  "systems",
  "replication",
  "debugging"
]

GOOD:
[
  "database replication",
  "production debugging"
]

Only include meaningful requirements.

HARD SKILLS:
Include actual technologies, programming languages,
databases, frameworks, cloud services, debugging
tools, testing systems, security technologies,
infrastructure, and similar technical requirements.

SOFT SKILLS:
Include actual behavioral requirements such as
collaboration, communication, ownership,
troubleshooting, reliability, customer focus,
problem solving, and knowledge sharing.

EXPERIENCE:
Include meaningful experience requirements.
Do not copy complete responsibility sentences.

KEYWORDS:
Choose important searchable phrases that matter
for ATS matching.

KEEP LISTS COMPACT:

hard_skills:
8-18 items

soft_skills:
4-10 items

experience_requirements:
3-8 items

keywords:
10-25 items

Avoid duplicates and overlapping items.

Compound technical concepts should stay together.

Examples:

"database replication engines"
is one requirement.

"security vulnerability remediation"
is one requirement.

"multi-region production services"
is one requirement.

Return ONLY JSON:

{
  "job_title": "",
  "hard_skills": [],
  "soft_skills": [],
  "responsibilities": [],
  "experience_requirements": [],
  "education_requirements": [],
  "keywords": []
}
"""

    return call_json_model(
        instructions,
        job_description,
    )


# ============================================================
# JOB ANALYSIS
# ============================================================

def analyze_resume_against_job(
    resume_text: str,
    job_description: str,
    job_intelligence: dict[str, Any],
) -> dict[str, Any]:

    instructions = """
You are an expert technical recruiter.

Compare the candidate resume with the target role.

Never invent candidate experience.

Clearly distinguish:
- evidence in the resume
- missing requirements
- requirements that the job does not specify

Return ONLY JSON:

{
  "summary": "",
  "matching_skills": [],
  "skill_gaps": [],
  "experience_comparison": "",
  "education_comparison": "",
  "recommendations": [],
  "resume_issues": []
}
"""

    payload = {
        "resume":
            resume_text,

        "job_description":
            job_description,

        "job_intelligence":
            job_intelligence,
    }

    return call_json_model(
        instructions,
        json.dumps(
            payload,
            indent=2,
        ),
    )


# ============================================================
# TARGET TITLE
# ============================================================

def ensure_target_title_in_summary(
    resume: dict[str, Any],
    target_job_title: str,
) -> dict[str, Any]:

    target = (
        target_job_title
        or ""
    ).strip()

    if not target:
        return resume

    summary = (
        resume.get(
            "summary"
        )
        or ""
    ).strip()

    if not summary:

        resume["summary"] = (
            "Software engineer targeting "
            f"{target} opportunities."
        )

        return resume

    normalized_summary = (
        summary.lower()
    )

    normalized_target = (
        target.lower()
    )

    short_title = ""

    if (
        "software development engineer ii"
        in normalized_target
    ):

        short_title = "sde2"

    elif (
        "software development engineer 2"
        in normalized_target
    ):

        short_title = "sde2"

    if (
        normalized_target
        in normalized_summary
    ):

        return resume

    if (
        short_title
        and short_title
        in normalized_summary
    ):

        return resume

    resume["summary"] = (
        f"{summary} "
        f"Targeting {target} opportunities."
    ).strip()

    return resume


# ============================================================
# TAILORING
# ============================================================

def tailor_resume_with_ai(
    resume_text: str,
    job_description: str,
    job_intelligence: dict[str, Any],
    original_resume: dict[str, Any],
    current_ats: dict[str, Any],
) -> dict[str, Any]:

    missing_hard_skills = (
        current_ats.get(
            "missing_hard_skills"
        )
        or []
    )

    missing_soft_skills = (
        current_ats.get(
            "missing_soft_skills"
        )
        or []
    )

    missing_keywords = (
        current_ats.get(
            "missing_keywords"
        )
        or []
    )

    target_title = (
        job_intelligence.get(
            "job_title"
        )
        or ""
    ).strip()

    instructions = f"""
You are an elite ATS resume optimization specialist.

TARGET JOB:
{target_title}

OBJECTIVE:
Create the strongest truthful ATS-aligned version of
the candidate's resume for this specific role.

============================================================
ABSOLUTE TRUTH RULE
============================================================

NEVER invent:

- technologies
- databases
- programming languages
- employers
- positions held
- dates
- projects
- certifications
- education
- metrics
- production experience
- responsibilities
- achievements

Use only information supported by the original resume.

============================================================
TITLE VISIBILITY
============================================================

The exact target job title should appear naturally in
the professional summary.

If the candidate never held that title, do not represent
it as a previous job.

Use language such as:

"Software engineer with experience in X, targeting
Software Development Engineer II (SDE2) opportunities."

============================================================
SKILL PRESERVATION
============================================================

Preserve all relevant technical skills already present.

Translate equivalent terminology naturally.

Examples:

AWS
Amazon Web Services

C++
C/C++

PostgreSQL
Postgres

SQL Server
MSSQL

CI/CD
Continuous Integration / Continuous Delivery

Do not add a skill simply because it appears in the job.

============================================================
MISSING HARD SKILLS
============================================================

"""

    instructions += "\n".join(
        f"- {item}"
        for item in missing_hard_skills[:30]
    )

    instructions += """

============================================================
MISSING SOFT SKILLS
============================================================

"""

    instructions += "\n".join(
        f"- {item}"
        for item in missing_soft_skills[:20]
    )

    instructions += """

============================================================
MISSING KEYWORDS
============================================================

"""

    instructions += "\n".join(
        f"- {item}"
        for item in missing_keywords[:40]
    )

    instructions += """

============================================================
MEASURABLE RESULTS
============================================================

Look for REAL measurable achievements in the original resume.

Use existing:
- percentages
- counts
- scale
- latency
- time savings
- performance improvements
- cost savings
- throughput
- users
- records
- deployments
- defect reductions

Do NOT invent metrics.

Make genuine existing measurements easy to identify.

============================================================
WRITING
============================================================

Use concise, evidence-based bullets.

Prefer:

Action + technology/process + result

Do not keyword stuff.

Do not make the resume unnaturally repetitive.

Keep all employers, titles, dates, education, and projects
accurate.

============================================================
RETURN JSON ONLY
============================================================

{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "linkedin": "",
  "github": "",
  "summary": "",
  "skills": [],
  "experience": [
    {
      "title": "",
      "company": "",
      "location": "",
      "dates": "",
      "bullets": []
    }
  ],
  "projects": [
    {
      "name": "",
      "technologies": [],
      "description": "",
      "bullets": []
    }
  ],
  "education": [
    {
      "degree": "",
      "institution": "",
      "location": "",
      "dates": ""
    }
  ],
  "certifications": []
}
"""

    payload = {
        "target_job_title":
            target_title,

        "job_description":
            job_description,

        "job_intelligence":
            job_intelligence,

        "current_ats":
            current_ats,

        "original_resume":
            original_resume,

        "original_resume_text":
            resume_text,
    }

    return call_json_model(
        instructions,
        json.dumps(
            payload,
            indent=2,
        ),
    )


# ============================================================
# FINAL RESUME QUALITY CONTROL
# ============================================================

def repair_resume_for_jobscan(
    resume: dict[str, Any],
    original_resume: dict[str, Any],
    job_description: str,
    job_intelligence: dict[str, Any],
    ats: dict[str, Any],
) -> dict[str, Any]:

    target_title = (
        job_intelligence.get(
            "job_title"
        )
        or ""
    ).strip()

    instructions = f"""
You are performing a final ATS resume quality-control pass.

TARGET TITLE:
{target_title}

Improve ATS searchability and job alignment.

STRICT:
Only use facts from the original resume.

Do NOT invent:
- technology
- employer
- job title held
- dates
- projects
- metrics
- responsibilities
- certifications
- education
- achievements

CHECK:

1. Target title is visible naturally in the summary.
2. Existing relevant technical skills are preserved.
3. Supported job terminology is visible.
4. Important job-relevant skills are easy to find.
5. Existing measurable achievements remain visible.
6. Employers remain unchanged.
7. Original job titles remain unchanged.
8. Dates remain unchanged.
9. Education remains unchanged.
10. Projects remain unchanged unless only wording is improved.
11. No unsupported skills.
12. No keyword stuffing.
13. Resume remains readable.

Return ONLY JSON:

{{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "linkedin": "",
  "github": "",
  "summary": "",
  "skills": [],
  "experience": [
    {{
      "title": "",
      "company": "",
      "location": "",
      "dates": "",
      "bullets": []
    }}
  ],
  "projects": [
    {{
      "name": "",
      "technologies": [],
      "description": "",
      "bullets": []
    }}
  ],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "location": "",
      "dates": ""
    }}
  ],
  "certifications": []
}}
"""

    payload = {
        "target_job_title":
            target_title,

        "job_description":
            job_description,

        "job_intelligence":
            job_intelligence,

        "original_resume":
            original_resume,

        "current_resume":
            resume,

        "ats":
            ats,
    }

    return call_json_model(
        instructions,
        json.dumps(
            payload,
            indent=2,
        ),
    )


# ============================================================
# MULTI-ROUND OPTIMIZATION
# ============================================================

def optimize_resume_for_ats(
    resume_text: str,
    job_description: str,
    job_intelligence: dict[str, Any],
    original_resume: dict[str, Any],
    baseline_ats: dict[str, Any],
    max_rounds: int = 5,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    int,
]:

    best_resume = original_resume

    best_ats = baseline_ats

    best_score = int(
        baseline_ats.get(
            "match_rate",
            0,
        )
    )

    rounds_completed = 0

    for round_number in range(
        1,
        max_rounds + 1,
    ):

        rounds_completed = round_number

        candidate_resume = (
            tailor_resume_with_ai(
                resume_text=resume_text,
                job_description=job_description,
                job_intelligence=job_intelligence,
                original_resume=original_resume,
                current_ats=best_ats,
            )
        )

        candidate_ats = build_ats_audit(
            resume=candidate_resume,
            job_intelligence=job_intelligence,
            filename="tailored-resume.docx",
            file_type="DOCX",
        )

        candidate_score = int(
            candidate_ats.get(
                "match_rate",
                0,
            )
        )

        if candidate_score > best_score:

            best_resume = candidate_resume

            best_ats = candidate_ats

            best_score = candidate_score

        if best_score >= 90:

            break

    repaired_resume = (
        repair_resume_for_jobscan(
            resume=best_resume,
            original_resume=original_resume,
            job_description=job_description,
            job_intelligence=job_intelligence,
            ats=best_ats,
        )
    )

    repaired_resume = (
        ensure_target_title_in_summary(
            repaired_resume,
            job_intelligence.get(
                "job_title",
                "",
            ),
        )
    )

    repaired_ats = build_ats_audit(
        resume=repaired_resume,
        job_intelligence=job_intelligence,
        filename="tailored-resume.docx",
        file_type="DOCX",
    )

    repaired_score = int(
        repaired_ats.get(
            "match_rate",
            0,
        )
    )

    if repaired_score > best_score:

        best_resume = repaired_resume

        best_ats = repaired_ats

        best_score = repaired_score

    return (
        best_resume,
        best_ats,
        rounds_completed,
    )


# ============================================================
# COVER LETTER
# ============================================================

def generate_cover_letter_with_ai(
    resume_text: str,
    job_description: str,
) -> dict[str, Any]:

    instructions = """
You are an expert professional cover letter writer.

Create a focused professional cover letter.

Use only facts supported by the resume.

Never invent:
- employers
- technologies
- metrics
- achievements
- experience

Return ONLY JSON:

{
  "date": "",
  "salutation": "Dear Hiring Manager,",
  "opening": "",
  "body_paragraphs": [],
  "closing": "Kind regards,",
  "signature": ""
}
"""

    return call_json_model(
        instructions,
        (
            "JOB DESCRIPTION:\n\n"
            + job_description
            + "\n\nRESUME:\n\n"
            + resume_text
        ),
    )


# ============================================================
# DOCX HELPERS
# ============================================================

def set_run_font(
    run,
    size: float = 10,
    bold: bool = False,
):

    run.font.name = (
        "Times New Roman"
    )

    r_pr = (
        run._element.get_or_add_rPr()
    )

    r_fonts = r_pr.rFonts

    if r_fonts is None:

        r_fonts = OxmlElement(
            "w:rFonts"
        )

        r_pr.insert(
            0,
            r_fonts,
        )

    r_fonts.set(
        qn("w:eastAsia"),
        "Times New Roman",
    )

    run.font.size = Pt(
        size
    )

    run.bold = bold


def add_heading_line(
    document: Document,
    title: str,
):

    p = document.add_paragraph()

    p.paragraph_format.space_before = Pt(
        9
    )

    p.paragraph_format.space_after = Pt(
        4
    )

    run = p.add_run(
        title.upper()
    )

    set_run_font(
        run,
        size=10,
        bold=True,
    )

    p_pr = (
        p._p.get_or_add_pPr()
    )

    p_bdr = OxmlElement(
        "w:pBdr"
    )

    bottom = OxmlElement(
        "w:bottom"
    )

    bottom.set(
        qn("w:val"),
        "single",
    )

    bottom.set(
        qn("w:sz"),
        "4",
    )

    bottom.set(
        qn("w:space"),
        "4",
    )

    bottom.set(
        qn("w:color"),
        "666666",
    )

    p_bdr.append(
        bottom
    )

    p_pr.append(
        p_bdr
    )


# ============================================================
# RESUME DOCX
# ============================================================

def render_resume_docx(
    resume: dict[str, Any],
) -> io.BytesIO:

    document = Document()

    section = (
        document.sections[0]
    )

    section.page_width = Inches(
        8.27
    )

    section.page_height = Inches(
        11.69
    )

    section.top_margin = Inches(
        0.55
    )

    section.bottom_margin = Inches(
        0.55
    )

    section.left_margin = Inches(
        0.65
    )

    section.right_margin = Inches(
        0.65
    )

    # NAME

    p = document.add_paragraph()

    p.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = p.add_run(
        resume.get(
            "name"
        )
        or "Candidate Name"
    )

    set_run_font(
        run,
        size=18,
        bold=True,
    )

    # CONTACT

    contact = [
        resume.get(
            "location"
        ),
        resume.get(
            "email"
        ),
        resume.get(
            "phone"
        ),
        resume.get(
            "linkedin"
        ),
        resume.get(
            "github"
        ),
    ]

    contact = [
        str(item)
        for item in contact
        if item
    ]

    if contact:

        p = document.add_paragraph()

        p.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        p.paragraph_format.space_after = Pt(
            7
        )

        run = p.add_run(
            " | ".join(
                contact
            )
        )

        set_run_font(
            run,
            size=8.5,
        )

    # SUMMARY

    if resume.get(
        "summary"
    ):

        add_heading_line(
            document,
            "Professional Summary",
        )

        p = document.add_paragraph()

        run = p.add_run(
            str(
                resume[
                    "summary"
                ]
            )
        )

        set_run_font(
            run,
            size=9.3,
        )

    # SKILLS

    skills = (
        resume.get(
            "skills"
        )
        or []
    )

    if skills:

        add_heading_line(
            document,
            "Technical Skills",
        )

        p = document.add_paragraph()

        run = p.add_run(
            ", ".join(
                str(item)
                for item in skills
            )
        )

        set_run_font(
            run,
            size=9.1,
        )

    # EXPERIENCE

    experience = (
        resume.get(
            "experience"
        )
        or []
    )

    if experience:

        add_heading_line(
            document,
            "Professional Experience",
        )

        for job in experience:

            if not isinstance(
                job,
                dict,
            ):
                continue

            p = document.add_paragraph()

            run = p.add_run(
                job.get(
                    "title"
                )
                or ""
            )

            set_run_font(
                run,
                size=9.6,
                bold=True,
            )

            dates = job.get(
                "dates"
            )

            if dates:

                run = p.add_run(
                    f" | {dates}"
                )

                set_run_font(
                    run,
                    size=8.8,
                )

            company = job.get(
                "company"
            )

            location = job.get(
                "location"
            )

            company_text = (
                company
                or ""
            )

            if location:

                company_text += (
                    f" | {location}"
                )

            if company_text:

                p = document.add_paragraph()

                run = p.add_run(
                    company_text
                )

                set_run_font(
                    run,
                    size=8.9,
                )

            for bullet in (
                job.get(
                    "bullets"
                )
                or []
            ):

                p = document.add_paragraph()

                p.paragraph_format.left_indent = Inches(
                    0.18
                )

                p.paragraph_format.first_line_indent = Inches(
                    -0.13
                )

                p.paragraph_format.space_after = Pt(
                    2
                )

                run = p.add_run(
                    "• "
                    + str(
                        bullet
                    )
                )

                set_run_font(
                    run,
                    size=9,
                )

    # PROJECTS

    projects = (
        resume.get(
            "projects"
        )
        or []
    )

    if projects:

        add_heading_line(
            document,
            "Projects",
        )

        for project in projects:

            if not isinstance(
                project,
                dict,
            ):
                continue

            p = document.add_paragraph()

            run = p.add_run(
                project.get(
                    "name"
                )
                or ""
            )

            set_run_font(
                run,
                size=9.5,
                bold=True,
            )

            technologies = (
                project.get(
                    "technologies"
                )
                or []
            )

            if technologies:

                run = p.add_run(
                    " | "
                    + ", ".join(
                        str(item)
                        for item in technologies
                    )
                )

                set_run_font(
                    run,
                    size=8.7,
                )

            if project.get(
                "description"
            ):

                p = document.add_paragraph()

                run = p.add_run(
                    str(
                        project[
                            "description"
                        ]
                    )
                )

                set_run_font(
                    run,
                    size=9,
                )

            for bullet in (
                project.get(
                    "bullets"
                )
                or []
            ):

                p = document.add_paragraph()

                p.paragraph_format.left_indent = Inches(
                    0.18
                )

                p.paragraph_format.first_line_indent = Inches(
                    -0.13
                )

                run = p.add_run(
                    "• "
                    + str(
                        bullet
                    )
                )

                set_run_font(
                    run,
                    size=9,
                )

    # EDUCATION

    education = (
        resume.get(
            "education"
        )
        or []
    )

    if education:

        add_heading_line(
            document,
            "Education",
        )

        for item in education:

            if not isinstance(
                item,
                dict,
            ):
                continue

            p = document.add_paragraph()

            run = p.add_run(
                item.get(
                    "degree"
                )
                or ""
            )

            set_run_font(
                run,
                size=9.4,
                bold=True,
            )

            details = []

            if item.get(
                "institution"
            ):

                details.append(
                    str(
                        item[
                            "institution"
                        ]
                    )
                )

            if item.get(
                "dates"
            ):

                details.append(
                    str(
                        item[
                            "dates"
                        ]
                    )
                )

            if details:

                run = p.add_run(
                    "\n"
                    + " | ".join(
                        details
                    )
                )

                set_run_font(
                    run,
                    size=8.8,
                )

    # CERTIFICATIONS

    certifications = (
        resume.get(
            "certifications"
        )
        or []
    )

    if certifications:

        add_heading_line(
            document,
            "Certifications",
        )

        for certification in certifications:

            p = document.add_paragraph()

            run = p.add_run(
                "• "
                + str(
                    certification
                )
            )

            set_run_font(
                run,
                size=9,
            )

    output = io.BytesIO()

    document.save(
        output
    )

    output.seek(0)

    return output


# ============================================================
# COVER LETTER DOCX
# ============================================================

def render_cover_letter_docx(
    letter: Any,
) -> io.BytesIO:

    document = Document()

    section = (
        document.sections[0]
    )

    section.page_width = Inches(
        8.27
    )

    section.page_height = Inches(
        11.69
    )

    section.top_margin = Inches(
        0.8
    )

    section.bottom_margin = Inches(
        0.8
    )

    section.left_margin = Inches(
        0.85
    )

    section.right_margin = Inches(
        0.85
    )

    if isinstance(
        letter,
        str,
    ):

        for block in letter.split(
            "\n"
        ):

            p = document.add_paragraph()

            run = p.add_run(
                block
            )

            set_run_font(
                run,
                size=11,
            )

    else:

        if letter.get(
            "date"
        ):

            p = document.add_paragraph()

            run = p.add_run(
                str(
                    letter[
                        "date"
                    ]
                )
            )

            set_run_font(
                run,
                size=11,
            )

        p = document.add_paragraph()

        run = p.add_run(
            letter.get(
                "salutation"
            )
            or "Dear Hiring Manager,"
        )

        set_run_font(
            run,
            size=11,
        )

        if letter.get(
            "opening"
        ):

            p = document.add_paragraph()

            run = p.add_run(
                str(
                    letter[
                        "opening"
                    ]
                )
            )

            set_run_font(
                run,
                size=11,
            )

        for paragraph in (
            letter.get(
                "body_paragraphs"
            )
            or []
        ):

            p = document.add_paragraph()

            p.paragraph_format.space_after = Pt(
                9
            )

            run = p.add_run(
                str(
                    paragraph
                )
            )

            set_run_font(
                run,
                size=11,
            )

        p = document.add_paragraph()

        run = p.add_run(
            letter.get(
                "closing"
            )
            or "Kind regards,"
        )

        set_run_font(
            run,
            size=11,
        )

        p = document.add_paragraph()

        run = p.add_run(
            letter.get(
                "signature"
            )
            or ""
        )

        set_run_font(
            run,
            size=11,
            bold=True,
        )

    output = io.BytesIO()

    document.save(
        output
    )

    output.seek(0)

    return output


# ============================================================
# ANALYZE
# ============================================================

@app.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(""),
    ashby_url: str = Form(""),
):

    data = await read_upload(
        resume
    )

    resume_text = extract_resume_text(
        resume.filename,
        data,
    )

    final_job_description = (
        resolve_job_description(
            job_description,
            ashby_url,
        )
    )

    try:

        resume_data = structure_resume(
            resume_text
        )

        job_intelligence = (
            extract_job_intelligence(
                final_job_description
            )
        )

        analysis = (
            analyze_resume_against_job(
                resume_text,
                final_job_description,
                job_intelligence,
            )
        )

        file_type = (
            "PDF"
            if resume.filename.lower().endswith(
                ".pdf"
            )
            else "DOCX"
        )

        ats = build_ats_audit(
            resume=resume_data,
            job_intelligence=job_intelligence,
            filename=resume.filename,
            file_type=file_type,
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Analysis failed: "
                f"{exc}"
            ),
        ) from exc

    return {
        "job_description":
            final_job_description,

        "job_intelligence":
            job_intelligence,

        "analysis":
            analysis,

        "ats":
            ats,
    }


# ============================================================
# TAILOR
# ============================================================

@app.post("/tailor")
async def tailor(
    resume: UploadFile = File(...),
    job_description: str = Form(""),
    ashby_url: str = Form(""),
):

    data = await read_upload(
        resume
    )

    resume_text = extract_resume_text(
        resume.filename,
        data,
    )

    final_job_description = (
        resolve_job_description(
            job_description,
            ashby_url,
        )
    )

    try:

        original_resume = (
            structure_resume(
                resume_text
            )
        )

        job_intelligence = (
            extract_job_intelligence(
                final_job_description
            )
        )

        analysis = (
            analyze_resume_against_job(
                resume_text,
                final_job_description,
                job_intelligence,
            )
        )

        original_file_type = (
            "PDF"
            if resume.filename.lower().endswith(
                ".pdf"
            )
            else "DOCX"
        )

        baseline_ats = build_ats_audit(
            resume=original_resume,
            job_intelligence=job_intelligence,
            filename=resume.filename,
            file_type=original_file_type,
        )

        (
            tailored_resume,
            tailored_ats,
            optimization_rounds,
        ) = optimize_resume_for_ats(
            resume_text=resume_text,
            job_description=final_job_description,
            job_intelligence=job_intelligence,
            original_resume=original_resume,
            baseline_ats=baseline_ats,
            max_rounds=5,
        )

        tailored_resume = (
            ensure_target_title_in_summary(
                tailored_resume,
                job_intelligence.get(
                    "job_title",
                    "",
                ),
            )
        )

        tailored_ats = build_ats_audit(
            resume=tailored_resume,
            job_intelligence=job_intelligence,
            filename="tailored-resume.docx",
            file_type="DOCX",
        )

        baseline_score = int(
            baseline_ats.get(
                "match_rate",
                0,
            )
        )

        tailored_score = int(
            tailored_ats.get(
                "match_rate",
                0,
            )
        )

        score_change = (
            tailored_score
            - baseline_score
        )

        tailored_ats[
            "baseline_match_rate"
        ] = baseline_score

        tailored_ats[
            "tailored_match_rate"
        ] = tailored_score

        tailored_ats[
            "score_change"
        ] = score_change

        tailored_ats[
            "optimization_rounds"
        ] = optimization_rounds

        tailored_ats[
            "optimization_target"
        ] = 90

        tailored_ats[
            "target_reached"
        ] = (
            tailored_score >= 90
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Resume tailoring failed: "
                f"{exc}"
            ),
        ) from exc

    return {
        "job_description":
            final_job_description,

        "job_intelligence":
            job_intelligence,

        "analysis":
            analysis,

        "original_resume":
            original_resume,

        "baseline_ats":
            baseline_ats,

        "tailored_resume":
            tailored_resume,

        "ats":
            tailored_ats,

        "comparison": {
            "baseline":
                baseline_score,

            "tailored":
                tailored_score,

            "change":
                score_change,
        },
    }


# ============================================================
# COVER LETTER
# ============================================================

@app.post("/cover-letter")
async def cover_letter(
    resume: UploadFile = File(...),
    job_description: str = Form(""),
    ashby_url: str = Form(""),
):

    data = await read_upload(
        resume
    )

    resume_text = extract_resume_text(
        resume.filename,
        data,
    )

    final_job_description = (
        resolve_job_description(
            job_description,
            ashby_url,
        )
    )

    try:

        letter = (
            generate_cover_letter_with_ai(
                resume_text,
                final_job_description,
            )
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Cover letter generation failed: "
                f"{exc}"
            ),
        ) from exc

    return {
        "job_description":
            final_job_description,

        "cover_letter":
            letter,
    }


# ============================================================
# DOWNLOAD RESUME
# ============================================================

@app.post("/download-resume")
async def download_resume(
    payload: dict[str, Any],
):

    resume_data = payload.get(
        "tailored_resume"
    )

    if not isinstance(
        resume_data,
        dict,
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Tailored resume data is missing."
            ),
        )

    try:

        document = render_resume_docx(
            resume_data
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create resume DOCX: "
                f"{exc}"
            ),
        ) from exc

    return StreamingResponse(
        document,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="tailored-resume.docx"'
        },
    )


# ============================================================
# DOWNLOAD COVER LETTER
# ============================================================

@app.post("/download-cover-letter")
async def download_cover_letter(
    payload: dict[str, Any],
):

    letter = payload.get(
        "cover_letter"
    )

    if not letter:

        raise HTTPException(
            status_code=400,
            detail=(
                "Cover letter data is missing."
            ),
        )

    try:

        document = (
            render_cover_letter_docx(
                letter
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create cover letter DOCX: "
                f"{exc}"
            ),
        ) from exc

    return StreamingResponse(
        document,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="cover-letter.docx"'
        },
    )