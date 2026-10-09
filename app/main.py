from pathlib import Path
from datetime import datetime
import json
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash.dash_table.Format import Format, Scheme, Group, Symbol
from dash import Dash, Input, Output, State, dcc, html, dash_table, no_update
from app.services import query, get_snapshot, product_page
from app.releases import pinned_release, report_path, current_release
from app.services import ENGINE
from analytics.core import decompose, scenario, revenue_anomalies

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "Executive Overview",
    "Revenue Intelligence",
    "Customer Intelligence",
    "Product Intelligence",
    "Operations Intelligence",
    "Geographic Intelligence",
    "Advanced Analytics",
    "Scenario Planning",
    "Data Quality & Methodology",
]
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = ["#246bfe", "#19a88e", "#f0aa45", "#8e74d7", "#e4677e"]
app = Dash(
    __name__,
    assets_folder=str(ROOT / "app/assets"),
    suppress_callback_exceptions=True,
    title="RevenueIQ | Commerce Intelligence",
)
server = app.server


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


@pinned_release
def layout():
    try:
        bounds = query(
            "select min(purchase_date) as start,max(purchase_date) as finish from warehouse.fact_orders"
        ).iloc[0]
        states = query("select distinct state from warehouse.dim_customers order by 1").state.tolist()
        categories = query("select distinct category from warehouse.dim_products order by 1").category.tolist()
    except Exception:
        logging.exception("Warehouse unavailable")
        return html.Div(
            [
                html.H1("RevenueIQ"),
                note("The warehouse is unavailable. Run the data pipeline and check the database connection."),
            ]
        )
    refresh_note = "Historical Olist dataset"
    return html.Div(
        [
            html.Aside(
                [
                    html.Div([html.Span("R", className="logo"), " RevenueIQ"], className="brand"),
                    html.Div("COMMERCE INTELLIGENCE", className="eyebrow"),
                    html.Nav(
                        [
                            html.Button(
                                [html.Span(f"{i + 1:02d}", className="nav-number"), p],
                                id={"type": "nav", "index": i},
                                className="nav-item",
                                n_clicks=0,
                            )
                            for i, p in enumerate(PAGES)
                        ]
                    ),
                    html.Div(
                        [
                            html.Strong("OLIST / BRAZIL"),
                            html.P("Historical public dataset"),
                            html.Small("BRL · 2016–2018\nCC BY-NC-SA 4.0"),
                        ],
                        className="sidebar-foot",
                    ),
                ],
                className="sidebar",
            ),
            html.Main(
                [
                    html.Header(
                        [
                            html.Div(
                                [
                                    html.Div("WORKSPACE / ANALYTICS", className="eyebrow"),
                                    html.H1(id="page-title", children=PAGES[0]),
                                ]
                            ),
                            html.Span("●  PostgreSQL connected", className="badge"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Purchase date"),
                                    dcc.DatePickerRange(
                                        id="dates",
                                        start_date=str(bounds.start),
                                        end_date=str(bounds.finish),
                                        display_format="DD MMM YYYY",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label("Customer state"),
                                    dcc.Dropdown(states, id="state", placeholder="All states"),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label("Category in basket"),
                                    dcc.Dropdown(categories, id="category", placeholder="All categories"),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label("Seller in basket"),
                                    dcc.Dropdown(
                                        query(
                                            "select seller_id from warehouse.dim_sellers order by 1"
                                        ).seller_id.tolist(),
                                        id="seller",
                                        placeholder="All sellers",
                                    ),
                                ]
                            ),
                            html.Button("Reset filters", id="reset", className="button"),
                            html.Button("Export CSV", id="export", className="button"),
                            dcc.Download(id="download"),
                        ],
                        className="filters",
                    ),
                    html.Div(
                        refresh_note
                        + " · Delivered-order merchandise value · Category/seller filters select whole baskets",
                        className="context",
                    ),
                    dcc.Store(id="page", data=0),
                    dcc.Store(id="release-generation"),
                    dcc.Interval(id="release-watch", interval=15000, n_intervals=0),
                    html.Div(id="release-status", className="context"),
                    html.Div(id="drill-feedback", className="context"),
                    dcc.Loading(html.Div(id="content"), type="circle"),
                    html.Footer(
                        "RevenueIQ  /  Evidence before decisions.  •  Historical transactions are not recognized accounting revenue."
                    ),
                ],
                className="main",
            ),
        ]
    )


app.layout = layout
from dash import ALL, ctx  # noqa: E402


@app.callback(Output("page", "data"), Input({"type": "nav", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def navigate(clicks):
    return ctx.triggered_id["index"]


@app.callback(Output({"type": "nav", "index": ALL}, "className"), Input("page", "data"))
def highlight_navigation(page):
    return ["nav-item active" if i == page else "nav-item" for i in range(len(PAGES))]


@app.callback(
    Output("dates", "start_date"),
    Output("dates", "end_date"),
    Output("state", "value"),
    Output("category", "value"),
    Output("seller", "value"),
    Input("reset", "n_clicks"),
    prevent_initial_call=True,
)
def reset(n):
    b = query("select min(purchase_date) as start,max(purchase_date) as finish from warehouse.fact_orders").iloc[0]
    return str(b.start), str(b.finish), None, None, None


@app.callback(
    Output("page-title", "children"),
    Output("content", "children"),
    Input("page", "data"),
    Input("dates", "start_date"),
    Input("dates", "end_date"),
    Input("state", "value"),
    Input("category", "value"),
    Input("seller", "value"),
    Input("release-generation", "data"),
)
@pinned_release
def render(page, start, end, state, category, seller=None, tick=0):
    try:
        if start and end and start > end:
            return PAGES[page], note("Choose an end date on or after the start date.")
        s = get_snapshot(start, end, state, category, seller)
        k = s["kpi"].iloc[0]
        if not k.orders:
            return PAGES[page], note(
                "No delivered orders match these filters. Broaden the date range or reset filters."
            )
        if page == 0:
            cards = [
                ("Merchandise sales", money(k.sales), "Delivered items, excluding freight"),
                ("Delivered orders", num(k.orders), "One row per order"),
                ("Purchasing customers", num(k.customers), "Persistent customer identity"),
                ("Average order value", money(k.aov), "Merchandise sales ÷ orders"),
                ("Repeat purchase rate", num(s["repeat"].iloc[0].rate, ".2%"), "Two or more orders in selection"),
                ("On-time delivery", num(k.on_time, ".2%"), "Known delivery and estimate dates"),
            ]
            return PAGES[page], [
                html.Div(
                    [
                        html.Div([html.Label(label), html.Strong(value), html.Small(detail)], className="kpi")
                        for label, value, detail in cards
                    ],
                    className="kpis",
                ),
                html.Div(
                    [
                        graph(px.area(s["monthly"], x="month", y="sales"), "Monthly merchandise sales"),
                        graph(
                            px.bar(s["categories"].head(8).iloc[::-1], x="sales", y="category", orientation="h"),
                            "Leading categories",
                            drill="category",
                        ),
                        graph(px.bar(s["monthly"], x="month", y="orders"), "Order volume"),
                        graph(
                            px.bar(s["regions"].head(10), x="state", y="sales"), "Regional contribution", drill="state"
                        ),
                        graph(
                            px.bar(s["segments"], x="customers", y="segment", orientation="h"),
                            "Customer segments · as-of labels",
                        ),
                        graph(px.bar(s["operations"], x="on_time", y="orders"), "Delivery punctuality"),
                    ],
                    className="grid",
                ),
            ]
        if page == 1:
            m = s["monthly"].copy()
            m["growth"] = m.sales.pct_change() * 100
            m["complete"] = pd.to_datetime(m.month).ge(pd.Timestamp(start)) & pd.to_datetime(m.month).map(
                lambda d: (d + pd.offsets.MonthEnd(0)).date() <= pd.Timestamp(end).date()
            )
            # Conservative comparable window avoids launch/tail artifacts.
            consecutive = pd.to_datetime(m.month).diff().dt.days.between(28, 31)
            m.loc[~(m.complete & m.complete.shift(1, fill_value=False) & consecutive), "growth"] = float("nan")
            comparable = m[(m.month.astype(str) >= "2017-01-01") & (m.month.astype(str) < "2018-08-01") & m.complete]
            year_prior = comparable[["month", "sales"]].copy()
            year_prior["month"] = pd.to_datetime(year_prior.month) + pd.DateOffset(years=1)
            year_prior = year_prior.rename(columns={"sales": "prior_year_sales"})
            year_current = comparable.copy()
            year_current["month"] = pd.to_datetime(year_current.month)
            year_current = year_current.merge(year_prior, on="month", how="inner")
            year_current["yoy_percent"] = (year_current.sales / year_current.prior_year_sales - 1) * 100
            charts = [
                graph(px.line(m, x="month", y="sales", markers=True), "Monthly sales"),
                graph(px.bar(m, x="month", y="growth"), "Month-over-month change (%)"),
            ]
            if len(comparable) >= 2:
                a, b = comparable.iloc[-2], comparable.iloc[-1]
                contributions = decompose(
                    [a.customers, a.orders / a.customers, a.aov], [b.customers, b.orders / b.customers, b.aov]
                )
                charts.append(
                    graph(
                        go.Figure(
                            go.Waterfall(
                                x=["Prior month", "Customers", "Frequency", "Order value", "Latest month"],
                                measure=["absolute", "relative", "relative", "relative", "total"],
                                y=[a.sales, *contributions, 0],
                            )
                        ),
                        "Exact change decomposition · last two complete months",
                    )
                )
            cats = s["categories"].copy()
            cats["cumulative_share"] = cats.sales.cumsum() / cats.sales.sum() * 100
            charts.extend(
                [
                    graph(
                        px.bar(cats.head(15), x="category", y="sales"), "Category sales contribution", drill="category"
                    ),
                    graph(px.line(cats, x="category", y="cumulative_share"), "Category Pareto · cumulative %"),
                ]
            )
            return PAGES[page], [
                note(
                    "Growth is descriptive. Partial boundary months are excluded from comparisons; sparse launch and terminal months are excluded from decomposition. Shapley contributions reconcile exactly and do not imply causation."
                ),
                html.Div(charts, className="grid"),
                html.H3("Year-over-year · complete months with a prior-year match"),
                table(year_current[["month", "sales", "prior_year_sales", "yoy_percent"]]),
                html.H3("Exploratory anomaly screen · complete 2017–July 2018 months"),
                note(
                    "Robust monthly-change score uses median absolute deviation; |score| > 3.5 flags investigation. Seasonality, changing category mix, and source coverage can explain flags. This retrospective screen is not an operational alert."
                ),
                table(revenue_anomalies(comparable)[["month", "sales", "robust_score", "flag"]]),
                html.H3("Seller contribution"),
                graph(
                    px.bar(s["sellers"].head(12), x="seller_id", y="sales"),
                    "Seller sales · click to explore",
                    drill="seller",
                ),
                table(s["sellers"]),
            ]
        if page == 2:
            return PAGES[page], [
                note(
                    f"Customer cutoff: {s['customer_boundary'].iloc[0].cutoff}. Selected known-delivered orders: {int(s['segments'].orders.sum()):,}; revenue views use the final-status population."
                ),
                note(
                    "Customer history ends at the selected cutoff and includes only orders delivered by that date; unknown/future deliveries are excluded. Segments describe customers active in the selected purchase window. Cohorts select acquisition orders within the filters, then follow all subsequent purchases through the cutoff. Future cells are absent; the cutoff month is partial."
                ),
                html.Div(
                    [
                        graph(px.bar(s["segments"], x="segment", y="sales"), "Known-delivered sales by as-of segment"),
                        graph(px.bar(s["segments"], x="segment", y="customers"), "Selected customer distribution"),
                    ],
                    className="grid",
                ),
                html.Div(
                    [
                        graph(
                            px.bar(s["acquisition"], x="month", y=["new_customers", "returning_customers"]),
                            "Selected customers · first observed month versus returning",
                        ),
                        graph(
                            px.bar(s["distribution"], x="frequency", y="customers"),
                            "Selected customers · purchase frequency as of cutoff",
                        ),
                    ],
                    className="grid",
                ),
                dcc.Dropdown(
                    s["segments"].segment.tolist(), id="segment-select", placeholder="Inspect a historical segment"
                ),
                html.Div(id="segment-detail"),
                dcc.Dropdown(
                    sorted(s["cohorts"].cohort.astype(str).unique()),
                    id="cohort-select",
                    placeholder="Select an acquisition cohort as of the cutoff",
                ),
                dcc.Graph(id="cohort-chart"),
                graph(
                    px.imshow(
                        s["cohorts"]
                        .assign(cohort=s["cohorts"].cohort.astype(str))
                        .pivot(index="cohort", columns="age", values="retention"),
                        aspect="auto",
                        color_continuous_scale="Blues",
                        zmin=0,
                        zmax=0.05,
                    ),
                    "As-of retention · color capped at 5%; hover for actual values",
                ),
                html.Div(
                    [
                        graph(
                            px.bar(
                                s["value_distribution"].query("monetary_bucket <= 2000"),
                                x="monetary_bucket",
                                y="customers",
                            ),
                            "Historical value distribution · up to R$2,100, R$100 bins",
                        ),
                        graph(
                            px.bar(s["recency_distribution"], x="recency_bucket", y="customers"),
                            "Recency as of cutoff · 30-day bins",
                        ),
                    ],
                    className="grid",
                ),
                table(s["segments"]),
            ]
        if page == 3:
            a = json.loads(report_path("analytics.json").read_text())
            return PAGES[page], [
                note(
                    "Click a category or use filters to inspect its baskets. Basket candidates are selected before 2018 and tested on later orders; validation remains exploratory, not proof of campaign impact."
                ),
                html.Div(
                    [
                        graph(px.bar(s["categories"].head(15), x="category", y="sales"), "Category contribution"),
                        graph(
                            px.scatter(s["products"], x="units", y="sales", hover_data=["product_id", "category"]),
                            "Product volume and value",
                        ),
                    ],
                    className="grid",
                ),
                graph(
                    px.line(
                        s["category_monthly"][s["category_monthly"].category.isin(s["categories"].head(5).category)],
                        x="month",
                        y="sales",
                        color="category",
                    ),
                    "Selected top-five category trends",
                ),
                html.H3("Product explorer · server-side pages ordered by sales"),
                dash_table.DataTable(
                    id="product-table",
                    columns=[
                        {"name": c.replace("_", " ").title(), "id": c}
                        for c in ["category", "product_id", "sales", "units", "average_price"]
                    ],
                    page_current=0,
                    page_size=20,
                    page_action="custom",
                    style_table={"overflowX": "auto"},
                    style_cell={"padding": "12px", "fontFamily": "Arial", "fontSize": 12, "textAlign": "left"},
                ),
                graph(
                    px.scatter(
                        s["category_quality"], x="on_time", y="review_score", size="orders", hover_name="category"
                    ),
                    "Category delivery and satisfaction · ≥30 selected orders",
                ),
                html.H3("Product pairs · training and later-period validation"),
                graph(
                    px.scatter(
                        pd.DataFrame(a["basket"]["rules"]),
                        x="support",
                        y="lift",
                        size="orders",
                        hover_data=["antecedent", "consequent", "confidence"],
                    ),
                    "Training pair support and lift · test results in table",
                )
                if a["basket"]["rules"]
                else note("No pairs meet the minimum count."),
                table(pd.DataFrame(a["basket"]["rules"])),
            ]
        if page == 4:
            return PAGES[page], [
                note(
                    "Punctuality compares delivery and estimate calendar dates. Unknown delivery dates are excluded from the rate. A multi-seller order’s delivery outcome is shared across its sellers; this is not seller-level causal attribution."
                ),
                html.Div(
                    [
                        graph(px.bar(s["operations"], x="on_time", y="review_score"), "Average review by punctuality"),
                        graph(px.bar(s["regions"], x="state", y="delivery_days"), "Mean delivery duration (days)"),
                        graph(
                            px.line(s["operations_monthly"], x="month", y="delivery_days"), "Delivery duration trend"
                        ),
                        graph(
                            px.bar(s["reviews"], x="score", y="orders"),
                            "Order-average review score · rounded to integer",
                        ),
                        graph(px.bar(s["status"], x="order_status", y="orders"), "All-status order population"),
                        graph(
                            px.bar(s["operations"], x="on_time", y=["median_days", "p90_days"], barmode="group"),
                            "Median and 90th percentile duration",
                        ),
                    ],
                    className="grid",
                ),
                graph(
                    px.bar(s["sellers"].head(12), x="seller_id", y="sales"),
                    "Seller sales · click to explore",
                    drill="seller",
                ),
                table(s["sellers"]),
            ]
        if page == 5:
            regions = s["regions"].merge(query("select * from warehouse.dim_geography"), on="state", how="left")
            return PAGES[page], [
                note(
                    "State-level aggregate source coordinates; bubble area encodes sales. Coordinates summarize sampled ZIP locations and are not official state centroids."
                ),
                graph(
                    px.scatter_geo(
                        regions,
                        lat="latitude",
                        lon="longitude",
                        size="sales",
                        color="on_time",
                        hover_name="state",
                        hover_data=["orders", "aov", "delivery_days"],
                        scope="south america",
                        color_continuous_scale="Teal",
                    ).update_geos(fitbounds="locations"),
                    "Brazil · sales and delivery performance",
                    drill="state",
                ),
                graph(
                    px.scatter_geo(
                        regions,
                        lat="latitude",
                        lon="longitude",
                        size="orders",
                        color="aov",
                        hover_name="state",
                        scope="south america",
                        color_continuous_scale="Blues",
                    ).update_geos(fitbounds="locations"),
                    "Brazil · order volume and average order value",
                ),
                table(s["regions"]),
            ]
        if page == 6:
            a = json.loads(report_path("analytics.json").read_text())
            f = a["forecast"]
            t = a["statistics"]
            cluster = t["clustered"]
            score = pd.DataFrame(f["scores"]).T.reset_index(names="model")
            return PAGES[page], [
                note(
                    "Full-history research outputs: global filters do not change fitted models or statistical samples. Historical exercise, not a forecast of current business."
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3("Late delivery and review scores"),
                                html.P(
                                    f"Mean difference: {t['mean_difference']:.2f} points; bootstrap 95% interval [{t['ci95'][0]:.2f}, {t['ci95'][1]:.2f}]."
                                ),
                                html.P(
                                    f"{t['late_n']:,} late orders versus {t['on_time_n']:,} on-time orders. Rank-biserial effect: {t['rank_biserial']:.3f}."
                                ),
                                html.P(
                                    "Association does not establish causation. See the executive report for hypotheses, assumptions, nonresponse bias, and methods."
                                ),
                            ],
                            className="panel",
                        ),
                        graph(
                            go.Figure(
                                [
                                    go.Scatter(y=f["actual"], name="Observed"),
                                    go.Scatter(y=f["predicted"], name=f["selected"]),
                                ]
                            ),
                            "Chronological one-step forecast evaluation",
                        ),
                    ],
                    className="grid",
                ),
                html.H3("Development-only model selection"),
                table(score),
                html.H3("Locked final-period results · May–July 2018"),
                table(
                    pd.DataFrame(
                        [
                            dict(model=f["selected"], **f["holdout_scores"]),
                            dict(model="Last-month reference", **f.get("holdout_baseline", {})),
                        ]
                    )
                ),
                note(
                    f"Frozen empirical 95% band covered {f['holdout_coverage']:.0%} of {f['holdout_months']} test months. These few observations cannot establish reliable nominal coverage."
                ),
                graph(
                    go.Figure(
                        [
                            go.Scatter(x=f["test_months"], y=f["upper"], line={"width": 0}, name="Upper band"),
                            go.Scatter(
                                x=f["test_months"],
                                y=f["lower"],
                                fill="tonexty",
                                line={"width": 0},
                                name="Frozen empirical band",
                            ),
                            go.Scatter(x=f["test_months"], y=f["actual"], name="Observed"),
                            go.Scatter(x=f["test_months"], y=f["predicted"], name="Locked-model prediction"),
                        ]
                    ),
                    "Held-out historical predictions and uncertainty",
                ),
                note(
                    f"Customer/seller dependence sensitivity: {cluster.get('orders', 0):,} single-seller reviewed orders. Cluster-robust mean difference {cluster.get('mean_difference', 0):.3f}; 95% interval {cluster.get('ci95')}. Multi-seller orders excluded; association remains noncausal."
                ),
                note(f["caveat"]),
                html.P(
                    f"Next historical month estimate: {money(f['next'])}; empirical band {money(f['interval'][0])}–{money(f['interval'][1])}."
                ),
            ]
        if page == 7:
            return PAGES[page], [
                note(
                    "Assumption-based scenario: customers × frequency × order value. Global filters define the baseline. No causal effect or profit is inferred."
                ),
                dcc.Store(id="baseline", data=float(k.sales)),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(label),
                                dcc.Slider(
                                    -30,
                                    30,
                                    1,
                                    value=0,
                                    updatemode="drag",
                                    marks={-30: "−30%", 0: "0%", 30: "+30%"},
                                    id=id,
                                ),
                            ],
                            className="panel",
                        )
                        for label, id in [
                            ("Customer growth", "customer-growth"),
                            ("Purchase frequency", "frequency-growth"),
                            ("Average order value", "aov-growth"),
                        ]
                    ]
                ),
                html.Div(id="scenario-result"),
            ]
        quality = json.loads(report_path("data_quality.json").read_text())
        return PAGES[page], [
            note(
                "Static public data, last publisher update recorded in docs/source_metadata.json. No live transactions. Raw records are preserved; missing attributes and quality warnings are documented."
            ),
            dcc.Markdown((ROOT / "docs/metrics.md").read_text()),
            html.H3("Raw source profile"),
            table(
                pd.DataFrame(
                    [
                        {"table": n, "rows": v["rows"], "exact_duplicates": v["exact_duplicates"]}
                        for n, v in quality["tables"].items()
                    ]
                )
            ),
            html.Ul([html.Li(w) for w in quality["warnings"]]),
        ]
    except Exception:
        logging.exception("Dashboard render failed")
        return PAGES[page], note(
            "This view could not load. Check that the pipeline and analytics report have completed; diagnostic details are in the server log."
        )


@app.callback(
    Output("product-table", "data"),
    Input("product-table", "page_current"),
    Input("product-table", "page_size"),
    State("dates", "start_date"),
    State("dates", "end_date"),
    State("state", "value"),
    State("category", "value"),
    State("seller", "value"),
)
@pinned_release
def paginate_products(page, size, start, end, state, category, seller):
    return product_page(page, size, start, end, state, category, seller).round(2).to_dict("records")


@app.callback(
    Output("segment-detail", "children"),
    Input("segment-select", "value"),
    State("dates", "start_date"),
    State("dates", "end_date"),
    State("state", "value"),
    State("category", "value"),
    State("seller", "value"),
)
@pinned_release
def segment_detail(segment, start=None, end=None, state=None, category=None, seller=None):
    if not segment:
        return note("Select a segment to inspect its recency, frequency, and value as of the selected cutoff.")
    df = get_snapshot(start, end, state, category, seller)["segment_detail"]
    return table(df[df.segment == segment])


@app.callback(
    Output("cohort-chart", "figure"),
    Input("cohort-select", "value"),
    State("dates", "start_date"),
    State("dates", "end_date"),
    State("state", "value"),
    State("category", "value"),
    State("seller", "value"),
)
@pinned_release
def cohort(selected, start=None, end=None, state=None, category=None, seller=None):
    if not selected:
        return go.Figure().update_layout(title="Select a cohort to inspect its trajectory")
    df = get_snapshot(start, end, state, category, seller)["cohorts"]
    df = df[df.cohort.astype(str) == selected]
    figure = go.Figure(
        [
            go.Scatter(
                x=df.age,
                y=df.retention,
                name="Retention",
                mode="lines+markers",
                customdata=df.partial_month,
                hovertemplate="Age %{x}: %{y:.2%}<br>Partial month: %{customdata}<extra></extra>",
            ),
            go.Scatter(
                x=df.age,
                y=df.cumulative_value_per_customer,
                name="Cumulative value / acquired customer (BRL)",
                yaxis="y2",
            ),
        ]
    )
    return figure.update_layout(
        title=f"Acquisition cohort {selected}",
        xaxis_title="Months since first known-delivered purchase",
        yaxis={"title": "Retention", "tickformat": ".1%"},
        yaxis2={"title": "Observed value (BRL)", "overlaying": "y", "side": "right"},
        legend={"orientation": "h", "y": 1.15},
    )


@app.callback(
    Output("scenario-result", "children"),
    Input("customer-growth", "value"),
    Input("frequency-growth", "value"),
    Input("aov-growth", "value"),
    State("baseline", "data"),
)
def simulate(c, f, a, baseline):
    projected = scenario(baseline, c / 100, f / 100, a / 100)
    sensitivity = pd.DataFrame(
        {
            "factor": ["Customers", "Frequency", "AOV"],
            "plus_one_percentage_point": [
                scenario(baseline, (c + 1) / 100, f / 100, a / 100) - projected,
                scenario(baseline, c / 100, (f + 1) / 100, a / 100) - projected,
                scenario(baseline, c / 100, f / 100, (a + 1) / 100) - projected,
            ],
        }
    )
    return [
        html.Div(
            [
                html.H2(money(projected)),
                html.P(
                    f"Change from selected baseline: {money(projected - baseline)} ({projected / baseline - 1:+.1%})"
                ),
            ],
            className="panel",
        ),
        table(
            pd.DataFrame(
                {
                    "case": ["Baseline", "Selected assumptions", "Optimistic (+5% each)", "Pessimistic (−5% each)"],
                    "merchandise_value": [
                        baseline,
                        projected,
                        scenario(baseline, 0.05, 0.05, 0.05),
                        scenario(baseline, -0.05, -0.05, -0.05),
                    ],
                }
            )
        ),
        graph(
            px.bar(sensitivity, x="factor", y="plus_one_percentage_point"),
            "Sensitivity · one additional percentage point",
        ),
    ]


@app.callback(
    Output("download", "data"),
    Input("export", "n_clicks"),
    State("page", "data"),
    State("dates", "start_date"),
    State("dates", "end_date"),
    State("state", "value"),
    State("category", "value"),
    State("seller", "value"),
    prevent_initial_call=True,
)
@pinned_release
def export(n, page, start, end, state, category, seller=None):
    if not n:
        return no_update
    key = {0: "monthly", 1: "monthly", 2: "segments", 3: "products", 4: "operations", 5: "regions"}.get(page, "kpi")
    return dcc.send_data_frame(
        get_snapshot(start, end, state, category, seller)[key].to_csv, f"revenueiq_{key}.csv", index=False
    )


@app.callback(
    Output("release-status", "children"),
    Output("release-generation", "data"),
    Input("release-watch", "n_intervals"),
    State("release-generation", "data"),
)
@pinned_release
def release_status(tick, previous):
    release = current_release(ENGINE)
    return (
        "Historical dataset · Last analysis: "
        + datetime.fromisoformat(
            json.loads(report_path("refresh_log.json").read_text())[-1]["started_at_utc"]
        ).strftime("%d %b %Y, %H:%M UTC"),
        release if release != previous else no_update,
    )


def drill_value(kind, click):
    if not click or not click.get("points"):
        return None
    point = click["points"][0]
    if kind == "state":
        return point.get("hovertext") or point.get("x")
    if kind == "category":
        return point.get("y") if isinstance(point.get("y"), str) else point.get("x")
    return point.get("x")


@app.callback(
    Output("state", "value", allow_duplicate=True),
    Output("category", "value", allow_duplicate=True),
    Output("seller", "value", allow_duplicate=True),
    Output("drill-feedback", "children"),
    Input({"type": "drill", "kind": ALL, "name": ALL}, "clickData"),
    prevent_initial_call=True,
)
def drill(clicks):
    triggered = ctx.triggered_id
    if not triggered:
        return no_update, no_update, no_update, no_update
    # Resolve the structured ID directly: Unicode graph titles can differ
    # between Dash's serialized trigger key and its input lookup key.
    payload = next(
        (item.get("value") for item in ctx.inputs_list[0] if item["id"] == triggered), None
    )
    if not payload:
        return no_update, no_update, no_update, no_update
    kind = triggered["kind"]
    value = drill_value(kind, payload)
    if not value:
        return no_update, no_update, no_update, no_update
    return (
        value if kind == "state" else no_update,
        value if kind == "category" else no_update,
        value if kind == "seller" else no_update,
        f"Exploring {kind}: {str(value).replace('_', ' ')} · filters apply to all selected-basket views. Reset filters to return.",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)
