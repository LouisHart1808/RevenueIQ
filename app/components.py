"""Shared presentation components and number formatting."""

import pandas as pd
from dash import dcc, html, dash_table
from dash.dash_table.Format import Format, Scheme, Group, Symbol


def graph(fig, title=None, drill=None):
    fig.update_layout(
        font={"family": "Inter, Arial, sans-serif", "color": "#40516a", "size": 12},
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 35, "r": 22, "t": 35, "b": 45},
        height=330,
        legend={"orientation": "h", "y": 1.12},
        title=None,
    )
    labels = {
        "sales": "Merchandise value (BRL)",
        "month": "Purchase month",
        "orders": "Orders",
        "customers": "Customers",
        "category": "Product category",
        "on_time": "On-time delivery rate",
        "aov": "Average order value (BRL)",
        "review_score": "Mean review score",
        "delivery_days": "Delivery duration (days)",
        "units": "Units",
        "state": "Customer state",
        "growth": "Month-over-month change (%)",
    }
    for axis in [fig.layout.xaxis, fig.layout.yaxis]:
        original = axis.title.text
        if original in labels:
            axis.title.text = labels[original]
        if original in ["sales", "aov", "average_price"]:
            axis.tickprefix = "R$ "
            axis.tickformat = ",.0f"
        elif original in ["on_time", "retention", "support", "confidence"]:
            axis.tickformat = ".0%"
    return html.Div(
        [
            html.H3(title) if title else None,
            dcc.Graph(
                figure=fig,
                responsive=True,
                style={"height": "330px"},
                config={"displaylogo": False},
                **({"id": {"type": "drill", "kind": drill, "name": title}} if drill else {}),
            ),
        ],
        className="panel",
    )


def table_column(name, series):
    label = {
        "sales": "Merchandise value (BRL)",
        "aov": "AOV (BRL)",
        "on_time": "On-time rate",
        "monetary": "Observed value (BRL)",
        "historical_value": "Observed value (BRL)",
        "test_q": "Test BH q-value",
        "orders": "Orders",
    }.get(name, name.replace("_", " ").title())
    column = {"name": label, "id": name}
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        percent = name in ["on_time", "retention", "support", "confidence", "test_support", "test_confidence", "rate"]
        currency = name in [
            "sales",
            "aov",
            "average_price",
            "monetary",
            "historical_value",
            "merchandise_value",
            "cumulative_value_per_customer",
            "prior_year_sales",
        ]
        column.update(
            type="numeric",
            format=Format(
                precision=0
                if name
                in ["orders", "customers", "units", "age", "rows", "frequency", "exact_duplicates", "test_orders"]
                else 2,
                scheme=Scheme.percentage if percent else Scheme.fixed,
                group=Group.yes,
                **({"symbol": Symbol.yes, "symbol_prefix": "R$ "} if currency else {}),
            ),
        )
    return column


def table(df):
    return dash_table.DataTable(
        data=df.round(4).to_dict("records"),
        columns=[table_column(c, df[c]) for c in df.columns],
        page_size=10,
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_cell={
            "fontFamily": "Arial",
            "fontSize": 12,
            "padding": "12px",
            "textAlign": "left",
            "maxWidth": 250,
            "overflow": "hidden",
            "textOverflow": "ellipsis",
        },
        style_header={"backgroundColor": "#f3f6fb", "fontWeight": "bold"},
        style_data={"border": "1px solid #edf0f5"},
    )


def note(text):
    return html.Div(text, className="note")


def money(x):
    return f"R$ {x:,.0f}"


def num(x, fmt=",.0f"):
    return "—" if pd.isna(x) else format(x, fmt)
