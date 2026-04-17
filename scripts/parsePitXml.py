#!/usr/bin/env python3
"""
parsePitXml.py
──────────────────────────────────────────────────────────────────────────────
Parses a PIT mutations.xml report and produces:
  - reports/mutations.csv    (one row per mutation, all fields)
  - reports/summary.json     (aggregated stats: kill rate, per-mutator counts)

Usage:
    python scripts/parsePitXml.py
    python scripts/parsePitXml.py --mutations Test/jsoup/target/pit-reports/mutations.xml --output reports/
"""

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from utils.paths import DEFAULT_MUTATIONS_XML, resolve_mutations_xml


# ──────────────────────────────────────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────────────────────────────────────

def parse_mutations(xml_path: str) -> list:
    """
    Parse every <mutation> element from PIT's mutations.xml.
    Returns a list of flat dicts ready for CSV output.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    records = []

    for mut in root.findall("mutation"):

        # Helper: safe text extraction
        def txt(tag):
            el = mut.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        killing_raw    = txt("killingTests")
        succeeding_raw = txt("succeedingTests")

        records.append({
            # Attributes on the <mutation> element
            "detected":          mut.get("detected", ""),
            "status":            mut.get("status", ""),
            "numberOfTestsRun":  mut.get("numberOfTestsRun", "0"),

            # Child elements
            "sourceFile":        txt("sourceFile"),
            "mutatedClass":      txt("mutatedClass"),
            "mutatedMethod":     txt("mutatedMethod"),
            "methodDescription": txt("methodDescription"),
            "lineNumber":        txt("lineNumber"),

            # Short mutator name (last segment after the last dot)
            "mutator":           txt("mutator").split(".")[-1],
            "mutatorFull":       txt("mutator"),

            "description":       txt("description"),

            # Count killing / succeeding tests (pipe-separated in the XML)
            "killingTestCount":  len(killing_raw.split("|")) if killing_raw else 0,
            "killingTests":      killing_raw,
            "succeedingTestCount": len(succeeding_raw.split("|")) if succeeding_raw else 0,
        })

    return records


# ──────────────────────────────────────────────────────────────────────────────
# Output writers
# ──────────────────────────────────────────────────────────────────────────────

def write_csv(records: list, out_path: str) -> None:
    """Write all mutation records to a CSV file."""
    if not records:
        print("  [WARN] No records to write.")
        return

    fields = list(records[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def write_summary(records: list, out_path: str) -> None:
    """Compute and write aggregated stats to JSON, and print to console."""
    total   = len(records)
    if total == 0:
        print("  [WARN] No mutations found.")
        return

    statuses = Counter(r["status"] for r in records)
    mutators = Counter(r["mutator"] for r in records)
    files    = Counter(r["sourceFile"] for r in records)
    methods  = Counter(r["mutatedMethod"] for r in records)

    killed   = statuses.get("KILLED",      0)
    survived = statuses.get("SURVIVED",    0)
    no_cov   = statuses.get("NO_COVERAGE", 0)
    run_err  = statuses.get("RUN_ERROR",   0)
    timed    = statuses.get("TIMED_OUT",   0)
    non_via  = statuses.get("NON_VIABLE",  0)
    covered  = total - no_cov - non_via

    mutation_score = round(killed / covered  * 100, 2) if covered  > 0 else 0.0
    kill_rate      = round(killed / total    * 100, 2) if total    > 0 else 0.0

    summary = {
        "total_mutations":   total,
        "statuses":          dict(statuses.most_common()),
        "mutation_score_pct": mutation_score,   # killed / covered  (standard)
        "kill_rate_pct":     kill_rate,          # killed / total
        "top_mutators":      dict(mutators.most_common(15)),
        "top_files":         dict(files.most_common(15)),
        "top_methods":       dict(methods.most_common(10)),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Pretty console print
    bar = "═" * 56
    print(f"\n{bar}")
    print(f"  PIT Mutation Report Summary")
    print(bar)
    print(f"  Total mutations    : {total:>6}")
    print(f"  Killed             : {killed:>6}  ({kill_rate:.1f}%)")
    print(f"  Survived           : {survived:>6}")
    print(f"  No coverage        : {no_cov:>6}")
    print(f"  Run errors         : {run_err:>6}   ← fix surefire config if > 0")
    print(f"  Timed out          : {timed:>6}")
    print(f"  Non viable         : {non_via:>6}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Mutation score     : {mutation_score:.1f}%  (killed / covered)")
    print(f"{bar}\n")

    print("Top mutator types:")
    for name, count in mutators.most_common(10):
        bar_width = int(count / total * 40)
        print(f"  {name:<45} {count:>5}  {'█' * bar_width}")

    print("\nTop mutated files:")
    for name, count in files.most_common(10):
        print(f"  {name:<40} {count:>5}")

    print()


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Parse a PIT mutations.xml report into CSV + JSON summary."
    )
    parser.add_argument(
        "--mutations",
        default=str(DEFAULT_MUTATIONS_XML),
        help="Path to PIT mutations.xml or project root (default: Test/jsoup/target/pit-reports/mutations.xml)",
    )
    parser.add_argument(
        "--output",
        default="reports",
        help="Output directory for CSV and JSON  (default: reports/)",
    )
    args = parser.parse_args()

    Path(args.output).mkdir(parents=True, exist_ok=True)

    mutations_xml = resolve_mutations_xml(args.mutations)

    print(f"Parsing {mutations_xml} ...")
    records = parse_mutations(str(mutations_xml))
    print(f"Found {len(records)} mutation records.")

    csv_path     = str(Path(args.output) / "mutations.csv")
    summary_path = str(Path(args.output) / "summary.json")

    write_csv(records, csv_path)
    write_summary(records, summary_path)

    print(f"CSV     → {csv_path}")
    print(f"Summary → {summary_path}")


if __name__ == "__main__":
    main()
