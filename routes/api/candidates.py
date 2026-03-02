import io
import logging

import anthropic
from flask import Blueprint, request, jsonify, current_app, send_file, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from user_model import db, Job, Candidate
from services.ai import score_candidate
from services.email import send_invite_email, send_decision_email, send_custom_email
from services.pdf import generate_candidate_report, generate_onboarding_doc
from services.storage import upload_file, download_file, delete_file
from utils.formatting import (
    extract_pdf_text, serialize_candidate,
    compute_analytics_data, build_analytics_csv,
)

logger = logging.getLogger(__name__)

candidates_api_bp = Blueprint("candidates_api_bp", __name__, url_prefix="/dashboard")


@candidates_api_bp.route("/upload-resumes/<int:job_id>", methods=["POST"])
@login_required
def upload_resumes(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    files = request.files.getlist("resumes")
    if not files:
        return jsonify({"success": False, "error": "No files provided"}), 400

    results = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            continue

        filename = secure_filename(file.filename)
        file_bytes = file.read()

        try:
            resume_text = extract_pdf_text(file_bytes)
        except Exception as e:
            logger.error("Resume PDF extraction failed for %s: %s", filename, e)
            continue

        if not resume_text:
            continue

        storage_path = f"resumes/{job_id}/{filename}"
        try:
            upload_file("documents", storage_path, file_bytes)
        except Exception as e:
            logger.error("Resume upload to storage failed for %s: %s", filename, e)
            # Don't skip candidate — the extracted text is sufficient for AI screening

        candidate = Candidate(job_id=job.id, resume_text=resume_text, resume_filename=filename)
        db.session.add(candidate)
        db.session.flush()
        results.append({"id": candidate.id, "filename": filename})

    if not results:
        db.session.commit()
        return jsonify({"success": False, "error": "No valid resumes could be processed"}), 400

    job.status = "ready"
    db.session.commit()

    return jsonify({"success": True, "candidates": results})


@candidates_api_bp.route("/remove-resume/<int:candidate_id>", methods=["DELETE"])
@login_required
def remove_resume(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    delete_file("documents", f"resumes/{candidate.job_id}/{candidate.resume_filename}")

    db.session.delete(candidate)
    db.session.commit()

    return jsonify({"success": True})


@candidates_api_bp.route("/start-screening/<int:job_id>", methods=["POST"])
@login_required
def start_screening(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    if job.status not in ("ready", "completed"):
        return jsonify({"success": False, "error": "Job is not ready for screening"}), 400

    job.status = "processing"
    db.session.commit()

    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        job.status = "ready"
        db.session.commit()
        return jsonify({"success": False, "error": "AI service not configured"}), 500

    client = anthropic.Anthropic(api_key=api_key)

    candidates = db.session.execute(
        db.select(Candidate).where(Candidate.job_id == job.id)
    ).scalars().all()

    if not candidates:
        job.status = "ready"
        db.session.commit()
        return jsonify({"success": False, "error": "No resumes to screen. Please upload resumes first."}), 400

    rate_limited = False
    for candidate in candidates:
        try:
            score_candidate(candidate, client, job.jd_text)
        except anthropic.RateLimitError:
            logger.warning("Rate limited after retries for %s", candidate.resume_filename)
            rate_limited = True
            candidate.status = "error"
            candidate.match_score = 0
            candidate.match_summary = "AI service is temporarily busy. Please retry in a few minutes."
            candidate.candidate_name = candidate.candidate_name or ""
        except Exception as e:
            logger.error("AI screening failed for %s: %s", candidate.resume_filename, e)
            candidate.status = "error"
            candidate.match_score = 0
            candidate.match_summary = f"Could not analyze this resume: {str(e)[:100]}"
            candidate.candidate_name = candidate.candidate_name or ""

    job.status = "completed"
    db.session.commit()

    threshold = current_user.match_threshold if current_user.match_threshold is not None else 70
    sorted_candidates = sorted(candidates, key=lambda c: c.match_score or 0, reverse=True)
    results = [serialize_candidate(c) for c in sorted_candidates if (c.match_score or 0) >= threshold]

    return jsonify({"success": True, "results": results, "rate_limited": rate_limited})


@candidates_api_bp.route("/screen-new-candidates/<int:job_id>", methods=["POST"])
@login_required
def screen_new_candidates(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    unscored = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .where(Candidate.status.in_(["pending", None]))
    ).scalars().all()

    if not unscored:
        return jsonify({"success": False, "error": "No new candidates to screen"}), 400

    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"success": False, "error": "AI service not configured"}), 500

    client = anthropic.Anthropic(api_key=api_key)
    rate_limited = False

    for candidate in unscored:
        try:
            score_candidate(candidate, client, job.jd_text)
        except anthropic.RateLimitError:
            rate_limited = True
            candidate.status = "error"
            candidate.match_score = 0
            candidate.match_summary = "AI service is temporarily busy. Please retry in a few minutes."
            candidate.candidate_name = candidate.candidate_name or ""
        except Exception as e:
            candidate.status = "error"
            candidate.match_score = 0
            candidate.match_summary = f"Could not analyze this resume: {str(e)[:100]}"
            candidate.candidate_name = candidate.candidate_name or ""

    job.status = "completed"
    db.session.commit()

    all_candidates = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .order_by(Candidate.match_score.desc())
    ).scalars().all()

    threshold = current_user.match_threshold if current_user.match_threshold is not None else 70
    filtered = [c for c in all_candidates if (c.match_score or 0) >= threshold]

    return jsonify({
        "success": True,
        "results": [serialize_candidate(c) for c in filtered],
        "rate_limited": rate_limited,
        "new_count": len(unscored)
    })


@candidates_api_bp.route("/results/<int:job_id>")
@login_required
def results(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    candidates = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .order_by(Candidate.match_score.desc())
    ).scalars().all()

    results = [serialize_candidate(c) for c in candidates]

    return jsonify({"success": True, "results": results, "job_title": job.title or ""})


@candidates_api_bp.route("/delete-candidate/<int:candidate_id>", methods=["DELETE"])
@login_required
def delete_candidate(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    delete_file("documents", f"resumes/{candidate.job_id}/{candidate.resume_filename}")

    db.session.delete(candidate)
    db.session.commit()
    return jsonify({"success": True})


@candidates_api_bp.route("/candidate-pdf/<int:candidate_id>")
@login_required
def candidate_pdf(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    return generate_candidate_report(candidate)


@candidates_api_bp.route("/resume-pdf/<int:candidate_id>")
@login_required
def resume_pdf(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    storage_path = f"resumes/{candidate.job_id}/{candidate.resume_filename}"
    try:
        file_bytes = download_file("documents", storage_path)
    except Exception as e:
        logger.error("Resume download from storage failed: %s", e)
        return jsonify({"success": False, "error": "Resume file not found"}), 404

    return send_file(
        io.BytesIO(file_bytes), mimetype="application/pdf",
        download_name=candidate.resume_filename
    )


@candidates_api_bp.route("/send-invites", methods=["POST"])
@login_required
def send_invites():
    data = request.get_json()
    candidate_ids = data.get("candidate_ids", [])
    scheduling_link = data.get("scheduling_link", "").strip() or None
    custom_message = data.get("message", "").strip()

    if not candidate_ids or not scheduling_link:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    candidates = db.session.execute(
        db.select(Candidate).where(Candidate.id.in_(candidate_ids))
    ).scalars().all()

    owned = [c for c in candidates if c.job.user_id == current_user.id]
    if not owned:
        return jsonify({"success": False, "error": "No valid candidates found"}), 404

    job = owned[0].job

    email_results = []
    for c in owned:
        c.status = "invited"

        email_sent = False
        if c.candidate_email:
            email_sent = send_invite_email(
                c.candidate_email, c.candidate_name, job.title,
                None, None, custom_message,
                company_name=current_user.company_name,
                scheduling_link=scheduling_link,
                reply_to=current_user.work_email
            )
        email_results.append({
            "id": c.id,
            "email_sent": email_sent,
            "name": c.candidate_name or c.resume_filename
        })

    db.session.commit()

    return jsonify({
        "success": True,
        "results": email_results
    })


@candidates_api_bp.route("/final-decision", methods=["POST"])
@login_required
def final_decision():
    data = request.get_json()
    candidate_id = data.get("candidate_id")
    decision = data.get("decision")
    notes = data.get("notes", "").strip()

    if not candidate_id or decision not in ("hire", "reject"):
        return jsonify({"success": False, "error": "Invalid request"}), 400

    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    if candidate.status not in ("invited", "interview_done"):
        return jsonify({"success": False, "error": "Candidate not eligible for decision"}), 400

    candidate.status = "final_hired" if decision == "hire" else "final_rejected"
    if notes:
        candidate.final_notes = notes

    db.session.commit()

    email_sent = False
    if candidate.candidate_email:
        company_name = current_user.company_name if current_user.company_name else None
        job_title = candidate.job.title if candidate.job else None
        email_sent = send_decision_email(
            candidate.candidate_email,
            candidate.candidate_name,
            job_title,
            decision,
            company_name=company_name,
            reply_to=current_user.work_email
        )

    return jsonify({"success": True, "email_sent": email_sent})


@candidates_api_bp.route("/send-custom-email", methods=["POST"])
@login_required
def send_custom_email_route():
    data = request.get_json()
    candidate_id = data.get("candidate_id")
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()

    if not candidate_id or not subject or not body:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    if not candidate.candidate_email:
        return jsonify({"success": False, "error": "No email on file"}), 400

    company_name = current_user.company_name if current_user.company_name else None
    email_sent = send_custom_email(
        candidate.candidate_email, candidate.candidate_name,
        subject, body, company_name=company_name,
        reply_to=current_user.work_email
    )

    return jsonify({"success": True, "email_sent": email_sent})


@candidates_api_bp.route("/generate-onboarding/<int:candidate_id>")
@login_required
def generate_onboarding(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    if candidate.status != "final_hired":
        return jsonify({"success": False, "error": "Candidate must be hired first"}), 400

    candidate.onboarding_generated = True
    db.session.commit()

    return generate_onboarding_doc(candidate, current_user)


@candidates_api_bp.route("/analytics-data")
@login_required
def analytics_data():
    range_param = request.args.get("range", "30d")
    return jsonify(compute_analytics_data(current_user.id, range_param))


@candidates_api_bp.route("/analytics-export-csv")
@login_required
def analytics_export_csv():
    range_param = request.args.get("range", "30d")
    csv_content = build_analytics_csv(current_user.id, range_param)
    filename = "quickhire-analytics-" + range_param + ".csv"
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=" + filename}
    )
