import io
import json
import os
import re
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from openai import OpenAI
from pydantic import BaseModel, Field
from pypdf import PdfReader


# =========================================================
# PATHS / ENVIRONMENT
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env",
    )
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
)

MODEL_NAME = "gpt-5.6"


if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not configured. "
        "Add it to the root .env file."
    )


client = OpenAI(
    api_key=OPENAI_API_KEY
)


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

allowed_origins = [
    origin.strip()
    for origin in FRONTEND_URL.split(",")
    if origin.strip()
]

if (
    "http://localhost:5173"
    not in allowed_origins
):
    allowed_origins.append(
        "http://localhost:5173"
    )

if (
    "http://127.0.0.1:5173"
    not in allowed_origins
):
    allowed_origins.append(
        "http://127.0.0.1:5173"
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CONSTANTS
# =========================================================

MAX_RESUME_FILE_SIZE = (
    10 * 1024 * 1024
)


# =========================================================
# GENERAL HELPERS
# =========================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value

    return []


def safe_dict(
    value: Any,
) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def strip_html(
    html: str,
) -> str:

    if not html:
        return ""

    text = html

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</p\s*>",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</div\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</li\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n[ \t]+",
        "\n",
        text,
    )

    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text,
    )

    return text.strip()


def extract_json_from_text(
    text: str,
) -> Dict[str, Any]:

    if not text:
        raise ValueError(
            "The AI returned an empty response."
        )

    cleaned = text.strip()

    cleaned = re.sub(
        r"^```json\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"^```\s*",
        "",
        cleaned,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    try:
        result = json.loads(cleaned)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):
        candidate = cleaned[
            start : end + 1
        ]

        try:
            result = json.loads(
                candidate
            )

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

    raise ValueError(
        "The AI returned invalid JSON."
    )


# =========================================================
# RESUME EXTRACTION
# =========================================================

def extract_pdf_text(
    file_bytes: bytes,
) -> str:

    try:
        reader = PdfReader(
            io.BytesIO(file_bytes)
        )

    except Exception as exc:
        raise ValueError(
            "Could not read the PDF resume."
        ) from exc

    text_parts = []

    for page in reader.pages:

        try:
            page_text = page.extract_text()

        except Exception:
            page_text = None

        if page_text:
            text_parts.append(
                page_text
            )

    return "\n".join(
        text_parts
    ).strip()


def extract_docx_text(
    file_bytes: bytes,
) -> str:

    try:
        document = Document(
            io.BytesIO(file_bytes)
        )

    except Exception as exc:
        raise ValueError(
            "Could not read the DOCX resume."
        ) from exc

    text_parts = []

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:
            text_parts.append(
                text
            )

    for table in document.tables:

        for row in table.rows:

            cells = []

            for cell in row.cells:

                cell_text = (
                    cell.text.strip()
                )

                if cell_text:
                    cells.append(
                        cell_text
                    )

            if cells:
                text_parts.append(
                    " | ".join(cells)
                )

    return "\n".join(
        text_parts
    ).strip()


async def extract_resume_text(
    resume: UploadFile,
) -> str:

    filename = (
        resume.filename or ""
    ).lower()

    if not (
        filename.endswith(".pdf")
        or filename.endswith(".docx")
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF and DOCX resumes "
                "are supported."
            ),
        )

    file_bytes = await resume.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded resume is empty."
            ),
        )

    if (
        len(file_bytes)
        > MAX_RESUME_FILE_SIZE
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "The resume is too large. "
                "Maximum size is 10 MB."
            ),
        )

    if filename.endswith(".pdf"):

        text = extract_pdf_text(
            file_bytes
        )

    else:

        text = extract_docx_text(
            file_bytes
        )

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "No readable text was found "
                "in the uploaded resume."
            ),
        )

    return text


# =========================================================
# ASHBY JOB URL EXTRACTION
# =========================================================

def extract_ashby_job_description(
    job_url: str,
) -> Dict[str, Any]:

    job_url = clean_text(
        job_url
    )

    if not job_url:
        raise ValueError(
            "The job URL is empty."
        )

    parsed = urlparse(
        job_url
    )

    hostname = (
        parsed.hostname or ""
    ).lower()

    if hostname != "jobs.ashbyhq.com":
        raise ValueError(
            "Automatic extraction currently "
            "supports Ashby job URLs only."
        )

    path_parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if len(path_parts) < 2:
        raise ValueError(
            "The Ashby job URL format is invalid."
        )

    board_name = path_parts[0]
    posting_id = path_parts[1]

    if not board_name:
        raise ValueError(
            "Could not determine the Ashby "
            "job board."
        )

    if not posting_id:
        raise ValueError(
            "Could not determine the Ashby "
            "posting ID."
        )

    # IMPORTANT:
    # This is Ashby's official public API.
    api_url = (
        "https://api.ashbyhq.com/"
        "posting-api/job-board/"
        f"{board_name}"
    )

    request = Request(
        api_url,
        headers={
            "User-Agent": (
                "AI-Job-Application-Agent/1.0"
            ),
            "Accept": "application/json",
        },
        method="GET",
    )

    try:

        with urlopen(
            request,
            timeout=20,
        ) as response:

            raw_body = response.read()

    except HTTPError as exc:

        raise ValueError(
            "Ashby returned HTTP "
            f"{exc.code} while retrieving "
            "the job board."
        ) from exc

    except URLError as exc:

        raise ValueError(
            "Could not connect to Ashby's "
            "job posting service."
        ) from exc

    except Exception as exc:

        raise ValueError(
            "Could not retrieve the Ashby "
            "job posting."
        ) from exc

    try:

        data = json.loads(
            raw_body.decode(
                "utf-8"
            )
        )

    except Exception as exc:

        raise ValueError(
            "Ashby returned invalid job "
            "posting data."
        ) from exc

    jobs = data.get(
        "jobs",
        [],
    )

    if not isinstance(
        jobs,
        list,
    ):
        raise ValueError(
            "Ashby returned an unexpected "
            "job posting format."
        )

    if not jobs:
        raise ValueError(
            "No published jobs were found "
            "for this Ashby job board."
        )

    matched_job = None

    # =====================================================
    # MATCH 1
    # Posting ID appears in URL
    # =====================================================

    for job in jobs:

        if not isinstance(
            job,
            dict,
        ):
            continue

        apply_url = clean_text(
            job.get(
                "applyUrl"
            )
        )

        job_page_url = clean_text(
            job.get(
                "jobUrl"
            )
        )

        if (
            posting_id.lower()
            in apply_url.lower()
            or posting_id.lower()
            in job_page_url.lower()
        ):
            matched_job = job
            break

    # =====================================================
    # MATCH 2
    # Compare URL paths
    # =====================================================

    if matched_job is None:

        normalized_input = (
            job_url
            .rstrip("/")
            .lower()
        )

        for job in jobs:

            if not isinstance(
                job,
                dict,
            ):
                continue

            candidates = [
                job.get(
                    "applyUrl"
                ),
                job.get(
                    "jobUrl"
                ),
            ]

            for candidate in candidates:

                if not candidate:
                    continue

                normalized_candidate = (
                    str(candidate)
                    .rstrip("/")
                    .lower()
                )

                if (
                    normalized_input
                    == normalized_candidate
                ):
                    matched_job = job
                    break

            if matched_job:
                break

    # =====================================================
    # MATCH 3
    # Compare the job path slug
    # =====================================================

    if matched_job is None:

        input_last_part = (
            path_parts[-1]
            .lower()
        )

        for job in jobs:

            if not isinstance(
                job,
                dict,
            ):
                continue

            for candidate in [
                job.get("applyUrl"),
                job.get("jobUrl"),
            ]:

                if not candidate:
                    continue

                candidate_parts = [
                    part
                    for part in urlparse(
                        str(candidate)
                    ).path.split("/")
                    if part
                ]

                if not candidate_parts:
                    continue

                candidate_last_part = (
                    candidate_parts[-1]
                    .lower()
                )

                if (
                    candidate_last_part
                    == input_last_part
                ):
                    matched_job = job
                    break

            if matched_job:
                break

    if matched_job is None:
        raise ValueError(
            "The Ashby job posting could not "
            "be matched to a published posting. "
            "The job may have been removed or "
            "the URL may have changed."
        )

    # =====================================================
    # DESCRIPTION
    # =====================================================

    description = clean_text(
        matched_job.get(
            "descriptionPlain"
        )
    )

    if not description:

        description = strip_html(
            matched_job.get(
                "descriptionHtml",
                "",
            )
        )

    if not description:

        raise ValueError(
            "The Ashby posting was found, "
            "but it does not contain a "
            "readable job description."
        )

    return {
        "job_title": clean_text(
            matched_job.get(
                "title"
            )
        ),
        "description": description,
        "job_url": clean_text(
            matched_job.get(
                "jobUrl"
            )
        ),
        "apply_url": clean_text(
            matched_job.get(
                "applyUrl"
            )
        ),
        "location": clean_text(
            matched_job.get(
                "location"
            )
        ),
        "workplace_type": clean_text(
            matched_job.get(
                "workplaceType"
            )
        ),
    }


# =========================================================
# JOB DESCRIPTION RESOLUTION
# =========================================================

def resolve_job_description(
    job_description: str,
    job_url: str,
) -> Dict[str, str]:

    job_description = clean_text(
        job_description
    )

    job_url = clean_text(
        job_url
    )

    # User pasted a job description.
    if job_description:

        return {
            "job_description": (
                job_description
            ),
            "job_title": "",
            "source_url": job_url,
        }

    # User supplied a URL.
    if job_url:

        parsed = urlparse(
            job_url
        )

        hostname = (
            parsed.hostname or ""
        ).lower()

        if hostname == "jobs.ashbyhq.com":

            result = (
                extract_ashby_job_description(
                    job_url
                )
            )

            return {
                "job_description": (
                    result["description"]
                ),
                "job_title": result.get(
                    "job_title",
                    "",
                ),
                "source_url": job_url,
            }

        raise ValueError(
            "Automatic extraction currently "
            "supports Ashby job URLs only. "
            "Please paste the job description "
            "for another job board."
        )

    raise ValueError(
        "Please provide a job description "
        "or a supported job URL."
    )


# =========================================================
# AI JOB ANALYSIS
# =========================================================

def analyze_application(
    job_description: str,
    resume_text: str,
) -> Dict[str, Any]:

    instructions = """
You are an expert technical recruiter.

Compare the candidate resume against the
specific job description.

IMPORTANT RULES:

- Be objective and factual.
- Do not invent candidate experience.
- Do not assume missing information means
  the candidate lacks a skill.
- Distinguish "not specified" from "not required".
- Only identify a candidate skill when the resume
  provides evidence.
- Only identify a job requirement when it is actually
  stated or clearly required.
- Ignore website navigation.
- Ignore unrelated job advertisements.
- Ignore unrelated vacancies.
- Ignore recruitment marketing.
- Ignore generic footer content.

Return ONLY valid JSON.

Use exactly this structure:

{
  "job_title": "",
  "match_score": 0,
  "match_level": "",
  "summary": "",
  "matching_skills": [],
  "skill_gaps": [],
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
  "keywords": []
}

Rules:

- match_score must be an integer from 0 to 100.
- Do not exaggerate the score.
- matching_skills must be an array of concise strings.
- skill_gaps must be an array of concise strings.
- keywords must be an array of concise strings.

match_level must be one of:

Strong Match
Moderate Match
Limited Match
Poor Match
"""

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=f"""
JOB DESCRIPTION:

{job_description}


CANDIDATE RESUME:

{resume_text}
""",
    )

    result = extract_json_from_text(
        response.output_text
    )

    # =====================================================
    # NORMALIZE RESULT
    # =====================================================

    result["job_title"] = clean_text(
        result.get(
            "job_title",
            "",
        )
    )

    try:

        result["match_score"] = int(
            result.get(
                "match_score",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        result["match_score"] = 0

    result["match_score"] = max(
        0,
        min(
            100,
            result["match_score"],
        ),
    )

    result["match_level"] = clean_text(
        result.get(
            "match_level",
            "",
        )
    )

    result["summary"] = clean_text(
        result.get(
            "summary",
            "",
        )
    )

    result["matching_skills"] = [
        clean_text(item)
        for item in safe_list(
            result.get(
                "matching_skills",
                [],
            )
        )
        if clean_text(item)
    ]

    result["skill_gaps"] = [
        clean_text(item)
        for item in safe_list(
            result.get(
                "skill_gaps",
                [],
            )
        )
        if clean_text(item)
    ]

    result["keywords"] = [
        clean_text(item)
        for item in safe_list(
            result.get(
                "keywords",
                [],
            )
        )
        if clean_text(item)
    ]

    experience = safe_dict(
        result.get(
            "experience",
            {},
        )
    )

    result["experience"] = {
        "required": clean_text(
            experience.get(
                "required",
                "Not specified",
            )
        ),
        "candidate": clean_text(
            experience.get(
                "candidate",
                "Not specified",
            )
        ),
        "assessment": clean_text(
            experience.get(
                "assessment",
                "Not specified",
            )
        ),
    }

    education = safe_dict(
        result.get(
            "education",
            {},
        )
    )

    result["education"] = {
        "required": clean_text(
            education.get(
                "required",
                "Not specified",
            )
        ),
        "candidate": clean_text(
            education.get(
                "candidate",
                "Not specified",
            )
        ),
        "assessment": clean_text(
            education.get(
                "assessment",
                "Not specified",
            )
        ),
    }

    return result


# =========================================================
# RESUME NORMALIZATION
# =========================================================

def normalize_resume(
    resume: Dict[str, Any],
) -> Dict[str, Any]:

    resume = safe_dict(
        resume
    )

    normalized = {
        "name": clean_text(
            resume.get("name")
        ),
        "location": clean_text(
            resume.get("location")
        ),
        "email": clean_text(
            resume.get("email")
        ),
        "phone": clean_text(
            resume.get("phone")
        ),
        "linkedin": clean_text(
            resume.get("linkedin")
        ),
        "authorization": clean_text(
            resume.get(
                "authorization"
            )
        ),
        "summary": clean_text(
            resume.get("summary")
        ),
    }

    # =====================================================
    # SKILLS
    # =====================================================

    raw_skills = safe_dict(
        resume.get(
            "skills"
        )
    )

    categories = [
        "Programming",
        "AI / LLM",
        "Machine Learning",
        "Backend / APIs",
        "Databases / Infrastructure",
        "Testing / Delivery",
    ]

    normalized_skills = {}

    for category in categories:

        values = raw_skills.get(
            category,
            [],
        )

        if isinstance(
            values,
            str,
        ):
            values = [
                item.strip()
                for item in values.split(",")
                if item.strip()
            ]

        normalized_skills[
            category
        ] = [
            clean_text(item)
            for item in safe_list(
                values
            )
            if clean_text(item)
        ]

    normalized["skills"] = (
        normalized_skills
    )

    # =====================================================
    # EXPERIENCE
    # =====================================================

    normalized["experience"] = []

    for item in safe_list(
        resume.get(
            "experience"
        )
    ):

        item = safe_dict(
            item
        )

        bullets = [
            clean_text(bullet)
            for bullet in safe_list(
                item.get(
                    "bullets"
                )
            )
            if clean_text(bullet)
        ]

        normalized["experience"].append(
            {
                "title": clean_text(
                    item.get(
                        "title"
                    )
                ),
                "company": clean_text(
                    item.get(
                        "company"
                    )
                ),
                "location": clean_text(
                    item.get(
                        "location"
                    )
                ),
                "dates": clean_text(
                    item.get(
                        "dates"
                    )
                ),
                "bullets": bullets,
            }
        )

    # =====================================================
    # PROJECTS
    # =====================================================

    normalized["projects"] = []

    for item in safe_list(
        resume.get(
            "projects"
        )
    ):

        item = safe_dict(
            item
        )

        technologies = [
            clean_text(tech)
            for tech in safe_list(
                item.get(
                    "technologies"
                )
            )
            if clean_text(tech)
        ]

        bullets = [
            clean_text(bullet)
            for bullet in safe_list(
                item.get(
                    "bullets"
                )
            )
            if clean_text(bullet)
        ]

        normalized["projects"].append(
            {
                "title": clean_text(
                    item.get(
                        "title"
                    )
                ),
                "technologies": technologies,
                "bullets": bullets,
            }
        )

    # =====================================================
    # EDUCATION
    # =====================================================

    normalized["education"] = []

    for item in safe_list(
        resume.get(
            "education"
        )
    ):

        item = safe_dict(
            item
        )

        normalized["education"].append(
            {
                "degree": clean_text(
                    item.get(
                        "degree"
                    )
                ),
                "institution": clean_text(
                    item.get(
                        "institution"
                    )
                ),
                "location": clean_text(
                    item.get(
                        "location"
                    )
                ),
                "dates": clean_text(
                    item.get(
                        "dates"
                    )
                ),
            }
        )

    return normalized


# =========================================================
# AI RESUME TAILORING
# =========================================================

def tailor_resume(
    job_description: str,
    resume_text: str,
) -> Dict[str, Any]:

    instructions = """
You are an expert ATS resume writer.

Create a truthful, job-targeted resume.

Use ONLY facts supported by the original resume.

NEVER invent:

- employers
- job titles
- technologies
- certifications
- projects
- education
- dates
- metrics
- achievements
- responsibilities
- production experience
- cloud platforms

You MAY:

- rewrite wording
- improve clarity
- reorder information
- improve bullet points
- prioritize relevant existing skills
- prioritize relevant existing projects
- improve the summary
- remove irrelevant information

Return ONLY valid JSON.

Use exactly this structure:

{
  "name": "",
  "location": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "authorization": "",
  "summary": "",

  "skills": {
    "Programming": [],
    "AI / LLM": [],
    "Machine Learning": [],
    "Backend / APIs": [],
    "Databases / Infrastructure": [],
    "Testing / Delivery": []
  },

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
      "title": "",
      "technologies": [],
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
  ]
}

Formatting rules:

- No markdown.
- No # symbols.
- No ** symbols.
- No bullet symbols inside bullet strings.
- Keep content concise.
- Preserve actual facts.
"""

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=f"""
JOB DESCRIPTION:

{job_description}


ORIGINAL RESUME:

{resume_text}
""",
    )

    result = extract_json_from_text(
        response.output_text
    )

    return normalize_resume(
        result
    )


# =========================================================
# COVER LETTER
# =========================================================

def generate_cover_letter(
    job_description: str,
    resume_text: str,
) -> str:

    instructions = """
You are an expert professional cover letter writer.

Write a concise, personalized cover letter.

Use only information supported by the resume.

Never invent:

- work experience
- technologies
- achievements
- metrics
- certifications
- education

Rules:

- Professional tone.
- Tailor to the specific job.
- Mention genuine relevant experience.
- Do not copy the job posting.
- Do not mention AI.
- No markdown.
- No bullets.
- Use normal paragraphs.
- Approximately 350–500 words.
- Finish with:

Kind regards,

Candidate Name
"""

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=f"""
JOB DESCRIPTION:

{job_description}


CANDIDATE RESUME:

{resume_text}
""",
    )

    return clean_text(
        response.output_text
    )


# =========================================================
# DOCX HELPERS
# =========================================================

def add_bottom_border(
    paragraph,
):
    p = paragraph._p

    pPr = p.get_or_add_pPr()

    pBdr = pPr.find(
        qn("w:pBdr")
    )

    if pBdr is None:

        pBdr = OxmlElement(
            "w:pBdr"
        )

        pPr.append(
            pBdr
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
        "6",
    )

    bottom.set(
        qn("w:space"),
        "1",
    )

    bottom.set(
        qn("w:color"),
        "777777",
    )

    pBdr.append(
        bottom
    )


def setup_document(
    document: Document,
):

    section = document.sections[0]

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

    normal = document.styles[
        "Normal"
    ]

    normal.font.name = (
        "Times New Roman"
    )

    normal.font.size = Pt(
        10.5
    )

    normal.font.bold = False

    normal.font.italic = False

    normal.paragraph_format.space_before = Pt(
        0
    )

    normal.paragraph_format.space_after = Pt(
        3
    )

    normal.paragraph_format.line_spacing = 1.0


def add_section_heading(
    document: Document,
    title: str,
):

    paragraph = document.add_paragraph()

    paragraph.paragraph_format.space_before = Pt(
        10
    )

    paragraph.paragraph_format.space_after = Pt(
        4
    )

    run = paragraph.add_run(
        title.upper()
    )

    run.font.name = (
        "Times New Roman"
    )

    run.font.size = Pt(
        11
    )

    run.bold = True

    add_bottom_border(
        paragraph
    )

    return paragraph


def add_bullet(
    document: Document,
    text: str,
):

    paragraph = (
        document.add_paragraph()
    )

    paragraph.paragraph_format.left_indent = Inches(
        0.18
    )

    paragraph.paragraph_format.first_line_indent = Inches(
        -0.12
    )

    paragraph.paragraph_format.space_before = Pt(
        0
    )

    paragraph.paragraph_format.space_after = Pt(
        2
    )

    bullet_run = paragraph.add_run(
        "• "
    )

    bullet_run.font.name = (
        "Times New Roman"
    )

    bullet_run.font.size = Pt(
        10.3
    )

    text_run = paragraph.add_run(
        clean_text(text)
    )

    text_run.font.name = (
        "Times New Roman"
    )

    text_run.font.size = Pt(
        10.3
    )

    text_run.bold = False

    text_run.italic = False

    return paragraph


# =========================================================
# RESUME DOCX
# =========================================================

def build_resume_docx(
    resume: Dict[str, Any],
) -> bytes:

    resume = normalize_resume(
        resume
    )

    document = Document()

    setup_document(
        document
    )

    # =====================================================
    # HEADER
    # =====================================================

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    paragraph.paragraph_format.space_after = Pt(
        2
    )

    name_run = paragraph.add_run(
        resume.get(
            "name",
            "Candidate",
        )
    )

    name_run.font.name = (
        "Times New Roman"
    )

    name_run.font.size = Pt(
        17
    )

    name_run.bold = True

    location = clean_text(
        resume.get(
            "location"
        )
    )

    if location:

        paragraph = (
            document.add_paragraph()
        )

        paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        paragraph.paragraph_format.space_after = Pt(
            1
        )

        run = paragraph.add_run(
            location
        )

        run.font.name = (
            "Times New Roman"
        )

        run.font.size = Pt(
            10
        )

    contacts = []

    for field in [
        "email",
        "phone",
        "linkedin",
    ]:

        value = clean_text(
            resume.get(field)
        )

        if value:
            contacts.append(
                value
            )

    if contacts:

        paragraph = (
            document.add_paragraph()
        )

        paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        paragraph.paragraph_format.space_after = Pt(
            1
        )

        run = paragraph.add_run(
            " | ".join(
                contacts
            )
        )

        run.font.name = (
            "Times New Roman"
        )

        run.font.size = Pt(
            9.5
        )

    authorization = clean_text(
        resume.get(
            "authorization"
        )
    )

    if authorization:

        paragraph = (
            document.add_paragraph()
        )

        paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        paragraph.paragraph_format.space_after = Pt(
            4
        )

        run = paragraph.add_run(
            authorization
        )

        run.font.name = (
            "Times New Roman"
        )

        run.font.size = Pt(
            9
        )

    # =====================================================
    # SUMMARY
    # =====================================================

    summary = clean_text(
        resume.get(
            "summary"
        )
    )

    if summary:

        add_section_heading(
            document,
            "Professional Summary",
        )

        paragraph = (
            document.add_paragraph()
        )

        paragraph.paragraph_format.space_after = Pt(
            4
        )

        run = paragraph.add_run(
            summary
        )

        run.font.name = (
            "Times New Roman"
        )

        run.font.size = Pt(
            10.3
        )

        run.bold = False

    # =====================================================
    # SKILLS
    # =====================================================

    skills = safe_dict(
        resume.get(
            "skills"
        )
    )

    if any(
        skills.values()
    ):

        add_section_heading(
            document,
            "Technical Skills",
        )

        for category, values in skills.items():

            if not values:
                continue

            paragraph = (
                document.add_paragraph()
            )

            paragraph.paragraph_format.space_after = Pt(
                2
            )

            label = paragraph.add_run(
                f"{category}: "
            )

            label.font.name = (
                "Times New Roman"
            )

            label.font.size = Pt(
                10
            )

            label.bold = True

            run = paragraph.add_run(
                ", ".join(
                    values
                )
            )

            run.font.name = (
                "Times New Roman"
            )

            run.font.size = Pt(
                10
            )

            run.bold = False

    # =====================================================
    # EXPERIENCE
    # =====================================================

    experience = safe_list(
        resume.get(
            "experience"
        )
    )

    if experience:

        add_section_heading(
            document,
            "Professional Experience",
        )

        for job in experience:

            title_paragraph = (
                document.add_paragraph()
            )

            title_paragraph.paragraph_format.space_before = Pt(
                3
            )

            title_paragraph.paragraph_format.space_after = Pt(
                1
            )

            title_paragraph.paragraph_format.tab_stops.add_tab_stop(
                Inches(6.85)
            )

            title_run = (
                title_paragraph.add_run(
                    clean_text(
                        job.get(
                            "title"
                        )
                    )
                )
            )

            title_run.font.name = (
                "Times New Roman"
            )

            title_run.font.size = Pt(
                10.5
            )

            title_run.bold = True

            dates = clean_text(
                job.get(
                    "dates"
                )
            )

            if dates:

                date_run = (
                    title_paragraph.add_run(
                        "\t" + dates
                    )
                )

                date_run.font.name = (
                    "Times New Roman"
                )

                date_run.font.size = Pt(
                    10
                )

                date_run.bold = False

            company_parts = []

            company = clean_text(
                job.get(
                    "company"
                )
            )

            location = clean_text(
                job.get(
                    "location"
                )
            )

            if company:
                company_parts.append(
                    company
                )

            if location:
                company_parts.append(
                    location
                )

            if company_parts:

                paragraph = (
                    document.add_paragraph()
                )

                paragraph.paragraph_format.space_after = Pt(
                    2
                )

                run = paragraph.add_run(
                    " | ".join(
                        company_parts
                    )
                )

                run.font.name = (
                    "Times New Roman"
                )

                run.font.size = Pt(
                    9.8
                )

                run.bold = False

            for bullet in safe_list(
                job.get(
                    "bullets"
                )
            ):

                if clean_text(bullet):

                    add_bullet(
                        document,
                        bullet,
                    )

    # =====================================================
    # PROJECTS
    # =====================================================

    projects = safe_list(
        resume.get(
            "projects"
        )
    )

    if projects:

        add_section_heading(
            document,
            "Projects",
        )

        for project in projects:

            paragraph = (
                document.add_paragraph()
            )

            paragraph.paragraph_format.space_before = Pt(
                3
            )

            paragraph.paragraph_format.space_after = Pt(
                1
            )

            run = paragraph.add_run(
                clean_text(
                    project.get(
                        "title"
                    )
                )
            )

            run.font.name = (
                "Times New Roman"
            )

            run.font.size = Pt(
                10.5
            )

            run.bold = True

            technologies = [
                clean_text(item)
                for item in safe_list(
                    project.get(
                        "technologies"
                    )
                )
                if clean_text(item)
            ]

            if technologies:

                paragraph = (
                    document.add_paragraph()
                )

                paragraph.paragraph_format.space_after = Pt(
                    2
                )

                run = paragraph.add_run(
                    ", ".join(
                        technologies
                    )
                )

                run.font.name = (
                    "Times New Roman"
                )

                run.font.size = Pt(
                    9.5
                )

                run.italic = True
                run.bold = False

            for bullet in safe_list(
                project.get(
                    "bullets"
                )
            ):

                if clean_text(bullet):

                    add_bullet(
                        document,
                        bullet,
                    )

    # =====================================================
    # EDUCATION
    # =====================================================

    education = safe_list(
        resume.get(
            "education"
        )
    )

    if education:

        add_section_heading(
            document,
            "Education",
        )

        for item in education:

            paragraph = (
                document.add_paragraph()
            )

            paragraph.paragraph_format.space_before = Pt(
                2
            )

            paragraph.paragraph_format.space_after = Pt(
                1
            )

            paragraph.paragraph_format.tab_stops.add_tab_stop(
                Inches(6.85)
            )

            degree_run = (
                paragraph.add_run(
                    clean_text(
                        item.get(
                            "degree"
                        )
                    )
                )
            )

            degree_run.font.name = (
                "Times New Roman"
            )

            degree_run.font.size = Pt(
                10.5
            )

            degree_run.bold = True

            dates = clean_text(
                item.get(
                    "dates"
                )
            )

            if dates:

                run = paragraph.add_run(
                    "\t" + dates
                )

                run.font.name = (
                    "Times New Roman"
                )

                run.font.size = Pt(
                    10
                )

                run.bold = False

            institution_parts = []

            institution = clean_text(
                item.get(
                    "institution"
                )
            )

            location = clean_text(
                item.get(
                    "location"
                )
            )

            if institution:
                institution_parts.append(
                    institution
                )

            if location:
                institution_parts.append(
                    location
                )

            if institution_parts:

                paragraph = (
                    document.add_paragraph()
                )

                paragraph.paragraph_format.space_after = Pt(
                    2
                )

                run = paragraph.add_run(
                    " | ".join(
                        institution_parts
                    )
                )

                run.font.name = (
                    "Times New Roman"
                )

                run.font.size = Pt(
                    9.8
                )

                run.bold = False

    output = io.BytesIO()

    document.save(
        output
    )

    return output.getvalue()


# =========================================================
# COVER LETTER DOCX
# =========================================================

def build_cover_letter_docx(
    content: str,
) -> bytes:

    document = Document()

    setup_document(
        document
    )

    normal = document.styles[
        "Normal"
    ]

    normal.font.name = (
        "Times New Roman"
    )

    normal.font.size = Pt(
        11
    )

    normal.font.bold = False
    normal.font.italic = False

    normal.paragraph_format.space_before = Pt(
        0
    )

    normal.paragraph_format.space_after = Pt(
        10
    )

    normal.paragraph_format.line_spacing = 1.15

    paragraphs = re.split(
        r"\n\s*\n",
        content.strip(),
    )

    for paragraph_text in paragraphs:

        paragraph_text = (
            paragraph_text.strip()
        )

        if not paragraph_text:
            continue

        paragraph = (
            document.add_paragraph()
        )

        paragraph.paragraph_format.space_after = Pt(
            10
        )

        paragraph.paragraph_format.line_spacing = 1.15

        run = paragraph.add_run(
            paragraph_text
        )

        run.font.name = (
            "Times New Roman"
        )

        run.font.size = Pt(
            11
        )

        run.bold = False
        run.italic = False

    output = io.BytesIO()

    document.save(
        output
    )

    return output.getvalue()


# =========================================================
# REQUEST MODELS
# =========================================================

class TailorResumeRequest(
    BaseModel
):

    resume_text: str = Field(
        default=""
    )

    job_description: str = Field(
        default=""
    )

    analysis: Optional[
        Dict[str, Any]
    ] = None


class CoverLetterRequest(
    BaseModel
):

    resume_text: str = Field(
        default=""
    )

    job_description: str = Field(
        default=""
    )

    analysis: Optional[
        Dict[str, Any]
    ] = None


class DownloadResumeRequest(
    BaseModel
):

    tailored_resume: Optional[
        Dict[str, Any]
    ] = None

    tailored_resume_text: Optional[
        str
    ] = None


class DownloadCoverLetterRequest(
    BaseModel
):

    cover_letter: str = Field(
        default=""
    )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "message": (
            "AI Job Application Agent API "
            "is running"
        ),
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# =========================================================
# ANALYZE JOB
# =========================================================

@app.post("/analyze")
async def analyze_job(

    resume: UploadFile = File(...),

    job_description: str = Form(
        ""
    ),

    job_url: str = Form(
        ""
    ),
):

    # -----------------------------------------------------
    # Resume
    # -----------------------------------------------------

    resume_text = (
        await extract_resume_text(
            resume
        )
    )

    # -----------------------------------------------------
    # Job description
    # -----------------------------------------------------

    try:

        resolved_job = (
            resolve_job_description(
                job_description,
                job_url,
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    actual_job_description = (
        resolved_job[
            "job_description"
        ]
    )

    detected_job_title = (
        clean_text(
            resolved_job.get(
                "job_title"
            )
        )
    )

    source_url = clean_text(
        resolved_job.get(
            "source_url"
        )
    )

    # -----------------------------------------------------
    # AI
    # -----------------------------------------------------

    try:

        analysis = (
            analyze_application(
                actual_job_description,
                resume_text,
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI job analysis failed. "
                f"{str(exc)}"
            ),
        ) from exc

    if not analysis.get(
        "job_title"
    ):

        analysis[
            "job_title"
        ] = detected_job_title

    return {
        "analysis": analysis,
        "resume_text": resume_text,
        "job_description": (
            actual_job_description
        ),
        "job_url": source_url,
        "job_title": clean_text(
            analysis.get(
                "job_title"
            )
        ),
    }


# =========================================================
# TAILOR RESUME
# =========================================================

@app.post("/tailor")
async def tailor_job_resume(
    request: TailorResumeRequest,
):

    if not request.resume_text.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "Resume text is required."
            ),
        )

    if not request.job_description.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "Job description is required."
            ),
        )

    try:

        tailored_resume = (
            tailor_resume(
                request.job_description,
                request.resume_text,
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Resume tailoring failed. "
                f"{str(exc)}"
            ),
        ) from exc

    return {
        "tailored_resume": (
            tailored_resume
        )
    }


# =========================================================
# COVER LETTER
# =========================================================

@app.post("/cover-letter")
async def create_cover_letter(
    request: CoverLetterRequest,
):

    if not request.resume_text.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "Resume text is required."
            ),
        )

    if not request.job_description.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "Job description is required."
            ),
        )

    try:

        cover_letter = (
            generate_cover_letter(
                request.job_description,
                request.resume_text,
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Cover letter generation "
                "failed. "
                f"{str(exc)}"
            ),
        ) from exc

    return {
        "cover_letter": cover_letter
    }


# =========================================================
# DOWNLOAD RESUME
# =========================================================

@app.post("/download-resume")
async def download_resume(
    request: DownloadResumeRequest,
):

    resume_data = (
        request.tailored_resume
    )

    # Compatibility with older frontend.
    if not resume_data:

        if not request.tailored_resume_text:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No tailored resume "
                    "was provided."
                ),
            )

        lines = [
            line.strip()
            for line in (
                request
                .tailored_resume_text
                .splitlines()
            )
            if line.strip()
        ]

        resume_data = {
            "name": (
                lines[0]
                if lines
                else "Tailored Resume"
            ),
            "summary": (
                "\n".join(
                    lines[1:]
                )
                if len(lines) > 1
                else ""
            ),
            "skills": {},
            "experience": [],
            "projects": [],
            "education": [],
        }

    try:

        document_bytes = (
            build_resume_docx(
                resume_data
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not create the "
                "resume DOCX. "
                f"{str(exc)}"
            ),
        ) from exc

    return Response(
        content=document_bytes,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                'attachment; '
                'filename="tailored_resume.docx"'
            )
        },
    )


# =========================================================
# DOWNLOAD COVER LETTER
# =========================================================

@app.post(
    "/download-cover-letter"
)
async def download_cover_letter(
    request: DownloadCoverLetterRequest,
):

    if not request.cover_letter.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "No cover letter was provided."
            ),
        )

    try:

        document_bytes = (
            build_cover_letter_docx(
                request.cover_letter
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not create the "
                "cover letter DOCX. "
                f"{str(exc)}"
            ),
        ) from exc

    return Response(
        content=document_bytes,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                'attachment; '
                'filename="cover_letter.docx"'
            )
        },
    )