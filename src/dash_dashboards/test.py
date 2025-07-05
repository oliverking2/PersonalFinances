"""Dashboard Example."""

from typing import Any, Tuple

import pandas as pd
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import dash_bootstrap_components as dbc

# Sample data
df = pd.DataFrame(
    {
        "date": pd.date_range("2025-01-01", periods=12, freq="ME"),
        "transactions": [120, 150, 90, 200, 230, 180, 210, 190, 220, 240, 260, 300],
    }
)

# Initialise Dash
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    url_base_pathname="/dashboard/",  # if you want to serve it under /dashboard/
)
server = app.server

config = {
    "displaylogo": False,  # hide the Plotly logo
    "displayModeBar": True,  # show the toolbar on hover
    "modeBarButtonsToRemove": [
        "select2d",  # rectangle-select
        "lasso2d",  # free-draw select
        "zoom2d",  # zoom button
        "zoomIn2d",  # zoom in
        "zoomOut2d",  # zoom out
        "pan2d",  # pan
        "autoScale2d",  # reset axes
    ],
    "scrollZoom": False,  # disable scroll-to-zoom
}

# Layout
app.layout = dbc.Container(
    [
        html.H1("Financial Dashboard"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Transaction range"),
                        dcc.RangeSlider(
                            id="range-slider",
                            min=df.transactions.min(),
                            max=df.transactions.max(),
                            step=10,
                            marks=None,
                            value=[df.transactions.min(), df.transactions.max()],
                        ),
                    ],
                    width=12,
                )
            ],
            className="mb-4",
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="line-chart", config=config), width=6),
                dbc.Col(dcc.Graph(id="bar-chart", config=config), width=6),
            ]
        ),
    ],
    fluid=True,
)


# Callbacks
@app.callback(
    Output("line-chart", "figure"), Output("bar-chart", "figure"), Input("range-slider", "value")
)
def update_charts(txn_range: Any) -> Tuple[Any, Any]:
    """Update charts."""
    low, high = txn_range
    dff = df[(df.transactions >= low) & (df.transactions <= high)]
    # build figures
    line_fig = px.line(
        dff, x="date", y="transactions", title="Monthly Transactions (Line)", markers=True
    )
    bar_fig = px.bar(
        dff, x="date", y="transactions", title="Monthly Transactions (Bar)", text="transactions"
    )

    for fig in (line_fig, bar_fig):
        fig.update_layout(dragmode=False, hovermode="x unified")
        for trace in fig.data:
            trace.name = "Transactions"
        fig.update_traces(hovertemplate="%{y}<extra></extra>")
        fig.update_layout(
            hoverlabel=dict(
                font=dict(size=12),
                bgcolor="white",
                bordercolor="gray",
            )
        )

    # keep your text above the bars
    bar_fig.update_traces(texttemplate="%{text}", textposition="outside")
    bar_fig.update_layout(margin=dict(b=20))

    return line_fig, bar_fig


if __name__ == "__main__":
    app.run(debug=False, port=8055)
