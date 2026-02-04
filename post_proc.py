#!/usr/bin/env python3
"""
Batch postprocessing:

1) Recursively collect per-(T,P) results from:
   - GlobalPropsTimeAvg.prop      -> average density (last column)
   - GlobalPropCalculated.prop    -> last line: D[H2O], viscosity

2) Write a plain text table:
   results/results.txt
   Columns: T  P  density  self_diffusion  viscosity

3) Recursively find rdf_all.rdf, compute averaged RDF, and save:
   results/rdf_T_<T>_P_<P>_<n>.png
   results/rdf_average_T_<T>_P_<P>_<n>.dat

4) Make preliminary plots (grouped by pressure) and save:
   results/T_vs_density.png
   results/T_vs_selfdiff.png
   results/T_vs_viscosity.png

Run:
  python postprocess_all.py /path/to/root
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple, Optional, List

import numpy as np
import matplotlib.pyplot as plt


DENSITY_FILE = "GlobalPropsTimeAvg.prop"
CALC_FILE = "GlobalPropCalculated.prop"
RDF_FILE = "rdf_all.rdf"

TP_DIR_RE = re.compile(r"^T_(\d+)_P_(\d+)$")


def find_tp_ancestor(p: Path) -> Optional[Tuple[int, int, Path]]:
    """Walk upward to find nearest ancestor directory named like T_313_P_1."""
    for parent in [p] + list(p.parents):
        if parent.is_dir():
            m = TP_DIR_RE.match(parent.name)
            if m:
                return int(m.group(1)), int(m.group(2)), parent
    return None


def avg_density(path: Path) -> float:
    total = 0.0
    n = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            try:
                dens = float(parts[-1])
            except ValueError:
                continue
            total += dens
            n += 1
    if n == 0:
        raise ValueError("No density data lines found")
    return total / n


def last_diff_visc(path: Path) -> Tuple[float, float]:
    last = None
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                last = s
    if last is None:
        raise ValueError("No data lines found")

    fields: Dict[str, float] = {}
    for item in last.split(","):
        item = item.strip()
        if ":" not in item:
            continue
        key, val = item.split(":", 1)
        fields[key.strip()] = float(val.strip())

    return fields["D[H2O]"], fields["viscosity"]


def process_rdf(rdf_path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    blocks = []
    current = None

    with rdf_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) == 2:
                if current is not None:
                    blocks.append(np.array(current, float))
                current = []
            else:
                current.append([float(x) for x in parts])

    if current is not None:
        blocks.append(np.array(current, float))

    if not blocks:
        raise ValueError("No RDF blocks found")

    r = blocks[0][:, 1]
    g77 = np.mean([b[:, 2] for b in blocks], axis=0)
    g88 = np.mean([b[:, 4] for b in blocks], axis=0)
    g78 = np.mean([b[:, 6] for b in blocks], axis=0)
    return r, g77, g88, g78


def write_results_txt(results_dir: Path, records: Dict[Tuple[int, int], dict]) -> None:
    out = results_dir / "results.txt"
    lines: List[str] = []
    lines.append(f"{'T(K)':>8} {'P(bar)':>8} {'Density':>12} {'SelfDiff':>15} {'Viscosity':>15}")

    for (T, P) in sorted(records.keys()):
        rec = records[(T, P)]
        dens = rec.get("density")
        diff = rec.get("self_diffusion")
        visc = rec.get("viscosity")

        if isinstance(dens, float) and isinstance(diff, float) and isinstance(visc, float):
            lines.append(f"{T:>8} {P:>8} {dens:12.6f} {diff:15.6e} {visc:15.6e}")
        else:
            # if missing/failed, still write something visible
            lines.append(f"{T:>8} {P:>8} {'MISSING':>12} {'':>15} {'':>15}")

    out.write_text("\n".join(lines), encoding="utf-8")


def plot_vs_temperature(results_dir: Path, records: Dict[Tuple[int, int], dict]) -> None:
    # Group by pressure so each pressure becomes a curve
    by_p: Dict[int, List[Tuple[int, float, float, float]]] = defaultdict(list)
    for (T, P), rec in records.items():
        dens = rec.get("density")
        diff = rec.get("self_diffusion")
        visc = rec.get("viscosity")
        if isinstance(dens, float) and isinstance(diff, float) and isinstance(visc, float):
            by_p[P].append((T, dens, diff, visc))

    def save_plot(y_index: int, ylabel: str, fname: str):
        plt.figure()
        for P in sorted(by_p.keys()):
            pts = sorted(by_p[P], key=lambda x: x[0])
            Ts = [t for (t, _, _, _) in pts]
            Ys = [x[y_index] for x in pts]  # 1=dens, 2=diff, 3=visc
            plt.plot(Ts, Ys, marker="o", label=f"P={P} bar")
        plt.xlabel("Temperature (K)")
        plt.ylabel(ylabel)
        plt.legend()
        plt.tight_layout()
        plt.savefig(results_dir / fname, dpi=300)
        plt.close()

    save_plot(1, "Density", "T_vs_density.png")
    save_plot(2, "Self-diffusion (D[H2O])", "T_vs_selfdiff.png")
    save_plot(3, "Viscosity", "T_vs_viscosity.png")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".", help="Root directory to scan (default: .)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    results_dir = root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Collect per-(T,P) simulation properties
    records: Dict[Tuple[int, int], dict] = {}

    dens_paths: Dict[Tuple[int, int], Path] = {}
    calc_paths: Dict[Tuple[int, int], Path] = {}

    for f in root.rglob(DENSITY_FILE):
        tp = find_tp_ancestor(f.parent)
        if tp:
            T, P, _ = tp
            dens_paths.setdefault((T, P), f)

    for f in root.rglob(CALC_FILE):
        tp = find_tp_ancestor(f.parent)
        if tp:
            T, P, _ = tp
            calc_paths.setdefault((T, P), f)

    all_keys = sorted(set(dens_paths) | set(calc_paths), key=lambda k: (k[0], k[1]))
    for key in all_keys:
        T, P = key
        records.setdefault((T, P), {})
        dfile = dens_paths.get((T, P))
        cfile = calc_paths.get((T, P))

        if dfile and cfile:
            try:
                records[(T, P)]["density"] = avg_density(dfile)
                diff, visc = last_diff_visc(cfile)
                records[(T, P)]["self_diffusion"] = diff
                records[(T, P)]["viscosity"] = visc
            except Exception:
                # leave missing if parse fails
                pass

    write_results_txt(results_dir, records)
    plot_vs_temperature(results_dir, records)

    # Process RDFs and save into results/
    rdf_counter: Dict[Tuple[int, int], int] = defaultdict(int)

    for rdf in root.rglob(RDF_FILE):
        tp = find_tp_ancestor(rdf.parent)
        if not tp:
            continue
        T, P, _ = tp
        try:
            r, g77, g88, g78 = process_rdf(rdf)

            rdf_counter[(T, P)] += 1
            idx = rdf_counter[(T, P)]

            # Save plot to results folder
            plt.figure()
            plt.plot(r, g77, label="O-O")
            plt.plot(r, g88, label="H-H")
            plt.plot(r, g78, label="O-H")
            plt.xlabel("r")
            plt.ylabel("g(r)")
            plt.legend()
            plt.tight_layout()
            plt.savefig(results_dir / f"rdf_T_{T}_P_{P}_{idx}.png", dpi=300)
            plt.close()

            # Save averaged data to results folder
            out = np.column_stack([r, g77, g88, g78])
            np.savetxt(
                results_dir / f"rdf_average_T_{T}_P_{P}_{idx}.dat",
                out,
                header="r g77 g88 g78",
            )
        except Exception:
            continue


if __name__ == "__main__":
    main()
