import pytest

from colony_manager.adapters.config.loader import FileRuleConfigProvider
from colony_manager.domain.errors import ConfigurationError


def test_loader_reads_placeholder_config_files(tmp_path):
    (tmp_path / "colony_types.yaml").write_text(
        "- name: research_mission\n  display_name: Research Mission\n  description: A colony focused on scientific research\n  initial_investment_pf: 1d5+2\n  base_stats:\n    size: 5\n    complacency: 10\n    order: 10\n    productivity: 10\n    piety: 10\n  resource_exploit_bonus: 1\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    (tmp_path / "personalities.yaml").write_text(
        "- name: test_personality\n  description: desc\n  stat_effects: []\n",
        encoding="utf-8",
    )
    (tmp_path / "rule_tables.yaml").write_text(
        'size_to_profit_factor:\n  - size: 1\n    profit_factor: 2\nleadership_modifier:\n  - stat_bonus: 0\n    modifier: 1\nlore_thresholds:\n  complacency:\n    placated_threshold: "> size"\n    zero_state: riots_and_unrest\n    default: stable\n  order:\n    zero_state: anarchy\n    orderly_threshold: "> size"\n    default: stable\n  productivity:\n    productive_threshold: "> size"\n    zero_state: halted\n    default: stable\n  piety:\n    pious_threshold: "> size"\n    zero_state: heretical\n    default: stable\n',  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    (tmp_path / "infrastructure_types.yaml").write_text(
        "- name: test_infra\n  display_name: Test Infrastructure\n  description: Test\n  states:\n    working:\n      description: Working\n      modifiers: []\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    (tmp_path / "representative_types.yaml").write_text(
        "- name: test_rep\n  display_name: Test Representative\n  description: Test\n  special_effects: []\n  themes: []\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    (tmp_path / "support_upgrades.yaml").write_text(
        "- name: test_upgrade\n  display_name: Test Upgrade\n  description: Test\n  stat_effects: []\n  mechanical_effects: []\n  lore_effects: []\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )

    provider = FileRuleConfigProvider(config_dir=tmp_path)

    assert provider.colony_types[0].name == "research_mission"
    assert provider.personalities[0].name == "test_personality"
    assert provider.get_base_profit_factor(1) == 2
    assert provider.get_leadership_modifier(0) == 1
    assert provider.infrastructure_types[0].name == "test_infra"
    assert provider.representative_types[0].name == "test_rep"
    assert provider.support_upgrades[0].name == "test_upgrade"


def test_loader_raises_for_missing_config(tmp_path):
    with pytest.raises(ConfigurationError):
        FileRuleConfigProvider(config_dir=tmp_path)


def test_loader_raises_for_invalid_entry(tmp_path):
    (tmp_path / "colony_types.yaml").write_text("- name: missing_base_values\n", encoding="utf-8")
    (tmp_path / "personalities.yaml").write_text(
        "- name: test\n  description: desc\n  effect: effect\n", encoding="utf-8"
    )
    (tmp_path / "rule_tables.yaml").write_text(
        "size_to_profit_factor: []\nleadership_modifier: []\nlore_thresholds: {}\n",
        encoding="utf-8",
    )
    (tmp_path / "infrastructure_types.yaml").write_text(
        "- name: test\n  display_name: Test\n  description: Test\n  states: {}\n", encoding="utf-8"
    )
    (tmp_path / "representative_types.yaml").write_text(
        "- name: test\n  display_name: Test\n  description: Test\n  special_effects: []\n  themes: []\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    (tmp_path / "support_upgrades.yaml").write_text(
        "- name: test\n  display_name: Test\n  description: Test\n  stat_effects: []\n  mechanical_effects: []\n  lore_effects: []\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError):
        FileRuleConfigProvider(config_dir=tmp_path)
