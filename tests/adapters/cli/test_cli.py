from pathlib import Path

from typer.testing import CliRunner

from colony_manager.adapters.cli.main import app

runner = CliRunner()


def _write_test_config(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "colony_types.yaml").write_text(
        "- name: research_mission\n  display_name: Research Mission\n  description: A colony focused on scientific research\n  initial_investment_pf: 1d5+2\n  base_stats:\n    size: 5\n    complacency: 10\n    order: 10\n    productivity: 10\n    piety: 10\n  resource_exploit_bonus: 0\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    (config_dir / "personalities.yaml").write_text(
        "- name: example_personality\n  description: desc\n  stat_effects: []\n",
        encoding="utf-8",
    )
    (config_dir / "rule_tables.yaml").write_text(
        'size_to_profit_factor:\n  - size: 5\n    profit_factor: 2\nleadership_modifier:\n  - stat_bonus: 0\n    modifier: 1\nlore_thresholds:\n  complacency:\n    placated_threshold: "> size"\n    zero_state: riots_and_unrest\n    default: stable\n  order:\n    zero_state: anarchy\n    orderly_threshold: "> size"\n    default: stable\n  productivity:\n    productive_threshold: "> size"\n    zero_state: halted\n    default: stable\n  piety:\n    pious_threshold: "> size"\n    zero_state: heretical\n    default: stable\n',  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    (config_dir / "infrastructure_types.yaml").write_text(
        "- name: test_infra\n  display_name: Test Infrastructure\n  description: Test\n  states:\n    working:\n      description: Working\n      modifiers: []\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    (config_dir / "representative_types.yaml").write_text(
        "- name: judge\n  display_name: Judge\n  description: Test\n  special_effects: []\n  themes: []\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    (config_dir / "support_upgrades.yaml").write_text(
        "- name: test_upgrade\n  display_name: Test Upgrade\n  description: Test\n  stat_effects: []\n  mechanical_effects: []\n  lore_effects: []\n",  # noqa: E501  # YAML fixture string; wrapping would break serialized data
        encoding="utf-8",
    )
    return config_dir


def test_cli_create_and_show_colony(tmp_path):
    config_dir = _write_test_config(tmp_path)

    result = runner.invoke(
        app,
        [
            "--config-dir",
            str(config_dir),
            "colony",
            "create",
            "Example Colony",
            "Owner",
            "research_mission",
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(app, ["--config-dir", str(config_dir), "colony", "show", "1"])
    assert result.exit_code == 0
    assert "Example Colony" in result.stdout
    assert "Owner" in result.stdout
    assert "Size" in result.stdout


def test_cli_list_colonies(tmp_path):
    config_dir = _write_test_config(tmp_path)

    result = runner.invoke(
        app,
        [
            "--config-dir",
            str(config_dir),
            "colony",
            "create",
            "Example Colony",
            "Owner",
            "research_mission",
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(app, ["--config-dir", str(config_dir), "colony", "list"])
    assert result.exit_code == 0
    assert "Example Colony" in result.stdout
    assert "research_mission" in result.stdout


def test_cli_representative_and_import_export_flow(tmp_path):
    config_dir = _write_test_config(tmp_path)

    create_result = runner.invoke(
        app,
        [
            "--config-dir",
            str(config_dir),
            "colony",
            "create",
            "Export Colony",
            "Owner",
            "research_mission",
        ],
    )
    assert create_result.exit_code == 0

    rep_result = runner.invoke(
        app,
        [
            "--config-dir",
            str(config_dir),
            "representative",
            "create",
            "Test Representative",
            "judge",
        ],
    )
    assert rep_result.exit_code == 0

    export_path = tmp_path / "colony_export.json"
    export_result = runner.invoke(
        app,
        ["--config-dir", str(config_dir), "colony", "export", "1", str(export_path)],
    )
    assert export_result.exit_code == 0
    assert export_path.exists()

    import_result = runner.invoke(
        app, ["--config-dir", str(config_dir), "colony", "import", str(export_path)]
    )
    assert import_result.exit_code == 0
    assert "Imported colony" in import_result.stdout
