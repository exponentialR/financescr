from dataclasses import dataclass
from typing import Dict, List, Optional

from app.providers.jsonl import read_jsonl


@dataclass(frozen=True)
class WatchlistEntity:
    entity_id: str
    list_type: str
    primary_name: str
    aliases: List[str]
    dob: List[str]
    nationalities: List[str]
    residence_countries: List[str]
    id_hashes: List[str]
    source: Optional[str] = None
    active: bool = True


class WatchlistProvider:
    def __init__(self, watchlist_path: str):
        self.watchlist_path = watchlist_path
        self._entities: List[WatchlistEntity] = []

    def load(self) -> None:
        entities: List[WatchlistEntity] = []
        for row in read_jsonl(self.watchlist_path):
            entities.append(
                WatchlistEntity(
                    entity_id=row["entity_id"],
                    list_type=row["list_type"],
                    primary_name=row["primary_name"],
                    aliases=row.get("aliases", []) or [],
                    dob=row.get("dob", []) or [],
                    nationalities=row.get("nationalities", []) or [],
                    residence_countries=row.get("residence_countries", []) or [],
                    id_hashes=row.get("id_hashes", []) or [],
                    source=row.get("source"),
                    active=bool(row.get("active", True)),
                )
            )
        self._entities = entities

    def all_entities(self) -> List[WatchlistEntity]:
        if not self._entities:
            self.load()
        return self._entities