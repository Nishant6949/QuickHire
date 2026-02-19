import json
import logging
import re
import time

import anthropic

logger = logging.getLogger(__name__)


def parse_ai_json(raw_text):
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        text = brace_match.group(0)
    return json.loads(text)


def clamp_score(value):
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return 0


def call_claude(client, prompt, system=None, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            kwargs = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt,
            }
            if system:
                kwargs["system"] = system
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning("Claude rate limited, retrying in %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
            else:
                raise


def build_jd_analysis_prompt(jd_text):
    system = (
        "You are an expert HR analyst. Extract structured information from job descriptions. "
        "Return ONLY valid JSON with no markdown or explanation."
    )
    messages = [
        {
            "role": "user",
            "content": (
                "Analyze this job description and extract the following. Return ONLY a valid JSON object:\n"
                "{\n"
                '  "title": "<job title>",\n'
                '  "department": "<department like Engineering, Product, Design, Sales, Marketing, HR, Finance, Operations, Data>",\n'
                '  "location": "<location or Remote>",\n'
                '  "seniority_level": "<Junior, Mid-Level, Senior, Lead, Manager, Director, VP, C-Level>",\n'
                '  "employment_type": "<Full-time, Part-time, Contract, Internship>",\n'
                '  "salary_range": "<salary range if mentioned, or empty string>",\n'
                '  "key_skills": ["<skill1>", "<skill2>", "..."]  // 5-10 most important skills\n'
                "}\n\n"
                "=== JOB DESCRIPTION ===\n" + jd_text
            )
        }
    ]
    return system, messages


def build_screening_prompt(jd_text, resume_text):
    return (
        "You are an expert recruitment AI. Analyze the candidate's resume against the job description below.\n\n"
        "Return ONLY a valid JSON object (no markdown, no explanation) with exactly these fields:\n"
        "{\n"
        '  "candidate_name": "<full name from resume>",\n'
        '  "candidate_email": "<email from resume or empty string>",\n'
        '  "match_score": <integer 0-100, overall fit>,\n'
        '  "skills_score": <integer 0-100, how well skills match>,\n'
        '  "experience_score": <integer 0-100, how well experience matches>,\n'
        '  "education_score": <integer 0-100, how well education matches>,\n'
        '  "matched_skills": [<list of specific skills from resume that match the JD>],\n'
        '  "match_summary": "<2-3 sentence summary explaining the match>"\n'
        "}\n\n"
        "Scoring guide:\n"
        "- 90-100: Excellent match, meets nearly all requirements\n"
        "- 70-89: Good match, meets most key requirements\n"
        "- 50-69: Partial match, meets some requirements\n"
        "- 0-49: Poor match, significant gaps\n\n"
        "=== JOB DESCRIPTION ===\n" + jd_text + "\n\n"
        "=== RESUME ===\n" + resume_text
    )


def score_candidate(candidate, client, jd_text):
    prompt = build_screening_prompt(jd_text, candidate.resume_text)
    raw = call_claude(client, prompt)
    logger.debug("AI response for %s: %s", candidate.resume_filename, raw[:300])
    result = parse_ai_json(raw)

    candidate.match_score = clamp_score(result.get("match_score", 0))
    candidate.skills_score = clamp_score(result.get("skills_score", 0))
    candidate.experience_score = clamp_score(result.get("experience_score", 0))
    candidate.education_score = clamp_score(result.get("education_score", 0))
    candidate.match_summary = str(result.get("match_summary", ""))[:500]
    candidate.candidate_name = str(result.get("candidate_name", ""))[:200] or None
    candidate.candidate_email = str(result.get("candidate_email", ""))[:200] or None

    skills = result.get("matched_skills", [])
    if isinstance(skills, list):
        candidate.matched_skills = json.dumps(skills)

    candidate.status = "scored"


def extract_job_title(jd_text):
    lines = jd_text.strip().split("\n")
    for line in lines[:5]:
        cleaned = line.strip()
        if 10 < len(cleaned) < 80 and not cleaned.endswith(":"):
            return cleaned
    return "Untitled Position"


def extract_department(jd_text):
    text_lower = jd_text.lower()
    departments = {
        "Engineering": ["engineering", "software", "developer", "backend", "frontend", "fullstack", "devops", "sre", "infrastructure"],
        "Product": ["product manager", "product owner", "product lead", "product management"],
        "Design": ["design", "ux", "ui ", "ui/ux", "graphic design", "visual design"],
        "Sales": ["sales", "account executive", "business development", "bdr", "sdr"],
        "Marketing": ["marketing", "growth", "content", "seo", "brand"],
        "HR": ["human resources", "people operations", "talent", "recruiter", "recruiting"],
        "Finance": ["finance", "accounting", "financial", "controller", "cfo"],
        "Operations": ["operations", "logistics", "supply chain", "procurement"],
        "Data": ["data science", "data engineer", "machine learning", "ml ", "analytics", "data analyst"],
    }
    for dept, keywords in departments.items():
        for kw in keywords:
            if kw in text_lower:
                return dept
    return None


def extract_location(jd_text):
    text_lower = jd_text.lower()
    if "remote" in text_lower:
        return "Remote"
    loc_match = re.search(r"location\s*[:\-–]\s*(.+)", jd_text, re.IGNORECASE)
    if loc_match:
        return loc_match.group(1).strip()[:100]
    return None
