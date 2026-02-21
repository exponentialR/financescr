#!/usr/bin/env python3
"""
scripts/generate_data_v1.py

Deterministic (seeded) synthetic data generator for Financescr:
- fincrime/v1: customers.jsonl, watchlist.jsonl, labels.jsonl
- credit/v1: applications.jsonl, labels.jsonl
- golden/v1: fincrime_golden.jsonl, credit_golden.jsonl

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

SALT_VERSION = "financescr_v1_salt"


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


# ----------------------------
# Synthetic name pools (expanded)
# ----------------------------

# Irish / UK
IRISH_FIRST = ["Sean", "Saoirse", "Niamh", "Ciaran", "Aidan", "Eoin", "Aoife", "Siobhan", "Conor", "Fiona"]
IRISH_LAST = ["O'Neill", "Murphy", "Kelly", "O'Brien", "Walsh", "Byrne", "Ryan", "O'Connor", "Doyle", "McCarthy"]

UK_FIRST = [
    "John", "James", "Michael", "David", "Robert", "Daniel", "Thomas", "Paul",
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Susan", "Jessica", "Sarah",
    "Emma", "Olivia", "Sophia", "Emily", "Charlotte", "Amelia",
]
UK_LAST = ["Smith", "Jones", "Taylor", "Brown", "Williams", "Davies", "Evans", "Wilson", "Johnson", "Walker"]

# French
FR_FIRST = ["Jean", "Pierre", "Louis", "Antoine", "Luc", "Hugo", "Camille", "Marie", "Sophie", "Chloe", "Nicolas", "Julien"]
FR_LAST = ["Dubois", "Moreau", "Lefevre", "Bernard", "Petit", "Roux", "Fournier", "Girard", "Lambert", "Leroy"]

# Spanish
ES_FIRST = ["Jose", "Juan", "Carlos", "Miguel", "Luis", "Javier", "Antonio", "Maria", "Carmen", "Laura", "Sofia", "Lucia"]
ES_LAST = ["Garcia", "Fernandez", "Gonzalez", "Rodriguez", "Lopez", "Martinez", "Sanchez", "Perez", "Gomez", "Diaz"]

# Portuguese
PT_FIRST = ["Joao", "Pedro", "Tiago", "Andre", "Rui", "Miguel", "Ana", "Beatriz", "Mariana", "Ines", "Sofia"]
PT_LAST = ["Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa", "Rodrigues", "Martins", "Almeida", "Gomes"]

# Polish
PL_FIRST = ["Jan", "Piotr", "Pawel", "Krzysztof", "Michal", "Tomasz", "Anna", "Katarzyna", "Agnieszka", "Magdalena", "Zofia"]
PL_LAST = ["Nowak", "Kowalski", "Wojcik", "Kaczmarek", "Zielinski", "Szymanski", "Dabrowski", "Kozlowski", "Jankowski", "Mazur"]

# Baltic
BALTIC_FIRST = ["Marius", "Tomas", "Jonas", "Lukas", "Aiste", "Ruta", "Egle", "Katrin", "Maarja", "Kristjan"]
BALTIC_LAST = ["Kazlauskas", "Jankauskas", "Petrauskas", "Vaitkus", "Ozols", "Berzins", "Kalnins", "Tamm", "Saar", "Kask"]

# Russian (Latin transliterations)
RU_FIRST = ["Ivan", "Dmitry", "Sergey", "Alexei", "Nikolai", "Andrei", "Vladimir", "Olga", "Natalia", "Irina", "Tatiana", "Anna"]
RU_LAST = ["Ivanov", "Petrov", "Sidorov", "Smirnov", "Volkov", "Sokolov", "Popov", "Morozov", "Kuznetsov", "Novikov"]

# Asia / Middle East / South Asia / East Asia
AR_FIRST = [
    "Mohammed", "Muhammad", "Ahmed", "Ali", "Hassan", "Omar", "Yusuf", "Khalid", "Abdullah", "Ibrahim",
    "Aisha", "Fatima", "Zainab", "Sana", "Mariam",
]
AR_LAST = ["Khan", "Hussain", "Abdullah", "Ibrahim", "Al-Sayed", "Al-Mansouri", "Al-Farsi", "Al-Hassan"]

IN_FIRST = ["Arjun", "Rahul", "Amit", "Sanjay", "Vikram", "Ravi", "Priya", "Ananya", "Neha", "Pooja", "Asha"]
IN_LAST = ["Singh", "Kaur", "Patel", "Sharma", "Gupta", "Mehta", "Iyer", "Nair", "Reddy"]

CN_FIRST = ["Wei", "Ming", "Jia", "Li", "Chen", "Xiao", "Hui", "Jun", "Fang", "Mei"]
CN_LAST = ["Zhang", "Wang", "Li", "Chen", "Liu", "Yang", "Huang", "Zhao"]

EU_COUNTRIES = ["GB", "IE", "FR", "DE", "ES", "IT", "NL", "BE", "PL", "SE", "NO", "DK", "PT", "CZ", "HU", "LT", "LV", "EE", "RU"]
ASIA_COUNTRIES = ["AE", "SA", "TR", "PK", "IN", "BD", "CN", "HK", "SG", "MY", "ID", "JP", "KR", "QA"]


def generate_base_name(rng: random.Random, region: str) -> Tuple[str, str, str]:
    """
    region: EU or ASIA, but internally we sample sub-regions for realism.
    """
    if region == "EU":
        bucket = rng.choices(
            ["UK", "IRISH", "FR", "ES", "PT", "PL", "BALTIC", "RU"],
            weights=[0.30, 0.12, 0.14, 0.14, 0.10, 0.10, 0.05, 0.05],
        )[0]
        if bucket == "UK":
            first, last = rng.choice(UK_FIRST), rng.choice(UK_LAST)
        elif bucket == "IRISH":
            first, last = rng.choice(IRISH_FIRST), rng.choice(IRISH_LAST)
        elif bucket == "FR":
            first, last = rng.choice(FR_FIRST), rng.choice(FR_LAST)
        elif bucket == "ES":
            first, last = rng.choice(ES_FIRST), rng.choice(ES_LAST)
        elif bucket == "PT":
            first, last = rng.choice(PT_FIRST), rng.choice(PT_LAST)
        elif bucket == "PL":
            first, last = rng.choice(PL_FIRST), rng.choice(PL_LAST)
        elif bucket == "BALTIC":
            first, last = rng.choice(BALTIC_FIRST), rng.choice(BALTIC_LAST)
        else:
            first, last = rng.choice(RU_FIRST), rng.choice(RU_LAST)
    else:
        bucket = rng.choices(["AR", "IN", "CN"], weights=[0.45, 0.35, 0.20])[0]
        if bucket == "AR":
            first, last = rng.choice(AR_FIRST), rng.choice(AR_LAST)
        elif bucket == "IN":
            first, last = rng.choice(IN_FIRST), rng.choice(IN_LAST)
        else:
            first, last = rng.choice(CN_FIRST), rng.choice(CN_LAST)

    # occasional middle initial or second given name
    mid = ""
    if maybe(rng, 0.22):
        mid = chr(ord("A") + rng.randint(0, 25))

    if maybe(rng, 0.08):
        # second given name (more realistic in EU/LatAm)
        extra = rng.choice(UK_FIRST + FR_FIRST + ES_FIRST + PT_FIRST + PL_FIRST + IRISH_FIRST)
        full = f"{first} {extra} {last}"
    else:
        full = f"{first} {mid + ' ' if mid else ''}{last}".strip()

    return first, last, full


def name_variants(rng: random.Random, full: str) -> List[str]:
    """
    Deterministic-ish noise:
      - remove/extra spaces
      - swap ordering
      - hyphenate given names
      - Irish apostrophe variants
      - ascii-fy diacritics (lightweight)
      - transliteration-ish variants (Arabic/Russian common)
    """
    parts = full.split()
    variants = set()
    variants.add(full)

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

    # apostrophe variations for Irish names
    if "O'" in full and maybe(rng, 0.40):
        variants.add(full.replace("O'", "O "))
        variants.add(full.replace("O'", "O"))
    if "Mc" in full and maybe(rng, 0.25):
        variants.add(full.replace("Mc", "Mac", 1))

    # diacritics/ascii-fying (lightweight)
    replace_map = {
        "Wójcik": "Wojcik",
        "Zieliński": "Zielinski",
        "Dąbrowski": "Dabrowski",
        "Kozłowski": "Kozlowski",
        "Š": "S", "Ž": "Z", "Ł": "L", "ł": "l", "ó": "o", "ń": "n", "ą": "a", "ę": "e",
        "ś": "s", "ć": "c", "ż": "z", "ź": "z",
    }
    if maybe(rng, 0.25):
        v = full
        for k, vv in replace_map.items():
            v = v.replace(k, vv)
        variants.add(v)

    # transliteration-ish variants (Arabic/Russian common)
    translit_pairs = [
        ("Mohammed", "Muhammad"), ("Muhammad", "Mohammed"), ("Mohammed", "Mohamad"),
        ("Yusuf", "Youssef"), ("Youssef", "Yusuf"),
        ("Ahmed", "Ahmad"), ("Ahmad", "Ahmed"),
        ("Dmitry", "Dmitri"), ("Sergey", "Sergei"), ("Alexei", "Aleksei"), ("Nikolai", "Nicolai"),
        ("Andrei", "Andrey"), ("Vladimir", "Wladimir"),
        ("Joao", "João"), ("Jose", "José"),
    ]
    for a, b in translit_pairs:
        if a in full and maybe(rng, 0.40):
            variants.add(full.replace(a, b))

    out = list(variants)
    rng.shuffle(out)
    return out[: max(4, min(12, len(out)))]


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
def gen_customers(rng: random.Random, n: int, dob_present: float = 0.95) -> List[Customer]:
    customers: List[Customer] = []
    for i in range(1, n + 1):
        region = "EU" if rng.random() < 0.55 else "ASIA"
        _, _, full = generate_base_name(rng, region)

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

        # id_number present less often (still realistic)
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

    # distribution: sanctions rarer but high severity
    def sample_list_type() -> str:
        x = rng.random()
        if x < 0.10:
            return "SANCTIONS"
        if x < 0.40:
            return "PEP"
        return "ADVERSE_MEDIA"

    # choose subset of customers to have a corresponding watchlist entity (true matches)
    n_link = int(0.25 * min(len(customers), n))  # ~25% of n are derived from customers
    linked_customers = rng.sample(customers, k=n_link)

    # first, create linked entities
    idx = 1
    for c in linked_customers:
        entity_id = pad_id("WL", idx)
        idx += 1
        link_map[c.customer_id] = entity_id

        aliases = name_variants(rng, c.name)
        primary_name = aliases[0]
        alias_list = [a for a in aliases[1:]]

        dob_list: List[str] = []
        if c.dob and maybe(rng, dob_present):
            dob_list = [c.dob]

        # nationality/residence may be missing
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

    # then, create remaining unrelated entities
    while len(entities) < n:
        region = "EU" if rng.random() < 0.45 else "ASIA"
        _, _, full = generate_base_name(rng, region)
        aliases = name_variants(rng, full)
        primary_name = aliases[0]
        alias_list = [a for a in aliases[1:]]

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
    """
    Scenario labels. We reference customer_id and (if MATCH) true_entity_id.
    """
    labels: List[dict] = []
    linked_ids = list(link_map.keys())

    for i in range(1, n_scenarios + 1):
        scenario_id = pad_id("SCN", i)

        # 45% matches, 55% non-matches
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


def gen_credit_applications(rng: random.Random, customers: List[Customer], n: int) -> List[dict]:
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

        utilisation = clamp(rng.betavariate(2.0, 3.5), 0.0, 1.0)
        missed = rng.choices([0, 1, 2, 3], weights=[0.78, 0.14, 0.06, 0.02])[0]
        volatility = clamp(rng.betavariate(2.0, 4.0), 0.0, 1.0)

        amount = clamp(rng.gauss(3500, 2500), 300, 15000)
        term = rng.choice([12, 18, 24, 36, 48])

        apps.append(
            {
                "application_id": pad_id("A", i),
                "customer_id": c.customer_id,
                "product": "PERSONAL_LOAN",
                "amount_gbp": round(amount, 2),
                "term_months": int(term),
                "income_monthly_gbp": round(income, 2),
                "outgoings_monthly_gbp": round(outgoings, 2),
                "employment_status": employment_status,
                "employment_months": employment_months,
                "credit_utilisation": round(utilisation, 4),
                "missed_payments_12m": int(missed),
                "bank_balance_volatility": round(volatility, 4),
            }
        )
    return apps


def gen_credit_labels(rng: random.Random, apps: List[dict]) -> List[dict]:
    """
    Generate default labels correlated with sensible risk drivers.
    We compute a synthetic PD via logistic function and sample default_12m.
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

        # synthetic risk score
        z = -2.2
        z += 1.3 * util
        z += 0.9 * vol
        z += 0.45 * amount_to_income
        z += 0.25 * (term / 48.0)
        z += 0.55 * (missed > 0)
        z += 0.75 * (missed >= 2)
        z += -0.0006 * surplus  # higher surplus lowers risk
        z += -0.10 * math.log(max(emp_months + 1, 1))
        if emp_status == "UNEMPLOYED":
            z += 0.8
        elif emp_status == "SELF_EMPLOYED":
            z += 0.2

        pd = clamp(sigmoid(z), 0.01, 0.60)
        default = 1 if rng.random() < pd else 0

        labels.append({"application_id": a["application_id"], "pd_12m": round(pd, 4), "default_12m": int(default)})
    return labels


def gen_golden_fincrime(customers: List[Customer], link_map: Dict[str, str]) -> List[dict]:
    """
    A small handcrafted regression set.
    Deterministic selection based on sorted ids.
    """
    golden: List[dict] = []

    linked = sorted(link_map.items())[:12]
    for i, (cid, eid) in enumerate(linked, start=1):
        golden.append(
            {"scenario_id": f"GSCN_{i:03d}", "customer_id": cid, "label": "MATCH", "true_entity_id": eid, "notes": "golden_match"}
        )

    # NO_MATCH scenarios on early customers (common-name collisions will show up naturally)
    for j in range(1, 19):
        cid = customers[j].customer_id
        golden.append(
            {
                "scenario_id": f"GSCN_{(len(golden)+1):03d}",
                "customer_id": cid,
                "label": "NO_MATCH",
                "true_entity_id": None,
                "notes": "golden_no_match_common_name",
            }
        )

    return golden[:30]


def gen_golden_credit(apps: List[dict], labels: List[dict]) -> List[dict]:
    """
    Select 30 apps across risk spectrum for regression.
    """
    by_app = {l["application_id"]: l for l in labels}
    scored = [(aid, by_app[aid]["pd_12m"]) for aid in by_app]
    scored.sort(key=lambda x: x[1])

    picks: List[str] = []
    picks += [aid for aid, _ in scored[:10]]
    picks += [aid for aid, _ in scored[len(scored) // 2 - 5 : len(scored) // 2 + 5]]
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
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n_customers", type=int, default=3000)
    ap.add_argument("--n_watchlist", type=int, default=3000)
    ap.add_argument("--n_credit_apps", type=int, default=3000)
    ap.add_argument("--n_fincrime_scenarios", type=int, default=1000)
    ap.add_argument("--customers_dob_present", type=float, default=0.95)
    ap.add_argument("--watchlist_dob_present", type=float, default=0.60)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out_root = Path(args.out_root)

    fincrime_dir = out_root / "fincrime" / "v1"
    credit_dir = out_root / "credit" / "v1"
    golden_dir = out_root / "golden" / "v1"

    # Customers
    customers = gen_customers(rng, args.n_customers, dob_present=args.customers_dob_present)
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

    # Watchlist
    watchlist_rows, link_map = gen_watchlist(rng, args.n_watchlist, customers, dob_present=args.watchlist_dob_present)
    write_jsonl(fincrime_dir / "watchlist.jsonl", watchlist_rows)

    # Fincrime labels
    fincrime_labels = gen_fincrime_labels(rng, customers, link_map, n_scenarios=args.n_fincrime_scenarios)
    write_jsonl(fincrime_dir / "labels.jsonl", fincrime_labels)

    # Credit applications + labels
    apps = gen_credit_applications(rng, customers, args.n_credit_apps)
    write_jsonl(credit_dir / "applications.jsonl", apps)

    credit_labels = gen_credit_labels(rng, apps)
    write_jsonl(credit_dir / "labels.jsonl", credit_labels)

    # Golden sets
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