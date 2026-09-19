"""Integration tests for the configuration API endpoints."""

from fastapi.testclient import TestClient


def test_get_colony_types_includes_full_payload(test_client: TestClient):
    """Colony-type payload exposes starting stats and special effects."""
    response = test_client.get("/api/v1/config/colony-types")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    by_id = {ct["id"]: ct for ct in data}
    assert "research_mission" in by_id
    assert "mining_and_industry" in by_id
    assert "ecclesiastical" in by_id
    assert "agricultural" in by_id

    mining = by_id["mining_and_industry"]
    assert mining["name"] == "Mining and Industry"
    # All five core stats are present so the FE can render any of them.
    for stat in ("size", "complacency", "productivity", "order", "piety"):
        assert stat in mining["base_stats"]
    assert mining["base_stats"]["productivity"] == 2
    assert mining["base_stats"]["size"] == 1

    # Mining begins with a free upgrade AND has a conditional exploit bonus.
    assert any(
        e.get("starts_with_upgrade") is True and e.get("upgrade_type") == "industrial_facility"
        for e in mining["special_effects"]
    )
    assert any(
        e.get("resource_types") and e.get("productivity_bonus") == 2
        for e in mining["special_effects"]
    )

    ecclesiastical = by_id["ecclesiastical"]
    assert any(
        e.get("starts_with_upgrade") is True and e.get("upgrade_type") == "cultural_improvement"
        for e in ecclesiastical["special_effects"]
    )
    assert any(e.get("order_piety_swap") is True for e in ecclesiastical["special_effects"])

    research = by_id["research_mission"]
    # Research is a purely conditional type: no free starting upgrade.
    assert not any(e.get("starts_with_upgrade") for e in research["special_effects"])
    assert any(
        e.get("resource_types") and e.get("productivity_bonus") == 2
        for e in research["special_effects"]
    )

    # initial_investment_pf is deliberately not part of the public payload (the
    # FE preview never renders Profit Factor investment).
    assert "initial_investment_pf" not in mining
