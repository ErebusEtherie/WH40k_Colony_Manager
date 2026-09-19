"""Configuration loading and validation for the colony manager."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import yaml

from colony_manager.adapters.config.schemas import (
    ColonyTypeConfig,
    InfrastructureTypeConfig,
    PersonalityConfig,
    RepresentativeTypeConfig,
    RuleTablesConfig,
    SupportUpgradeConfig,
)
from colony_manager.domain.enums import LoreState, ModifierStat
from colony_manager.domain.errors import ConfigurationError
from colony_manager.domain.ports.rule_config_provider import RuleConfigProvider


class FileRuleConfigProvider(RuleConfigProvider):
    """Load rule config from YAML files and expose it via the protocol."""

    def __init__(self, config_dir: str | Path | None = None) -> None:
        if config_dir is None:
            # Default to project root config directory
            self.config_dir = Path(__file__).resolve().parents[4] / "config"
        else:
            self.config_dir = Path(config_dir)
        # Handle read-only mounts gracefully - config dir may be mounted read-only
        # which is fine as long as it already exists with the required files
        with contextlib.suppress(OSError):
            # Config directory may be mounted read-only, which is acceptable
            # if it already exists and contains the required configuration files
            self.config_dir.mkdir(parents=True, exist_ok=True)
        self._colony_types = self._load_colony_types()
        self._personalities = self._load_personalities()
        self._rule_tables = self._load_rule_tables()
        self._infrastructure_types = self._load_infrastructure_types()
        self._representative_types = self._load_representative_types()
        self._support_upgrades = self._load_support_upgrades()

    def get_base_profit_factor(self, size: int) -> int:
        entries = [entry for entry in self._rule_tables.size_to_profit_factor if entry.size == size]
        if not entries:
            raise ConfigurationError(f"No profit factor mapping for size {size}")
        return entries[0].profit_factor

    def get_leadership_modifier(self, stat_bonus: int) -> int:
        if not self._rule_tables.leadership_modifier:
            raise ConfigurationError("No leadership modifier entries configured")

        exact_matches = [
            entry
            for entry in self._rule_tables.leadership_modifier
            if entry.stat_bonus == stat_bonus
        ]
        if exact_matches:
            return exact_matches[0].modifier

        closest = min(
            self._rule_tables.leadership_modifier,
            key=lambda entry: (abs(entry.stat_bonus - stat_bonus), abs(entry.stat_bonus)),
        )
        return closest.modifier

    def get_lore_state_for_stat(self, stat: ModifierStat, value: int, size: int) -> LoreState:
        """Get lore state for a stat - delegates to domain rules for consistency."""
        from colony_manager.domain.rules.lore_state_resolver import resolve_lore_state

        return resolve_lore_state(stat, value, size)

    def get_event_roll_interval_days(self) -> int:
        """Get the global event roll interval in days (default: 60)."""
        if self._rule_tables.game_cycles:
            return self._rule_tables.game_cycles.event_roll_interval_days
        return 60

    def get_development_roll_interval_days(self) -> int:
        """Get the global development roll interval in days (default: 90)."""
        if self._rule_tables.game_cycles:
            return self._rule_tables.game_cycles.development_roll_interval_days
        return 90

    def get_pf_state_bonuses(self) -> dict[str, int]:
        """Get Profit Factor bonuses for colony states."""
        if self._rule_tables.pf_state_bonuses:
            return {
                "placated": self._rule_tables.pf_state_bonuses.placated,
                "productive": self._rule_tables.pf_state_bonuses.productive,
                "orderly": self._rule_tables.pf_state_bonuses.orderly,
            }
        # Default values per Rogue Trader Colony Rules
        return {"placated": 1, "productive": 2, "orderly": 2}

    @property
    def colony_types(self) -> list[ColonyTypeConfig]:
        return self._colony_types

    def get_colony_type_config(self, colony_type_name: str) -> ColonyTypeConfig:
        """Get colony type configuration by name."""
        for ct in self._colony_types:
            if ct.name == colony_type_name:
                return ct
        raise ConfigurationError(f"Unknown colony type: {colony_type_name}")

    @property
    def personalities(self) -> list[PersonalityConfig]:
        return self._personalities

    @property
    def infrastructure_types(self) -> list[InfrastructureTypeConfig]:
        return self._infrastructure_types

    def get_infrastructure_type_config(self, infrastructure_name: str) -> dict[str, object]:
        """Get infrastructure type configuration by name."""
        for infra in self._infrastructure_types:
            if infra.name == infrastructure_name:
                return infra.model_dump()
        raise ConfigurationError(f"Unknown infrastructure type: {infrastructure_name}")

    @property
    def representative_types(self) -> list[RepresentativeTypeConfig]:
        return self._representative_types

    def get_representative_type_config(self, representative_name: str) -> dict[str, object]:
        """Get representative type configuration by name."""
        for rep in self._representative_types:
            if rep.name == representative_name:
                return rep.model_dump()
        raise ConfigurationError(f"Unknown representative type: {representative_name}")

    @property
    def support_upgrades(self) -> list[SupportUpgradeConfig]:
        return self._support_upgrades

    def get_support_upgrade_config(self, upgrade_name: str) -> dict[str, object]:
        """Get support upgrade configuration by name."""
        for upgrade in self._support_upgrades:
            if upgrade.name == upgrade_name:
                return upgrade.model_dump()
        raise ConfigurationError(f"Unknown support upgrade: {upgrade_name}")

    def get_profit_factor_table(self) -> dict[str, int]:
        """Get colony size to profit factor lookup table."""
        return {
            str(entry.size): entry.profit_factor
            for entry in self._rule_tables.size_to_profit_factor
        }

    def get_lore_thresholds(self) -> dict[str, object]:
        """Get threshold configuration for state transitions."""
        return self._rule_tables.lore_thresholds.model_dump()

    def _load_colony_types(self) -> list[ColonyTypeConfig]:
        return self._load_yaml_list("colony_types.yaml", ColonyTypeConfig)

    def _load_personalities(self) -> list[PersonalityConfig]:
        return self._load_yaml_list("personalities.yaml", PersonalityConfig)

    def _load_rule_tables(self) -> RuleTablesConfig:
        path = self.config_dir / "rule_tables.yaml"
        if not path.exists():
            raise ConfigurationError(f"Missing config file: {path}")
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:  # pragma: no cover - exercised via invalid YAML
            raise ConfigurationError(f"Invalid YAML in {path}: {exc}") from exc
        try:
            return RuleTablesConfig.model_validate(data)
        except Exception as exc:  # pragma: no cover - exercised via invalid config
            raise ConfigurationError(f"Invalid rule tables config: {exc}") from exc

    def _load_yaml_list(self, filename: str, model_type: type[Any]) -> list[Any]:
        path = self.config_dir / filename
        if not path.exists():
            raise ConfigurationError(f"Missing config file: {path}")
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or []
        except yaml.YAMLError as exc:  # pragma: no cover - exercised via invalid YAML
            raise ConfigurationError(f"Invalid YAML in {path}: {exc}") from exc
        if not isinstance(data, list):
            raise ConfigurationError(f"Expected a list in {path}")
        try:
            return [model_type.model_validate(item) for item in data]
        except Exception as exc:  # pragma: no cover - exercised via invalid config
            raise ConfigurationError(f"Invalid {filename} config: {exc}") from exc

    def _load_infrastructure_types(self) -> list[InfrastructureTypeConfig]:
        return self._load_yaml_list("infrastructure_types.yaml", InfrastructureTypeConfig)

    def _load_representative_types(self) -> list[RepresentativeTypeConfig]:
        return self._load_yaml_list("representative_types.yaml", RepresentativeTypeConfig)

    def _load_support_upgrades(self) -> list[SupportUpgradeConfig]:
        return self._load_yaml_list("support_upgrades.yaml", SupportUpgradeConfig)
