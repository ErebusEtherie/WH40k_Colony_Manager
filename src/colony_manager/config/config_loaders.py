"""Configuration loaders for rule tables.

Loads YAML configuration files into validated Pydantic models.
Per `.clinerules/02-domain-modeling.md`, rule tables are data, not code.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError


class ConfigurationError(Exception):
    """Raised when configuration loading fails."""


class ModifierConfig(BaseModel):
    """A single modifier from config."""

    stat: str
    value: int


class InfrastructureStateConfig(BaseModel):
    """Configuration for a single infrastructure state."""

    description: str
    modifiers: list[ModifierConfig] = Field(default_factory=list)


class InfrastructureTypeConfig(BaseModel):
    """Configuration for an infrastructure type."""

    name: str
    display_name: str
    description: str
    states: dict[str, InfrastructureStateConfig]


class ConditionalBonusConfig(BaseModel):
    """A conditional bonus for support upgrades."""

    colony_types: list[str]
    value: int


class SupportUpgradeStatEffectConfig(BaseModel):
    """Configuration for a support upgrade stat effect."""

    stat: str
    value: int
    conditional_bonuses: list[ConditionalBonusConfig] = Field(default_factory=list)
    choices: list[str] | None = None
    excludes: list[str] = Field(default_factory=list)


class MechanicalEffectConfig(BaseModel):
    """Configuration for a mechanical effect."""

    description: str
    type: str
    skills: list[str] | None = None
    skill: str | None = None
    bonus: int | None = None
    condition: str | None = None
    interval_days: int | None = None
    roll: str | None = None
    threshold: int | None = None
    reward: str | None = None


class SupportUpgradeConfig(BaseModel):
    """Configuration for a support upgrade."""

    name: str
    display_name: str
    description: str
    stat_effects: list[SupportUpgradeStatEffectConfig] = Field(default_factory=list)
    mechanical_effects: list[MechanicalEffectConfig] = Field(default_factory=list)
    lore_effects: list[str] = Field(default_factory=list)


class InfrastructureConfigLoader:
    """Loader for infrastructure type configurations."""

    def __init__(self, config_path: Path | None = None):
        """Initialize the loader.

        Args:
            config_path: Path to the infrastructure_types.yaml file.
                Defaults to config/infrastructure_types.yaml in project root.
        """
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent.parent.parent / "config" / "infrastructure_types.yaml"
            )
        self.config_path = config_path

    def load(self) -> dict[str, InfrastructureTypeConfig]:
        """Load and validate infrastructure configurations.

        Returns:
            Dictionary mapping infrastructure type name to config.

        Raises:
            ConfigurationError: If config file is missing, malformed, or contains invalid data.
        """
        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise ConfigurationError(
                f"Infrastructure config not found: {self.config_path}"
            ) from None
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {self.config_path}: {e}") from e

        configs = {}
        for item in data:
            try:
                config = InfrastructureTypeConfig(**item)
                configs[config.name] = config
            except ValidationError as e:
                raise ConfigurationError(
                    f"Invalid config for '{item.get('name', 'unknown')}': {e}"
                ) from e

        return configs


class SupportUpgradeConfigLoader:
    """Loader for support upgrade configurations."""

    def __init__(self, config_path: Path | None = None):
        """Initialize the loader.

        Args:
            config_path: Path to the support_upgrades.yaml file.
                Defaults to config/support_upgrades.yaml in project root.
        """
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent.parent.parent / "config" / "support_upgrades.yaml"
            )
        self.config_path = config_path

    def load(self) -> dict[str, SupportUpgradeConfig]:
        """Load and validate support upgrade configurations.

        Returns:
            Dictionary mapping support upgrade name to config.

        Raises:
            ConfigurationError: If config file is missing, malformed, or contains invalid data.
        """
        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise ConfigurationError(
                f"Support upgrade config not found: {self.config_path}"
            ) from None
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {self.config_path}: {e}") from e

        configs = {}
        for item in data:
            try:
                config = SupportUpgradeConfig(**item)
                configs[config.name] = config
            except ValidationError as e:
                raise ConfigurationError(
                    f"Invalid config for '{item.get('name', 'unknown')}': {e}"
                ) from e

        return configs


__all__ = [
    "ConfigurationError",
    "InfrastructureConfigLoader",
    "InfrastructureTypeConfig",
    "ModifierConfig",
    "SupportUpgradeConfig",
    "SupportUpgradeConfigLoader",
]
