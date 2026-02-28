import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_data_v2.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class GenerateDataV2Tests(unittest.TestCase):
    def _run_generator(
        self,
        out_root: Path,
        *,
        version: str,
        seed: int = 42,
        n_customers: int = 60,
        n_watchlist: int = 60,
        n_credit_apps: int = 60,
        n_fincrime_scenarios: int = 40,
        credit_raw_fields_rate: float = 0.7,
    ) -> dict:
        cmd = [
            sys.executable,
            str(SCRIPT_PATH),
            "--out_root",
            str(out_root),
            "--version",
            version,
            "--seed",
            str(seed),
            "--n_customers",
            str(n_customers),
            "--n_watchlist",
            str(n_watchlist),
            "--n_credit_apps",
            str(n_credit_apps),
            "--n_fincrime_scenarios",
            str(n_fincrime_scenarios),
            "--credit_raw_fields_rate",
            str(credit_raw_fields_rate),
        ]
        try:
            subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            self.fail(
                "generate_data_v2.py failed\n"
                f"stdout:\n{exc.stdout}\n"
                f"stderr:\n{exc.stderr}"
            )

        return {
            "customers": out_root / "fincrime" / version / "customers.jsonl",
            "watchlist": out_root / "fincrime" / version / "watchlist.jsonl",
            "fincrime_labels": out_root / "fincrime" / version / "labels.jsonl",
            "applications": out_root / "credit" / version / "applications.jsonl",
            "credit_labels": out_root / "credit" / version / "labels.jsonl",
            "fincrime_golden": out_root / "golden" / version / "fincrime_golden.jsonl",
            "credit_golden": out_root / "golden" / version / "credit_golden.jsonl",
        }

    def test_smoke_generates_expected_files_and_row_counts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td)
            n_customers = 60
            n_watchlist = 60
            n_credit_apps = 60
            n_fincrime_scenarios = 40
            paths = self._run_generator(
                out_root,
                version="smoke",
                seed=101,
                n_customers=n_customers,
                n_watchlist=n_watchlist,
                n_credit_apps=n_credit_apps,
                n_fincrime_scenarios=n_fincrime_scenarios,
            )

            for path in paths.values():
                self.assertTrue(path.exists(), f"missing output file: {path}")

            self.assertEqual(_count_lines(paths["customers"]), n_customers)
            self.assertEqual(_count_lines(paths["watchlist"]), n_watchlist)
            self.assertEqual(
                _count_lines(paths["fincrime_labels"]), n_fincrime_scenarios
            )
            self.assertEqual(_count_lines(paths["applications"]), n_credit_apps)
            self.assertEqual(_count_lines(paths["credit_labels"]), n_credit_apps)
            self.assertEqual(_count_lines(paths["fincrime_golden"]), 30)
            self.assertEqual(_count_lines(paths["credit_golden"]), 30)

    def test_same_seed_produces_identical_files(self) -> None:
        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            paths_a = self._run_generator(Path(td1), version="det", seed=42)
            paths_b = self._run_generator(Path(td2), version="det", seed=42)

            self.assertEqual(set(paths_a.keys()), set(paths_b.keys()))
            for name in sorted(paths_a):
                self.assertEqual(
                    _sha256(paths_a[name]),
                    _sha256(paths_b[name]),
                    f"output drift detected in {name}",
                )

    def test_credit_derived_features_match_raw_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            paths = self._run_generator(
                Path(td),
                version="raw",
                seed=7,
                credit_raw_fields_rate=1.0,
            )

            with paths["applications"].open("r", encoding="utf-8") as f:
                rows = [json.loads(line) for line in f]

            self.assertGreater(len(rows), 0)
            for row in rows:
                self.assertIn("revolving_balance_gbp", row)
                self.assertIn("revolving_limit_gbp", row)
                self.assertIn("balance_mean_gbp", row)
                self.assertIn("balance_std_gbp", row)
                self.assertIn("days_overdraft_90d", row)

                util = float(row["credit_utilisation"])
                vol = float(row["bank_balance_volatility"])
                self.assertGreaterEqual(util, 0.0)
                self.assertLessEqual(util, 1.0)
                self.assertGreaterEqual(vol, 0.0)
                self.assertLessEqual(vol, 1.0)

                expected_util = round(
                    _clamp(
                        float(row["revolving_balance_gbp"])
                        / max(float(row["revolving_limit_gbp"]), 1.0),
                        0.0,
                        1.0,
                    ),
                    4,
                )
                expected_vol = round(
                    _clamp(
                        float(row["balance_std_gbp"])
                        / max(float(row["balance_mean_gbp"]), 1.0),
                        0.0,
                        1.0,
                    ),
                    4,
                )

                # Raw fields are rounded to 2dp in output, while derived fields are rounded
                # from higher-precision internals, so allow a tight tolerance.
                self.assertAlmostEqual(util, expected_util, delta=5e-4)
                self.assertAlmostEqual(vol, expected_vol, delta=5e-4)


if __name__ == "__main__":
    unittest.main()
