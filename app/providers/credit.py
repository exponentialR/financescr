from dataclasses import dataclass
from typing import Any, Dict

from app.providers.jsonl import read_jsonl


@dataclass(frozen=True)
class CreditApplication:
    application_id: str
    customer_id: str
    product: str
    amount_gbp: float
    term_months: int
    income_monthly_gbp: float
    outgoings_monthly_gbp: float
    employment_status: str
    employment_months: int
    credit_utilisation: float
    missed_payments_12m: int
    bank_balance_volatility: float


class CreditProvider:
    def __init__(self, applications_path: str):
        self.applications_path = applications_path
        self._by_id: Dict[str, CreditApplication] = {}

    def load(self) -> None:
        by_id: Dict[str, CreditApplication] = {}
        for row in read_jsonl(self.applications_path):
            aid = row["application_id"]
            by_id[aid] = CreditApplication(
                application_id=aid,
                customer_id=row["customer_id"],
                product=row["product"],
                amount_gbp=float(row["amount_gbp"]),
                term_months=int(row["term_months"]),
                income_monthly_gbp=float(row["income_monthly_gbp"]),
                outgoings_monthly_gbp=float(row["outgoings_monthly_gbp"]),
                employment_status=row["employment_status"],
                employment_months=int(row["employment_months"]),
                credit_utilisation=float(row["credit_utilisation"]),
                missed_payments_12m=int(row["missed_payments_12m"]),
                bank_balance_volatility=float(row["bank_balance_volatility"]),
            )
        self._by_id = by_id

    def get_application(self, application_id: str) -> CreditApplication:
        if not self._by_id:
            self.load()
        try:
            return self._by_id[application_id]
        except KeyError as e:
            raise KeyError(f"Application not found: {application_id}") from e