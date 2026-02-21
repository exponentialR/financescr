# app/settings.py

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any


@dataclass(frozen=True)
class Settings:
    version_stamp: str
    data_root: str

    # Policy paths
    fincrime_policy_path: str
    credit_policy_path: str

    # Fincrime data paths
    fincrime_customers_path: str
    fincrime_watchlist_path: str
    fincrime_labels_path: str

    # Credit data paths
    credit_applications_path: str
    credit_labels_path: str

    # Golden sets (warn-only)
    golden_fincrime_path: str
    golden_credit_path: str


def load_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _require_file(path: str, label: str) -> None:
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"Missing required {label} file: {path}")
    if p.is_dir():
        raise RuntimeError(f"Expected file but found directory for {label}: {path}")


def _warn_missing(path: str, label: str) -> None:
    p = Path(path)
    if not p.exists():
        # warn-only: don't crash startup for golden sets
        print(f"[WARN] Missing optional {label} file: {path}")


def get_settings() -> Settings:
    return Settings(
        version_stamp=os.environ.get("VERSION_STAMP", "financescr@dev"),
        data_root=os.environ.get("DATA_ROOT", "/data"),

        fincrime_policy_path=os.environ.get("FINCRIME_POLICY_PATH", "/data/fincrime/v1/policy.json"),
        credit_policy_path=os.environ.get("CREDIT_POLICY_PATH", "/data/credit/v1/policy.json"),

        fincrime_customers_path=os.environ.get("FINCRIME_CUSTOMERS_PATH", "/data/fincrime/v1/customers.jsonl"),
        fincrime_watchlist_path=os.environ.get("FINCRIME_WATCHLIST_PATH", "/data/fincrime/v1/watchlist.jsonl"),
        fincrime_labels_path=os.environ.get("FINCRIME_LABELS_PATH", "/data/fincrime/v1/labels.jsonl"),

        credit_applications_path=os.environ.get("CREDIT_APPLICATIONS_PATH", "/data/credit/v1/applications.jsonl"),
        credit_labels_path=os.environ.get("CREDIT_LABELS_PATH", "/data/credit/v1/labels.jsonl"),

        golden_fincrime_path=os.environ.get("GOLDEN_FINCRIME_PATH", "/data/golden/v1/fincrime_golden.jsonl"),
        golden_credit_path=os.environ.get("GOLDEN_CREDIT_PATH", "/data/golden/v1/credit_golden.jsonl"),
    )


def validate_data_pack() -> Dict[str, Any]:
    s = get_settings()

    # Load and validate policies (fail-fast)
    fincrime_policy = load_json(s.fincrime_policy_path)
    credit_policy = load_json(s.credit_policy_path)

    for k in ["retrieval_top_k", "return_top_n", "threshold", "uncertainty_band"]:
        if k not in fincrime_policy:
            raise RuntimeError(f"Fincrime policy missing key: {k}")

    for k in ["pd_threshold_approve", "pd_threshold_refer", "affordability"]:
        if k not in credit_policy:
            raise RuntimeError(f"Credit policy missing key: {k}")

    # Required dataset files (fail-fast)
    _require_file(s.fincrime_customers_path, "fincrime customers")
    _require_file(s.fincrime_watchlist_path, "fincrime watchlist")
    _require_file(s.fincrime_labels_path, "fincrime labels")

    _require_file(s.credit_applications_path, "credit applications")
    _require_file(s.credit_labels_path, "credit labels")

    # Optional golden sets (warn-only)
    _warn_missing(s.golden_fincrime_path, "golden fincrime")
    _warn_missing(s.golden_credit_path, "golden credit")

    return {
        "fincrime_policy_version": "fincrime/v1",
        "credit_policy_version": "credit/v1",
        "fincrime_data_version": "fincrime/v1",
        "credit_data_version": "credit/v1",
    }