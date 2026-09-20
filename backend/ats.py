from __future__ import annotations

import re
from typing import Any


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return " ".join(
            clean_text(item)
            for item in value
        )

    if isinstance(value, dict):
        return " ".join(
            clean_text(item)
            for item in value.values()
        )

    return str(value)


def normalize_text(value: Any) -> str:
    text = clean_text(value).lower()

    text = (
        text
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("&", " and ")
    )

    text = re.sub(
        r"[,:;|]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# COMMON EQUIVALENT TERMS
# ============================================================

ALIASES: dict[str, set[str]] = {
    "aws": {
        "aws",
        "amazon web services",
        "amazon aws",
    },

    "c++": {
        "c++",
        "c/c++",
        "cpp",
        "c plus plus",
    },

    "c": {
        "c",
        "c programming",
    },

    "postgresql": {
        "postgresql",
        "postgres",
        "postgres sql",
    },

    "sql server": {
        "sql server",
        "microsoft sql server",
        "mssql",
    },

    "javascript": {
        "javascript",
        "java script",
        "js",
    },

    "typescript": {
        "typescript",
        "type script",
        "ts",
    },

    "python": {
        "python",
        "python3",
        "python 3",
    },

    "java": {
        "java",
        "java programming",
    },

    "kubernetes": {
        "kubernetes",
        "k8s",
    },

    "ci/cd": {
        "ci/cd",
        "ci cd",
        "continuous integration",
        "continuous delivery",
        "continuous deployment",
    },

    "rest api": {
        "rest api",
        "rest apis",
        "restful api",
        "restful apis",
    },

    "microservices": {
        "microservice",
        "microservices",
        "micro-services",
    },

    "unit testing": {
        "unit testing",
        "unit test",
        "unit tests",
    },

    "integration testing": {
        "integration testing",
        "integration test",
        "integration tests",
    },

    "automated testing": {
        "automated testing",
        "automated tests",
        "test automation",
    },

    "database replication": {
        "database replication",
        "database replication engine",
        "replication engine",
        "replication systems",
    },

    "release management": {
        "release management",
        "release engineering",
        "release process",
    },

    "security compliance": {
        "security compliance",
        "security compliance requirements",
        "compliance",
    },

    "object oriented programming": {
        "object oriented programming",
        "object-oriented programming",
        "oop",
    },

    "production debugging": {
        "production debugging",
        "production troubleshooting",
        "troubleshooting production issues",
        "debugging production issues",
    },

    "release pipelines": {
        "release pipelines",
        "deployment pipelines",
        "release pipeline",
        "deployment pipeline",
    },

    "distributed systems": {
        "distributed systems",
        "distributed system",
        "distributed services",
    },

    "code review": {
        "code review",
        "code reviews",
        "peer review",
    },

    "cross-functional collaboration": {
        "cross-functional collaboration",
        "cross functional collaboration",
        "cross-functional work",
    },
}


# ============================================================
# GENERIC WORDS THAT SHOULD NOT BECOME SKILLS
# ============================================================

GENERIC_REQUIREMENT_WORDS = {
    "software",
    "engineering",
    "engineer",
    "development",
    "developer",
    "system",
    "systems",
    "application",
    "applications",
    "service",
    "services",
    "technology",
    "technologies",
    "programming",
    "experience",
    "knowledge",
    "ability",
    "skills",
    "skill",
    "working",
    "work",
    "build",
    "building",
    "develop",
    "developing",
    "strong",
    "excellent",
    "good",
    "responsibility",
    "responsibilities",
    "team",
    "teams",
}


# ============================================================
# SKILL MATCHING
# ============================================================

def skill_matches(
    skill: Any,
    resume_text: str,
) -> bool:

    skill_text = normalize_text(
        skill
    )

    resume = normalize_text(
        resume_text
    )

    if not skill_text:
        return False

    if skill_text in resume:
        return True

    for canonical, aliases in ALIASES.items():

        canonical_normalized = normalize_text(
            canonical
        )

        alias_values = {
            normalize_text(alias)
            for alias in aliases
        }

        if (
            skill_text == canonical_normalized
            or skill_text in alias_values
        ):
            return any(
                alias in resume
                for alias in alias_values
            )

    tokens = [
        token
        for token in re.findall(
            r"[a-z0-9+#.]+",
            skill_text,
        )
        if (
            len(token) > 2
            and token not in GENERIC_REQUIREMENT_WORDS
        )
    ]

    if len(tokens) >= 2:

        matched_tokens = sum(
            1
            for token in tokens
            if token in resume
        )

        return (
            matched_tokens
            / len(tokens)
            >= 0.70
        )

    return False


def match_items(
    items: list[Any] | None,
    resume_text: str,
) -> dict[str, Any]:

    cleaned: list[str] = []
    seen: set[str] = set()

    for item in items or []:

        value = clean_text(
            item
        ).strip()

        if not value:
            continue

        normalized = normalize_text(
            value
        )

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        cleaned.append(
            value
        )

    matched: list[str] = []
    missing: list[str] = []

    for item in cleaned:

        if skill_matches(
            item,
            resume_text,
        ):
            matched.append(item)
        else:
            missing.append(item)

    total = len(cleaned)
    matched_count = len(matched)

    rate = (
        round(
            matched_count
            / total
            * 100
        )
        if total
        else 0
    )

    return {
        "total": total,
        "matched": matched_count,
        "rate": rate,
        "matched_items": matched,
        "missing_items": missing,
    }


# ============================================================
# RESUME TEXT
# ============================================================

def build_resume_text(
    resume: dict[str, Any],
) -> str:

    return clean_text(
        [
            resume.get("name"),
            resume.get("summary"),
            resume.get("skills"),
            resume.get("experience"),
            resume.get("projects"),
            resume.get("education"),
            resume.get("certifications"),
        ]
    )


# ============================================================
# SECTION CHECK
# ============================================================

def check_sections(
    resume: dict[str, Any],
) -> dict[str, bool]:

    return {
        "summary": bool(
            clean_text(
                resume.get("summary")
            ).strip()
        ),
        "skills": bool(
            resume.get("skills")
        ),
        "work_experience": bool(
            resume.get("experience")
        ),
        "projects": bool(
            resume.get("projects")
        ),
        "education": bool(
            resume.get("education")
        ),
        "certifications": bool(
            resume.get("certifications")
        ),
    }


# ============================================================
# CONTACT CHECK
# ============================================================

def check_contact(
    resume: dict[str, Any],
) -> dict[str, bool]:

    return {
        "name": bool(
            clean_text(
                resume.get("name")
                or resume.get("full_name")
            ).strip()
        ),
        "email": bool(
            clean_text(
                resume.get("email")
            ).strip()
        ),
        "phone": bool(
            clean_text(
                resume.get("phone")
            ).strip()
        ),
        "location": bool(
            clean_text(
                resume.get("location")
            ).strip()
        ),
        "linkedin": bool(
            clean_text(
                resume.get("linkedin")
            ).strip()
        ),
        "github": bool(
            clean_text(
                resume.get("github")
            ).strip()
        ),
    }


# ============================================================
# TITLE CHECK
# ============================================================

def check_job_title(
    job_title: str,
    resume_text: str,
) -> dict[str, Any]:

    title = normalize_text(
        job_title
    )

    resume = normalize_text(
        resume_text
    )

    if not title:

        return {
            "matched": False,
            "status": "Not available",
        }

    if title in resume:

        return {
            "matched": True,
            "status": "Found",
        }

    variants = {
        title
    }

    replacements = [
        (
            "software development engineer ii",
            "sde2",
        ),
        (
            "software development engineer 2",
            "sde2",
        ),
        (
            "software development engineer",
            "sde",
        ),
        (
            "senior software engineer",
            "software engineer",
        ),
    ]

    for old, new in replacements:

        if old in title:

            variants.add(
                title.replace(
                    old,
                    new,
                )
            )

    for variant in variants:

        if (
            variant
            and variant in resume
        ):

            return {
                "matched": True,
                "status": "Found",
            }

    tokens = [
        token
        for token in re.findall(
            r"[a-z0-9+#.]+",
            title,
        )
        if token not in {
            "the",
            "and",
            "of",
            "for",
            "a",
            "an",
            "to",
            "in",
            "at",
            "with",
            "ii",
            "2",
        }
    ]

    if not tokens:

        return {
            "matched": False,
            "status": "Review",
        }

    matched = [
        token
        for token in tokens
        if token in resume
    ]

    ratio = (
        len(matched)
        / len(tokens)
    )

    return {
        "matched": ratio >= 0.5,
        "status": (
            "Found"
            if ratio >= 0.5
            else "Review"
        ),
    }


# ============================================================
# EXPERIENCE MATCHING
# ============================================================

EXPERIENCE_STOP_WORDS = {
    "years",
    "year",
    "experience",
    "with",
    "and",
    "the",
    "using",
    "building",
    "developing",
    "working",
    "strong",
    "ability",
    "knowledge",
    "preferred",
    "required",
    "plus",
    "including",
    "across",
    "such",
    "within",
    "demonstrated",
    "proven",
    "role",
    "roles",
}


def experience_requirement_matches(
    requirement: str,
    resume_text: str,
) -> bool:

    requirement_normalized = normalize_text(
        requirement
    )

    resume = normalize_text(
        resume_text
    )

    if not requirement_normalized:
        return False

    if requirement_normalized in resume:
        return True

    tokens = [
        token
        for token in re.findall(
            r"[a-z0-9+#.]+",
            requirement_normalized,
        )
        if (
            len(token) >= 3
            and token not in EXPERIENCE_STOP_WORDS
            and token not in GENERIC_REQUIREMENT_WORDS
        )
    ]

    if not tokens:
        return False

    matches = [
        token
        for token in tokens
        if token in resume
    ]

    ratio = (
        len(matches)
        / len(tokens)
    )

    return ratio >= 0.55


def match_experience_requirements(
    items: list[Any] | None,
    resume_text: str,
) -> dict[str, Any]:

    cleaned: list[str] = []
    seen: set[str] = set()

    for item in items or []:

        value = clean_text(
            item
        ).strip()

        normalized = normalize_text(
            value
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        cleaned.append(
            value
        )

    matched = []
    missing = []

    for item in cleaned:

        if experience_requirement_matches(
            item,
            resume_text,
        ):
            matched.append(item)
        else:
            missing.append(item)

    total = len(cleaned)
    matched_count = len(matched)

    rate = (
        round(
            matched_count
            / total
            * 100
        )
        if total
        else 0
    )

    return {
        "total": total,
        "matched": matched_count,
        "rate": rate,
        "matched_items": matched,
        "missing_items": missing,
    }


# ============================================================
# MEASURABLE RESULTS
# ============================================================

MEASUREMENT_PATTERNS = [
    r"\b\d+(?:\.\d+)?\s*%",
    r"\$\s*\d+(?:\.\d+)?",
    r"\b\d+(?:\.\d+)?\s*(?:ms|sec|secs|seconds|minutes|hours|days)\b",
    r"\b\d+(?:\.\d+)?\s*(?:million|billion|k|m)\b",
    r"\b\d+\+\b",
]


def count_measurable_results(
    resume_text: str,
) -> int:

    found: set[str] = set()

    for pattern in MEASUREMENT_PATTERNS:

        matches = re.findall(
            pattern,
            resume_text,
            flags=re.IGNORECASE,
        )

        for match in matches:

            found.add(
                normalize_text(
                    match
                )
            )

    return len(found)


# ============================================================
# WORD COUNT
# ============================================================

def count_words(
    resume_text: str,
) -> int:

    return len(
        re.findall(
            r"\b[\w+#./-]+\b",
            resume_text,
        )
    )


# ============================================================
# DATE FORMAT
# ============================================================

def check_date_formatting(
    resume: dict[str, Any],
) -> bool:

    experience = (
        resume.get("experience")
        or []
    )

    if not experience:
        return False

    total = 0
    valid = 0

    for item in experience:

        if not isinstance(
            item,
            dict,
        ):
            continue

        dates = clean_text(
            item.get("dates")
            or item.get("duration")
        ).strip()

        if not dates:
            continue

        total += 1

        if re.search(
            r"\b(?:19|20)\d{2}\b",
            dates,
        ):
            valid += 1

    return (
        total > 0
        and valid == total
    )


# ============================================================
# IMPROVEMENT SUGGESTIONS
# ============================================================

def build_ats_improvement_suggestions(
    resume: dict[str, Any],
    job_intelligence: dict[str, Any],
    ats: dict[str, Any],
) -> list[dict[str, Any]]:

    suggestions: list[dict[str, Any]] = []

    # Target title
    if ats.get(
        "job_title_check"
    ):

        suggestions.append({
            "type": "matched",
            "category": "Target title",
            "item": ats.get(
                "job_title"
            ) or "Target title",
            "status": "Matched",
            "message": (
                "The target title is visible in the resume."
            ),
        })

    else:

        suggestions.append({
            "type": "missing",
            "category": "Target title",
            "item": ats.get(
                "job_title"
            ) or "Target title",
            "status": "Missing",
            "message": (
                "Add the target title naturally to the "
                "summary without claiming that you held "
                "the position."
            ),
        })

    # Hard skills
    for item in (
        ats.get(
            "matched_hard_skills"
        )
        or []
    ):

        suggestions.append({
            "type": "matched",
            "category": "Hard skill",
            "item": item,
            "status": "Matched",
            "message": (
                "This technical requirement is supported "
                "by the current resume."
            ),
        })

    for item in (
        ats.get(
            "missing_hard_skills"
        )
        or []
    ):

        suggestions.append({
            "type": "missing",
            "category": "Hard skill",
            "item": item,
            "status": "Missing",
            "message": (
                "Only add this term when the candidate "
                "has genuine evidence supporting it."
            ),
        })

    # Soft skills
    for item in (
        ats.get(
            "matched_soft_skills"
        )
        or []
    ):

        suggestions.append({
            "type": "matched",
            "category": "Soft skill",
            "item": item,
            "status": "Matched",
            "message": (
                "This capability is represented in "
                "the resume."
            ),
        })

    for item in (
        ats.get(
            "missing_soft_skills"
        )
        or []
    ):

        suggestions.append({
            "type": "missing",
            "category": "Soft skill",
            "item": item,
            "status": "Missing",
            "message": (
                "Surface an existing accomplishment "
                "that demonstrates this capability."
            ),
        })

    # Keywords
    for item in (
        ats.get(
            "matched_keywords"
        )
        or []
    ):

        suggestions.append({
            "type": "matched",
            "category": "Keyword",
            "item": item,
            "status": "Matched",
            "message": (
                "This searchable term is already present."
            ),
        })

    for item in (
        ats.get(
            "missing_keywords"
        )
        or []
    ):

        suggestions.append({
            "type": "missing",
            "category": "Keyword",
            "item": item,
            "status": "Missing",
            "message": (
                "Use this terminology only when the "
                "candidate has real supporting evidence."
            ),
        })

    # Experience
    for item in (
        ats.get(
            "matched_experience"
        )
        or []
    ):

        suggestions.append({
            "type": "matched",
            "category": "Experience",
            "item": item,
            "status": "Matched",
            "message": (
                "The resume contains supporting evidence "
                "for this experience requirement."
            ),
        })

    for item in (
        ats.get(
            "missing_experience"
        )
        or []
    ):

        suggestions.append({
            "type": "missing",
            "category": "Experience",
            "item": item,
            "status": "Missing",
            "message": (
                "Do not invent this experience. "
                "Review whether an existing project or "
                "role genuinely supports part of it."
            ),
        })

    # Measurable results
    measured = int(
        ats.get(
            "measurable_results_count",
            0,
        )
        or 0
    )

    if measured >= 5:

        suggestions.append({
            "type": "matched",
            "category": "Measurable results",
            "item": f"{measured} detected",
            "status": "Strong",
            "message": (
                "Multiple measurable achievements "
                "were detected."
            ),
        })

    else:

        suggestions.append({
            "type": "improvement",
            "category": "Measurable results",
            "item": f"{measured}/5 detected",
            "status": "Improve",
            "message": (
                "Use real metrics already supported by "
                "the resume, such as percentages, scale, "
                "time saved, throughput, latency, counts, "
                "or performance improvements."
            ),
        })

    # Searchability
    searchability = int(
        ats.get(
            "searchability_score",
            0,
        )
        or 0
    )

    if searchability >= 90:

        suggestions.append({
            "type": "matched",
            "category": "Searchability",
            "item": f"{searchability}%",
            "status": "Strong",
            "message": (
                "Resume structure and searchable information "
                "are in good shape."
            ),
        })

    else:

        suggestions.append({
            "type": "improvement",
            "category": "Searchability",
            "item": f"{searchability}%",
            "status": "Improve",
            "message": (
                "Improve title visibility, section structure, "
                "and contact information."
            ),
        })

    # Formatting
    formatting = int(
        ats.get(
            "formatting_score",
            0,
        )
        or 0
    )

    if formatting >= 90:

        suggestions.append({
            "type": "matched",
            "category": "Formatting",
            "item": f"{formatting}%",
            "status": "Strong",
            "message": (
                "The resume uses an ATS-friendly structure."
            ),
        })

    else:

        suggestions.append({
            "type": "improvement",
            "category": "Formatting",
            "item": f"{formatting}%",
            "status": "Improve",
            "message": (
                "Use a clean single-column layout, standard "
                "headings, consistent dates, and a simple "
                "filename."
            ),
        })

    return suggestions[:100]


# ============================================================
# FULL ATS AUDIT
# ============================================================

def build_ats_audit(
    resume: dict[str, Any],
    job_intelligence: dict[str, Any],
    filename: str = "",
    file_type: str = "",
) -> dict[str, Any]:

    resume_text = build_resume_text(
        resume
    )

    hard_skills = (
        job_intelligence.get(
            "hard_skills"
        )
        or []
    )

    soft_skills = (
        job_intelligence.get(
            "soft_skills"
        )
        or []
    )

    keywords = (
        job_intelligence.get(
            "keywords"
        )
        or []
    )

    experience_requirements = (
        job_intelligence.get(
            "experience_requirements"
        )
        or []
    )

    job_title = clean_text(
        job_intelligence.get(
            "job_title"
        )
    )

    hard = match_items(
        hard_skills,
        resume_text,
    )

    soft = match_items(
        soft_skills,
        resume_text,
    )

    keyword_result = match_items(
        keywords,
        resume_text,
    )

    experience = (
        match_experience_requirements(
            experience_requirements,
            resume_text,
        )
    )

    title = check_job_title(
        job_title,
        resume_text,
    )

    contact = check_contact(
        resume
    )

    sections = check_sections(
        resume
    )

    contact_score = round(
        sum(
            contact.values()
        )
        / len(contact)
        * 100
    )

    section_score = round(
        (
            int(sections["summary"])
            + int(sections["skills"])
            + int(sections["work_experience"])
        )
        / 3
        * 100
    )

    measurable_results = (
        count_measurable_results(
            resume_text
        )
    )

    measurable_score = min(
        100,
        round(
            measurable_results
            / 5
            * 100
        ),
    )

    date_formatting = (
        check_date_formatting(
            resume
        )
    )

    words = count_words(
        resume_text
    )

    if 250 <= words <= 1000:

        word_score = 100

    elif 150 <= words < 250:

        word_score = 85

    elif 1000 < words <= 1200:

        word_score = 90

    elif words < 100:

        word_score = 55

    else:

        word_score = 75

    searchability_score = round(
        (
            contact_score
            + section_score
            + (
                100
                if title["matched"]
                else 0
            )
            + (
                100
                if date_formatting
                else 0
            )
        )
        / 4
    )

    normalized_file_type = normalize_text(
        file_type
    )

    valid_file_type = (
        normalized_file_type
        in {
            "pdf",
            "docx",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
    )

    filename_ok = bool(
        filename.strip()
    )

    formatting_score = round(
        (
            (
                100
                if valid_file_type
                else 0
            )
            + (
                100
                if filename_ok
                else 0
            )
            + section_score
        )
        / 3
    )

    title_score = (
        100
        if title["matched"]
        else 0
    )

    overall_score = round(
        hard["rate"] * 0.35
        + keyword_result["rate"] * 0.22
        + experience["rate"] * 0.12
        + soft["rate"] * 0.07
        + title_score * 0.08
        + measurable_score * 0.05
        + searchability_score * 0.06
        + formatting_score * 0.05
    )

    overall_score = max(
        0,
        min(
            100,
            overall_score,
        ),
    )

    base_audit = {
        "job_title":
            job_title,

        "job_title_check":
            title["matched"],

        "matched_hard_skills":
            hard["matched_items"],

        "missing_hard_skills":
            hard["missing_items"],

        "matched_soft_skills":
            soft["matched_items"],

        "missing_soft_skills":
            soft["missing_items"],

        "matched_keywords":
            keyword_result["matched_items"],

        "missing_keywords":
            keyword_result["missing_items"],

        "matched_experience":
            experience["matched_items"],

        "missing_experience":
            experience["missing_items"],

        "measurable_results_count":
            measurable_results,

        "searchability_score":
            searchability_score,

        "formatting_score":
            formatting_score,
    }

    improvement_suggestions = (
        build_ats_improvement_suggestions(
            resume=resume,
            job_intelligence=job_intelligence,
            ats=base_audit,
        )
    )

    return {
        "match_rate":
            overall_score,

        "ats_score":
            overall_score,

        "overall_score":
            overall_score,

        "searchability_score":
            searchability_score,

        "contact_score":
            contact_score,

        "contact_information":
            contact,

        "hard_skills_total":
            hard["total"],

        "hard_skills_matched":
            hard["matched"],

        "hard_skills_rate":
            hard["rate"],

        "hard_skills_match":
            (
                f"{hard['matched']}/{hard['total']}"
                if hard["total"]
                else "0/0"
            ),

        "matched_hard_skills":
            hard["matched_items"],

        "missing_hard_skills":
            hard["missing_items"],

        "soft_skills_total":
            soft["total"],

        "soft_skills_matched":
            soft["matched"],

        "soft_skills_rate":
            soft["rate"],

        "soft_skills_match":
            (
                f"{soft['matched']}/{soft['total']}"
                if soft["total"]
                else "0/0"
            ),

        "matched_soft_skills":
            soft["matched_items"],

        "missing_soft_skills":
            soft["missing_items"],

        "keyword_total":
            keyword_result["total"],

        "keyword_matched":
            keyword_result["matched"],

        "keyword_match_rate":
            keyword_result["rate"],

        "keyword_match":
            (
                f"{keyword_result['matched']}/{keyword_result['total']}"
                if keyword_result["total"]
                else "0/0"
            ),

        "matched_keywords":
            keyword_result["matched_items"],

        "missing_keywords":
            keyword_result["missing_items"],

        "experience_total":
            experience["total"],

        "experience_matched":
            experience["matched"],

        "experience_match_rate":
            experience["rate"],

        "experience_match":
            (
                f"{experience['matched']}/{experience['total']}"
                if experience["total"]
                else "0/0"
            ),

        "matched_experience":
            experience["matched_items"],

        "missing_experience":
            experience["missing_items"],

        "job_title":
            job_title,

        "job_title_check":
            title["matched"],

        "job_title_status":
            title["status"],

        "measurable_results_count":
            measurable_results,

        "measurable_results_target":
            5,

        "measurable_results_score":
            measurable_score,

        "section_presence":
            sections,

        "section_score":
            section_score,

        "date_formatting":
            date_formatting,

        "word_count":
            words,

        "word_count_score":
            word_score,

        "file_type":
            file_type or "DOCX",

        "filename":
            filename or "Available",

        "filename_check":
            filename_ok,

        "formatting_score":
            formatting_score,

        "physical_address_flag":
            bool(
                resume.get(
                    "location"
                )
            ),

        "summary_present":
            sections["summary"],

        "education_present":
            sections["education"],

        "work_experience_present":
            sections["work_experience"],

        "improvement_suggestions":
            improvement_suggestions,
    }