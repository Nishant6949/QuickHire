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
    auto_screen: Mapped[bool] = mapped_column(Boolean, default=True)
    match_threshold: Mapped[int] = mapped_column(Integer, default=70)
    bias_detection: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_matches: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_weekly: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_expire: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_updates: Mapped[bool] = mapped_column(Boolean, default=False)
    jobs: Mapped[list["Job"]] = relationship(back_populates="user", cascade="all, delete-orphan")


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
