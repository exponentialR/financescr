from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.providers.jsonl import read_jsonl


@dataclass(frozen=True)
class CustomerRecord:
    customer_id: str
    name: str
    dob: Optional[str] = None
    nationality: Optional[str] = None
    residence_country: Optional[str] = None
    id_hash: Optional[str] = None


class CustomerProvider:
    def __init__(self, customers_path: str):
        self.customers_path = customers_path
        self._by_id: Dict[str, CustomerRecord] = {}

    def load(self) -> None:
        by_id: Dict[str, CustomerRecord] = {}
        for row in read_jsonl(self.customers_path):
            cid = row["customer_id"]
            by_id[cid] = CustomerRecord(
                customer_id=cid,
                name=row["name"],
                dob=row.get("dob"),
                nationality=row.get("nationality"),
                residence_country=row.get("residence_country"),
                id_hash=row.get("id_hash"),
            )
        self._by_id = by_id

    def get_customer(self, customer_id: str) -> CustomerRecord:
        if not self._by_id:
            self.load()
        try:
            return self._by_id[customer_id]
        except KeyError as e:
            raise KeyError(f"Customer not found: {customer_id}") from e