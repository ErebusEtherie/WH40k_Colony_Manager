"""Dependency injection for the API."""

import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from colony_manager.adapters.config.loader import FileRuleConfigProvider
from colony_manager.adapters.persistence.colony_repository_impl import SqlAlchemyColonyRepository
from colony_manager.adapters.persistence.db import build_database_url
from colony_manager.adapters.persistence.infrastructure_repository_impl import (
    SqlAlchemyInfrastructureRepository,
)
from colony_manager.adapters.persistence.repositories.audit_log_repository_impl import (
    SqlAlchemyAuditLogRepository,
)
from colony_manager.adapters.persistence.repositories.colony_user_repository_impl import (
    SqlAlchemyColonyUserRepository,
)
from colony_manager.adapters.persistence.repositories.development_plan_repository_impl import (
    SqlAlchemyDevelopmentPlanRepository,
)
from colony_manager.adapters.persistence.repositories.event_repository_impl import (
    SqlAlchemyEventRepository,
)
from colony_manager.adapters.persistence.repositories.login_attempt_repository_impl import (
    SqlAlchemyLoginAttemptRepository,
)
from colony_manager.adapters.persistence.repositories.token_blacklist_repository_impl import (
    SqlAlchemyTokenBlacklistRepository,
)
from colony_manager.adapters.persistence.repositories.token_issuance_repository_impl import (
    SqlAlchemyTokenIssuanceRepository,
)
from colony_manager.adapters.persistence.representative_repository_impl import (
    SqlAlchemyRepresentativeRepository,
)
from colony_manager.adapters.persistence.support_upgrade_repository_impl import (
    SqlAlchemySupportUpgradeRepository,
)
from colony_manager.adapters.persistence.user_repository_impl import SqlAlchemyUserRepository
from colony_manager.application.services.auth_service import AuthService
from colony_manager.application.services.colony_service import ColonyService
from colony_manager.application.services.colony_user_service import ColonyUserService
from colony_manager.application.services.development_plan_service import DevelopmentPlanService
from colony_manager.application.services.event_service import EventService
from colony_manager.application.services.representative_service import RepresentativeService
from colony_manager.application.services.user_service import UserService
from colony_manager.config.settings import get_security_settings
from colony_manager.domain.ports.audit_log_repository import AuditLogRepository
from colony_manager.domain.ports.colony_repository import ColonyRepository
from colony_manager.domain.ports.colony_user_repository import ColonyUserRepository
from colony_manager.domain.ports.development_plan_repository import DevelopmentPlanRepository
from colony_manager.domain.ports.event_repository import EventRepository
from colony_manager.domain.ports.infrastructure_repository import InfrastructureRepository
from colony_manager.domain.ports.login_attempt_repository import LoginAttemptRepository
from colony_manager.domain.ports.representative_repository import RepresentativeRepository
from colony_manager.domain.ports.rule_config_provider import RuleConfigProvider
from colony_manager.domain.ports.support_upgrade_repository import SupportUpgradeRepository
from colony_manager.domain.ports.token_blacklist_repository import TokenBlacklistRepository
from colony_manager.domain.ports.token_issuance_repository import TokenIssuanceRepository
from colony_manager.domain.ports.user_repository import UserRepository

# Default paths - config is at project root, not src/config
DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[3].parent / "config"
DEFAULT_DB_PATH = DEFAULT_CONFIG_DIR.parent / "colony_manager.sqlite"


def get_config_dir() -> Path:
    """Get the config directory path.

    Checks CONFIG_DIR environment variable first, then falls back to default.
    """
    # Allow override via environment variable
    if config_dir := os.getenv("CONFIG_DIR"):
        return Path(config_dir)
    return DEFAULT_CONFIG_DIR


def get_db_path() -> Path:
    """Get the database file path.

    Checks DATABASE_PATH environment variable first, then falls back to default.
    """
    # Allow override via environment variable
    if db_path := os.getenv("DATABASE_PATH"):
        return Path(db_path)
    return DEFAULT_DB_PATH


# Global singleton for rule config provider
_rule_config_provider: RuleConfigProvider | None = None


def get_rule_config_provider() -> RuleConfigProvider:
    """Get the global rule config provider singleton.

    Returns:
        RuleConfigProvider instance loaded at startup.

    Raises:
        RuntimeError: If config provider hasn't been initialized yet.
    """
    if _rule_config_provider is None:
        raise RuntimeError(
            "Rule config provider not initialized. Call "
            "init_rule_config_provider() during application startup."
        )
    return _rule_config_provider


def init_rule_config_provider(config_dir: Path | None = None) -> RuleConfigProvider:
    """Initialize the global rule config provider singleton.

    Args:
        config_dir: Optional config directory path. Defaults to DEFAULT_CONFIG_DIR.

    Returns:
        Initialized RuleConfigProvider instance.
    """
    global _rule_config_provider
    if config_dir is None:
        config_dir = get_config_dir()
    _rule_config_provider = FileRuleConfigProvider(config_dir=config_dir)
    return _rule_config_provider


def get_colony_repository(db_path: Annotated[Path, Depends(get_db_path)]) -> ColonyRepository:
    """Get colony repository instance."""
    return SqlAlchemyColonyRepository(build_database_url(db_path))


def get_representative_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> RepresentativeRepository:
    """Get representative repository instance."""
    return SqlAlchemyRepresentativeRepository(build_database_url(db_path))


def get_user_repository(db_path: Annotated[Path, Depends(get_db_path)]) -> UserRepository:
    """Get user repository instance."""
    return SqlAlchemyUserRepository(build_database_url(db_path))


def get_event_repository(db_path: Annotated[Path, Depends(get_db_path)]) -> EventRepository:
    """Get event repository instance."""
    return SqlAlchemyEventRepository(build_database_url(db_path))


def get_development_plan_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> DevelopmentPlanRepository:
    """Get development plan repository instance."""
    return SqlAlchemyDevelopmentPlanRepository(build_database_url(db_path))


def get_audit_log_repository(db_path: Annotated[Path, Depends(get_db_path)]) -> AuditLogRepository:
    """Get audit log repository instance."""
    return SqlAlchemyAuditLogRepository(build_database_url(db_path))


def get_colony_user_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> ColonyUserRepository:
    """Get colony user repository instance."""
    return SqlAlchemyColonyUserRepository(build_database_url(db_path))


def get_colony_service(
    colony_repository: Annotated[ColonyRepository, Depends(get_colony_repository)],
    representative_repository: Annotated[
        RepresentativeRepository, Depends(get_representative_repository)
    ],
    rule_config_provider: Annotated[RuleConfigProvider, Depends(get_rule_config_provider)],
    colony_user_repository: Annotated[ColonyUserRepository, Depends(get_colony_user_repository)],
    audit_log_repository: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> ColonyService:
    """Get colony service instance with dependencies."""
    return ColonyService(
        colony_repository,
        representative_repository,
        rule_config_provider,
        colony_user_repository,
        audit_log_repository,
    )


def get_representative_service(
    colony_repository: Annotated[ColonyRepository, Depends(get_colony_repository)],
    representative_repository: Annotated[
        RepresentativeRepository, Depends(get_representative_repository)
    ],
) -> RepresentativeService:
    """Get representative service instance with dependencies."""
    return RepresentativeService(colony_repository, representative_repository)


def get_event_service(
    event_repository: Annotated[EventRepository, Depends(get_event_repository)],
    audit_log_repository: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> EventService:
    """Get event service instance with dependencies."""
    return EventService(event_repository, audit_log_repository)


def get_infrastructure_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> InfrastructureRepository:
    """Get infrastructure repository instance."""
    return SqlAlchemyInfrastructureRepository(build_database_url(db_path))


def get_support_upgrade_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> SupportUpgradeRepository:
    """Get support upgrade repository instance."""
    return SqlAlchemySupportUpgradeRepository(build_database_url(db_path))


def get_development_plan_service(
    plan_repository: Annotated[DevelopmentPlanRepository, Depends(get_development_plan_repository)],
    audit_log_repository: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    infrastructure_repository: Annotated[
        InfrastructureRepository, Depends(get_infrastructure_repository)
    ],
    support_upgrade_repository: Annotated[
        SupportUpgradeRepository, Depends(get_support_upgrade_repository)
    ],
) -> DevelopmentPlanService:
    """Get development plan service instance with dependencies."""
    return DevelopmentPlanService(
        plan_repository, audit_log_repository, infrastructure_repository, support_upgrade_repository
    )


def get_colony_user_service(
    membership_repository: Annotated[ColonyUserRepository, Depends(get_colony_user_repository)],
    audit_log_repository: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> ColonyUserService:
    """Get colony user service instance with dependencies."""
    return ColonyUserService(membership_repository, audit_log_repository, user_repository)


def get_token_blacklist_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> TokenBlacklistRepository:
    """Get token blacklist repository instance."""
    return SqlAlchemyTokenBlacklistRepository(build_database_url(db_path))


def get_login_attempt_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> LoginAttemptRepository:
    """Get login attempt repository instance."""
    return SqlAlchemyLoginAttemptRepository(build_database_url(db_path))


def get_token_issuance_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> TokenIssuanceRepository:
    """Get token issuance repository instance."""
    return SqlAlchemyTokenIssuanceRepository(build_database_url(db_path))


def get_auth_service(
    token_blacklist_repository: Annotated[
        TokenBlacklistRepository, Depends(get_token_blacklist_repository)
    ],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    login_attempt_repository: Annotated[
        LoginAttemptRepository, Depends(get_login_attempt_repository)
    ],
    token_issuance_repository: Annotated[
        TokenIssuanceRepository, Depends(get_token_issuance_repository)
    ],
) -> AuthService:
    """Get auth service instance with dependencies."""
    settings = get_security_settings()
    return AuthService(
        token_blacklist_repository,
        user_repository,
        login_attempt_repository,
        token_issuance_repository,
        refresh_reuse_detection_enabled=settings.refresh_reuse_detection_enabled,
    )


def get_user_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    audit_log_repository: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> UserService:
    """Get user service instance with dependencies."""
    return UserService(user_repository, audit_log_repository)
