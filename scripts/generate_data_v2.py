#!/usr/bin/env python3
"""
scripts/generate_data_v2.py

Deterministic (seeded) synthetic data generator for Financescr with more realistic credit signals
and large name pools loaded from scripts/names_v1.json.

Outputs (by version):
- fincrime/<version>: customers.jsonl, watchlist.jsonl, labels.jsonl
- credit/<version>: applications.jsonl, labels.jsonl
- golden/<version>: fincrime_golden.jsonl, credit_golden.jsonl

Credit adds optional raw fields:
- revolving_balance_gbp, revolving_limit_gbp
- balance_mean_gbp, balance_std_gbp, days_overdraft_90d

Derived features (when raw fields exist):
- credit_utilisation = clip(revolving_balance / max(revolving_limit, eps), 0, 1)
- bank_balance_volatility = clip(balance_std / max(balance_mean, eps), 0, 1)

No external deps. Output lives OUTSIDE repo (e.g. ~/financescr_data).
"""

import argparse
import hashlib
import json
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SALT_VERSION = "financescr_v2_salt"
EPS = 1.0  # for safe division in derived features


# ----------------------------
# Utilities
# ----------------------------
def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def id_hash(value: str) -> str:
    # NEVER store raw id_number; store only deterministic salted hash
    return "sha256:" + sha256_hex(f"{SALT_VERSION}:{value}")


def write_jsonl(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def rand_date(rng: random.Random, start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=rng.randint(0, delta))


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def pad_id(prefix: str, i: int, width: int = 6) -> str:
    return f"{prefix}_{i:0{width}d}"


def maybe(rng: random.Random, p: float) -> bool:
    return rng.random() < p


def load_name_pools(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"names file not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


# ----------------------------
# Name generation (from pools)
# ----------------------------
def generate_base_name(rng: random.Random, pools: dict, region: str) -> Tuple[str, str, str]:
    """
    region: EU or ASIA

    pools schema (scripts/names_v1.json):
      {
        "EU": {"UK": {"first": [...], "last": [...]}, ...},
        "ASIA": {"AR": {...}, "IN": {...}, "CN": {...}},
        "weights": {"EU": {"UK": 0.30, ...}, "ASIA": {"AR": 0.45, ...}}
      }
    """
    if region == "EU":
        buckets = list(pools["EU"].keys())
        weights = [float(pools["weights"]["EU"].get(b, 0.0)) for b in buckets]
        bucket = rng.choices(buckets, weights=weights, k=1)[0]
        first = rng.choice(pools["EU"][bucket]["first"])
        last = rng.choice(pools["EU"][bucket]["last"])
        extra_pool = pools["EU"][bucket]["first"]
    else:
        buckets = list(pools["ASIA"].keys())
        weights = [float(pools["weights"]["ASIA"].get(b, 0.0)) for b in buckets]
        bucket = rng.choices(buckets, weights=weights, k=1)[0]
        first = rng.choice(pools["ASIA"][bucket]["first"])
        last = rng.choice(pools["ASIA"][bucket]["last"])
        extra_pool = pools["ASIA"][bucket]["first"]

    # occasional middle initial or second given name
    mid = ""
    if maybe(rng, 0.22):
        mid = chr(ord("A") + rng.randint(0, 25))

    if maybe(rng, 0.08):
        extra = rng.choice(extra_pool)
        full = f"{first} {extra} {last}"
    else:
        full = f"{first} {mid + ' ' if mid else ''}{last}".strip()

    return first, last, full


def name_variants(rng: random.Random, full: str) -> List[str]:
    """
    Deterministic-ish noise variants for retrieval/matching realism.
    """
    parts = full.split()
    variants = {full}

    # drop middle initial if present
    if len(parts) == 3 and len(parts[1]) == 1:
        variants.add(f"{parts[0]} {parts[2]}")

    # swap order
    if len(parts) >= 2 and maybe(rng, 0.22):
        variants.add(f"{parts[-1]} {' '.join(parts[:-1])}")

    # remove spaces / double spaces
    if maybe(rng, 0.20):
        variants.add("  ".join(parts))
    if maybe(rng, 0.18):
        variants.add(" ".join(parts).replace(" ", ""))

    # hyphenate given names sometimes
    if len(parts) >= 3 and maybe(rng, 0.10):
        variants.add(f"{parts[0]}-{parts[1]} {parts[2]}")

    # apostrophe variations (Irish)
    if "O'" in full and maybe(rng, 0.40):
        variants.add(full.replace("O'", "O "))
        variants.add(full.replace("O'", "O"))
    if "Mc" in full and maybe(rng, 0.25):
        variants.add(full.replace("Mc", "Mac", 1))

    # lightweight diacritics/ascii-fying (covers some cases)
    replace_map = {
        "Š": "S", "Ž": "Z", "Ł": "L", "ł": "l", "ó": "o", "ń": "n", "ą": "a", "ę": "e",
        "ś": "s", "ć": "c", "ż": "z", "ź": "z",
        "João": "Joao", "José": "Jose",
    }
    if maybe(rng, 0.25):
        v = full
        for k, vv in replace_map.items():
            v = v.replace(k, vv)
        variants.add(v)

    # transliteration-ish variants (light)
    translit_pairs = [
        ("Mohammed", "Muhammad"), ("Muhammad", "Mohammed"), ("Mohammed", "Mohamad"),
        ("Yusuf", "Youssef"), ("Youssef", "Yusuf"),
        ("Ahmed", "Ahmad"), ("Ahmad", "Ahmed"),
        ("Dmitry", "Dmitri"), ("Sergey", "Sergei"), ("Alexei", "Aleksei"), ("Nikolai", "Nicolai"),
        ("Andrei", "Andrey"), ("Vladimir", "Wladimir"),
    ]
    for a, b in translit_pairs:
        if a in full and maybe(rng, 0.40):
            variants.add(full.replace(a, b))

    out = list(variants)
    rng.shuffle(out)
    return out[: max(4, min(12, len(out)))]


# ----------------------------
# Country pools
# ----------------------------
EU_COUNTRIES = ["GB", "IE", "FR", "DE", "ES", "IT", "NL", "BE", "PL", "SE", "NO", "DK", "PT", "CZ", "HU", "LT", "LV", "EE", "RU"]
ASIA_COUNTRIES = ["AE", "SA", "TR", "PK", "IN", "BD", "CN", "HK", "SG", "MY", "ID", "JP", "KR", "QA"]


# ----------------------------
# Data records
# ----------------------------
@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    dob: Optional[str]
    nationality: Optional[str]
    residence_country: Optional[str]
    id_hash: Optional[str]
    region: str


# ----------------------------
# Generators
# ----------------------------
def gen_customers(rng: random.Random, pools: dict, n: int, dob_present: float = 0.95) -> List[Customer]:
    customers: List[Customer] = []
    for i in range(1, n + 1):
        region = "EU" if rng.random() < 0.55 else "ASIA"
        _, _, full = generate_base_name(rng, pools, region)

        dob = None
        if maybe(rng, dob_present):
            d = rand_date(rng, date(1955, 1, 1), date(2005, 12, 31))
            dob = d.isoformat()

        if region == "EU":
            nationality = rng.choice(EU_COUNTRIES)
            residence = rng.choice(EU_COUNTRIES)
        else:
            nationality = rng.choice(ASIA_COUNTRIES)
            residence = rng.choice(EU_COUNTRIES + ASIA_COUNTRIES)

        idh = None
        if maybe(rng, 0.35):
            id_number = f"P{rng.randint(1000000, 9999999)}"
            idh = id_hash(id_number)

        customers.append(
            Customer(
                customer_id=pad_id("C", i),
                name=full,
                dob=dob,
                nationality=nationality if maybe(rng, 0.98) else None,
                residence_country=residence if maybe(rng, 0.98) else None,
                id_hash=idh,
                region=region,
            )
        )
    return customers


def gen_watchlist(
    rng: random.Random,
    pools: dict,
    n: int,
    customers: List[Customer],
    dob_present: float = 0.60,
) -> Tuple[List[dict], Dict[str, str]]:
    """
    Returns:
      - watchlist entities list
      - mapping of customer_id -> entity_id for linked "true match" subset
    """
    entities: List[dict] = []
    link_map: Dict[str, str] = {}

    def sample_list_type() -> str:
        x = rng.random()
        if x < 0.10:
            return "SANCTIONS"
        if x < 0.40:
            return "PEP"
        return "ADVERSE_MEDIA"

    # ~25% of watchlist entities are derived from customers (true-match linkage)
    n_link = int(0.25 * min(len(customers), n))
    linked_customers = rng.sample(customers, k=n_link)

    idx = 1
    for c in linked_customers:
        entity_id = pad_id("WL", idx)
        idx += 1
        link_map[c.customer_id] = entity_id

        aliases = name_variants(rng, c.name)
        primary_name = aliases[0]
        alias_list = aliases[1:]

        dob_list: List[str] = []
        if c.dob and maybe(rng, dob_present):
            dob_list = [c.dob]

        nationalities = [c.nationality] if c.nationality and maybe(rng, 0.9) else []
        residences = [c.residence_country] if c.residence_country and maybe(rng, 0.8) else []
        id_hashes = [c.id_hash] if c.id_hash and maybe(rng, 0.7) else []

        entities.append(
            {
                "entity_id": entity_id,
                "list_type": sample_list_type(),
                "primary_name": primary_name,
                "aliases": alias_list,
                "dob": dob_list,
                "nationalities": nationalities,
                "residence_countries": residences,
                "id_hashes": id_hashes,
                "source": rng.choice(["OFAC", "EU", "UN", "HMT", "DEMO"]),
                "active": True,
            }
        )

    while len(entities) < n:
        region = "EU" if rng.random() < 0.45 else "ASIA"
        _, _, full = generate_base_name(rng, pools, region)

        aliases = name_variants(rng, full)
        primary_name = aliases[0]
        alias_list = aliases[1:]

        dob_list: List[str] = []
        if maybe(rng, dob_present):
            d = rand_date(rng, date(1950, 1, 1), date(2006, 12, 31))
            dob_list = [d.isoformat()]

        nationalities = [rng.choice(EU_COUNTRIES if region == "EU" else ASIA_COUNTRIES)] if maybe(rng, 0.75) else []
        residences = [rng.choice(EU_COUNTRIES + ASIA_COUNTRIES)] if maybe(rng, 0.60) else []

        id_hashes: List[str] = []
        if maybe(rng, 0.10):
            id_hashes = [id_hash(f"P{rng.randint(1000000, 9999999)}")]

        entities.append(
            {
                "entity_id": pad_id("WL", len(entities) + 1),
                "list_type": sample_list_type(),
                "primary_name": primary_name,
                "aliases": alias_list,
                "dob": dob_list,
                "nationalities": nationalities,
                "residence_countries": residences,
                "id_hashes": id_hashes,
                "source": rng.choice(["OFAC", "EU", "UN", "HMT", "DEMO"]),
                "active": True,
            }
        )

    return entities, link_map


def gen_fincrime_labels(
    rng: random.Random,
    customers: List[Customer],
    link_map: Dict[str, str],
    n_scenarios: int = 1000,
) -> List[dict]:
    labels: List[dict] = []
    linked_ids = list(link_map.keys())

    for i in range(1, n_scenarios + 1):
        scenario_id = pad_id("SCN", i)
        is_match = rng.random() < 0.45

        if is_match and linked_ids:
            cid = rng.choice(linked_ids)
            labels.append(
                {
                    "scenario_id": scenario_id,
                    "customer_id": cid,
                    "label": "MATCH",
                    "true_entity_id": link_map[cid],
                    "notes": "synthetic_match",
                }
            )
        else:
            cid = rng.choice(customers).customer_id
            labels.append(
                {
                    "scenario_id": scenario_id,
                    "customer_id": cid,
                    "label": "NO_MATCH",
                    "true_entity_id": None,
                    "notes": "synthetic_no_match",
                }
            )
    return labels


def derive_credit_utilisation(revolving_balance: float, revolving_limit: float) -> float:
    return clamp(revolving_balance / max(revolving_limit, EPS), 0.0, 1.0)


def derive_balance_volatility(balance_mean: float, balance_std: float) -> float:
    return clamp(balance_std / max(balance_mean, EPS), 0.0, 1.0)


def gen_credit_applications(
    rng: random.Random,
    customers: List[Customer],
    n: int,
    raw_fields_rate: float = 0.70,
) -> List[dict]:
    """
    raw_fields_rate: probability that an application includes raw balance/limit/stat fields
                     so derived utilisation/volatility can be recomputed deterministically.
    """
    apps: List[dict] = []
    chosen = customers if len(customers) >= n else (customers * (n // len(customers) + 1))

    for i in range(1, n + 1):
        c = chosen[i - 1]

        # income by region distribution
        if c.region == "EU":
            income = clamp(rng.gauss(2800, 900), 900, 9000)
        else:
            income = clamp(rng.gauss(2200, 1100), 600, 9000)

        outgoings_ratio = clamp(rng.gauss(0.55, 0.18), 0.15, 0.90)
        outgoings = income * outgoings_ratio

        employment_status = rng.choices(
            ["EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED"], weights=[0.72, 0.18, 0.10]
        )[0]
        employment_months = int(clamp(rng.gauss(24 if employment_status != "UNEMPLOYED" else 4, 18), 0, 240))

        missed = rng.choices([0, 1, 2, 3], weights=[0.78, 0.14, 0.06, 0.02])[0]
        amount = clamp(rng.gauss(3500, 2500), 300, 15000)
        term = rng.choice([12, 18, 24, 36, 48])

        include_raw = maybe(rng, raw_fields_rate)

        if include_raw:
            # revolving limit scales with income
            revolving_limit = clamp(rng.gauss(income * 2.2, income * 1.2), 300, 20000)
            util = clamp(rng.betavariate(2.0, 3.5), 0.0, 1.0)
            revolving_balance = clamp(revolving_limit * util, 0.0, revolving_limit)

            surplus = income - outgoings
            balance_mean = clamp(rng.gauss(max(surplus, 50) * 2.5, max(surplus, 50) * 1.5), 0.0, 30000.0)

            base_vol = clamp(rng.betavariate(2.0, 4.0), 0.0, 1.0)
            if employment_status == "UNEMPLOYED":
                base_vol = clamp(base_vol + 0.20, 0.0, 1.0)
            if missed >= 2:
                base_vol = clamp(base_vol + 0.15, 0.0, 1.0)

            balance_std = clamp(balance_mean * base_vol, 0.0, max(balance_mean, 1.0))

            od_base = 0
            if surplus < 200:
                od_base += rng.randint(0, 12)
            if missed > 0:
                od_base += rng.randint(0, 8)
            if employment_status == "UNEMPLOYED":
                od_base += rng.randint(0, 10)
            days_overdraft_90d = int(clamp(od_base, 0, 90))

            credit_utilisation = round(derive_credit_utilisation(revolving_balance, revolving_limit), 4)
            bank_balance_volatility = round(derive_balance_volatility(balance_mean, balance_std), 4)
        else:
            # fallback proxies (always present)
            revolving_limit = None
            revolving_balance = None
            balance_mean = None
            balance_std = None
            days_overdraft_90d = None
            credit_utilisation = round(clamp(rng.betavariate(2.0, 3.5), 0.0, 1.0), 4)
            bank_balance_volatility = round(clamp(rng.betavariate(2.0, 4.0), 0.0, 1.0), 4)

        app = {
            "application_id": pad_id("A", i),
            "customer_id": c.customer_id,
            "product": "PERSONAL_LOAN",
            "amount_gbp": round(amount, 2),
            "term_months": int(term),
            "income_monthly_gbp": round(income, 2),
            "outgoings_monthly_gbp": round(outgoings, 2),
            "employment_status": employment_status,
            "employment_months": employment_months,
            "credit_utilisation": credit_utilisation,
            "missed_payments_12m": int(missed),
            "bank_balance_volatility": bank_balance_volatility,
        }

        if include_raw:
            app.update(
                {
                    "revolving_balance_gbp": round(float(revolving_balance), 2),
                    "revolving_limit_gbp": round(float(revolving_limit), 2),
                    "balance_mean_gbp": round(float(balance_mean), 2),
                    "balance_std_gbp": round(float(balance_std), 2),
                    "days_overdraft_90d": int(days_overdraft_90d),
                }
            )

        apps.append(app)

    return apps


def gen_credit_labels(rng: random.Random, apps: List[dict]) -> List[dict]:
    """
    Generate default labels correlated with risk drivers.
    """
    labels: List[dict] = []
    for a in apps:
        income = float(a["income_monthly_gbp"])
        outgoings = float(a["outgoings_monthly_gbp"])
        util = float(a["credit_utilisation"])
        missed = int(a["missed_payments_12m"])
        vol = float(a["bank_balance_volatility"])
        amount = float(a["amount_gbp"])
        term = int(a["term_months"])
        emp_status = a["employment_status"]
        emp_months = int(a["employment_months"])

        surplus = income - outgoings
        amount_to_income = amount / max(income, 1.0)

        z = -2.2
        z += 1.3 * util
        z += 0.9 * vol
        z += 0.45 * amount_to_income
        z += 0.25 * (term / 48.0)
        z += 0.55 * (missed > 0)
        z += 0.75 * (missed >= 2)
        z += -0.0006 * surplus
        z += -0.10 * math.log(max(emp_months + 1, 1))
        if emp_status == "UNEMPLOYED":
            z += 0.8
        elif emp_status == "SELF_EMPLOYED":
            z += 0.2

        if "days_overdraft_90d" in a and a["days_overdraft_90d"] is not None:
            z += 0.015 * min(int(a["days_overdraft_90d"]), 30) / 30.0

        pd = clamp(sigmoid(z), 0.01, 0.60)
        default = 1 if rng.random() < pd else 0
        labels.append({"application_id": a["application_id"], "pd_12m": round(pd, 4), "default_12m": int(default)})
    return labels


def gen_golden_fincrime(customers: List[Customer], link_map: Dict[str, str]) -> List[dict]:
    golden: List[dict] = []
    linked = sorted(link_map.items())[:12]
    for i, (cid, eid) in enumerate(linked, start=1):
        golden.append(
            {"scenario_id": f"GSCN_{i:03d}", "customer_id": cid, "label": "MATCH", "true_entity_id": eid, "notes": "golden_match"}
        )
    for j in range(1, 19):
        cid = customers[j].customer_id
        golden.append(
            {"scenario_id": f"GSCN_{(len(golden)+1):03d}", "customer_id": cid, "label": "NO_MATCH", "true_entity_id": None, "notes": "golden_no_match_common_name"}
        )
    return golden[:30]


def gen_golden_credit(apps: List[dict], labels: List[dict]) -> List[dict]:
    by_app = {l["application_id"]: l for l in labels}
    scored = [(aid, by_app[aid]["pd_12m"]) for aid in by_app]
    scored.sort(key=lambda x: x[1])

    picks: List[str] = []
    picks += [aid for aid, _ in scored[:10]]
    picks += [aid for aid, _ in scored[len(scored) // 2 - 5: len(scored) // 2 + 5]]
    picks += [aid for aid, _ in scored[-10:]]

    golden = []
    for i, aid in enumerate(picks[:30], start=1):
        golden.append({"golden_id": f"GCRED_{i:03d}", "application_id": aid, "notes": "golden_credit_regression"})
    return golden


# ----------------------------
# Main
# ----------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_root", default=str(Path.home() / "financescr_data"), help="Output root (host path)")
    ap.add_argument("--version", default="v2", help="data pack version folder label (e.g. v1, v2)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n_customers", type=int, default=3000)
    ap.add_argument("--n_watchlist", type=int, default=3000)
    ap.add_argument("--n_credit_apps", type=int, default=3000)
    ap.add_argument("--n_fincrime_scenarios", type=int, default=1000)
    ap.add_argument("--customers_dob_present", type=float, default=0.95)
    ap.add_argument("--watchlist_dob_present", type=float, default=0.60)
    ap.add_argument("--credit_raw_fields_rate", type=float, default=0.70)
    ap.add_argument("--names_path", default=str(Path(__file__).resolve().parent / "names_v1.json"), help="Path to name pools JSON")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out_root = Path(args.out_root)
    pools = load_name_pools(args.names_path)

    fincrime_dir = out_root / "fincrime" / args.version
    credit_dir = out_root / "credit" / args.version
    golden_dir = out_root / "golden" / args.version

    customers = gen_customers(rng, pools, args.n_customers, dob_present=args.customers_dob_present)
    customers_rows = [
        {
            "customer_id": c.customer_id,
            "name": c.name,
            "dob": c.dob,
            "nationality": c.nationality,
            "residence_country": c.residence_country,
            "id_hash": c.id_hash,
            "region": c.region,
        }
        for c in customers
    ]
    write_jsonl(fincrime_dir / "customers.jsonl", customers_rows)

    watchlist_rows, link_map = gen_watchlist(rng, pools, args.n_watchlist, customers, dob_present=args.watchlist_dob_present)
    write_jsonl(fincrime_dir / "watchlist.jsonl", watchlist_rows)

    fincrime_labels = gen_fincrime_labels(rng, customers, link_map, n_scenarios=args.n_fincrime_scenarios)
    write_jsonl(fincrime_dir / "labels.jsonl", fincrime_labels)

    apps = gen_credit_applications(rng, customers, args.n_credit_apps, raw_fields_rate=args.credit_raw_fields_rate)
    write_jsonl(credit_dir / "applications.jsonl", apps)

    credit_labels = gen_credit_labels(rng, apps)
    write_jsonl(credit_dir / "labels.jsonl", credit_labels)

    write_jsonl(golden_dir / "fincrime_golden.jsonl", gen_golden_fincrime(customers, link_map))
    write_jsonl(golden_dir / "credit_golden.jsonl", gen_golden_credit(apps, credit_labels))

    print("Generated:")
    print(f"  {fincrime_dir}/customers.jsonl ({len(customers_rows)})")
    print(f"  {fincrime_dir}/watchlist.jsonl ({len(watchlist_rows)})")
    print(f"  {fincrime_dir}/labels.jsonl ({len(fincrime_labels)})")
    print(f"  {credit_dir}/applications.jsonl ({len(apps)})")
    print(f"  {credit_dir}/labels.jsonl ({len(credit_labels)})")
    print(f"  {golden_dir}/fincrime_golden.jsonl (~30)")
    print(f"  {golden_dir}/credit_golden.jsonl (~30)")


if __name__ == "__main__":
    main()