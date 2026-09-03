import json
import logging
import re
import time
from collections import Counter

import anthropic

logger = logging.getLogger(__name__)

COMMON_SKILLS = [
    'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'node.js', 'node',
    'flask', 'django', 'fastapi', 'sql', 'postgresql', 'mysql', 'mongodb', 'aws', 'azure', 'gcp',
    'docker', 'kubernetes', 'git', 'github', 'ci/cd', 'devops', 'linux', 'html', 'css', 'figma',
    'power bi', 'tableau', 'excel', 'machine learning', 'artificial intelligence', 'data analysis',
    'data analytics', 'communication', 'leadership', 'project management', 'agile', 'scrum',
    'cybersecurity', 'networking', 'rest api', 'api', 'terraform', 'jenkins', 'c++', 'c#', '.net',
]
STOPWORDS = {
    'with', 'that', 'this', 'from', 'your', 'have', 'will', 'into', 'about', 'their', 'they',
    'role', 'work', 'team', 'skills', 'experience', 'years', 'job', 'candidate', 'required',
    'responsibilities', 'requirements', 'using', 'ability', 'strong', 'looking', 'including',
    'company', 'position', 'must', 'preferred', 'knowledge', 'excellent', 'good', 'support',
}


def parse_ai_json(raw_text):
    text = raw_text.strip()
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    brace_match = re.search(r'\{.*\}', text, re.DOTALL)
    if brace_match:
        text = brace_match.group(0)
    return json.loads(text)


def clamp_score(value):
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return 0


def call_claude(client, prompt, system=None, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            kwargs = {
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 1024,
                'messages': [{'role': 'user', 'content': prompt}] if isinstance(prompt, str) else prompt,
            }
            if system:
                kwargs['system'] = system
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt < max_retries:
                wait = attempt + 1
                logger.warning('Claude rate limited, retrying in %ds', wait)
                time.sleep(wait)
            else:
                raise


def build_jd_analysis_prompt(jd_text):
    system = (
        'You are an expert HR analyst. Extract structured information from job descriptions. '
        'Return ONLY valid JSON with no markdown or explanation.'
    )
    messages = [{'role': 'user', 'content': (
        'Analyze this job description and return ONLY a valid JSON object with: '
        'title, department, location, seniority_level, employment_type, salary_range, '
        'and key_skills (5-10 most important skills).\n\n=== JOB DESCRIPTION ===\n' + jd_text
    )}]
    return system, messages


def build_screening_prompt(jd_text, resume_text):
    return (
        "You are an expert recruitment AI. Analyze the candidate's resume against the job description below.\n\n"
        'Return ONLY valid JSON with candidate_name, candidate_email, match_score, skills_score, '
        'experience_score, education_score, matched_skills, and match_summary. Scores must be integers 0-100.\n\n'
        '=== JOB DESCRIPTION ===\n' + jd_text + '\n\n=== RESUME ===\n' + resume_text
    )


def _tokens(text):
    return re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-/]{2,}", (text or '').lower())


def _skill_matches(jd_text, resume_text):
    jd_lower = (jd_text or '').lower()
    resume_lower = (resume_text or '').lower()
    skills = []
    for skill in COMMON_SKILLS:
        if skill in jd_lower and skill in resume_lower:
            skills.append(skill.upper() if skill in {'sql', 'aws', 'gcp', 'api'} else skill.title())

    if len(skills) < 5:
        jd_counts = Counter(t for t in _tokens(jd_text) if t not in STOPWORDS and len(t) > 3)
        resume_set = set(_tokens(resume_text))
        for token, _ in jd_counts.most_common(25):
            if token in resume_set and token.title() not in skills:
                skills.append(token.title())
            if len(skills) >= 10:
                break
    return skills[:10]


def analyze_job_description_fallback(jd_text):
    title = extract_job_title(jd_text)
    department = extract_department(jd_text) or ''
    location = extract_location(jd_text) or ''
    lower = (jd_text or '').lower()
    seniority = ''
    for label, words in [
        ('Director', ['director']), ('Manager', ['manager']), ('Lead', ['lead ', 'team lead']),
        ('Senior', ['senior', 'sr.']), ('Junior', ['junior', 'graduate', 'entry level']),
    ]:
        if any(w in lower for w in words):
            seniority = label
            break
    if not seniority:
        seniority = 'Mid-Level'

    employment = ''
    for label, words in [
        ('Full-time', ['full-time', 'full time']), ('Part-time', ['part-time', 'part time']),
        ('Contract', ['contract']), ('Internship', ['internship', 'intern']),
    ]:
        if any(w in lower for w in words):
            employment = label
            break

    salary_match = re.search(r'(?:\$|AUD\s*)[\d,]+(?:\s*[-–]\s*(?:\$|AUD\s*)?[\d,]+)?', jd_text or '', re.I)
    skills = []
    for skill in COMMON_SKILLS:
        if skill in lower:
            skills.append(skill.upper() if skill in {'sql', 'aws', 'gcp', 'api'} else skill.title())
    if len(skills) < 5:
        counts = Counter(t for t in _tokens(jd_text) if t not in STOPWORDS and len(t) > 3)
        for token, _ in counts.most_common(12):
            display = token.title()
            if display not in skills:
                skills.append(display)
            if len(skills) >= 8:
                break

    return {
        'title': title,
        'department': department,
        'location': location,
        'seniority_level': seniority,
        'employment_type': employment,
        'salary_range': salary_match.group(0) if salary_match else '',
        'key_skills': skills[:10],
    }


def _extract_name(resume_text):
    for raw in (resume_text or '').splitlines()[:12]:
        line = raw.strip()
        if not line or '@' in line or len(line) > 70:
            continue
        if re.fullmatch(r"[A-Za-z][A-Za-z .'-]{2,60}", line) and len(line.split()) <= 5:
            if line.lower() not in {'resume', 'curriculum vitae', 'cv', 'profile', 'summary'}:
                return line
    return ''


def _extract_email(resume_text):
    match = re.search(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', resume_text or '', re.I)
    return match.group(0) if match else ''


def score_candidate_fallback(candidate, jd_text):
    resume_text = candidate.resume_text or ''
    matched = _skill_matches(jd_text, resume_text)
    jd_terms = {t for t in _tokens(jd_text) if t not in STOPWORDS and len(t) > 3}
    resume_terms = set(_tokens(resume_text))
    overlap = len(jd_terms & resume_terms) / max(1, len(jd_terms))

    skills_score = clamp_score(35 + overlap * 65)
    if matched:
        skills_score = max(skills_score, min(100, 45 + len(matched) * 6))

    years = [int(x) for x in re.findall(r'(\d{1,2})\+?\s*(?:years?|yrs?)', resume_text, re.I)]
    max_years = max(years) if years else 0
    experience_score = min(100, 45 + max_years * 7) if max_years else max(35, skills_score - 10)

    education_words = ['bachelor', 'master', 'degree', 'diploma', 'university', 'college', 'phd', 'certificate']
    education_hits = sum(1 for word in education_words if word in resume_text.lower())
    education_score = min(100, 45 + education_hits * 10) if education_hits else 45

    overall = round(skills_score * 0.55 + experience_score * 0.30 + education_score * 0.15)
    candidate.match_score = clamp_score(overall)
    candidate.skills_score = clamp_score(skills_score)
    candidate.experience_score = clamp_score(experience_score)
    candidate.education_score = clamp_score(education_score)
    candidate.candidate_name = candidate.candidate_name or _extract_name(resume_text) or None
    candidate.candidate_email = candidate.candidate_email or _extract_email(resume_text) or None
    candidate.matched_skills = json.dumps(matched)
    candidate.match_summary = (
        f'Local screening found {len(matched)} direct skill matches. '
        f'The candidate received {candidate.match_score}% overall based on skills, experience and education evidence. '
        'Connect an Anthropic API key for a richer semantic assessment.'
    )
    candidate.status = 'scored'


def score_candidate(candidate, client, jd_text):
    if client is None:
        score_candidate_fallback(candidate, jd_text)
        return 'local'

    prompt = build_screening_prompt(jd_text, candidate.resume_text)
    raw = call_claude(client, prompt)
    result = parse_ai_json(raw)

    candidate.match_score = clamp_score(result.get('match_score', 0))
    candidate.skills_score = clamp_score(result.get('skills_score', 0))
    candidate.experience_score = clamp_score(result.get('experience_score', 0))
    candidate.education_score = clamp_score(result.get('education_score', 0))
    candidate.match_summary = str(result.get('match_summary', ''))[:800]
    candidate.candidate_name = str(result.get('candidate_name', ''))[:200] or None
    candidate.candidate_email = str(result.get('candidate_email', ''))[:200] or None
    skills = result.get('matched_skills', [])
    if isinstance(skills, list):
        candidate.matched_skills = json.dumps(skills[:20])
    candidate.status = 'scored'
    return 'anthropic'


def extract_job_title(jd_text):
    lines = (jd_text or '').strip().split('\n')
    for line in lines[:8]:
        cleaned = line.strip().strip('#*- ')
        if 4 < len(cleaned) < 100 and not cleaned.endswith(':'):
            return cleaned
    return 'Untitled Position'


def extract_department(jd_text):
    text_lower = (jd_text or '').lower()
    departments = {
        'Engineering': ['engineering', 'software', 'developer', 'backend', 'frontend', 'fullstack', 'devops', 'sre', 'infrastructure'],
        'Product': ['product manager', 'product owner', 'product lead', 'product management'],
        'Design': ['design', 'ux', 'ui ', 'ui/ux', 'graphic design', 'visual design'],
        'Sales': ['sales', 'account executive', 'business development', 'bdr', 'sdr'],
        'Marketing': ['marketing', 'growth', 'content', 'seo', 'brand'],
        'HR': ['human resources', 'people operations', 'talent', 'recruiter', 'recruiting'],
        'Finance': ['finance', 'accounting', 'financial', 'controller', 'cfo'],
        'Operations': ['operations', 'logistics', 'supply chain', 'procurement'],
        'Data': ['data science', 'data engineer', 'machine learning', 'analytics', 'data analyst'],
    }
    for dept, keywords in departments.items():
        if any(kw in text_lower for kw in keywords):
            return dept
    return None


def extract_location(jd_text):
    text_lower = (jd_text or '').lower()
    if 'remote' in text_lower:
        return 'Remote'
    loc_match = re.search(r'location\s*[:\-–]\s*(.+)', jd_text or '', re.IGNORECASE)
    if loc_match:
        return loc_match.group(1).strip()[:100]
    return None
