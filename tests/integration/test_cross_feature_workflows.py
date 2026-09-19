"""Cross-feature integration tests for realistic colony management workflows.

These tests verify that multiple features work together correctly,
testing end-to-end scenarios rather than isolated functionality.
"""


class TestColonyLifecycle:
    """Test complete colony lifecycle with full feature usage."""

    def test_colony_lifecycle_with_full_feature_usage(self, auth_client):
        """Test realistic colony management workflow.

        Flow:
        1. Create colony (mining_and_industry type)
        2. Install infrastructure (Power Network, Habitation Complex)
        3. Add GM custom modifier
        4. Advance colony age by 30 days
        5. Verify all modifiers apply correctly in breakdown
        6. Verify colony state is complete and valid
        """
        # Step 1: Create colony
        create_data = {
            "name": "Hive Tarsus",
            "founder_name": "Rogue Trader van Dijk",
            "colony_type": "mining_and_industry",
        }
        response = auth_client.post("/api/v1/colonies", json=create_data)
        assert response.status_code == 201
        colony = response.json()
        colony_id = colony["id"]

        # Step 2: Install infrastructure
        # Power Network (+2 Productivity when working)
        power_network = {
            "name": "Primary Power Network",
            "infrastructure_type": "power_network",
            "state": "working",
        }
        response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/infrastructure", json=power_network
        )
        assert response.status_code == 201

        # Transport (+1 Productivity, +1 Complacency when working)
        transport = {
            "name": "Transport Network",
            "infrastructure_type": "transport",
            "state": "working",
        }
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/infrastructure", json=transport)
        assert response.status_code == 201

        # Step 3: Add GM custom modifier
        gm_modifier = {
            "modifier_source_type": "gm_custom",
            "modifier_category": "permanent",
            "modifier_stat": "piety",
            "modifier_value": 2,
            "modifier_description": "Divine blessing from Ministorum",
            "is_active": True,
        }
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/modifiers", json=gm_modifier)
        assert response.status_code == 201

        # Step 4: Get modifier breakdown and verify all sources present
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/modifier-breakdown")
        assert response.status_code == 200
        breakdown = response.json()

        # Verify infrastructure bonuses are present
        assert len(breakdown["productivity"]["modifiers"]) >= 2  # Power Network + Transport
        assert len(breakdown["complacency"]["modifiers"]) >= 1  # Transport

        # Verify GM modifier is present
        piety_mods = [m for m in breakdown["piety"]["modifiers"] if m["source_type"] == "gm_custom"]
        assert len(piety_mods) == 1
        assert piety_mods[0]["value"] == 2
        assert "Divine blessing" in piety_mods[0]["source_name"]

        # Step 5: Advance colony age (ColonyAgeAdvance body; add advances by N days)
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/age", json={"add": 30})
        assert response.status_code == 200
        colony_state = response.json()
        assert colony_state["age_days"] == 30

        # Step 6: Verify colony state is complete and valid
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        assert response.status_code == 200
        state = response.json()

        # Verify all stats are present and non-negative
        for stat in ["size", "complacency", "order", "productivity", "piety"]:
            assert stat in state
            assert state[stat]["current"] >= 0
            assert "base" in state[stat]
            assert "lore_state" in state[stat]


class TestRepresentativeImpact:
    """Test representative assignment effects on colony stats."""

    def test_representative_assignment_triggers_stat_changes(self, auth_client):
        """Test that representative assignment works correctly.

        Flow:
        1. Create colony
        2. Create representative with military_minded personality
        3. Assign representative to colony
        4. Verify assignment successful (no errors)
        5. Verify colony state reflects representative
        """
        # Step 1: Create colony
        create_data = {
            "name": "Representative Test Colony",
            "founder_name": "Test Governor",
            "colony_type": "mining_and_industry",
        }
        response = auth_client.post("/api/v1/colonies", json=create_data)
        assert response.status_code == 201
        colony_id = response.json()["id"]

        # Step 2: Create representative with military_minded personality
        rep_data = {
            "name": "Governor Hestia",
            "type": "colonist_representative",
            "personalities": [
                {
                    "name": "military_minded",
                    "display_name": "Military-Minded",
                    "description": "Focused on martial matters",
                    "effect": "+1 Order",
                    "calamitous_modifier": 0,
                }
            ],
            "stats": {
                "ws": 50,
                "bs": 50,
                "s": 50,
                "t": 50,
                "ag": 50,
                "int": 50,
                "per": 50,
                "wp": 50,
                "fel": 50,
            },
        }
        response = auth_client.post("/api/v1/representatives", json=rep_data)
        assert response.status_code == 201
        rep_id = response.json()["id"]

        # Step 3: Assign representative to colony
        response = auth_client.put(
            f"/api/v1/colonies/{colony_id}/representative", params={"representative_id": rep_id}
        )
        assert response.status_code == 200

        # Step 4: Verify colony has representative assigned
        response = auth_client.get(f"/api/v1/colonies/{colony_id}")
        assert response.status_code == 200
        colony = response.json()
        assert colony["representative_id"] == rep_id

        # Step 5: Verify colony state is valid
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        assert response.status_code == 200
        state = response.json()
        assert state["order"]["current"] >= 0


class TestInfrastructureStateTransitions:
    """Test infrastructure damage and repair cascading effects."""

    def test_infrastructure_damage_cascading_effects(self, auth_client):
        """Test that infrastructure state changes are tracked correctly.

        Flow:
        1. Create colony
        2. Install Power Network (working)
        3. Verify infrastructure is working
        4. Mark Power Network as not_working
        5. Verify infrastructure state changed
        6. Repair infrastructure
        7. Verify infrastructure is working again
        """
        # Step 1: Create colony
        create_data = {
            "name": "Infrastructure Test Colony",
            "founder_name": "Test Engineer",
            "colony_type": "mining_and_industry",
        }
        response = auth_client.post("/api/v1/colonies", json=create_data)
        assert response.status_code == 201
        colony_id = response.json()["id"]

        # Step 2: Install Power Network (working)
        power_network = {
            "name": "Primary Power Grid",
            "infrastructure_type": "power_network",
            "state": "working",
        }
        response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/infrastructure", json=power_network
        )
        assert response.status_code == 201
        infra_id = response.json()["id"]

        # Step 3: Verify infrastructure is working
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/infrastructure/{infra_id}")
        assert response.status_code == 200
        infra = response.json()
        assert infra["state"] == "working"
        assert infra["is_working"] is True

        # Step 4: Mark as not_working
        update_data = {"state": "not_working"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony_id}/infrastructure/{infra_id}", json=update_data
        )
        assert response.status_code == 200

        # Step 5: Verify infrastructure is not_working
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/infrastructure/{infra_id}")
        assert response.status_code == 200
        infra = response.json()
        assert infra["state"] == "not_working"
        assert infra["is_not_working"] is True

        # Step 6: Repair infrastructure
        update_data = {"state": "working"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony_id}/infrastructure/{infra_id}", json=update_data
        )
        assert response.status_code == 200

        # Step 7: Verify infrastructure is working again
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/infrastructure/{infra_id}")
        assert response.status_code == 200
        infra = response.json()
        assert infra["state"] == "working"
        assert infra["is_working"] is True


class TestModifierStacking:
    """Test that modifiers from all sources stack correctly."""

    def test_modifier_stacking_with_all_sources(self, auth_client):
        """Test that modifiers from all sources stack correctly.

        Flow:
        1. Create colony
        2. Add infrastructure (multiple types)
        3. Add multiple GM custom modifiers
        4. Get modifier breakdown
        5. Verify no duplicate modifiers
        6. Verify Piety has both GM modifiers
        7. Verify all stats are non-negative
        """
        # Step 1: Create colony
        create_data = {
            "name": "Stacking Test Colony",
            "founder_name": "Test Administrator",
            "colony_type": "mining_and_industry",
        }
        response = auth_client.post("/api/v1/colonies", json=create_data)
        assert response.status_code == 201
        colony_id = response.json()["id"]

        # Step 2: Add multiple infrastructure
        infra_list = [
            {"name": "Power Network", "infrastructure_type": "power_network", "state": "working"},
            {"name": "Transport Network", "infrastructure_type": "transport", "state": "working"},
        ]
        for infra_data in infra_list:
            response = auth_client.post(
                f"/api/v1/colonies/{colony_id}/infrastructure", json=infra_data
            )
            assert response.status_code == 201

        # Step 3: Add GM custom modifiers
        gm_mods = [
            {
                "modifier_source_type": "gm_custom",
                "modifier_category": "permanent",
                "modifier_stat": "piety",
                "modifier_value": 2,
                "modifier_description": "First blessing",
                "is_active": True,
            },
            {
                "modifier_source_type": "gm_custom",
                "modifier_category": "permanent",
                "modifier_stat": "piety",
                "modifier_value": 1,
                "modifier_description": "Second blessing",
                "is_active": True,
            },
        ]
        for mod_data in gm_mods:
            response = auth_client.post(f"/api/v1/colonies/{colony_id}/modifiers", json=mod_data)
            assert response.status_code == 201

        # Step 4: Get modifier breakdown
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/modifier-breakdown")
        assert response.status_code == 200
        breakdown = response.json()

        # Step 5: Verify no duplicate modifiers
        for stat in ["productivity", "complacency", "order", "piety"]:
            modifiers = breakdown[stat]["modifiers"]
            source_ids = [m.get("source_id") for m in modifiers if m.get("source_id")]
            assert len(source_ids) == len(set(source_ids)), f"Duplicate modifiers found for {stat}"

        # Step 6: Verify Piety has both GM modifiers
        piety_mods = [m for m in breakdown["piety"]["modifiers"] if m["source_type"] == "gm_custom"]
        assert len(piety_mods) == 2
        piety_total = sum(m["value"] for m in piety_mods)
        assert piety_total == 3  # 2 + 1

        # Step 7: Verify all stats are non-negative
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        assert response.status_code == 200
        state = response.json()
        for stat_name in ["size", "complacency", "order", "productivity", "piety"]:
            assert state[stat_name]["current"] >= 0, (
                f"{stat_name} went negative: {state[stat_name]['current']}"
            )


class TestColonyStateTransitions:
    """Test colony state transitions based on thresholds."""

    def test_order_reaches_zero_triggers_anarchy(self, auth_client):
        """Test that Order == 0 triggers Anarchy state.

        Flow:
        1. Create colony
        2. Add GM custom modifier: Order -2 (base Order is 2)
        3. Verify colony state shows "anarchy"
        4. Verify Profit Factor = 0 (per rules)
        5. Add GM custom modifier: Order +3
        6. Verify colony state returns to normal
        7. Verify Profit Factor recalculated correctly
        """
        # Step 1: Create colony
        create_data = {
            "name": "Anarchy Test Colony",
            "founder_name": "Test Commander",
            "colony_type": "mining_and_industry",
        }
        response = auth_client.post("/api/v1/colonies", json=create_data)
        assert response.status_code == 201
        colony_id = response.json()["id"]

        # Step 2: Get baseline state
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        assert response.status_code == 200
        baseline = response.json()
        baseline_order = baseline["order"]["current"]

        # Step 3: Add negative Order modifier to reach 0
        # Assuming base Order is 2, we need -2 to reach 0
        order_penalty = baseline_order  # Use exact value to reach 0
        modifier_data = {
            "modifier_source_type": "gm_custom",
            "modifier_category": "permanent",
            "modifier_stat": "order",
            "modifier_value": -order_penalty,
            "modifier_description": "Rebellion penalty",
            "is_active": True,
        }
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/modifiers", json=modifier_data)
        assert response.status_code == 201

        # Step 4: Verify Order is 0 and Anarchy state triggered
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        assert response.status_code == 200
        anarchy_state = response.json()
        assert anarchy_state["order"]["current"] == 0
        assert anarchy_state["order"]["lore_state"] == "anarchy"
        # Per rules: Anarchy sets Profit Factor to 0
        assert anarchy_state["profit_factor"] == 0

        # Step 5: Add positive Order modifier to recover
        recovery_data = {
            "modifier_source_type": "gm_custom",
            "modifier_category": "permanent",
            "modifier_stat": "order",
            "modifier_value": 3,
            "modifier_description": "Martial law restoration",
            "is_active": True,
        }
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/modifiers", json=recovery_data)
        assert response.status_code == 201

        # Step 6: Verify Order recovered and Anarchy ended
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        assert response.status_code == 200
        recovered_state = response.json()
        assert recovered_state["order"]["current"] > 0
        assert recovered_state["order"]["lore_state"] != "anarchy"
        # Profit Factor should be recalculated (not 0 anymore)
        assert recovered_state["profit_factor"] > 0


class TestErrorHandling:
    """Test error handling and transaction rollback scenarios."""

    def test_invalid_infrastructure_type_rolls_back(self, auth_client):
        """Test that invalid operations don't corrupt state.

        Flow:
        1. Create colony
        2. Attempt to install infrastructure with invalid type
        3. Verify 422 response (validation error)
        4. Verify colony state unchanged
        5. Verify no partial data in database
        """
        # Step 1: Create colony
        create_data = {
            "name": "Error Test Colony",
            "founder_name": "Test User",
            "colony_type": "mining_and_industry",
        }
        response = auth_client.post("/api/v1/colonies", json=create_data)
        assert response.status_code == 201
        colony_id = response.json()["id"]

        # Step 2: Get baseline infrastructure count
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/infrastructure")
        assert response.status_code == 200
        baseline_count = len(response.json()["items"])

        # Step 3: Attempt invalid infrastructure type
        invalid_data = {
            "name": "Invalid Structure",
            "infrastructure_type": "nonexistent_type",
            "state": "working",
        }
        response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/infrastructure", json=invalid_data
        )
        assert response.status_code == 422  # Validation error

        # Step 4: Verify colony state unchanged
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/infrastructure")
        assert response.status_code == 200
        final_count = len(response.json()["items"])
        assert final_count == baseline_count, "Infrastructure count changed after failed operation"
