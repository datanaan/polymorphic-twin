"""In-memory DomainPack registry.

Provides a simple registry for loading, storing, and retrieving DomainPack
instances by domain_id. Supports loading all YAML files from a directory.
"""
from __future__ import annotations

from pathlib import Path

from .parser import parse_domainpack
from .types import DomainPack


class DomainPackRegistry:
    """In-memory registry of DomainPack instances keyed by domain_id."""

    def __init__(self) -> None:
        self._packs: dict[str, DomainPack] = {}

    def register(self, pack: DomainPack) -> None:
        """Register a DomainPack instance.

        Args:
            pack: The DomainPack to register.

        Raises:
            ValueError: If a pack with the same domain_id is already registered.
        """
        if pack.domain_id in self._packs:
            raise ValueError(f"DomainPack already registered: {pack.domain_id}")
        self._packs[pack.domain_id] = pack

    def get(self, domain_id: str) -> DomainPack | None:
        """Retrieve a DomainPack by domain_id.

        Returns None if not found.
        """
        return self._packs.get(domain_id)

    def list_all(self) -> list[str]:
        """Return all registered domain_ids."""
        return list(self._packs.keys())

    def remove(self, domain_id: str) -> bool:
        """Remove a DomainPack by domain_id.

        Returns True if the pack was found and removed, False otherwise.
        """
        if domain_id in self._packs:
            del self._packs[domain_id]
            return True
        return False

    def load_from_directory(self, path: str | Path) -> list[str]:
        """Load all YAML/YML/JSON DomainPack files from a directory.

        Args:
            path: Directory path containing DomainPack files.

        Returns:
            List of domain_ids that were successfully loaded and registered.

        Raises:
            FileNotFoundError: If the directory does not exist.
        """
        path = Path(path)
        if not path.is_dir():
            raise FileNotFoundError(f"Directory not found: {path}")

        loaded_ids: list[str] = []
        for filepath in sorted(path.iterdir()):
            if filepath.suffix in (".yaml", ".yml", ".json"):
                try:
                    pack = parse_domainpack(filepath)
                    self.register(pack)
                    loaded_ids.append(pack.domain_id)
                except Exception:
                    # Skip files that fail to parse/validate
                    # (invalid test fixtures, etc.)
                    continue

        return loaded_ids
