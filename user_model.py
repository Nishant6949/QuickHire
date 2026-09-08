from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, DateTime, Boolean, ForeignKey
from flask_login import LoginManager, UserMixin
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()


class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    work_email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    company_size: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    auto_screen: Mapped[bool] = mapped_column(Boolean, default=True)
    match_threshold: Mapped[int] = mapped_column(Integer, default=70)
    bias_detection: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_matches: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_weekly: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_expire: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_updates: Mapped[bool] = mapped_column(Boolean, default=False)
    jobs: Mapped[list["Job"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    team_members: Mapped[list["TeamMember"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class TeamMember(db.Model):
    __tablename__ = "team_members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="Interviewer")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="invited")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    owner: Mapped["User"] = relationship(back_populates="team_members")


class Job(db.Model):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    jd_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    department: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    seniority_level: Mapped[str | None] = mapped_column(String, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String, nullable=True)
    salary_range_text: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    user: Mapped["User"] = relationship(back_populates="jobs")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class ResetToken(db.Model):
    __tablename__ = "reset_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Candidate(db.Model):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    resume_filename: Mapped[str] = mapped_column(String, nullable=False)
    candidate_name: Mapped[str | None] = mapped_column(String, nullable=True)
    candidate_email: Mapped[str | None] = mapped_column(String, nullable=True)
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skills_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    interview_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    final_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    job: Mapped["Job"] = relationship(back_populates="candidates")

class CandidateAccount(db.Model):
    """Candidate-side account, separate from recruiter User accounts."""
    __tablename__ = "candidate_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class SavedJob(db.Model):
    __tablename__ = "saved_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidate_accounts.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Notification(db.Model):
    """In-app notification for either a recruiter or candidate account."""
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    candidate_account_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("candidate_accounts.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="info")
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class LoginOTP(db.Model):
    """Short-lived hashed OTP for email two-factor authentication."""
    __tablename__ = "login_otps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
