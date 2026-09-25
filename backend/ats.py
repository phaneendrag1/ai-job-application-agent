from __future__ import annotations

import re
from collections import Counter
from typing import Any


# ============================================================
# JOBPILOT AI — ATS ENGINE V3
# ============================================================
#
# Fast, deterministic ATS compatibility analysis.
#
# This engine evaluates:
#
#   1. Job Match
#      - Hard skills
#      - Keywords
#      - Experience evidence
#      - Job title
#      - Soft skills
#
#   2. ATS Readability
#      - Required sections
#      - Contact information
#      - File format
#      - Parseability
#
#   3. Resume Quality
#      - Quantified results
#      - Action verbs
#      - Repetition
#      - Bullet quality
#
#   4. Career Fit
#      - Seniority / experience evidence
#
# IMPORTANT:
# This is an ATS compatibility ESTIMATE.
# It is not an employer's actual ATS score.
#
# No AI call is made by this file.
# ============================================================


# ============================================================
# STOPWORDS
# ============================================================

STOPWORDS = {
    "about",
    "above",
    "across",
    "after",
    "again",
    "against",
    "also",
    "among",
    "and",
    "any",
    "around",
    "are",
    "as",
    "been",
    "being",
    "below",
    "between",
    "both",
    "build",
    "building",
    "can",
    "could",
    "develop",
    "developed",
    "developing",
    "development",
    "ensure",
    "ensuring",
    "experience",
    "for",
    "from",
    "have",
    "having",
    "into",
    "its",
    "job",
    "maintain",
    "maintaining",
    "make",
    "making",
    "more",
    "must",
    "other",
    "our",
    "over",
    "perform",
    "performed",
    "performing",
    "provide",
    "providing",
    "responsible",
    "responsibilities",
    "should",
    "software",
    "support",
    "supporting",
    "team",
    "teams",
    "that",
    "their",
    "these",
    "this",
    "those",
    "through",
    "under",
    "using",
    "work",
    "worked",
    "working",
    "within",
    "will",
    "with",
    "you",
    "your",
}


# ============================================================
# TECHNOLOGY ALIASES
# ============================================================

ALIASES = {
    # Languages
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "py": "python",
    "python": "python",
    "c++": "cpp",
    "cpp": "cpp",
    "c#": "csharp",
    "csharp": "csharp",
    "golang": "go",
    "go": "go",

    # Databases
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mongo": "mongodb",
    "mongodb": "mongodb",
    "mssql": "sql server",
    "sql server": "sql server",
    "mysql": "mysql",
    "sql": "sql",
    "oracle db": "oracle",
    "oracle database": "oracle",
    "oracle": "oracle",

    # Frontend
    "reactjs": "react",
    "react.js": "react",
    "react": "react",
    "angularjs": "angular",
    "angular.js": "angular",
    "angular": "angular",
    "vuejs": "vue",
    "vue.js": "vue",
    "vue": "vue",

    # Backend
    "nodejs": "node",
    "node.js": "node",
    "node": "node",
    "spring boot": "spring boot",
    "spring": "spring",
    ".net": "dotnet",
    "dot net": "dotnet",
    "dotnet": "dotnet",

    # Cloud
    "amazon web services": "aws",
    "aws": "aws",
    "amazon ec2": "ec2",
    "ec2": "ec2",
    "amazon s3": "s3",
    "s3": "s3",
    "amazon rds": "rds",
    "rds": "rds",
    "google cloud": "gcp",
    "gcp": "gcp",
    "microsoft azure": "azure",
    "azure": "azure",

    # DevOps
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "ci/cd": "cicd",
    "ci cd": "cicd",
    "continuous integration": "cicd",
    "continuous delivery": "cicd",
    "docker": "docker",
    "terraform": "terraform",

    # APIs / Architecture
    "rest api": "rest",
    "rest apis": "rest",
    "restful api": "rest",
    "restful": "rest",
    "rest": "rest",
    "microservice": "microservices",
    "microservices": "microservices",

    # Messaging
    "apache kafka": "kafka",
    "kafka": "kafka",
    "rabbitmq": "rabbitmq",

    # AI
    "machine learning": "machine learning",
    "ml": "machine learning",
    "artificial intelligence": "ai",
    "ai": "ai",
    "natural language processing": "nlp",
    "nlp": "nlp",

    # Testing
    "unit testing": "unit testing",
    "automated testing": "automated testing",
    "test automation": "test automation",
    "junit": "junit",
    "pytest": "pytest",

    # Source control
    "github": "github",
    "gitlab": "gitlab",
    "git": "git",

    # Tools
    "jira": "jira",
}


# ============================================================
# ACTION VERBS
# ============================================================

ACTION_VERBS = {
    "achieved",
    "architected",
    "automated",
    "built",
    "configured",
    "created",
    "decreased",
    "delivered",
    "deployed",
    "designed",
    "developed",
    "drove",
    "engineered",
    "implemented",
    "improved",
    "increased",
    "integrated",
    "launched",
    "migrated",
    "modernized",
    "optimized",
    "refactored",
    "reduced",
    "resolved",
    "scaled",
    "streamlined",
    "tested",
    "troubleshot",
    "validated",
}


# ============================================================
# WEAK / GENERIC BULLET STARTERS
# ============================================================

WEAK_STARTERS = {
    "worked",
    "helped",
    "assisted",
    "responsible",
    "responsible for",
    "involved",
    "participated",
    "supported",
    "did",
    "handled",
}


# ============================================================
# SENIORITY TERMS
# ============================================================

SENIORITY_TERMS = {
    "intern": "intern",
    "internship": "intern",
    "graduate": "graduate",
    "new graduate": "graduate",
    "junior": "junior",
    "entry level": "junior",
    "entry-level": "junior",
    "associate": "associate",
    "mid level": "mid",
    "mid-level": "mid",
    "senior": "senior",
    "staff": "staff",
    "principal": "principal",
    "lead": "lead",
    "manager": "manager",
    "director": "director",
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(value: Any) -> str:
    text = str(value or "").lower()

    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("’", "'")

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def canonical(value: str) -> str:
    value = normalize(value)

    return ALIASES.get(
        value,
        value,
    )


def text_tokens(
    value: str,
) -> list[str]:

    value = normalize(value)

    raw = re.findall(
        r"[a-zA-Z0-9+#./-]+",
        value,
    )

    tokens: list[str] = []

    for token in raw:

        token = token.strip(
            ".,;:()[]{}"
        )

        if not token:
            continue

        normalized = canonical(token)

        if normalized in STOPWORDS:
            continue

        if len(normalized) < 3:
            continue

        tokens.append(normalized)

    return tokens


def meaningful_tokens(
    value: str,
) -> set[str]:

    return set(
        text_tokens(value)
    )


# ============================================================
# RESUME SECTION EXTRACTION
# ============================================================

def get_resume_sections(
    resume: dict[str, Any],
) -> dict[str, str]:

    experience_parts: list[str] = []
    project_parts: list[str] = []
    education_parts: list[str] = []
    skills_parts: list[str] = []
    certification_parts: list[str] = []

    # ----------------------------
    # Skills
    # ----------------------------

    for skill in resume.get(
        "skills",
        [],
    ) or []:

        skills_parts.append(
            str(skill)
        )

    # ----------------------------
    # Experience
    # ----------------------------

    for experience in resume.get(
        "experience",
        [],
    ) or []:

        for field in [
            "company",
            "title",
            "location",
            "dates",
        ]:

            value = experience.get(
                field,
                "",
            )

            if value:
                experience_parts.append(
                    str(value)
                )

        for bullet in experience.get(
            "bullets",
            [],
        ) or []:

            experience_parts.append(
                str(bullet)
            )

    # ----------------------------
    # Projects
    # ----------------------------

    for project in resume.get(
        "projects",
        [],
    ) or []:

        for field in [
            "name",
            "dates",
        ]:

            value = project.get(
                field,
                "",
            )

            if value:
                project_parts.append(
                    str(value)
                )

        for bullet in project.get(
            "bullets",
            [],
        ) or []:

            project_parts.append(
                str(bullet)
            )

    # ----------------------------
    # Education
    # ----------------------------

    for education in resume.get(
        "education",
        [],
    ) or []:

        for field in [
            "school",
            "degree",
            "dates",
        ]:

            value = education.get(
                field,
                "",
            )

            if value:
                education_parts.append(
                    str(value)
                )

        for detail in education.get(
            "details",
            [],
        ) or []:

            education_parts.append(
                str(detail)
            )

    # ----------------------------
    # Certifications
    # ----------------------------

    for certification in resume.get(
        "certifications",
        [],
    ) or []:

        certification_parts.append(
            str(certification)
        )

    return {
        "summary": normalize(
            resume.get(
                "summary",
                "",
            )
        ),

        "skills": normalize(
            " ".join(
                skills_parts
            )
        ),

        "experience": normalize(
            " ".join(
                experience_parts
            )
        ),

        "projects": normalize(
            " ".join(
                project_parts
            )
        ),

        "education": normalize(
            " ".join(
                education_parts
            )
        ),

        "certifications": normalize(
            " ".join(
                certification_parts
            )
        ),
    }


def flatten_resume(
    resume: dict[str, Any],
) -> str:

    sections = get_resume_sections(
        resume
    )

    return normalize(
        " ".join(
            sections.values()
        )
    )


# ============================================================
# MATCHING
# ============================================================

def phrase_matches(
    term: str,
    resume_text: str,
) -> bool:

    term = normalize(term)

    if not term:
        return False

    if term in resume_text:
        return True

    canonical_term = canonical(
        term
    )

    if canonical_term in resume_text:
        return True

    aliases_to_check = [
        key
        for key, value in ALIASES.items()
        if value == canonical_term
    ]

    for alias in aliases_to_check:

        if alias in resume_text:
            return True

    return False


def token_match_ratio(
    requirement: str,
    resume_text: str,
) -> float:

    requirement_tokens = meaningful_tokens(
        requirement
    )

    if not requirement_tokens:
        return 0.0

    resume_tokens = meaningful_tokens(
        resume_text
    )

    if not resume_tokens:
        return 0.0

    matched = (
        requirement_tokens
        & resume_tokens
    )

    return (
        len(matched)
        / len(requirement_tokens)
    )


def requirement_score(
    requirement: str,
    resume_text: str,
) -> int:

    requirement = str(
        requirement or ""
    ).strip()

    if not requirement:
        return 0

    if phrase_matches(
        requirement,
        resume_text,
    ):
        return 100

    tokens = meaningful_tokens(
        requirement
    )

    if not tokens:
        return 0

    ratio = token_match_ratio(
        requirement,
        resume_text,
    )

    if len(tokens) <= 2:

        if ratio >= 1.0:
            return 100

        if ratio >= 0.5:
            return 60

        return 0

    if ratio >= 0.70:
        return 100

    if ratio >= 0.50:
        return 85

    if ratio >= 0.35:
        return 70

    if ratio >= 0.20:
        return 45

    if ratio >= 0.10:
        return 20

    return 0


# ============================================================
# SKILL GROUP
# ============================================================

def score_skill_group(
    items: list[str],
    resume_text: str,
) -> dict[str, Any]:

    unique: list[str] = []
    seen: set[str] = set()

    for item in items or []:

        clean = str(
            item or ""
        ).strip()

        if not clean:
            continue

        key = canonical(
            clean
        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            clean
        )

    matched: list[str] = []
    partial: list[str] = []
    missing: list[str] = []

    scores: dict[str, int] = {}

    for item in unique:

        score = requirement_score(
            item,
            resume_text,
        )

        scores[item] = score

        if score >= 75:

            matched.append(
                item
            )

        elif score >= 25:

            partial.append(
                item
            )

        else:

            missing.append(
                item
            )

    if unique:

        weighted = (
            len(matched)
            + len(partial) * 0.5
        )

        rate = round(
            weighted
            / len(unique)
            * 100
        )

    else:

        rate = 100

    return {
        "total": len(unique),
        "matched": len(matched),
        "partial": len(partial),
        "missing": len(missing),
        "rate": min(
            100,
            rate,
        ),
        "matched_items": matched,
        "partial_items": partial,
        "missing_items": missing,
        "scores": scores,
    }


# ============================================================
# EXPERIENCE EVIDENCE
# ============================================================

def score_experience_requirement(
    requirement: str,
    sections: dict[str, str],
) -> dict[str, Any]:

    professional_score = requirement_score(
        requirement,
        sections["experience"],
    )

    project_score = requirement_score(
        requirement,
        sections["projects"],
    )

    education_score = requirement_score(
        requirement,
        sections["education"],
    )

    skills_score = requirement_score(
        requirement,
        sections["skills"],
    )

    summary_score = requirement_score(
        requirement,
        sections["summary"],
    )

    scores = {
        "professional": professional_score,
        "project": project_score,
        "education": education_score,
        "skills": skills_score,
        "summary": summary_score,
    }

    strongest_source = max(
        scores,
        key=scores.get,
    )

    strongest_score = scores[
        strongest_source
    ]

    if strongest_score >= 75:

        if strongest_source == "professional":
            evidence_type = "direct"

        elif strongest_source == "project":
            evidence_type = "project"

        elif strongest_source == "education":
            evidence_type = "education"

        else:
            evidence_type = "supporting"

    elif strongest_score >= 25:

        evidence_type = "partial"

    else:

        evidence_type = "missing"

    return {
        "score": strongest_score,
        "source": strongest_source,
        "type": evidence_type,
        "scores": scores,
    }


def score_experience_requirements(
    requirements: list[str],
    sections: dict[str, str],
) -> dict[str, Any]:

    unique: list[str] = []
    seen: set[str] = set()

    for requirement in requirements or []:

        clean = str(
            requirement or ""
        ).strip()

        if not clean:
            continue

        key = normalize(
            clean
        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            clean
        )

    direct: list[str] = []
    project: list[str] = []
    education: list[str] = []
    supporting: list[str] = []
    partial: list[str] = []
    missing: list[str] = []

    total_scores: list[int] = []

    evidence_details: list[dict[str, Any]] = []

    for requirement in unique:

        evidence = score_experience_requirement(
            requirement,
            sections,
        )

        score = evidence["score"]

        total_scores.append(
            score
        )

        evidence_details.append(
            {
                "requirement": requirement,
                **evidence,
            }
        )

        if evidence["type"] == "direct":
            direct.append(requirement)

        elif evidence["type"] == "project":
            project.append(requirement)

        elif evidence["type"] == "education":
            education.append(requirement)

        elif evidence["type"] == "supporting":
            supporting.append(requirement)

        elif evidence["type"] == "partial":
            partial.append(requirement)

        else:
            missing.append(requirement)

    if total_scores:

        rate = round(
            sum(total_scores)
            / len(total_scores)
        )

    else:

        rate = 100

    return {
        "total": len(unique),
        "matched": len(direct),
        "partial": len(partial),
        "missing": len(missing),
        "rate": rate,
        "matched_items": direct,
        "project_items": project,
        "education_items": education,
        "supporting_items": supporting,
        "partial_items": partial,
        "missing_items": missing,
        "evidence_details": evidence_details,
    }


# ============================================================
# JOB TITLE
# ============================================================

def title_score(
    job_title: str,
    resume_text: str,
) -> int:

    job_title = normalize(
        job_title
    )

    resume_text = normalize(
        resume_text
    )

    if not job_title:
        return 100

    if not resume_text:
        return 0

    if job_title in resume_text:
        return 100

    title_variations = {
        "software developer": "software engineer",
        "software development engineer": "software engineer",
        "sde": "software engineer",
        "sde1": "software engineer",
        "sde 1": "software engineer",
        "sde2": "software engineer",
        "sde 2": "software engineer",
        "application developer": "software engineer",
        "backend developer": "software engineer",
        "backend engineer": "software engineer",
        "full stack developer": "software engineer",
        "full-stack developer": "software engineer",
        "full stack engineer": "software engineer",
    }

    normalized_target = title_variations.get(
        job_title,
        job_title,
    )

    core_roles = [
        "software engineer",
        "software developer",
        "backend engineer",
        "backend developer",
        "full stack engineer",
        "full stack developer",
        "frontend engineer",
        "frontend developer",
        "web developer",
        "application developer",
        "systems engineer",
        "data engineer",
        "machine learning engineer",
        "devops engineer",
        "cloud engineer",
    ]

    matched_core_role = None

    for role in core_roles:

        if role in normalized_target:

            matched_core_role = role
            break

    if matched_core_role:

        if matched_core_role in resume_text:
            return 90

        equivalent_roles = {
            "software engineer": [
                "software developer",
                "application developer",
                "backend engineer",
                "backend developer",
            ],
            "software developer": [
                "software engineer",
                "application developer",
                "backend engineer",
            ],
            "backend engineer": [
                "backend developer",
                "software engineer",
                "software developer",
            ],
            "backend developer": [
                "backend engineer",
                "software engineer",
                "software developer",
            ],
        }

        for equivalent in equivalent_roles.get(
            matched_core_role,
            [],
        ):

            if equivalent in resume_text:
                return 80

    tokens = meaningful_tokens(
        job_title
    )

    if not tokens:
        return 50

    resume_tokens = meaningful_tokens(
        resume_text
    )

    matched = (
        tokens
        & resume_tokens
    )

    ratio = (
        len(matched)
        / len(tokens)
    )

    if ratio >= 0.75:
        return 80

    if ratio >= 0.50:
        return 60

    if ratio >= 0.25:
        return 35

    return 0


# ============================================================
# SECTIONS
# ============================================================

def calculate_sections(
    resume: dict[str, Any],
) -> tuple[dict[str, bool], int]:

    sections = {
        "summary": bool(
            str(
                resume.get(
                    "summary",
                    "",
                )
                or ""
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
    }

    score = round(
        sum(
            sections.values()
        )
        / len(sections)
        * 100
    )

    return (
        sections,
        score,
    )


# ============================================================
# CONTACT
# ============================================================

def calculate_contact(
    resume: dict[str, Any],
) -> tuple[dict[str, bool], int]:

    contact = {
        "name": bool(
            resume.get("name")
        ),

        "email": bool(
            resume.get("email")
        ),

        "phone": bool(
            resume.get("phone")
        ),

        "linkedin_or_github": bool(
            resume.get("linkedin")
            or resume.get("github")
        ),
    }

    score = round(
        sum(
            contact.values()
        )
        / len(contact)
        * 100
    )

    return (
        contact,
        score,
    )


# ============================================================
# QUANTIFIED RESULTS
# ============================================================

def get_all_bullets(
    resume: dict[str, Any],
) -> list[str]:

    bullets: list[str] = []

    for experience in resume.get(
        "experience",
        [],
    ) or []:

        for bullet in experience.get(
            "bullets",
            [],
        ) or []:

            if str(bullet).strip():

                bullets.append(
                    str(bullet).strip()
                )

    for project in resume.get(
        "projects",
        [],
    ) or []:

        for bullet in project.get(
            "bullets",
            [],
        ) or []:

            if str(bullet).strip():

                bullets.append(
                    str(bullet).strip()
                )

    return bullets


def count_measurable_results(
    resume: dict[str, Any],
) -> int:

    count = 0

    patterns = [
        r"\d+%",
        r"\$\s?\d+",
        r"\b\d[\d,.]*\b",
        r"\bincreased\b",
        r"\breduced\b",
        r"\bimproved\b",
        r"\bsaved\b",
        r"\bgrew\b",
        r"\bdecreased\b",
        r"\bcut\b",
        r"\bboosted\b",
        r"\bscaled\b",
    ]

    for bullet in get_all_bullets(
        resume
    ):

        if any(
            re.search(
                pattern,
                bullet,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        ):

            count += 1

    return count


def calculate_quantification_score(
    resume: dict[str, Any],
) -> dict[str, Any]:

    bullets = get_all_bullets(
        resume
    )

    total = len(
        bullets
    )

    measurable = count_measurable_results(
        resume
    )

    if total == 0:

        return {
            "score": 0,
            "total_bullets": 0,
            "measurable_bullets": 0,
        }

    ratio = (
        measurable
        / total
    )

    if ratio >= 0.50:
        score = 100

    elif ratio >= 0.35:
        score = 90

    elif ratio >= 0.25:
        score = 80

    elif ratio >= 0.15:
        score = 70

    elif ratio > 0:
        score = 55

    else:
        score = 35

    return {
        "score": score,
        "total_bullets": total,
        "measurable_bullets": measurable,
    }


# ============================================================
# ACTION VERBS
# ============================================================

def first_word(
    sentence: str,
) -> str:

    words = re.findall(
        r"[A-Za-z]+",
        sentence.lower(),
    )

    if not words:
        return ""

    return words[0]


def calculate_action_verb_score(
    resume: dict[str, Any],
) -> dict[str, Any]:

    bullets = get_all_bullets(
        resume
    )

    if not bullets:

        return {
            "score": 0,
            "total_bullets": 0,
            "strong_bullets": 0,
            "weak_bullets": 0,
        }

    strong = 0
    weak = 0

    for bullet in bullets:

        start = first_word(
            bullet
        )

        if start in ACTION_VERBS:

            strong += 1

        elif start in WEAK_STARTERS:

            weak += 1

    ratio = strong / len(
        bullets
    )

    if ratio >= 0.70:
        score = 100

    elif ratio >= 0.50:
        score = 90

    elif ratio >= 0.35:
        score = 80

    elif ratio >= 0.20:
        score = 70

    else:
        score = 55

    return {
        "score": score,
        "total_bullets": len(bullets),
        "strong_bullets": strong,
        "weak_bullets": weak,
    }


# ============================================================
# REPETITION
# ============================================================

def calculate_repetition(
    resume: dict[str, Any],
) -> dict[str, Any]:

    bullets = get_all_bullets(
        resume
    )

    words: list[str] = []

    for bullet in bullets:

        tokens = text_tokens(
            bullet
        )

        words.extend(
            tokens
        )

    if not words:

        return {
            "score": 100,
            "repeated_words": {},
            "total_meaningful_words": 0,
        }

    counts = Counter(
        words
    )

    # Ignore very common technical words.
    ignored = {
        "java",
        "python",
        "aws",
        "sql",
        "software",
        "api",
        "apis",
        "system",
        "systems",
        "development",
        "developer",
        "engineering",
        "engineer",
    }

    repeated = {
        word: count
        for word, count in counts.items()
        if count >= 3
        and word not in ignored
    }

    # Repetition penalty.
    penalty = 0

    for count in repeated.values():

        if count == 3:
            penalty += 3

        elif count == 4:
            penalty += 5

        elif count >= 5:
            penalty += 8

    score = max(
        0,
        100 - penalty,
    )

    return {
        "score": score,
        "repeated_words": dict(
            sorted(
                repeated.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ),
        "total_meaningful_words": len(words),
    }


# ============================================================
# BULLET QUALITY
# ============================================================

def calculate_bullet_quality(
    resume: dict[str, Any],
) -> dict[str, Any]:

    bullets = get_all_bullets(
        resume
    )

    if not bullets:

        return {
            "score": 0,
            "total_bullets": 0,
            "strong_bullets": 0,
            "weak_bullets": 0,
        }

    strong = 0
    weak = 0

    for bullet in bullets:

        words = text_tokens(
            bullet
        )

        start = first_word(
            bullet
        )

        # A useful bullet usually has:
        # action + technical/content detail.
        has_action = (
            start in ACTION_VERBS
        )

        has_substance = (
            len(words) >= 7
        )

        has_metric = bool(
            re.search(
                r"\d+%|\$\s?\d+|\b\d[\d,.]*\b",
                bullet,
            )
        )

        if (
            has_action
            and has_substance
        ):

            strong += 1

        elif (
            has_action
            or has_metric
        ):

            strong += 1

        else:

            weak += 1

    ratio = strong / len(
        bullets
    )

    if ratio >= 0.80:
        score = 100

    elif ratio >= 0.65:
        score = 90

    elif ratio >= 0.50:
        score = 80

    elif ratio >= 0.35:
        score = 70

    else:
        score = 55

    return {
        "score": score,
        "total_bullets": len(bullets),
        "strong_bullets": strong,
        "weak_bullets": weak,
    }


# ============================================================
# WORD COUNT
# ============================================================

def calculate_word_score(
    resume_text: str,
) -> tuple[int, int]:

    word_count = len(
        re.findall(
            r"\b[\w+#.-]+\b",
            resume_text,
        )
    )

    if 350 <= word_count <= 850:

        score = 100

    elif 250 <= word_count <= 1000:

        score = 90

    else:

        score = 75

    return (
        word_count,
        score,
    )


# ============================================================
# ATS PARSEABILITY
# ============================================================

def calculate_parseability(
    resume: dict[str, Any],
    resume_text: str,
) -> dict[str, Any]:

    checks = {
        "name": bool(
            resume.get("name")
        ),

        "email": bool(
            resume.get("email")
        ),

        "experience": bool(
            resume.get("experience")
        ),

        "education": bool(
            resume.get("education")
        ),

        "skills": bool(
            resume.get("skills")
        ),

        "summary": bool(
            resume.get("summary")
        ),

        "text_content": len(
            resume_text
        ) >= 300,
    }

    score = round(
        sum(
            checks.values()
        )
        / len(checks)
        * 100
    )

    return {
        "score": score,
        "checks": checks,
    }


# ============================================================
# FILE FORMAT
# ============================================================

def calculate_formatting_score(
    filename: str,
    file_type: str,
) -> tuple[int, bool]:

    filename_ok = bool(
        filename
        and re.match(
            r"^[A-Za-z0-9][A-Za-z0-9_. -]{2,100}\.(pdf|docx)$",
            filename,
            flags=re.IGNORECASE,
        )
    )

    score = 100

    # Both are accepted by JobPilot.
    # PDF gets a small preference for ATS portability.
    if file_type.upper() == "PDF":

        score = 100

    elif file_type.upper() == "DOCX":

        score = 95

    else:

        score = 70

    if not filename_ok:

        score -= 5

    return (
        max(
            0,
            score,
        ),
        filename_ok,
    )


# ============================================================
# SENIORITY / CAREER FIT
# ============================================================

def detect_seniority_terms(
    text: str,
) -> set[str]:

    text = normalize(
        text
    )

    found = set()

    for term, level in SENIORITY_TERMS.items():

        if term in text:

            found.add(
                level
            )

    return found


def calculate_seniority_fit(
    job_intelligence: dict[str, Any],
    resume: dict[str, Any],
) -> dict[str, Any]:

    job_text = normalize(
        " ".join(
            [
                str(
                    job_intelligence.get(
                        "job_title",
                        "",
                    )
                    or ""
                ),
                " ".join(
                    str(x)
                    for x in (
                        job_intelligence.get(
                            "qualifications",
                            [],
                        )
                        or []
                    )
                ),
                " ".join(
                    str(x)
                    for x in (
                        job_intelligence.get(
                            "responsibilities",
                            [],
                        )
                        or []
                    )
                ),
            ]
        )
    )

    resume_text = flatten_resume(
        resume
    )

    job_levels = detect_seniority_terms(
        job_text
    )

    resume_levels = detect_seniority_terms(
        resume_text
    )

    # No explicit seniority signal.
    if not job_levels:

        return {
            "score": 100,
            "job_levels": [],
            "resume_levels": list(
                resume_levels
            ),
            "status": "No explicit seniority requirement detected",
        }

    # Matching seniority signal.
    if job_levels & resume_levels:

        return {
            "score": 100,
            "job_levels": list(
                job_levels
            ),
            "resume_levels": list(
                resume_levels
            ),
            "status": "Matching seniority evidence found",
        }

    # Graduate / junior roles can reasonably use project evidence.
    if (
        "graduate" in job_levels
        or "junior" in job_levels
    ):

        if resume.get("projects"):

            return {
                "score": 85,
                "job_levels": list(
                    job_levels
                ),
                "resume_levels": list(
                    resume_levels
                ),
                "status": "Graduate/junior role with project evidence",
            }

    return {
        "score": 60,
        "job_levels": list(
            job_levels
        ),
        "resume_levels": list(
            resume_levels
        ),
        "status": "Seniority signal differs from explicit resume title",
    }


# ============================================================
# MAIN ATS AUDIT
# ============================================================

def build_ats_audit(
    resume: dict[str, Any],
    job_intelligence: dict[str, Any],
    filename: str = "",
    file_type: str = "",
) -> dict[str, Any]:

    # --------------------------------------------------------
    # Resume
    # --------------------------------------------------------

    resume_sections = get_resume_sections(
        resume
    )

    resume_text = flatten_resume(
        resume
    )

    # --------------------------------------------------------
    # Job match
    # --------------------------------------------------------

    hard_skills = score_skill_group(
        job_intelligence.get(
            "hard_skills",
            [],
        ),
        resume_text,
    )

    soft_skills = score_skill_group(
        job_intelligence.get(
            "soft_skills",
            [],
        ),
        resume_text,
    )

    keywords = score_skill_group(
        job_intelligence.get(
            "keywords",
            [],
        ),
        resume_text,
    )

    requirements: list[str] = []

    requirements.extend(
        job_intelligence.get(
            "responsibilities",
            [],
        )
        or []
    )

    requirements.extend(
        job_intelligence.get(
            "qualifications",
            [],
        )
        or []
    )

    experience = score_experience_requirements(
        requirements,
        resume_sections,
    )

    # --------------------------------------------------------
    # Job title
    # --------------------------------------------------------

    job_title = str(
        job_intelligence.get(
            "job_title",
            "",
        )
        or ""
    ).strip()

    title = title_score(
        job_title,
        resume_text,
    )

    # --------------------------------------------------------
    # Sections
    # --------------------------------------------------------

    sections, section_score = calculate_sections(
        resume
    )

    # --------------------------------------------------------
    # Contact
    # --------------------------------------------------------

    contact, contact_score = calculate_contact(
        resume
    )

    # --------------------------------------------------------
    # Resume quality
    # --------------------------------------------------------

    quantification = calculate_quantification_score(
        resume
    )

    action_verbs = calculate_action_verb_score(
        resume
    )

    repetition = calculate_repetition(
        resume
    )

    bullet_quality = calculate_bullet_quality(
        resume
    )

    # --------------------------------------------------------
    # ATS readability
    # --------------------------------------------------------

    parseability = calculate_parseability(
        resume,
        resume_text,
    )

    formatting_score, filename_ok = (
        calculate_formatting_score(
            filename,
            file_type,
        )
    )

    # --------------------------------------------------------
    # Word count
    # --------------------------------------------------------

    word_count, word_score = calculate_word_score(
        resume_text
    )

    # --------------------------------------------------------
    # Seniority
    # --------------------------------------------------------

    seniority = calculate_seniority_fit(
        job_intelligence,
        resume,
    )

    # ========================================================
    # JOB MATCH SCORE
    # ========================================================
    #
    # Technical skills:       35%
    # Keywords:               25%
    # Experience evidence:   15%
    # Job title:              10%
    # Soft skills:             3%
    # Resume sections:         5%
    # Contact:                 4%
    # Formatting:              3%
    #
    # 100% total
    # ========================================================

    job_match_score = round(
        hard_skills["rate"] * 0.35
        + keywords["rate"] * 0.25
        + experience["rate"] * 0.15
        + title * 0.10
        + soft_skills["rate"] * 0.03
        + section_score * 0.05
        + contact_score * 0.04
        + formatting_score * 0.03
    )

    job_match_score = max(
        0,
        min(
            100,
            job_match_score,
        ),
    )

    # ========================================================
    # ATS READABILITY SCORE
    # ========================================================

    ats_readability_score = round(
        parseability["score"] * 0.45
        + section_score * 0.25
        + contact_score * 0.15
        + formatting_score * 0.15
    )

    ats_readability_score = max(
        0,
        min(
            100,
            ats_readability_score,
        ),
    )

    # ========================================================
    # RESUME QUALITY SCORE
    # ========================================================

    resume_quality_score = round(
        quantification["score"] * 0.30
        + action_verbs["score"] * 0.20
        + repetition["score"] * 0.20
        + bullet_quality["score"] * 0.30
    )

    resume_quality_score = max(
        0,
        min(
            100,
            resume_quality_score,
        ),
    )

    # ========================================================
    # FINAL ATS COMPATIBILITY
    # ========================================================
    #
    # Job Match       70%
    # ATS Readability 20%
    # Resume Quality  10%
    #
    # This keeps job relevance as the main factor.
    # ========================================================

    overall = round(
        job_match_score * 0.70
        + ats_readability_score * 0.20
        + resume_quality_score * 0.10
    )

    overall = max(
        0,
        min(
            100,
            overall,
        ),
    )

    # ========================================================
    # EVIDENCE SUMMARY
    # ========================================================

    evidence_summary = {
        "direct": experience[
            "matched_items"
        ],

        "project": experience[
            "project_items"
        ],

        "education": experience[
            "education_items"
        ],

        "supporting": experience[
            "supporting_items"
        ],

        "partial": experience[
            "partial_items"
        ],

        "missing": experience[
            "missing_items"
        ],
    }

    # ========================================================
    # SUGGESTIONS
    # ========================================================

    suggestions: list[str] = []

    if hard_skills["missing_items"]:

        suggestions.append(
            "Add only genuinely demonstrated technical skills that match the target role."
        )

    if keywords["missing_items"]:

        suggestions.append(
            "Use relevant job-description terminology when it truthfully describes existing experience."
        )

    if experience["missing_items"]:

        suggestions.append(
            "Strengthen experience or project bullets with existing evidence that maps to the role."
        )

    if experience["project_items"]:

        suggestions.append(
            "Relevant project experience is contributing evidence for this application."
        )

    if quantification["measurable_bullets"] < 5:

        suggestions.append(
            "Add more real, verifiable outcomes or metrics where supported by your experience."
        )

    if action_verbs["weak_bullets"]:

        suggestions.append(
            "Replace weak bullet starters with specific action verbs where appropriate."
        )

    if repetition["repeated_words"]:

        repeated_words = list(
            repetition[
                "repeated_words"
            ].keys()
        )[:3]

        suggestions.append(
            "Review repeated wording: "
            + ", ".join(
                repeated_words
            )
            + "."
        )

    if title < 70 and job_title:

        suggestions.append(
            "The resume does not closely match the core target job title."
        )

    if parseability["score"] < 90:

        suggestions.append(
            "Improve ATS readability by ensuring the resume has clear text-based sections and complete contact information."
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        # ====================================================
        # MAIN SCORE
        # ====================================================

        "overall_score": overall,

        "ats_score": overall,

        "match_rate": overall,

        "label": "ATS Compatibility Estimate",

        "disclaimer": (
            "This is a compatibility estimate based on "
            "the supplied job description and resume. "
            "Employer ATS configurations vary."
        ),

        # ====================================================
        # HIGH-LEVEL CATEGORIES
        # ====================================================

        "job_match_score":
            job_match_score,

        "ats_readability_score":
            ats_readability_score,

        "resume_quality_score":
            resume_quality_score,

        "seniority_score":
            seniority["score"],

        # ====================================================
        # UI BREAKDOWN
        # ====================================================

        "breakdown": {
            "hard_skills":
                hard_skills["rate"],

            "keywords":
                keywords["rate"],

            "experience":
                experience["rate"],

            "soft_skills":
                soft_skills["rate"],

            "job_title":
                title,

            "sections":
                section_score,

            "contact":
                contact_score,

            "formatting":
                formatting_score,
        },

        # ====================================================
        # HARD SKILLS
        # ====================================================

        "hard_skills_total":
            hard_skills["total"],

        "hard_skills_matched":
            hard_skills["matched"],

        "hard_skills_match": (
            f"{hard_skills['matched']}/"
            f"{hard_skills['total']}"
        ),

        "matched_hard_skills":
            hard_skills["matched_items"],

        "partial_hard_skills":
            hard_skills["partial_items"],

        "missing_hard_skills":
            hard_skills["missing_items"],

        # ====================================================
        # SOFT SKILLS
        # ====================================================

        "soft_skills_total":
            soft_skills["total"],

        "soft_skills_matched":
            soft_skills["matched"],

        "soft_skills_match": (
            f"{soft_skills['matched']}/"
            f"{soft_skills['total']}"
        ),

        "matched_soft_skills":
            soft_skills["matched_items"],

        "partial_soft_skills":
            soft_skills["partial_items"],

        "missing_soft_skills":
            soft_skills["missing_items"],

        # ====================================================
        # KEYWORDS
        # ====================================================

        "keyword_total":
            keywords["total"],

        "keyword_matched":
            keywords["matched"],

        "keyword_match": (
            f"{keywords['matched']}/"
            f"{keywords['total']}"
        ),

        "matched_keywords":
            keywords["matched_items"],

        "partial_keywords":
            keywords["partial_items"],

        "missing_keywords":
            keywords["missing_items"],

        # ====================================================
        # EXPERIENCE
        # ====================================================

        "experience_total":
            experience["total"],

        "experience_matched":
            experience["matched"],

        "experience_match": (
            f"{experience['matched']}/"
            f"{experience['total']}"
        ),

        "matched_experience":
            experience["matched_items"],

        "project_experience":
            experience["project_items"],

        "education_experience":
            experience["education_items"],

        "supporting_experience":
            experience["supporting_items"],

        "partial_experience":
            experience["partial_items"],

        "missing_experience":
            experience["missing_items"],

        "experience_evidence":
            experience["evidence_details"],

        "evidence_summary":
            evidence_summary,

        # ====================================================
        # JOB TITLE
        # ====================================================

        "job_title":
            job_title,

        "job_title_check":
            title >= 70,

        "job_title_score":
            title,

        # ====================================================
        # ATS READABILITY
        # ====================================================

        "parseability_score":
            parseability["score"],

        "parseability_checks":
            parseability["checks"],

        # ====================================================
        # RESUME QUALITY
        # ====================================================

        "quantification_score":
            quantification["score"],

        "measurable_results_count":
            quantification[
                "measurable_bullets"
            ],

        "measurable_results_target":
            5,

        "total_bullets":
            quantification[
                "total_bullets"
            ],

        "action_verb_score":
            action_verbs["score"],

        "strong_action_bullets":
            action_verbs[
                "strong_bullets"
            ],

        "weak_action_bullets":
            action_verbs[
                "weak_bullets"
            ],

        "repetition_score":
            repetition["score"],

        "repeated_words":
            repetition[
                "repeated_words"
            ],

        "bullet_quality_score":
            bullet_quality["score"],

        "strong_bullets":
            bullet_quality[
                "strong_bullets"
            ],

        "weak_bullets":
            bullet_quality[
                "weak_bullets"
            ],

        # ====================================================
        # SENIORITY
        # ====================================================

        "seniority": seniority,

        # ====================================================
        # SECTIONS
        # ====================================================

        "section_presence":
            sections,

        "section_score":
            section_score,

        # ====================================================
        # CONTACT
        # ====================================================

        "contact_information":
            contact,

        "contact_score":
            contact_score,

        # ====================================================
        # WORD COUNT
        # ====================================================

        "word_count":
            word_count,

        "word_count_score":
            word_score,

        # ====================================================
        # FILE
        # ====================================================

        "filename":
            filename or "Available",

        "filename_check":
            filename_ok,

        "file_type":
            file_type or "DOCX",

        "formatting_score":
            formatting_score,

        # ====================================================
        # SUGGESTIONS
        # ====================================================

        "improvement_suggestions":
            suggestions[:10],
    }