#!/usr/bin/env python3
# Sweep VECTOR_WIDTH, rebuild, run vrun, record utilization, and plot.
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
INTRIN_PATH = SCRIPT_DIR / 'CMU418intrin.h'
MAKE_DIR = SCRIPT_DIR
VRUN_PATH = SCRIPT_DIR / 'vrun'
WIDTH_PATTERN = re.compile(r'(^\s*#define\s+VECTOR_WIDTH\s+)(\d+)', re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Sweep VECTOR_WIDTH values, rebuild, run ./vrun -s <N>, record utilization, and plot results.',
    )
    parser.add_argument('--min-width', type=int, default=2, help='Smallest VECTOR_WIDTH to test (inclusive).')
    parser.add_argument('--max-width', type=int, default=32, help='Largest VECTOR_WIDTH to test (inclusive).')
    parser.add_argument('--step', type=int, default=2, help='Increment applied to VECTOR_WIDTH between runs.')
    parser.add_argument('--samples', '-s', type=int, default=10000, help='Sample count passed to ./vrun (-s argument).')
    parser.add_argument('--csv', type=Path, default=SCRIPT_DIR / 'vector_utilization_results.csv', help='CSV output path.')
    parser.add_argument('--plot', type=Path, default=SCRIPT_DIR / 'vector_utilization.png', help='Plot output path.')
    parser.add_argument('--skip-plot', action='store_true', help='Skip matplotlib plot generation (CSV is still produced).')
    parser.add_argument('--make-jobs', '-j', type=int, default=None, help='Optional -j value forwarded to make.')
    parser.add_argument('--keep-width', action='store_true', help='Keep the last tested VECTOR_WIDTH instead of restoring the original header.')
    parser.add_argument('--verbose', action='store_true', help='Show vrun stdout for each run.')
    args = parser.parse_args()

    if args.min_width < 1 or args.max_width < 1:
        parser.error('VECTOR_WIDTH must be positive.')
    if args.step < 1:
        parser.error('Step must be positive.')
    if args.min_width > args.max_width:
        parser.error('min-width must be <= max-width.')
    return args


def set_vector_width(value: int) -> None:
    text = INTRIN_PATH.read_text()
    new_text, count = WIDTH_PATTERN.subn(lambda match: f"{match.group(1)}{value}", text, count=1)
    if count != 1:
        raise RuntimeError(f'Failed to update VECTOR_WIDTH in {INTRIN_PATH}')
    INTRIN_PATH.write_text(new_text)


def run_make(args: argparse.Namespace) -> None:
    cmd = ['make']
    if args.make_jobs:
        cmd.append(f'-j{args.make_jobs}')
    subprocess.run(cmd, cwd=MAKE_DIR, check=True)


def run_vrun(sample_count: int) -> str:
    if not VRUN_PATH.exists():
        raise FileNotFoundError(f'{VRUN_PATH} does not exist. Build vrun first.')
    result = subprocess.run(
        [str(VRUN_PATH), '-s', str(sample_count)],
        cwd=MAKE_DIR,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise RuntimeError(f'vrun exited with code {result.returncode}')
    return result.stdout


def extract_utilization(run_output: str) -> float:
    match = re.search(r'Vector Utilization:\s*([0-9.]+)%', run_output)
    if not match:
        raise RuntimeError('Could not find vector utilization in vrun output.')
    return float(match.group(1))


def save_csv(results, csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open('w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['vector_width', 'vector_utilization_percent'])
        writer.writerows(results)


def save_plot(results, plot_path: Path, sample_count: int) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - matplotlib availability is environment-specific
        raise RuntimeError(
            'matplotlib is required for plotting. Install it or pass --skip-plot to disable plotting.'
        ) from exc

    plt.rcParams.update({
        "font.family": "serif",         
        "font.size": 10,                 
        "axes.labelsize": 11,            
        "axes.titlesize": 11,           
        "xtick.labelsize": 9,            
        "ytick.labelsize": 9,            
        "legend.fontsize": 9,           
    })

    plot_path.parent.mkdir(parents=True, exist_ok=True)
    widths = [item[0] for item in results]
    utils = [item[1] for item in results]

    fig, ax = plt.subplots(figsize=(3.5, 2.6))

    ax.plot(
        widths,
        utils,
        marker='o',
        linestyle='-',
        linewidth=1.5,
        markersize=4,
    )

    ax.set_xlabel('VECTOR_WIDTH')
    ax.set_ylabel('Vector Utilization (%)')

    ax.set_title(f'Vector Utilization vs. VECTOR_WIDTH (samples={sample_count})')

    ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.4)

    for spine in ax.spines.values():
        spine.set_linewidth(0.8)

    fig.tight_layout()
    fig.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def main() -> None:
    args = parse_args()
    original_text = INTRIN_PATH.read_text()
    widths = list(range(args.min_width, args.max_width + 1, args.step))
    results = []

    try:
        for width in widths:
            print(f'\n=== Testing VECTOR_WIDTH = {width} ===')
            set_vector_width(width)
            run_make(args)
            run_output = run_vrun(args.samples)
            if args.verbose:
                sys.stdout.write(run_output)
            utilization = extract_utilization(run_output)
            results.append((width, utilization))
            print(f'Vector utilization @ width {width}: {utilization:.2f}%')
    finally:
        if args.keep_width:
            print('Keeping the last VECTOR_WIDTH change as requested.')
        else:
            INTRIN_PATH.write_text(original_text)
            print('Restored original CMU418intrin.h.')

    save_csv(results, args.csv)
    print(f'Saved CSV results to {args.csv}')

    if not args.skip_plot:
        save_plot(results, args.plot, args.samples)
        print(f'Saved plot to {args.plot}')
    else:
        print('Plot generation skipped per --skip-plot.')

    print('\nSweep complete. Results:')
    for width, utilization in results:
        print(f'  width {width:2d} -> {utilization:6.2f}%')


if __name__ == '__main__':
    main()
