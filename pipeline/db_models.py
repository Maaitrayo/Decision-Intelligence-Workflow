from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    baseline_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyst_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critic_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    query_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    key_signals: Mapped[list["KeySignalRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    ignored_signals: Mapped[list["IgnoredSignalRecord"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    uncertainties: Mapped[list["UncertaintyRecord"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    trace_entries: Mapped[list["TraceEntryRecord"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    chat_sessions: Mapped[list["ChatSessionRecord"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class KeySignalRecord(Base):
    __tablename__ = "key_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)

    run: Mapped[RunRecord] = relationship(back_populates="key_signals")


class IgnoredSignalRecord(Base):
    __tablename__ = "ignored_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    run: Mapped[RunRecord] = relationship(back_populates="ignored_signals")


class UncertaintyRecord(Base):
    __tablename__ = "uncertainties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    signal_a: Mapped[str] = mapped_column(String(500), nullable=False)
    signal_b: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    run: Mapped[RunRecord] = relationship(back_populates="uncertainties")


class TraceEntryRecord(Base):
    __tablename__ = "trace_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    inputs_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    outputs_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    decision: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    run: Mapped[RunRecord] = relationship(back_populates="trace_entries")


class ChatSessionRecord(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    run: Mapped[RunRecord] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessageRecord"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ChatMessageRecord(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session: Mapped[ChatSessionRecord] = relationship(back_populates="messages")
