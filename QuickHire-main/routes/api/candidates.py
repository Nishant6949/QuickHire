import logging
import os

import anthropic
from markupsafe import escape
from flask import Blueprint, request, jsonify, current_app, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from user_model import db, Job, Candidate
from services.ai import score_candidate
from services.email import send_invite_email, send_decision_email, send_custom_email
from services.pdf import generate_candidate_report, generate_onboarding_doc
from services.storage import upload_file, delete_file
from services.notifications import notify_candidate, notify_recruiter
from utils.formatting import (
    extract_pdf_text, serialize_candidate,
    compute_analytics_data, build_analytics_csv,
)

logger = logging.getLogger(__name__)

candidates_api_bp = Blueprint("candidates_api_bp", __name__, url_prefix="/dashboard")


def _screening_batch_size():
    raw = os.getenv("SCREENING_BATCH_SIZE")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            logger.warning("Invalid SCREENING_BATCH_SIZE=%s. Falling back to default.", raw)
    # Vercel Hobby-safe default
    if os.getenv("VERCEL"):
        return 1
    return 5


def _resume_parse_limits():
    pages_raw = os.getenv("RESUME_PARSE_MAX_PAGES")
    chars_raw = os.getenv("RESUME_PARSE_MAX_CHARS")
    try:
        pages = int(pages_raw) if pages_raw else None
    except ValueError:
        pages = None
    try:
        chars = int(chars_raw) if chars_raw else None
    except ValueError:
        chars = None

    if pages is None:
        pages = 3 if os.getenv("VERCEL") else None
    if chars is None:
        chars = 20000 if os.getenv("VERCEL") else None

    return pages, chars


def _serialize_ranked_candidates(candidates):
    threshold = current_user.match_threshold if current_user.match_threshold is not None else 70
    ranked = sorted(candidates, key=lambda c: c.match_score or 0, reverse=True)
    return [serialize_candidate(c) for c in ranked if (c.match_score or 0) >= threshold]


def _score_candidate_batch(candidates, client, jd_text):
    rate_limited = False
    modes = set()
    for candidate in candidates:
        try:
            modes.add(score_candidate(candidate, client, jd_text))
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
    return rate_limited, ("anthropic" if "anthropic" in modes else "local")


@candidates_api_bp.route("/upload-resumes/<int:job_id>", methods=["POST"])
@login_required
def upload_resumes(job_id):
    try:
        job = db.session.get(Job, job_id)
        if not job or job.user_id != current_user.id:
            return jsonify({"success": False, "error": "Job not found"}), 404

        files = request.files.getlist("resumes")
        if not files:
            return jsonify({"success": False, "error": "No files provided"}), 400

        max_pages, max_chars = _resume_parse_limits()
        created = []
        first_error = None

        for file in files:
            raw_name = (file.filename or "").strip()
            if not raw_name:
                if not first_error:
                    first_error = "One or more selected files were empty."
                continue
            if not raw_name.lower().endswith(".pdf"):
                continue

            filename = secure_filename(raw_name)
            file_bytes = file.read()
            if not file_bytes:
                if not first_error:
                    first_error = f"File is empty: {filename}"
                continue

            try:
                resume_text = extract_pdf_text(file_bytes, max_pages=max_pages, max_chars=max_chars)
            except Exception as e:
                logger.error("Resume PDF extraction failed for %s: %s", filename, e)
                if not first_error:
                    first_error = f"Could not read PDF: {filename}"
                continue

            if not resume_text:
                if not first_error:
                    first_error = f"No readable text found in: {filename}"
                continue

            storage_path = f"resumes/{job_id}/{filename}"
            try:
                upload_file("documents", storage_path, file_bytes)
            except Exception as e:
                logger.error("Resume upload to storage failed for %s: %s", filename, e)

            candidate = Candidate(job_id=job.id, resume_text=resume_text, resume_filename=filename)
            db.session.add(candidate)
            created.append(candidate)

        if not created:
            db.session.rollback()
            return jsonify({
                "success": False,
                "error": first_error or "No valid resumes could be processed"
            }), 400

        job.status = "ready"
        db.session.commit()

        results = [{"id": c.id, "filename": c.resume_filename} for c in created]
        return jsonify({"success": True, "candidates": results})
    except Exception as e:
        db.session.rollback()
        logger.exception("Unexpected error uploading resumes for job %s: %s", job_id, e)
        return jsonify({
            "success": False,
            "error": "Server error while processing resumes. Please try a smaller PDF."
        }), 500


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

    if job.status not in ("ready", "completed", "processing"):
        return jsonify({"success": False, "error": "Job is not ready for screening"}), 400

    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key) if api_key else None

    candidates = db.session.execute(
        db.select(Candidate).where(Candidate.job_id == job.id)
    ).scalars().all()

    if not candidates:
        job.status = "ready"
        db.session.commit()
        return jsonify({"success": False, "error": "No resumes to screen. Please upload resumes first."}), 400

    pending = [c for c in candidates if c.status in ("pending", None)]
    total = len(candidates)
    if not pending:
        job.status = "completed"
        db.session.commit()
        return jsonify({
            "success": True,
            "results": _serialize_ranked_candidates(candidates),
            "rate_limited": False,
            "processed": 0,
            "remaining": 0,
            "total": total,
            "completed": True,
        })

    batch = pending[:_screening_batch_size()]
    rate_limited, screening_mode = _score_candidate_batch(batch, client, job.jd_text)
    remaining = max(0, len(pending) - len(batch))
    job.status = "completed" if remaining == 0 else "processing"
    db.session.commit()

    refreshed = db.session.execute(
        db.select(Candidate).where(Candidate.job_id == job.id)
    ).scalars().all()

    return jsonify({
        "success": True,
        "results": _serialize_ranked_candidates(refreshed),
        "rate_limited": rate_limited,
        "processed": len(batch),
        "remaining": remaining,
        "total": total,
        "completed": remaining == 0,
        "screening_mode": screening_mode,
    })


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
    client = anthropic.Anthropic(api_key=api_key) if api_key else None
    batch = unscored[:_screening_batch_size()]
    rate_limited, screening_mode = _score_candidate_batch(batch, client, job.jd_text)
    remaining = max(0, len(unscored) - len(batch))
    job.status = "completed" if remaining == 0 else "processing"
    db.session.commit()

    all_candidates = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .order_by(Candidate.match_score.desc())
    ).scalars().all()

    return jsonify({
        "success": True,
        "results": [serialize_candidate(c) for c in all_candidates],
        "rate_limited": rate_limited,
        "new_count": len(batch),
        "processed": len(batch),
        "remaining": remaining,
        "total": len(unscored),
        "completed": remaining == 0,
        "screening_mode": screening_mode,
    })


@candidates_api_bp.route("/candidate-status/<int:candidate_id>", methods=["PATCH"])
@login_required
def update_candidate_status(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = str(data.get("status", "")).strip()
    allowed = {
        "scored", "shortlisted", "invited", "interview_done",
        "final_hired", "final_rejected"
    }
    if new_status not in allowed:
        return jsonify({"success": False, "error": "Invalid candidate status"}), 400

    candidate.status = new_status
    status_label = new_status.replace("_", " ").title()
    notify_candidate(
        candidate.candidate_email, "Application status updated",
        f"Your application for {candidate.job.title or 'the position'} is now {status_label}.",
        category="status"
    )
    db.session.commit()
    return jsonify({"success": True, "candidate": serialize_candidate(candidate)})


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

    name = escape(candidate.candidate_name or candidate.resume_filename or "Resume")
    text = escape(candidate.resume_text or "No resume text available.")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{name} — Resume</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 800px;
       margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #1a1a1a; }}
h1 {{ font-size: 1.4rem; border-bottom: 2px solid #e5e7eb; padding-bottom: .5rem; }}
pre {{ white-space: pre-wrap; word-wrap: break-word; font-family: inherit;
       background: #f9fafb; padding: 1.5rem; border-radius: 8px; }}
</style></head>
<body><h1>{name}</h1><pre>{text}</pre></body></html>"""

    return Response(html, content_type="text/html")


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
        notify_candidate(
            c.candidate_email, "Interview invitation",
            f"You have been invited to the next stage for {job.title or 'your application'}.",
            category="interview"
        )

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

    decision_label = "Hired" if decision == "hire" else "Application update"
    decision_message = (
        f"Congratulations — you have been selected for {candidate.job.title or 'the position'}."
        if decision == "hire" else
        f"A final decision has been recorded for your {candidate.job.title or 'job'} application."
    )
    notify_candidate(candidate.candidate_email, decision_label, decision_message, category="decision")
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
