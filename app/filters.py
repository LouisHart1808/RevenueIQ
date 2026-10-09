"""Shared parameterized whole-basket filter semantics."""


def predicate(start=None, end=None, state=None, category=None, seller=None):
    conditions = ["1=1"]
    params = {}
    for key, value, clause in [
        ("start", start, "o.purchase_date>=:start"),
        ("end", end, "o.purchase_date<=:end"),
        ("state", state, "o.state=:state"),
    ]:
        if value:
            conditions.append(clause)
            params[key] = value
    if category or seller:
        clauses = ["i.order_id=o.order_id"]
        for key, value in [("category", category), ("seller_id", seller)]:
            if value:
                clauses.append(f"i.{key}=:{key}")
                params[key] = value
        conditions.append("exists(select 1 from warehouse.fact_order_items i where " + " and ".join(clauses) + ")")
    return " and ".join(conditions), params
