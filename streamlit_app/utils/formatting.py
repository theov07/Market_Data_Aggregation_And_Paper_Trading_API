"""
Formatting helpers.
"""


def fmt_price(value, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def fmt_qty(value, decimals: int = 4) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def side_badge(side: str) -> str:
    cls = "badge-green" if side == "buy" else "badge-red"
    return f'<span class="badge {cls}">{side.upper()}</span>'


def status_badge(status: str) -> str:
    mapping = {"open": "badge-blue", "filled": "badge-green",
               "cancelled": "badge-orange", "rejected": "badge-red"}
    cls = mapping.get(status, "badge-gray")
    return f'<span class="badge {cls}">{status.upper()}</span>'
