"""Rebuild all Blog 3 tables, figures, checks, and article from the local extract."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(*args):
    print("Running:", " ".join(map(str, args)), flush=True)
    subprocess.run([PY, *map(str, args)], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--website-root", type=Path, help="Optional local Quarto website, e.g. ../myrepo1")
    args = parser.parse_args()
    data = ROOT / "data/raw/cps_00001.csv.gz"
    ddi = ROOT / "data/metadata/cps_00001.xml"
    if not data.exists() or not ddi.exists():
        raise SystemExit("Place the matching authenticated IPUMS CSV.GZ and DDI XML at the paths in README.md.")
    (ROOT / "results").mkdir(exist_ok=True)
    run(ROOT / "code/analyze_asec.py", data, "--out", ROOT / "results")
    run(ROOT / "code/audit_results.py")
    run(ROOT / "code/plot_results.py")
    run(ROOT / "code/verify_results.py")
    post_args = [ROOT / "code/build_post.py"]
    if args.website_root:
        post_args += ["--website-root", args.website_root.resolve()]
    run(*post_args)
    source_rows = []
    for path, url in [
        (data, "https://cps.ipums.org/cps-action/data_requests/download"),
        (ddi, "https://cps.ipums.org/cps-action/data_requests/download"),
        (ROOT / "data/metadata/cps_1992-2002-occ2010-xwalk.xlsx",
         "https://cps.ipums.org/cps/resources/occupation_and_industry/occ2010/cps_1992-2002-occ2010-xwalk.xlsx"),
    ]:
        source_rows.append({"path": str(path.relative_to(ROOT)), "source_url": url,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    with (ROOT / "results/source_log.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "source_url", "sha256", "bytes"])
        writer.writeheader()
        writer.writerows(source_rows)
    os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache" / "mplconfig")
    (ROOT / ".cache" / "mplconfig").mkdir(parents=True, exist_ok=True)
    import pandas, numpy, matplotlib
    (ROOT / "results/session_info.txt").write_text(
        f"Python {platform.python_version()}\npandas {pandas.__version__}\n"
        f"numpy {numpy.__version__}\nmatplotlib {matplotlib.__version__}\n")
    files = [x for x in (ROOT / "results").rglob("*") if x.is_file() and x.name != "output_manifest.json"]
    files.append(ROOT / "blog_post.qmd")
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    (ROOT / "results/output_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Finished: {len(manifest)} generated outputs recorded in results/output_manifest.json")


if __name__ == "__main__":
    main()
