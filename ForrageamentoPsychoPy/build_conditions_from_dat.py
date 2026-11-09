"""
Rebuild conditions/conditions_exp1.csv from Experiment Builder .dat export.
Run from this folder: python build_conditions_from_dat.py [path/to/SEQUENCE.dat]
"""
import csv
import os
import re
import sys

_DEFAULT_DAT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "VíctorCorreard",
    "ForrageamentoVisualExp1_1",
    "datasets",
    "SEQUENCE_DataSource_ForrageamentoVisualExp1_1_SEQUENCE_1nSEQUENCE.dat",
)


def main():
    path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_DAT)
    if not os.path.isfile(path):
        print("File not found:", path, file=sys.stderr)
        return 1
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # skip header lines starting with $ or type row
    data_lines = [
        ln
        for ln in lines[2:]
        if ln.strip() and not ln.strip().startswith("string")
    ]
    for ln in data_lines:
        parts = re.split(r"\t", ln.strip())
        if len(parts) < 6:
            continue
        trial = parts[0].strip('"')
        correctkey = parts[1].strip('"')
        drift = parts[2].strip('"')
        fe = parts[3].strip('"')
        fd = parts[4].strip('"')
        alvos = parts[5].strip('"')
        rows.append(
            {
                "trial": trial,
                "correctkey": correctkey,
                "drift_stimuli": drift,
                "fundoesquerda": fe,
                "fundodireita": fd,
                "alvos": alvos,
            }
        )
    out = os.path.join(os.path.dirname(__file__), "conditions", "conditions_exp1.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "trial",
                "correctkey",
                "drift_stimuli",
                "fundoesquerda",
                "fundodireita",
                "alvos",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    print("Wrote", out, "rows", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
