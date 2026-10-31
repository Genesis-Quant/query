"""Opt-in old/new rolling-controls benchmark on 300+ stocks and two full years.

Run with the configured read-only DolphinDB credentials:
    python tests/benchmark_rolling_controls.py --output /tmp/controls-benchmark.json

All data and functions are session-local. Timing excludes source generation, upload,
compilation and result download, but includes grouping, fitting and row restoration.
"""

import argparse
import ast
import hashlib
import json
import platform
import statistics
import time
from pathlib import Path

import numpy as np
import pandas as pd

from query import create_session
from query.database.compile.query.functions.runtime import APPLY_ROLLING_OLS

BASELINE_SCRIPT = r"""
def benchmark_baseline_apply(target, controls, on, code, time, window, min_periods, intercept) {
    n = size(target)
    output = dict(STRING, ANY)
    output["alpha"] = take(double(NULL), n)
    output["residual"] = take(double(NULL), n)
    if (n == 0) return transpose(output)
    mask = take(true, n)
    if (type(on) != VOID) mask = normalize_on(on, n)
    selected = table(long(0 .. (n - 1)) as row_id, string(code) as code, timestamp(time) as time)
    selected = selected[mask]
    for (current_code in distinct(selected.code)) {
        rows = select row_id, time from selected where code = current_code order by time, row_id
        indices = rows.row_id
        coefficients = rolling_controls_regression(
            target[indices], controls[indices], window, min_periods, intercept
        )
        for (name in coefficients.columnNames()) {
            if (!(name in output)) output[name] = take(double(NULL), n)
            values = output[name]
            values[indices] = coefficients[name]
            output[name] = values
        }
    }
    return transpose(output)
}
"""

SCENARIOS = (
    "common_numeric", "common_categorical", "grouped_controls", "individual_controls",
    "random_missing", "suspensions", "constant_collinear", "no_intercept",
)


def make_source(scenario, stocks=300):
    dates = pd.bdate_range("2024-01-01", "2025-12-31")
    rng = np.random.default_rng(61041)
    days = len(dates)
    market = rng.normal(0, 0.01, (days, 3))
    x = np.tile(market[:, 0], stocks)
    z = np.tile(market[:, 1], stocks)
    w = np.tile(market[:, 2], stocks)
    stock_id = np.repeat(np.arange(stocks), days)
    day_id = np.tile(np.arange(days), stocks)
    if scenario == "individual_controls":
        x = x + rng.normal(0, 0.005, stocks * days)
        z = z + rng.normal(0, 0.005, stocks * days)
    elif scenario == "grouped_controls":
        grouped = rng.normal(0, 0.006, (10, days))
        z = z + grouped[stock_id % 10, day_id]
    elif scenario == "constant_collinear":
        z = 2 * x
        w = np.ones_like(x)
    target = (0.001 + stock_id * 1e-6 + (0.7 + stock_id / stocks) * x
              - 0.6 * z + 0.3 * w + rng.normal(0, 0.008, stocks * days))
    selected = np.ones(stocks * days, dtype=bool)
    if scenario == "random_missing":
        target[rng.random(len(target)) < 0.02] = np.nan
        z[rng.random(len(z)) < 0.01] = np.nan
        x[(stock_id % 7 == 0) & (day_id % 43 == 0)] = np.inf
    if scenario == "suspensions":
        for group in range(10):
            start = 55 + group * 13
            selected[(stock_id % 10 == group) & (day_id >= start) & (day_id < start + 5)] = False
        selected[rng.random(len(selected)) < 0.005] = False
    source = pd.DataFrame({
        "time": np.tile(dates.to_numpy(), stocks),
        "code": np.repeat([f"S{i:04}" for i in range(stocks)], days),
        "target": target, "x": x, "z": z, "w": w, "selected": selected,
        "industry": np.tile(np.array(["bank", "retail", "tech"])[(np.arange(days) // 35) % 3], stocks),
        "flag": np.tile((np.arange(days) // 17) % 2 == 0, stocks),
    })
    if scenario == "common_categorical":
        controls = ["x", "industry", "flag"]
    else:
        controls = ["x", "z", "w"]
    minimum = 45 if scenario in {"random_missing", "suspensions"} else 63
    return source, controls, minimum, scenario != "no_intercept"


def compare(before, after):
    columns = sorted(set(before.columns) | set(after.columns))
    left = before.reindex(columns=columns).to_numpy(dtype=float)
    right = after.reindex(columns=columns).to_numpy(dtype=float)
    np.testing.assert_array_equal(np.isnan(left), np.isnan(right))
    np.testing.assert_allclose(left, right, atol=1e-10, rtol=1e-7, equal_nan=True)
    finite = np.isfinite(left) & np.isfinite(right)
    return float(np.max(np.abs(left[finite] - right[finite]))) if finite.any() else 0.0


def load_baseline(path):
    if path is None:
        return BASELINE_SCRIPT
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "APPLY_ROLLING_OLS" for target in node.targets))
    definition = ast.literal_eval(next(keyword.value for keyword in assignment.value.keywords
                                      if keyword.arg == "definition"))
    return definition.replace("def apply_rolling_ols(", "def benchmark_baseline_apply(")


def run(args):
    if args.stocks < 300:
        raise ValueError("Benchmark requires at least 300 stocks")
    scenarios = args.scenario or SCENARIOS
    baseline = load_baseline(args.baseline)
    output = {
        "baseline": "Query 0.1.3 4c3ec80d6e0fc0178b226324c97bad53163c5984",
        "baseline_script_sha256": hashlib.sha256(baseline.encode()).hexdigest(),
        "candidate_script_sha256": hashlib.sha256(APPLY_ROLLING_OLS.definition.encode()).hexdigest(),
        "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
        "window": 63, "repetitions": args.repetitions, "warmups_per_implementation": args.warmups,
        "timing": "server elapsed nanoseconds; grouping, fitting, output restoration included; upload/compile/download excluded",
        "results": [],
    }
    output["session_policy"] = "fresh session per scenario, 600-second limit per scenario"
    for scenario in scenarios:
        source, controls, minimum, intercept = make_source(scenario, args.stocks)
        session = create_session(max_time=600)
        try:
            session.run(baseline)
            output["server_version"] = session.run("version()")
            output["server_os"] = session.run("getOS()")
            output["server_workers"] = session.run('getConfig("workerNum")')
            output["server_max_memory_gb"] = session.run('getConfig("maxMemSize")')
            session.upload({"benchmarkSource": source})
            fields = ",".join(f"benchmarkSource.{name} as c{i}" for i, name in enumerate(controls))
            session.run(f"benchmarkControls=table({fields});NULL")
            call_args = ("benchmarkSource.target,benchmarkControls,benchmarkSource.selected,"
                         f"benchmarkSource.code,benchmarkSource.time,63,{minimum},"
                         + ("true" if intercept else "false"))
            scripts = {
                "before": f"benchmarkResult=benchmark_baseline_apply({call_args})",
                "after": f"benchmarkResult=apply_rolling_ols({call_args},NULL)",
            }
            print(f"START {scenario}: {args.stocks} stocks, {source.time.nunique()} dates, {len(source)} rows", flush=True)
            for _ in range(args.warmups):
                for script in scripts.values():
                    session.run(script + ";NULL")
            baseline_frame = session.run(scripts["before"] + ";benchmarkResult")
            actual_frame = session.run(scripts["after"] + ";benchmarkResult")
            difference = compare(baseline_frame, actual_frame)
            seconds = {"before": [], "after": []}
            for repetition in range(args.repetitions):
                order = ("before", "after") if repetition % 2 == 0 else ("after", "before")
                for name in order:
                    measured = session.run("benchmarkClock=long(now(true));" + scripts[name]
                                           + ";double(long(now(true))-benchmarkClock)/1000000000.0")
                    seconds[name].append(float(measured))
            old = statistics.median(seconds["before"])
            new = statistics.median(seconds["after"])
            result = {
                "scenario": scenario, "stocks": args.stocks, "dates": source.time.nunique(),
                "start": str(source.time.min().date()), "end": str(source.time.max().date()),
                "rows": len(source), "controls": controls, "min_periods": minimum, "intercept": intercept,
                "before_seconds": seconds["before"], "after_seconds": seconds["after"],
                "before_median_seconds": old, "after_median_seconds": new, "speedup": old / new,
                "max_absolute_difference": difference, "null_masks_equal": True,
                "columns": sorted(actual_frame.columns),
            }
            output["results"].append(result)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            print("RESULT " + json.dumps(result, ensure_ascii=False), flush=True)
            session.run('undef("benchmarkResult",VAR);NULL')
        finally:
            session.close()
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stocks", default=300, type=int)
    parser.add_argument("--repetitions", default=3, type=int)
    parser.add_argument("--warmups", default=1, type=int)
    parser.add_argument("--scenario", choices=SCENARIOS, action="append")
    parser.add_argument("--baseline", type=Path, help="Exact pre-optimization runtime.py; loaded as source, not imported")
    arguments = parser.parse_args()
    if arguments.repetitions < 1 or arguments.warmups < 0:
        parser.error("repetitions must be positive and warmups nonnegative")
    started = time.perf_counter()
    run(arguments)
    print(f"Benchmark completed in {time.perf_counter() - started:.3f}s", flush=True)
