import json
import logging

import anthropic
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from user_model import db, Job, Candidate
from services.ai import (
    call_claude, parse_ai_json, build_jd_analysis_prompt,
    extract_job_title, extract_department, extract_location,
    analyze_job_description_fallback,
)
from services.storage import upload_file, delete_file
from utils.formatting import (
    extract_pdf_text, format_salary, format_jd_text, render_status_badge,
    serialize_candidate, job_stats_for_user, build_jobs_list,
)

logger = logging.getLogger(__name__)

jobs_api_bp = Blueprint("jobs_api_bp", __name__, url_prefix="/dashboard")


@jobs_api_bp.route("/upload-jd", methods=["POST"])
@login_required
def upload_jd():
    jd_text = ""
    jd_filename = None

    if "jd_file" in request.files and request.files["jd_file"].filename:
        file = request.files["jd_file"]
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"success": False, "error": "Only PDF files are supported"}), 400

        jd_filename = secure_filename(file.filename)
        file_bytes = file.read()

        try:
            jd_text = extract_pdf_text(file_bytes)
        except Exception as e:
            logger.error("JD PDF extraction failed: %s", e)
            return jsonify({"success": False, "error": "Could not read PDF. It may be image-based or corrupted."}), 400

        if not jd_text:
            return jsonify({"success": False, "error": "No text found in PDF. It may be image-based."}), 400

        storage_path = f"jd/{current_user.id}/{jd_filename}"
        try:
            upload_file("documents", storage_path, file_bytes)
        except Exception as e:
            logger.error("JD upload to storage failed: %s", e)
            # Don't block job creation — the extracted text is sufficient for analysis

    elif request.form.get("jd_text", "").strip():
        jd_text = request.form["jd_text"].strip()

    else:
        return jsonify({"success": False, "error": "Please provide a job description"}), 400

    title = extract_job_title(jd_text)
    department = extract_department(jd_text)
    location = extract_location(jd_text)
    job = Job(
        user_id=current_user.id, jd_text=jd_text, jd_filename=jd_filename,
        title=title, department=department, location=location, status="draft"
    )
    db.session.add(job)
    db.session.commit()

    return jsonify({"success": True, "job_id": job.id, "title": title})


@jobs_api_bp.route("/analyze-jd/<int:job_id>", methods=["POST"])
@login_required
def analyze_jd(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    api_key = current_app.config.get("ANTHROPIC_API_KEY")

    try:
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
            system_msg, user_msgs = build_jd_analysis_prompt(job.jd_text)
            raw = call_claude(client, user_msgs, system=system_msg)
            result = parse_ai_json(raw)
            mode = "anthropic"
        else:
            result = analyze_job_description_fallback(job.jd_text)
            mode = "local"

        job.title = str(result.get("title", ""))[:200] or job.title
        job.department = str(result.get("department", ""))[:100] or job.department
        job.location = str(result.get("location", ""))[:100] or job.location
        job.seniority_level = str(result.get("seniority_level", ""))[:100] or None
        job.employment_type = str(result.get("employment_type", ""))[:100] or None
        job.salary_range_text = str(result.get("salary_range", ""))[:100] or None

        skills = result.get("key_skills", [])
        if isinstance(skills, list):
            job.required_skills = json.dumps(skills)

        job.ai_analyzed = True
        db.session.commit()

        return jsonify({
            "success": True,
            "analysis": {
                "title": job.title or "",
                "department": job.department or "",
                "location": job.location or "",
                "seniority_level": job.seniority_level or "",
                "employment_type": job.employment_type or "",
                "salary_range": job.salary_range_text or "",
                "key_skills": skills if isinstance(skills, list) else []
            },
            "analysis_mode": mode,
        })
    except Exception as e:
        logger.error("JD analysis failed, using local fallback: %s", e)
        try:
            result = analyze_job_description_fallback(job.jd_text)
            job.title = result.get("title") or job.title
            job.department = result.get("department") or job.department
            job.location = result.get("location") or job.location
            job.seniority_level = result.get("seniority_level") or None
            job.employment_type = result.get("employment_type") or None
            job.salary_range_text = result.get("salary_range") or None
            job.required_skills = json.dumps(result.get("key_skills", []))
            db.session.commit()
            return jsonify({"success": True, "analysis": result, "analysis_mode": "local"})
        except Exception:
            return jsonify({"success": False, "error": "Could not analyze this job description"}), 500


@jobs_api_bp.route("/create-job", methods=["POST"])
@login_required
def create_job():
    title = request.form.get("title", "").strip()
    if not title:
        return jsonify({"success": False, "error": "Job title is required"}), 400

    department = request.form.get("department", "").strip() or None
    location = request.form.get("location", "").strip() or None
    description = request.form.get("description", "").strip() or ""
    skills = request.form.get("skills", "").strip() or None

    salary_min = None
    salary_max = None
    try:
        if request.form.get("salary_min"):
            salary_min = int(request.form["salary_min"])
        if request.form.get("salary_max"):
            salary_max = int(request.form["salary_max"])
    except ValueError:
        pass

    job = Job(
        user_id=current_user.id, title=title, jd_text=description,
        department=department, location=location,
        salary_min=salary_min, salary_max=salary_max,
        required_skills=skills, status="open"
    )
    db.session.add(job)
    db.session.commit()

    stats = job_stats_for_user(current_user.id)
    return jsonify({
        "success": True,
        "job": {
            "id": job.id, "title": job.title, "department": job.department or "",
            "location": job.location or "", "status": job.status,
            "status_html": render_status_badge(job.status),
            "candidate_count": 0, "created_at": job.created_at.strftime("%Y-%m-%d"),
        },
        "stats": stats,
    })


@jobs_api_bp.route("/job-detail/<int:job_id>")
@login_required
def job_detail(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    candidates = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .order_by(Candidate.match_score.desc())
    ).scalars().all()

    return jsonify({
        "success": True,
        "job": {
            "id": job.id,
            "title": job.title or "Untitled",
            "department": job.department or "",
            "location": job.location or "",
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_display": format_salary(job.salary_min, job.salary_max),
            "required_skills": job.required_skills or "",
            "jd_text": job.jd_text or "",
            "jd_text_html": format_jd_text(job.jd_text),
            "status": job.status,
            "status_html": render_status_badge(job.status),
            "created_at": job.created_at.strftime("%Y-%m-%d"),
        },
        "candidates": [serialize_candidate(c) for c in candidates]
    })


@jobs_api_bp.route("/jobs-filtered")
@login_required
def jobs_filtered():
    q = request.args.get("q", "").strip() or None
    dept = request.args.get("dept") or None
    status = request.args.get("status") or None
    days = request.args.get("days") or None
    jobs_data = build_jobs_list(current_user.id, q=q, dept=dept, status=status, days=days)
    stats = job_stats_for_user(current_user.id)
    department_rows = db.session.execute(
        db.select(Job.department)
        .where(Job.user_id == current_user.id)
        .where(Job.department.isnot(None))
        .distinct()
    ).scalars().all()
    departments = sorted(d for d in department_rows if d)
    return jsonify({"success": True, "jobs": jobs_data, "stats": stats, "departments": departments})


@jobs_api_bp.route("/update-job-status/<int:job_id>", methods=["PATCH"])
@login_required
def update_job_status(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    data = request.get_json()
    new_status = data.get("status", "").strip()
    allowed = {"open", "draft", "closed", "completed"}
    if new_status not in allowed:
        return jsonify({"success": False, "error": "Invalid status"}), 400

    job.status = new_status
    db.session.commit()

    stats = job_stats_for_user(current_user.id)
    return jsonify({
        "success": True, "status": job.status,
        "status_html": render_status_badge(job.status), "stats": stats,
    })


@jobs_api_bp.route("/delete-job/<int:job_id>", methods=["DELETE"])
@login_required
def delete_job(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    # Delete JD file from storage if it exists
    if job.jd_filename:
        delete_file("documents", f"jd/{current_user.id}/{job.jd_filename}")

    # Delete all candidate resume files from storage
    for candidate in job.candidates:
        delete_file("documents", f"resumes/{job_id}/{candidate.resume_filename}")

    db.session.delete(job)
    db.session.commit()
    stats = job_stats_for_user(current_user.id)
    return jsonify({"success": True, "stats": stats})
