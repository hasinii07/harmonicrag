import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings

REGISTRY_FILENAME = "embedding_index_registry.json"


def _registry_path(path: Optional[Path] = None) -> Path:
    return path or (settings.metadata_dir / REGISTRY_FILENAME)


def _load_registry(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": 1, "collections": {}}
    try:
        with path.open("r", encoding="utf-8") as registry_file:
            registry = json.load(registry_file)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Embedding index registry is invalid JSON: {path}") from exc

    if registry.get("version") != 1 or not isinstance(registry.get("collections"), dict):
        raise RuntimeError(f"Embedding index registry has an unsupported format: {path}")
    return registry


def get_migrated_collections(
    source_name: str,
    embedding_signature: str,
    path: Optional[Path] = None
) -> List[str]:
    registry = _load_registry(_registry_path(path))
    return [
        name
        for name, metadata in registry["collections"].items()
        if metadata.get("source_collection") == source_name
        and metadata.get("embedding_signature") == embedding_signature
        and metadata.get("state") == "complete"
    ]


def register_migrated_collection(
    collection_name: str,
    source_name: str,
    embedding_signature: str,
    source_count: int,
    path: Optional[Path] = None
) -> None:
    registry_path = _registry_path(path)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry = _load_registry(registry_path)
    registry["collections"][collection_name] = {
        "source_collection": source_name,
        "embedding_signature": embedding_signature,
        "source_count": source_count,
        "state": "complete"
    }

    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=registry_path.parent,
            delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(registry, temporary_file, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, registry_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
