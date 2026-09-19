"""Import a portable save file back into domain models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from colony_manager.adapters.io.mappers import save_file_to_domain
from colony_manager.adapters.io.save_file_schema import ColonySaveFile


class ColonyImporter:
    """Import colony data from a portable JSON format."""

    def import_from_path(self, path: str | Path) -> dict[str, Any]:
        """Import colony from a file path.

        Returns:
            Dictionary with 'colony', 'representative', 'events',
            'development_plans', 'colony_users'
        """
        payload = Path(path).read_text(encoding="utf-8")
        return self.import_from_string(payload)

    def import_from_string(self, payload: str) -> dict[str, Any]:
        """Import colony from a JSON string.

        Returns:
            Dictionary with 'colony', 'representative', 'events',
            'development_plans', 'colony_users'
        """
        save_file = ColonySaveFile.model_validate_json(payload)
        return save_file_to_domain(save_file)
