"""SQLAlchemy ORM models for persistence."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Foreign key constants - avoid string duplication
USERS_ID_FK = "users.id"
COLONIES_ID_FK = "colonies.id"
REPRESENTATIVES_ID_FK = "representatives.id"
EVENTS_ID_FK = "events.id"

# Relationship cascade constant - avoid string duplication
CASCADE_DELETE_ORPHAN = "all, delete-orphan"


class Base(DeclarativeBase):
    pass


class ColonyORM(Base):
    __tablename__ = "colonies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    founder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    patron_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    star_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    colony_type: Mapped[str] = mapped_column(String(255), nullable=False)
    age_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    age_last_updated: Mapped[date] = mapped_column(Date, nullable=False)
    current_event: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # GM-authored dossier notes (Colony Dossier Notes & Strategic Intent)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_complacency: Mapped[int] = mapped_column(Integer, nullable=False)
    base_order: Mapped[int] = mapped_column(Integer, nullable=False)
    base_productivity: Mapped[int] = mapped_column(Integer, nullable=False)
    base_piety: Mapped[int] = mapped_column(Integer, nullable=False)
    base_size: Mapped[int] = mapped_column(Integer, nullable=False)
    representative_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(REPRESENTATIVES_ID_FK), nullable=True
    )
    # Dynasty outcome for Dynasty Member representatives
    dynasty_outcome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Lock flags - prevent stat increases until resolved
    complacency_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    productivity_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Planetary resources as JSON array
    planetary_resources: Mapped[str | None] = mapped_column(Text, nullable=True)

    modifiers: Mapped[list[ModifierORM]] = relationship(
        "ModifierORM", back_populates="colony", cascade=CASCADE_DELETE_ORPHAN
    )
    infrastructure: Mapped[list[InfrastructureORM]] = relationship(
        "InfrastructureORM", back_populates="colony", cascade=CASCADE_DELETE_ORPHAN
    )
    support_upgrades: Mapped[list[SupportUpgradeORM]] = relationship(
        "SupportUpgradeORM", back_populates="colony", cascade=CASCADE_DELETE_ORPHAN
    )
    resources: Mapped[list[ResourceORM]] = relationship(
        "ResourceORM", back_populates="colony", cascade=CASCADE_DELETE_ORPHAN
    )

    # Phase 4+ relationships
    events: Mapped[list[EventORM]] = relationship(
        "EventORM", back_populates="colony", cascade=CASCADE_DELETE_ORPHAN
    )
    development_plans: Mapped[list[DevelopmentPlanORM]] = relationship(
        "DevelopmentPlanORM", back_populates="colony", cascade=CASCADE_DELETE_ORPHAN
    )
    audit_logs: Mapped[list[AuditLogORM]] = relationship(
        "AuditLogORM", back_populates="colony", cascade=CASCADE_DELETE_ORPHAN
    )
    colony_users: Mapped[list[ColonyUserORM]] = relationship(
        "ColonyUserORM", back_populates="colony", cascade=CASCADE_DELETE_ORPHAN
    )


class RepresentativeORM(Base):
    __tablename__ = "representatives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    personalities: Mapped[str] = mapped_column(Text, nullable=False)
    stats: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[str] = mapped_column(Text, nullable=False)
    talents: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to_colony_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(COLONIES_ID_FK), nullable=True
    )


class ModifierORM(Base):
    __tablename__ = "modifiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    colony_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(COLONIES_ID_FK, ondelete="CASCADE"), nullable=False
    )
    modifier_source_type: Mapped[str] = mapped_column(String(255), nullable=False)
    modifier_category: Mapped[str] = mapped_column(String(50), nullable=False)
    modifier_stat: Mapped[str] = mapped_column(String(255), nullable=False)
    modifier_value: Mapped[int] = mapped_column(Integer, nullable=False)
    modifier_description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    colony: Mapped[ColonyORM] = relationship("ColonyORM", back_populates="modifiers")


class InfrastructureORM(Base):
    __tablename__ = "infrastructure"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    colony_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(COLONIES_ID_FK, ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    infrastructure_type: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="planned")
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")

    colony: Mapped[ColonyORM] = relationship("ColonyORM", back_populates="infrastructure")


class SupportUpgradeORM(Base):
    __tablename__ = "support_upgrades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    colony_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(COLONIES_ID_FK, ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    upgrade_type: Mapped[str] = mapped_column(String(255), nullable=False)
    custom_stat_choice: Mapped[str | None] = mapped_column(String(50), nullable=True)
    custom_product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affiliated_group: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")

    colony: Mapped[ColonyORM] = relationship("ColonyORM", back_populates="support_upgrades")


class ResourceORM(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    colony_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(COLONIES_ID_FK, ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    abundance: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    discovered_date: Mapped[date] = mapped_column(Date, nullable=False)

    colony: Mapped[ColonyORM] = relationship("ColonyORM", back_populates="resources")


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[date] = mapped_column(Date, nullable=True)
    updated_at: Mapped[date] = mapped_column(Date, nullable=True)
    # Note: Colony membership is managed via ColonyUserORM, not this field.
    # The managed_colony_id field was removed in favor of proper many-to-many
    # relationships through the ColonyUserORM model with role-based access control.

    # Phase 4+ relationships
    colony_memberships: Mapped[list[ColonyUserORM]] = relationship(
        "ColonyUserORM",
        foreign_keys="ColonyUserORM.user_id",
        back_populates="user",
        cascade=CASCADE_DELETE_ORPHAN,
    )
    created_events: Mapped[list[EventORM]] = relationship(
        "EventORM", foreign_keys="EventORM.created_by", cascade=CASCADE_DELETE_ORPHAN
    )
    created_development_plans: Mapped[list[DevelopmentPlanORM]] = relationship(
        "DevelopmentPlanORM",
        foreign_keys="DevelopmentPlanORM.created_by",
        cascade=CASCADE_DELETE_ORPHAN,
    )


class EventORM(Base):
    """ORM model for colony events."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    colony_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(COLONIES_ID_FK, ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey(USERS_ID_FK), nullable=False)
    created_at: Mapped[date] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    colony: Mapped[ColonyORM] = relationship("ColonyORM", back_populates="events")
    modifiers: Mapped[list[EventModifierORM]] = relationship(
        "EventModifierORM", back_populates="event", cascade=CASCADE_DELETE_ORPHAN
    )


class EventModifierORM(Base):
    """ORM model for event modifiers."""

    __tablename__ = "event_modifiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(EVENTS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    stat: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relationships
    event: Mapped[EventORM] = relationship("EventORM", back_populates="modifiers")


class DevelopmentPlanORM(Base):
    """ORM model for development plans."""

    __tablename__ = "development_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    colony_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(COLONIES_ID_FK, ondelete="CASCADE"), nullable=False
    )
    upgrade_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_name: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planned")
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey(USERS_ID_FK), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relationships
    colony: Mapped[ColonyORM] = relationship("ColonyORM", back_populates="development_plans")


class AuditLogORM(Base):
    """ORM model for audit log entries."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[int] = mapped_column(Integer, ForeignKey(USERS_ID_FK), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    colony_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(COLONIES_ID_FK, ondelete="CASCADE"), nullable=True
    )

    # Relationships
    colony: Mapped[ColonyORM] = relationship("ColonyORM", back_populates="audit_logs")


class ColonyUserORM(Base):
    """ORM model for colony-user membership."""

    __tablename__ = "colony_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    colony_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(COLONIES_ID_FK, ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")
    joined_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    invited_by: Mapped[int | None] = mapped_column(Integer, ForeignKey(USERS_ID_FK), nullable=True)

    # Relationships
    colony: Mapped[ColonyORM] = relationship("ColonyORM", back_populates="colony_users")
    user: Mapped[UserORM] = relationship(
        "UserORM", foreign_keys=[user_id], back_populates="colony_memberships"
    )
    inviter: Mapped[UserORM | None] = relationship("UserORM", foreign_keys=[invited_by])


class TokenBlacklistORM(Base):
    """ORM model for blacklisted JWT tokens."""

    __tablename__ = "token_blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)


class LoginAttemptORM(Base):
    """ORM model for login attempt tracking."""

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)


class TokenIssuanceORM(Base):
    """ORM model for token issuance tracking."""

    __tablename__ = "token_issuance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    token_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token_type: Mapped[str] = mapped_column(String(10), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
