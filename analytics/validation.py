"""Dependence-aware uncertainty and chronological association validation."""

from collections import Counter
from itertools import combinations
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_cluster_2groups
from scipy.stats import norm, fisher_exact


def clustered_review_difference(frame):
    """Two-way cluster-robust OLS mean difference on single-seller reviewed orders."""
    df = frame.sort_values("order_id").dropna(subset=["review_score", "on_time", "customer_unique_id", "seller_id"])
    n_customers = df.customer_unique_id.nunique()
    n_sellers = df.seller_id.nunique()
    if min(n_customers, n_sellers) < 30 or df.on_time.nunique() < 2:
        return {"supported": False, "reason": "Requires two outcome groups and at least 30 clusters per dimension"}
    late = (~df.on_time.astype(bool)).astype(float)
    fitted = sm.OLS(df.review_score.astype(float), sm.add_constant(late)).fit()
    groups = np.column_stack([pd.factorize(df.customer_unique_id)[0], pd.factorize(df.seller_id)[0]])
    covariance, _, _ = cov_cluster_2groups(fitted, groups, use_correction=True)
    variance = float(covariance[1, 1])
    if variance <= 0:
        return {"supported": False, "reason": "Nonpositive two-way covariance estimate; interval withheld"}
    se = np.sqrt(variance)
    effect = float(fitted.params.iloc[1])
    return {
        "supported": True,
        "orders": len(df),
        "late_n": int(late.sum()),
        "on_time_n": int((1 - late).sum()),
        "customer_clusters": n_customers,
        "seller_clusters": n_sellers,
        "mean_difference": effect,
        "standard_error": float(se),
        "ci95": [effect - 1.96 * se, effect + 1.96 * se],
        "p_value": float(2 * norm.sf(abs(effect / se))),
        "method": "OLS difference of means, two-way customer/seller clustered covariance with finite-sample correction and normal critical value",
        "limitations": "Single-seller reviewed orders only; cross-cluster independence and many clusters assumed. Nonresponse and confounding remain; no causal claim.",
    }


def _counts(frame):
    baskets = frame.groupby("order_id", sort=True).product_id.apply(lambda x: sorted(set(x)))
    return (
        baskets,
        Counter(p for b in baskets for p in b),
        Counter(pair for b in baskets for pair in combinations(b, 2)),
    )


def validate_baskets(items, split="2018-01-01", minimum=20):
    """Freeze pair candidates on pre-split data, evaluate all candidates after split."""
    dates = pd.to_datetime(items.purchase_date)
    train, singles, pairs = _counts(items[dates < pd.Timestamp(split)])
    test, test_singles, test_pairs = _counts(items[dates >= pd.Timestamp(split)])
    candidates = sorted((pair, n) for pair, n in pairs.items() if n >= minimum)
    pairs_evaluated = []
    for (a, b), n in candidates:
        both = test_pairs[(a, b)]
        na = test_singles[a]
        nb = test_singles[b]
        total = len(test)
        if total:
            _, p = fisher_exact([[both, na - both], [nb - both, total - na - nb + both]], alternative="greater")
        else:
            p = 1.0
        pairs_evaluated.append({"a": a, "b": b, "train_count": n, "test_count": both, "test_p": float(p)})
    # Benjamini-Hochberg correction on unique unordered pairs, before directional expansion.
    ordered = sorted(range(len(pairs_evaluated)), key=lambda i: pairs_evaluated[i]["test_p"])
    last = 1.0
    for rank in range(len(ordered), 0, -1):
        index = ordered[rank - 1]
        last = min(last, pairs_evaluated[index]["test_p"] * len(ordered) / rank)
        pairs_evaluated[index]["test_q"] = last
    rules = []
    for pair in pairs_evaluated:
        for a, b in [(pair["a"], pair["b"]), (pair["b"], pair["a"])]:
            n = pair["train_count"]
            tn = pair["test_count"]
            ta = test_singles[a]
            tb = test_singles[b]
            lift = tn * len(test) / (ta * tb) if ta and tb else None
            rules.append(
                {
                    "antecedent": a,
                    "consequent": b,
                    "orders": n,
                    "support": n / len(train),
                    "confidence": n / singles[a],
                    "lift": n * len(train) / (singles[a] * singles[b]),
                    "test_orders": tn,
                    "test_support": tn / len(test) if len(test) else None,
                    "test_confidence": tn / ta if ta else None,
                    "test_lift": lift,
                    "test_q": pair["test_q"],
                    "replicated": bool(tn >= 5 and lift is not None and lift > 1 and pair["test_q"] <= 0.05),
                }
            )
    rules.sort(key=lambda x: (-x["orders"], x["antecedent"], x["consequent"]))
    return {
        "split_date": split,
        "training_orders": len(train),
        "test_orders": len(test),
        "total_orders": len(train) + len(test),
        "multi_product_orders": int(train.map(len).gt(1).sum() + test.map(len).gt(1).sum()),
        "minimum_pair_orders": minimum,
        "candidate_pairs": len(candidates),
        "replicated_pairs": sum(r["replicated"] for r in rules) // 2,
        "rules": rules,
        "limitations": "Candidates selected before 2018. Replication requires >=5 later co-purchases, lift>1 and BH q<=0.05. BH assumes independence or suitable positive dependence; overlapping products may violate this. Customer dependence, selection and nonstationarity remain; not causal campaign evidence.",
    }
