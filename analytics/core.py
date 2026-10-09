"""Pure analytical utilities, with explicit assumptions and reproducible seeds."""

import itertools
import numpy as np
from scipy.stats import mannwhitneyu
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def scenario(sales, customer_growth=0, frequency_growth=0, aov_growth=0):
    values = np.asarray([sales, customer_growth, frequency_growth, aov_growth], dtype=float)
    if not np.isfinite(values).all() or sales < 0 or min(values[1:]) < -1:
        raise ValueError("Finite inputs required; growth cannot be below -100%")
    return float(sales * (1 + customer_growth) * (1 + frequency_growth) * (1 + aov_growth))


def decompose(before, after):
    """Shapley allocation of C × F × A; sums exactly to observed sales change."""
    a, b = np.array(before, dtype=float), np.array(after, dtype=float)
    if len(a) != 3 or len(b) != 3 or not np.isfinite([a, b]).all():
        raise ValueError("Three finite factors required")
    contributions = np.zeros(3)
    for order in itertools.permutations(range(3)):
        current = a.copy()
        for i in order:
            old = current.prod()
            current[i] = b[i]
            contributions[i] += (current.prod() - old) / 6
    return contributions


def errors(actual, predicted):
    a, p = np.asarray(actual), np.asarray(predicted)
    if len(a) == 0 or a.shape != p.shape:
        raise ValueError("Matching nonempty arrays required")
    diff = a - p
    denominator = np.abs(a) + np.abs(p)
    return {
        "MAE": float(np.abs(diff).mean()),
        "RMSE": float(np.sqrt((diff**2).mean())),
        "WAPE": float(np.abs(diff).sum() / np.abs(a).sum()) if np.abs(a).sum() else None,
        "sMAPE": float(
            np.mean(
                np.divide(2 * np.abs(diff), denominator, out=np.zeros_like(diff, dtype=float), where=denominator != 0)
            )
        ),
    }


def compare_reviews(late, on_time, iterations=1000):
    a, b = np.sort(np.asarray(late, dtype=float)), np.sort(np.asarray(on_time, dtype=float))
    if min(len(a), len(b)) < 10:
        return {"supported": False, "reason": "At least ten reviewed orders per group required"}
    rng = np.random.default_rng(42)
    boot = [
        rng.choice(a, len(a), replace=True).mean() - rng.choice(b, len(b), replace=True).mean()
        for _ in range(iterations)
    ]
    test = mannwhitneyu(a, b, alternative="two-sided")
    return {
        "supported": True,
        "late_n": len(a),
        "on_time_n": len(b),
        "late_mean": float(a.mean()),
        "on_time_mean": float(b.mean()),
        "mean_difference": float(a.mean() - b.mean()),
        "ci95": np.quantile(boot, [0.025, 0.975]).tolist(),
        "p_value": float(test.pvalue),
        "p_value_note": "Below floating-point precision" if test.pvalue == 0 else "Two-sided asymptotic Mann–Whitney",
        "rank_biserial": float(2 * test.statistic / (len(a) * len(b)) - 1),
    }


def forecast(series, holdout=3):
    """Select only on development folds; freeze interval width before final rolling test."""
    y = np.asarray(series, dtype=float)
    if len(y) < 18 or holdout < 1 or len(y) - holdout < 15:
        return {"supported": False, "reason": "Requires >=18 months and >=3 development folds after 12-month warmup"}
    methods = {
        "Last month": lambda x: x[-1],
        "Three month mean": lambda x: x[-3:].mean(),
        "Seasonal naive": lambda x: x[-12],
        "Damped trend": lambda x: (
            float(
                ExponentialSmoothing(x / 1000, trend="add", damped_trend=True, initialization_method="estimated")
                .fit(optimized=True)
                .forecast(1)[0]
            )
            * 1000
        ),
    }
    split = len(y) - holdout
    scores = {}
    predictions = {}
    for name, func in methods.items():
        predictions[name] = np.array([max(0, func(y[:i])) for i in range(12, split)])
        scores[name] = errors(y[12:split], predictions[name])
    selected = min(scores, key=lambda k: scores[k]["MAE"])
    residuals = np.abs(y[12:split] - predictions[selected])
    # Empirical 95th percentile, not a finite-sample conformal guarantee with so few folds.
    width = float(np.quantile(residuals, 0.95))
    predicted = np.array([max(0, methods[selected](y[:i])) for i in range(split, len(y))])
    lower = np.maximum(0, predicted - width)
    upper = predicted + width
    actual = y[split:]
    next_value = max(0, methods[selected](y))
    return {
        "supported": True,
        "folds": split - 12,
        "selection_end_index": split - 1,
        "holdout_start_index": split,
        "scores": scores,
        "selected": selected,
        "next": float(next_value),
        "interval": [max(0, next_value - width), next_value + width],
        "actual": actual.tolist(),
        "predicted": predicted.tolist(),
        "holdout_scores": errors(actual, predicted),
        "holdout_baseline": errors(actual, y[split - 1 : -1]),
        "holdout_months": holdout,
        "lower": lower.tolist(),
        "upper": upper.tolist(),
        "interval_width_frozen": width,
        "holdout_coverage": float(((actual >= lower) & (actual <= upper)).mean()),
        "nominal_coverage": 0.95,
        "caveat": "Final months are excluded from model selection and interval calibration. Fixed selected method is refitted using only information available before each test month. Historical dataset was explored in v1: this is a retrospective locked holdout, not never-viewed external evidence. Few calibration/test months cannot establish 95% coverage.",
    }


def revenue_anomalies(frame):
    """Retrospective robust screen of monthly percentage changes, not causal diagnosis."""
    result = frame.copy()
    changes = result.sales.pct_change()
    center = changes.median()
    mad = (changes - center).abs().median()
    result["robust_score"] = (changes - center) / (1.4826 * mad) if mad > 0 else 0.0
    result["flag"] = result.robust_score.abs() > 3.5
    return result
