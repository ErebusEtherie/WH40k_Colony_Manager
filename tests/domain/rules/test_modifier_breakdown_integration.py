"""Integration tests for infrastructure and support upgrade modifier breakdowns."""

from datetime import date
from pathlib import Path

import pytest

from colony_manager.config.config_loaders import (
    ConfigurationError,
    InfrastructureConfigLoader,
    SupportUpgradeConfigLoader,
)
from colony_manager.domain.enums import (
    ColonyType,
    InfrastructureState,
    InfrastructureType,
    ModifierStat,
    SupportUpgradeType,
)
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.infrastructure import Infrastructure
from colony_manager.domain.models.support_upgrade import SupportUpgrade
from colony_manager.domain.rules.infrastructure_rules import (
    apply_infrastructure_modifiers,
    get_missing_infrastructure_penalty,
)
from colony_manager.domain.rules.support_upgrade_rules import get_support_upgrade_modifiers


@pytest.fixture
def base_colony() -> Colony:
    return Colony(
        id=1,
        name="Test Colony",
        founder_name="Test Founder",
        colony_type=ColonyType.AGRICULTURAL,
        age_days=0,
        age_last_updated=date.today(),
        base_complacency=5,
        base_order=5,
        base_productivity=5,
        base_piety=5,
        base_size=5,
    )


class TestInfrastructureModifiers:
    def test_working_infrastructure_includes_instance_name(self, base_colony: Colony) -> None:
        transport = Infrastructure(
            id=1,
            colony_id=1,
            name="Grand Spaceport",
            infrastructure_type=InfrastructureType.TRANSPORT,
            state=InfrastructureState.WORKING,
        )
        modifiers = apply_infrastructure_modifiers([transport])
        assert len(modifiers) == 2
        assert all(mod.source_entity_id == 1 for mod in modifiers)
        assert all("Grand Spaceport" in mod.modifier_description for mod in modifiers)

    def test_missing_infrastructure_penalty_shows_count(self, base_colony: Colony) -> None:
        transport = Infrastructure(
            id=1,
            colony_id=1,
            name="Spaceport",
            infrastructure_type=InfrastructureType.TRANSPORT,
            state=InfrastructureState.WORKING,
        )
        penalties = get_missing_infrastructure_penalty([transport], colony_id=1)
        assert len(penalties) == 1
        assert penalties[0].modifier_value == -4
        assert "4 missing" in penalties[0].modifier_description


class TestSupportUpgradeModifiers:
    def test_support_upgrade_includes_instance_name(self, base_colony: Colony) -> None:
        arbites = SupportUpgrade(
            id=10,
            colony_id=1,
            name="99th Arbites Precinct",
            upgrade_type=SupportUpgradeType.ARBITES_PRECINCT,
        )
        modifiers = get_support_upgrade_modifiers(arbites, base_colony.colony_type)
        assert len(modifiers) == 1
        assert modifiers[0].source_entity_id == 10
        assert "99th Arbites Precinct" in modifiers[0].modifier_description

    def test_cultural_improvement_shows_chosen_stat(self, base_colony: Colony) -> None:
        cultural = SupportUpgrade(
            id=11,
            colony_id=1,
            name="Saint's Cathedral",
            upgrade_type=SupportUpgradeType.CULTURAL_IMPROVEMENT,
            custom_stat_choice=ModifierStat.PIETY,
        )
        modifiers = get_support_upgrade_modifiers(cultural, base_colony.colony_type)
        assert len(modifiers) == 1
        assert modifiers[0].source_entity_id == 11
        assert "chosen: piety" in modifiers[0].modifier_description.lower()


class TestConditionalBonuses:
    def test_mechanicum_station_mining_bonus(self) -> None:
        mechanicum = SupportUpgrade(
            id=21,
            colony_id=2,
            name="Forge Temple",
            upgrade_type=SupportUpgradeType.MECHANICUM_STATION,
        )
        modifiers = get_support_upgrade_modifiers(mechanicum, ColonyType.MINING_AND_INDUSTRY)
        assert len(modifiers) == 1
        assert modifiers[0].modifier_value == 2
        assert "Mining And Industry" in modifiers[0].modifier_description


class TestConfigLoading:
    def test_infrastructure_config_loads(self) -> None:
        loader = InfrastructureConfigLoader()
        config = loader.load()
        assert "transport" in config
        assert len(config["transport"].states["working"].modifiers) == 2

    def test_support_upgrade_config_loads(self) -> None:
        loader = SupportUpgradeConfigLoader()
        config = loader.load()
        assert "mechanicum_station" in config
        assert len(config["mechanicum_station"].stat_effects[0].conditional_bonuses) == 2

    def test_infrastructure_config_missing_file_raises_error(self) -> None:
        """Test that missing config file raises ConfigurationError."""
        loader = InfrastructureConfigLoader(config_path=Path("/nonexistent/path.yaml"))
        with pytest.raises(ConfigurationError, match="Infrastructure config not found"):
            loader.load()

    def test_support_upgrade_config_missing_file_raises_error(self) -> None:
        """Test that missing config file raises ConfigurationError."""
        loader = SupportUpgradeConfigLoader(config_path=Path("/nonexistent/path.yaml"))
        with pytest.raises(ConfigurationError, match="Support upgrade config not found"):
            loader.load()
