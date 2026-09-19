"""Export/Import API integration tests."""


class TestExportColony:
    """Test colony export functionality."""

    def test_export_colony_basic(self, auth_client):
        """Test exporting a basic colony."""
        create_data = {
            "name": "Export Test Colony",
            "founder_name": "Test Trader",
            "colony_type": "mining_and_industry",
        }
        response = auth_client.post("/api/v1/colonies", json=create_data)
        assert response.status_code == 201
        colony = response.json()
        assert "id" in colony
        colony_id = colony["id"]

        response = auth_client.get(f"/api/v1/colonies/{colony_id}/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers.get("content-disposition", "")

        export_data = response.json()
        assert export_data["name"] == "Export Test Colony"
        assert export_data["founder_name"] == "Test Trader"
        assert "base_size" in export_data
        assert "events" in export_data
        assert "development_plans" in export_data
        assert "colony_users" in export_data

    def test_export_colony_not_found(self, auth_client):
        """Test exporting non-existent colony returns 404."""
        response = auth_client.get("/api/v1/colonies/99999/export")
        assert response.status_code == 404
        assert "detail" in response.json()


class TestImportColony:
    """Test colony import functionality."""

    def test_import_colony_invalid_format(self, auth_client):
        """Test importing invalid data returns 400."""
        invalid_data = {"name": "Incomplete"}
        response = auth_client.post("/api/v1/colonies/import", json=invalid_data)
        assert response.status_code == 400
        assert "Invalid import file format" in response.json()["detail"]

    def test_import_export_roundtrip(self, auth_client):
        """Test that exporting then importing preserves data."""
        create_data = {
            "name": "Roundtrip Colony",
            "founder_name": "Founder",
            "colony_type": "mining_and_industry",
        }
        response = auth_client.post("/api/v1/colonies", json=create_data)
        assert response.status_code == 201
        original_id = response.json()["id"]

        response = auth_client.get(f"/api/v1/colonies/{original_id}/export")
        assert response.status_code == 200
        export_data = response.json()

        response = auth_client.post("/api/v1/colonies/import", json=export_data)
        assert response.status_code == 201
        result = response.json()
        assert "id" in result
        new_id = result["id"]

        response = auth_client.get(f"/api/v1/colonies/{new_id}/export")
        assert response.status_code == 200
        reimport_data = response.json()

        assert export_data["name"] == reimport_data["name"]
        assert export_data["colony_type"] == reimport_data["colony_type"]
        assert export_data["founder_name"] == reimport_data["founder_name"]
