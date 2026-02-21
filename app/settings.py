import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    version_stamp: str
    data_root: str
    fincrime_policy_path: str
    credit_policy_path: str


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_settings() -> Settings:
    return Settings(
        version_stamp=os.environ.get("VERSION_STAMP", "financescr@dev"),
        data_root=os.environ.get("DATA_ROOT", "/data"),
        fincrime_policy_path=os.environ.get("FINCRIME_POLICY_PATH", "/data/fincrime/v1/policy.json"),
        credit_policy_path=os.environ.get("CREDIT_POLICY_PATH", "/data/credit/v1/policy.json"),
    )


def validate_data_pack() -> dict:
    s = get_settings()
    fincrime_policy = load_json(s.fincrime_policy_path)
    credit_policy = load_json(s.credit_policy_path)

    # minimal sanity checks (fail fast)
    for k in ["retrieval_top_k", "return_top_n", "threshold", "uncertainty_band"]:
        if k not in fincrime_policy:
            raise RuntimeError(f"fincrime policy missing key: {k}")

    for k in ["pd_threshold_approve", "pd_threshold_refer", "affordability"]:
        if k not in credit_policy:
            raise RuntimeError(f"credit policy missing key: {k}")

    return {
        "fincrime_policy_version": "fincrime/v1",
        "credit_policy_version": "credit/v1",
    }