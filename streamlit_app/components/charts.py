"""
Plotly chart factories for the dashboard.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional


_DARK = dict(
    paper_bgcolor="#0f1117",
    plot_bgcolor="#0f1117",
    font_color="#94a3b8",
    xaxis=dict(gridcolor="#1e2230", zerolinecolor="#1e2230"),
    yaxis=dict(gridcolor="#1e2230", zerolinecolor="#1e2230"),
    margin=dict(l=30, r=20, t=30, b=30),
)


def dark_layout(**kwargs) -> dict:
    base = dict(**_DARK)
    base.update(kwargs)
    return base


# ── Candlestick ───────────────────────────────────────────────────────────────

def candlestick_chart(df: pd.DataFrame, title: str = "") -> go.Figure:
    """
    df must have columns: open_time, open, high, low, close, volume
    """
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["open_time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="OHLC",
        increasing_line_color="#22c55e",
        decreasing_line_color="#ef4444",
    ))
    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        height=400,
        **dark_layout(),
    )
    return fig


# ── Line chart ────────────────────────────────────────────────────────────────

def line_chart(
    x: list,
    y: list,
    title: str = "",
    yaxis_title: str = "",
    color: str = "#3b82f6",
    height: int = 300,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode="lines",
        line=dict(color=color, width=2),
        name=yaxis_title,
    ))
    fig.update_layout(
        title=title,
        yaxis_title=yaxis_title,
        height=height,
        **dark_layout(),
    )
    return fig


def multi_line_chart(
    series: dict[str, tuple[list, list]],   # name -> (x, y)
    title: str = "",
    yaxis_title: str = "",
    height: int = 320,
) -> go.Figure:
    colors = ["#3b82f6", "#22c55e", "#f59e0b", "#a78bfa", "#f43f5e"]
    fig = go.Figure()
    for i, (name, (x, y)) in enumerate(series.items()):
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode="lines",
            line=dict(color=colors[i % len(colors)], width=2),
            name=name,
        ))
    fig.update_layout(
        title=title,
        yaxis_title=yaxis_title,
        height=height,
        **dark_layout(),
    )
    return fig


# ── Bar chart ─────────────────────────────────────────────────────────────────

def bar_chart(
    x: list,
    y: list,
    title: str = "",
    color: str = "#3b82f6",
    height: int = 280,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=y, marker_color=color, name=""))
    fig.update_layout(title=title, height=height, showlegend=False, **dark_layout())
    return fig


# ── Pie chart ─────────────────────────────────────────────────────────────────

def pie_chart(labels: list, values: list, title: str = "", height: int = 280) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.45,
        marker=dict(colors=["#3b82f6", "#22c55e", "#f59e0b", "#a78bfa", "#f43f5e"]),
        textfont=dict(color="#e2e8f0"),
    ))
    fig.update_layout(title=title, height=height, **dark_layout())
    return fig


# ── Spread gauge ──────────────────────────────────────────────────────────────

def spread_gauge(spread: float, mid: float, title: str = "Spread") -> go.Figure:
    pct = (spread / mid * 100) if mid else 0
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number=dict(suffix="%", font=dict(color="#e2e8f0", size=28)),
        gauge=dict(
            axis=dict(range=[0, 0.5], tickcolor="#555"),
            bar=dict(color="#3b82f6"),
            bgcolor="#1e2230",
            bordercolor="#2d3348",
            steps=[
                dict(range=[0, 0.1],  color="#14532d"),
                dict(range=[0.1, 0.3], color="#713f12"),
                dict(range=[0.3, 0.5], color="#7f1d1d"),
            ],
        ),
        title=dict(text=title, font=dict(color="#94a3b8", size=14)),
    ))
    fig.update_layout(height=220, **dark_layout())
    return fig


# ── Volume bars ───────────────────────────────────────────────────────────────

def trade_volume_bars(trades: list, height: int = 250) -> go.Figure:
    """trades: list of TradeSnapshot."""
    buy_vol  = sum(t.quantity for t in trades if t.side == "buy")
    sell_vol = sum(t.quantity for t in trades if t.side == "sell")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Buy"], y=[buy_vol],  marker_color="#22c55e", name="Buy"))
    fig.add_trace(go.Bar(x=["Sell"], y=[sell_vol], marker_color="#ef4444", name="Sell"))
    fig.update_layout(
        title="Trade Volume (session)",
        height=height,
        barmode="group",
        **dark_layout(),
    )
    return fig


# ── Order book ladder ─────────────────────────────────────────────────────────

def order_book_bars(
    bid_price: float, bid_qty: float,
    ask_price: float, ask_qty: float,
    height: int = 200,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Best Bid"], y=[bid_qty], marker_color="#22c55e", name="Bid"))
    fig.add_trace(go.Bar(x=["Best Ask"], y=[ask_qty], marker_color="#ef4444", name="Ask"))
    annotation_text = f"Bid {bid_price:,.2f} / Ask {ask_price:,.2f}"
    fig.update_layout(
        title=annotation_text,
        height=height,
        showlegend=True,
        **dark_layout(),
    )
    return fig
