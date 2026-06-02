"""
Structure Sniper — Professional Trading Journal
================================================
Full dark-mode Streamlit dashboard with:
  • Tab navigation (Overview / Log Trade / Trade History / Advanced Analytics)
  • Persistent PostgreSQL database (Supabase)
  • Colour-coded trade table (green wins / red losses)
  • R-multiple distribution histogram
  • Running drawdown chart
  • Monthly performance heat-map
  • Summary banner with key metrics
"""

from __future__ import annotations

import calendar
import psycopg2
from psycopg2 import extras
from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─── Config ────────────────────────────────────────────────────────────────────

APP_TITLE = "Structure Sniper — Trading Journal"

GREEN = "#00C896"
RED = "#EF5350"
AMBER = "#FFA726"
BLUE = "#42A5F5"
BG = "#0B0E17"
BG2 = "#141824"
BG3 = "#1C2235"
TEXT = "#E8EAF0"
TEXT2 = "#8B92A8"
BORDER = "#252D3D"

# ─── Custom CSS ────────────────────────────────────────────────────────────────

CUSTOM_CSS = f"""
<style>
/* ── Global resets ── */
html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}

/* ── Banner ── */
.banner {{
    background: {BG2};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1.25rem 1.75rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
}}
.banner-title {{
    font-size: 22px;
    font-weight: 600;
    color: {TEXT};
    letter-spacing: -0.4px;
}}
.banner-sub {{
    font-size: 13px;
    color: {TEXT2};
    margin-top: 3px;
}}
.banner-stats {{
    display: flex;
    gap: 2rem;
    flex-wrap: wrap;
}}
.bstat {{
    text-align: right;
}}
.bstat-value {{
    font-size: 22px;
    font-weight: 600;
    color: {TEXT};
}}
.bstat-label {{
    font-size: 11px;
    color: {TEXT2};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.bstat-value.pos {{ color: {GREEN}; }}
.bstat-value.neg {{ color: {RED}; }}
.bstat-value.neu {{ color: {AMBER}; }}

/* ── KPI cards ── */
.kpi-row {{
    display: flex;
    gap: 10px;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
}}
.kpi-card {{
    flex: 1;
    min-width: 140px;
    background: {BG2};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1rem 1.25rem;
}}
.kpi-label {{
    font-size: 11px;
    font-weight: 500;
    color: {TEXT2};
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}}
.kpi-value {{
    font-size: 24px;
    font-weight: 600;
    color: {TEXT};
    line-height: 1;
}}
.kpi-sub {{
    font-size: 12px;
    color: {TEXT2};
    margin-top: 4px;
}}
.kpi-value.pos {{ color: {GREEN}; }}
.kpi-value.neg {{ color: {RED}; }}

/* ── Section headers ── */
.section-header {{
    font-size: 14px;
    font-weight: 600;
    color: {TEXT};
    letter-spacing: -0.2px;
    margin: 1.25rem 0 0.75rem;
    padding-bottom: 8px;
    border-bottom: 1px solid {BORDER};
}}

/* ── Streak badges ── */
.streak-win {{
    display: inline-block;
    background: rgba(0,200,150,0.15);
    color: {GREEN};
    border: 1px solid rgba(0,200,150,0.3);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 12px;
    font-weight: 600;
}}
.streak-loss {{
    display: inline-block;
    background: rgba(239,83,80,0.15);
    color: {RED};
    border: 1px solid rgba(239,83,80,0.3);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 12px;
    font-weight: 600;
}}
.streak-neutral {{
    display: inline-block;
    background: rgba(139,146,168,0.15);
    color: {TEXT2};
    border: 1px solid {BORDER};
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 12px;
    font-weight: 600;
}}

/* ── Tab styling ── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    background: {BG};
    border-bottom: 1px solid {BORDER};
    padding-bottom: 0;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent;
    border: none;
    color: {TEXT2};
    font-size: 13px;
    font-weight: 500;
    padding: 8px 16px;
    border-radius: 6px 6px 0 0;
}}
.stTabs [aria-selected="true"] {{
    background: {BG2} !important;
    color: {TEXT} !important;
    border-bottom: 2px solid {GREEN} !important;
}}
</style>
"""

# ─── Database ──────────────────────────────────────────────────────────────────

import psycopg2
from psycopg2 import extras
import streamlit as st


def get_connection():
    """Establishes a connection to the PostgreSQL database, verifying it is active."""
    # Check if connection already exists in Streamlit session state
    if 'db_conn' in st.session_state and st.session_state.db_conn is not None:
        try:
            # Test if the connection is still alive
            with st.session_state.db_conn.cursor() as tmp_curr:
                tmp_curr.execute("SELECT 1;")
            return st.session_state.db_conn
        except (psycopg2.InterfaceError, psycopg2.OperationalError):
            # If it's dead, clear it out so we can establish a fresh one
            st.session_state.db_conn = None

    # Connect to the database using your Streamlit secrets
    try:
        conn = psycopg2.connect(
            host=st.secrets["DB_HOST"],
            database=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            port=int(st.secrets["DB_PORT"])
        )
        # Store it globally in session state so it persists across button clicks
        st.session_state.db_conn = conn
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        raise e


def get_cursor():
    """Get a cursor from the connection."""
    conn = get_connection()
    return conn, conn.cursor(cursor_factory=extras.RealDictCursor)


def initialize_db() -> None:
    conn, cursor = get_cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                trade_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT,
                timeframe TEXT,
                session TEXT,
                strategy TEXT,
                direction TEXT NOT NULL,
                status TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                position_size REAL NOT NULL,
                fees REAL NOT NULL,
                gross_pnl REAL,
                net_pnl REAL,
                risk_amount REAL,
                planned_rr REAL,
                r_multiple REAL,
                outcome TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to initialize database: {e}")
    finally:
        cursor.close()
        conn.close()


def load_trades() -> pd.DataFrame:
    conn, cursor = get_cursor()
    try:
        cursor.execute("SELECT * FROM trades ORDER BY trade_date, id")
        rows = cursor.fetchall()
        df = pd.DataFrame([dict(row) for row in rows]) if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to load trades: {e}")
        df = pd.DataFrame()
    finally:
        cursor.close()
        conn.close()
    
    if df.empty:
        return df
    numeric_cols = [
        "entry_price", "exit_price", "stop_loss", "take_profit",
        "position_size", "fees", "gross_pnl", "net_pnl",
        "risk_amount", "planned_rr", "r_multiple",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    return df


def save_trade(trade: dict) -> None:
    conn, cursor = get_cursor()
    try:
        cursor.execute("""
            INSERT INTO trades (
                trade_date, symbol, market, timeframe, session, strategy, direction,
                status, entry_price, exit_price, stop_loss, take_profit, position_size,
                fees, gross_pnl, net_pnl, risk_amount, planned_rr, r_multiple, outcome,
                notes, created_at
            ) VALUES (
                %(trade_date)s, %(symbol)s, %(market)s, %(timeframe)s, %(session)s, %(strategy)s, %(direction)s,
                %(status)s, %(entry_price)s, %(exit_price)s, %(stop_loss)s, %(take_profit)s, %(position_size)s,
                %(fees)s, %(gross_pnl)s, %(net_pnl)s, %(risk_amount)s, %(planned_rr)s, %(r_multiple)s, %(outcome)s,
                %(notes)s, %(created_at)s
            )
        """, trade)
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to save trade: {e}")
    finally:
        cursor.close()
        conn.close()


def close_open_trade(trade_id: int, exit_price: float, fees: float,
                     additional_notes: str, append_notes: bool) -> None:
    conn, cursor = get_cursor()
    try:
        cursor.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
        trade = cursor.fetchone()
        if trade is None:
            raise ValueError("Trade not found.")
        if trade["status"] != "Open":
            raise ValueError("Only open trades can be closed here.")

        metrics = calculate_trade_metrics(
            direction=str(trade["direction"]),
            entry_price=float(trade["entry_price"]),
            exit_price=float(exit_price),
            stop_loss=float(trade["stop_loss"]),
            take_profit=float(trade["take_profit"]),
            position_size=float(trade["position_size"]),
            fees=float(fees),
            status="Closed",
        )

        existing = (trade["notes"] or "").strip()
        new_note = additional_notes.strip()
        if append_notes:
            merged = f"{existing}\n\nClose update: {new_note}".strip() if new_note else existing
        else:
            merged = new_note if new_note else existing

        cursor.execute("""
            UPDATE trades SET
                status=%s, exit_price=%s, fees=%s, gross_pnl=%s, net_pnl=%s,
                risk_amount=%s, planned_rr=%s, r_multiple=%s, outcome=%s, notes=%s
            WHERE id=%s
        """, (
            "Closed", float(exit_price), float(fees),
            metrics["gross_pnl"], metrics["net_pnl"], metrics["risk_amount"],
            metrics["planned_rr"], metrics["r_multiple"], metrics["outcome"],
            merged, trade_id,
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ─── Calculations ──────────────────────────────────────────────────────────────

def calculate_trade_metrics(
    direction: str, entry_price: float, exit_price: Optional[float],
    stop_loss: float, take_profit: float, position_size: float,
    fees: float, status: str,
) -> dict:
    d = direction.lower()
    risk_per_unit = (entry_price - stop_loss) if d == "long" else (stop_loss - entry_price)
    reward_per_unit = (take_profit - entry_price) if d == "long" else (entry_price - take_profit)
    risk_amount = risk_per_unit * position_size
    planned_rr = reward_per_unit / risk_per_unit if risk_per_unit > 0 else None

    if status == "Open" or exit_price is None:
        return {"gross_pnl": None, "net_pnl": None,
                "risk_amount": risk_amount if risk_amount > 0 else None,
                "planned_rr": planned_rr, "r_multiple": None, "outcome": "Open"}

    price_change = (exit_price - entry_price) if d == "long" else (entry_price - exit_price)
    gross_pnl = price_change * position_size
    net_pnl = gross_pnl - fees
    outcome = "Win" if net_pnl > 0 else ("Loss" if net_pnl < 0 else "Breakeven")
    r_multiple = net_pnl / risk_amount if risk_amount and risk_amount > 0 else None

    return {"gross_pnl": gross_pnl, "net_pnl": net_pnl,
            "risk_amount": risk_amount if risk_amount > 0 else None,
            "planned_rr": planned_rr, "r_multiple": r_multiple, "outcome": outcome}


def validate_trade(direction, entry_price, stop_loss, take_profit,
                   position_size, status, exit_price) -> list[str]:
    errors = []
    if position_size <= 0:
        errors.append("Position size must be greater than zero.")
    if direction == "Long":
        if stop_loss >= entry_price:
            errors.append("Long trade: stop loss must be below entry.")
        if take_profit <= entry_price:
            errors.append("Long trade: take profit must be above entry.")
    else:
        if stop_loss <= entry_price:
            errors.append("Short trade: stop loss must be above entry.")
        if take_profit >= entry_price:
            errors.append("Short trade: take profit must be below entry.")
    if status == "Closed":
        if exit_price is None:
            errors.append("Exit price required for closed trade.")
        elif exit_price <= 0:
            errors.append("Exit price must be greater than zero.")
    return errors


def safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0


def normalize_label(value, fallback: str = "Unspecified") -> str:
    if value is None:
        return fallback
    if isinstance(value, float) and np.isnan(value):
        return fallback
    text = str(value).strip()
    return text if text else fallback


# ─── Summary metrics ───────────────────────────────────────────────────────────

def compute_summary(closed: pd.DataFrame) -> dict:
    if closed.empty:
        return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
                "net_pnl": 0.0, "avg_r": 0.0, "profit_factor": 0.0,
                "max_dd": 0.0, "streak": 0, "streak_type": "none"}

    total = len(closed)
    wins = int((closed["outcome"] == "Win").sum())
    losses = int((closed["outcome"] == "Loss").sum())
    win_rate = safe_div(wins, total) * 100
    net_pnl = float(closed["net_pnl"].sum())
    avg_r = float(closed["r_multiple"].dropna().mean()) if closed["r_multiple"].notna().any() else 0.0

    gp = float(closed.loc[closed["net_pnl"] > 0, "net_pnl"].sum())
    gl = abs(float(closed.loc[closed["net_pnl"] < 0, "net_pnl"].sum()))
    profit_factor = safe_div(gp, gl) if gl > 0 else float("inf")

    eq = closed.sort_values(["trade_date", "id"])["net_pnl"].cumsum()
    peak = eq.cummax().clip(lower=0.0)
    dd = eq - peak
    max_dd = float(dd.min())

    outcomes = closed.sort_values(["trade_date", "id"])["outcome"].tolist()
    streak = 0
    streak_type = "none"
    if outcomes:
        last = outcomes[-1]
        streak_type = "win" if last == "Win" else ("loss" if last == "Loss" else "none")
        for o in reversed(outcomes):
            if o == last:
                streak += 1
            else:
                break

    return {"total": total, "wins": wins, "losses": losses, "win_rate": win_rate,
            "net_pnl": net_pnl, "avg_r": avg_r, "profit_factor": profit_factor,
            "max_dd": max_dd, "streak": streak, "streak_type": streak_type}


# ─── Charts ────────────────────────────────────────────────────────────────────

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, size=12),
    margin=dict(l=10, r=10, t=36, b=10),
    xaxis=dict(gridcolor=BORDER, linecolor=BORDER, showgrid=True),
    yaxis=dict(gridcolor=BORDER, linecolor=BORDER, showgrid=True),
)


def chart_equity(closed: pd.DataFrame) -> go.Figure:
    df = closed.sort_values(["trade_date", "id"]).copy()
    df["equity"] = df["net_pnl"].cumsum()
    df["colour"] = df["equity"].apply(lambda v: GREEN if v >= 0 else RED)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["trade_date"], y=df["equity"],
        mode="lines+markers",
        line=dict(color=GREEN, width=2),
        marker=dict(size=5, color=df["colour"]),
        fill="tozeroy",
        fillcolor="rgba(0,200,150,0.08)",
        name="Equity",
    ))
    fig.update_layout(title="Equity Curve", **CHART_LAYOUT)
    return fig


def chart_drawdown(closed: pd.DataFrame) -> go.Figure:
    df = closed.sort_values(["trade_date", "id"]).copy()
    df["equity"] = df["net_pnl"].cumsum()
    df["peak"] = df["equity"].cummax().clip(lower=0.0)
    df["drawdown"] = df["equity"] - df["peak"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["trade_date"], y=df["drawdown"],
        mode="lines",
        line=dict(color=RED, width=2),
        fill="tozeroy",
        fillcolor="rgba(239,83,80,0.12)",
        name="Drawdown",
    ))
    fig.update_layout(title="Running Drawdown", **CHART_LAYOUT)
    return fig


def chart_rolling_winrate(closed: pd.DataFrame) -> go.Figure:
    df = closed.sort_values(["trade_date", "id"]).copy()
    df["is_win"] = (df["outcome"] == "Win").astype(int)
    df["rolling_wr"] = df["is_win"].rolling(20, min_periods=1).mean() * 100

    fig = go.Figure()
    fig.add_hline(y=50, line_dash="dot", line_color=TEXT2, opacity=0.5)
    fig.add_trace(go.Scatter(
        x=df["trade_date"], y=df["rolling_wr"],
        mode="lines", line=dict(color=BLUE, width=2),
        name="Win Rate (20)",
    ))
    fig.update_layout(title="Rolling Win Rate (20 trades)", yaxis_range=[0, 100], **CHART_LAYOUT)
    return fig


def chart_r_histogram(closed: pd.DataFrame) -> go.Figure:
    r_vals = closed["r_multiple"].dropna()
    if r_vals.empty:
        fig = go.Figure()
        fig.update_layout(title="R-Multiple Distribution — no data yet", **CHART_LAYOUT)
        return fig

    colours = [GREEN if v >= 0 else RED for v in r_vals]
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=r_vals, nbinsx=30,
        marker_color=colours,
        opacity=0.8,
        name="R-Multiple",
    ))
    fig.add_vline(x=0, line_color=TEXT2, line_dash="dash", opacity=0.6)
    fig.add_vline(x=1, line_color=GREEN, line_dash="dot", opacity=0.8,
                  annotation_text="1R", annotation_position="top right")
    fig.update_layout(title="R-Multiple Distribution", bargap=0.05, **CHART_LAYOUT)
    return fig


def chart_session_pnl(closed: pd.DataFrame) -> go.Figure:
    df = closed.copy()
    df["session_label"] = df["session"].apply(normalize_label)
    agg = df.groupby("session_label")["net_pnl"].sum().reset_index().sort_values("net_pnl", ascending=False)
    colours = [GREEN if v >= 0 else RED for v in agg["net_pnl"]]
    fig = go.Figure(go.Bar(x=agg["session_label"], y=agg["net_pnl"],
                           marker_color=colours, name="Net PnL"))
    fig.update_layout(title="Net PnL by Session", **CHART_LAYOUT)
    return fig


def chart_strategy_pnl(closed: pd.DataFrame) -> go.Figure:
    df = closed.copy()
    df["strategy_label"] = df["strategy"].apply(normalize_label)
    agg = df.groupby("strategy_label")["net_pnl"].sum().reset_index().sort_values("net_pnl", ascending=False)
    colours = [GREEN if v >= 0 else RED for v in agg["net_pnl"]]
    fig = go.Figure(go.Bar(x=agg["strategy_label"], y=agg["net_pnl"],
                           marker_color=colours, name="Net PnL"))
    fig.update_layout(title="Net PnL by Strategy", **CHART_LAYOUT)
    return fig


def chart_monthly_heatmap(closed: pd.DataFrame) -> go.Figure:
    df = closed.copy()
    df["year"] = df["trade_date"].dt.year
    df["month"] = df["trade_date"].dt.month
    pivot = df.groupby(["year", "month"])["net_pnl"].sum().unstack(fill_value=0)

    all_months = list(range(1, 13))
    for m in all_months:
        if m not in pivot.columns:
            pivot[m] = 0.0
    pivot = pivot[all_months]

    month_names = [calendar.month_abbr[m] for m in all_months]
    years = [str(y) for y in pivot.index.tolist()]
    z = pivot.values.tolist()

    text = [[f"{v:,.0f}" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z, x=month_names, y=years,
        text=text, texttemplate="%{text}",
        colorscale=[[0, "#8B1A1A"], [0.5, "#1C2235"], [1, "#1A5C3A"]],
        showscale=True,
        colorbar=dict(title="PnL", tickfont=dict(color=TEXT)),
    ))
    fig.update_layout(title="Monthly Performance Heat-Map", **CHART_LAYOUT,
                      xaxis=dict(side="top"), yaxis=dict(autorange="reversed"))
    return fig


# ─── Trade table with colour coding ───────────────────────────────────────────

def styled_trade_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No trades match the current filters.")
        return

    display = df.copy()
    display["trade_date"] = display["trade_date"].dt.date

    cols = ["id", "trade_date", "symbol", "session", "strategy", "direction",
            "status", "entry_price", "exit_price", "stop_loss", "take_profit",
            "position_size", "fees", "net_pnl", "r_multiple", "outcome", "notes"]

    display = display[[c for c in cols if c in display.columns]]

    def row_colour(row):
        outcome = row.get("outcome", "")
        if outcome == "Win":
            bg = "rgba(0,200,150,0.08)"
        elif outcome == "Loss":
            bg = "rgba(239,83,80,0.08)"
        else:
            bg = ""
        return [f"background-color: {bg}"] * len(row)

    def r_colour(val):
        if pd.isna(val):
            return ""
        return f"color: {GREEN}" if val >= 0 else f"color: {RED}"

    def pnl_colour(val):
        if pd.isna(val):
            return ""
        return f"color: {GREEN}; font-weight:600" if val >= 0 else f"color: {RED}; font-weight:600"

    styled = (
        display.style
        .apply(row_colour, axis=1)
        .map(r_colour, subset=["r_multiple"])
        .map(pnl_colour, subset=["net_pnl"])
        .format({
            "entry_price": "{:.5f}",
            "exit_price": "{:.5f}",
            "stop_loss": "{:.5f}",
            "take_profit": "{:.5f}",
            "net_pnl": "{:,.2f}",
            "r_multiple": "{:.2f}",
            "position_size": "{:.4f}",
            "fees": "{:.2f}",
        }, na_rep="—")
    )

    csv = display.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download CSV", csv, "trades.csv", "text/csv")
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ─── Filters ───────────────────────────────────────────────────────────────────

def apply_filters(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades

    with st.sidebar:
        st.markdown(f"### Filters")
        min_d = trades["trade_date"].min().date()
        max_d = trades["trade_date"].max().date()
        date_range = st.date_input("Date range", value=(min_d, max_d),
                                   min_value=min_d, max_value=max_d)

        symbols = sorted(trades["symbol"].dropna().unique().tolist())
        sessions = sorted([s for s in trades["session"].dropna().unique() if s])
        strategies = sorted([s for s in trades["strategy"].dropna().unique() if s])

        sel_sym = st.multiselect("Symbol", symbols, default=symbols)
        sel_ses = st.multiselect("Session", sessions, default=sessions)
        sel_str = st.multiselect("Strategy", strategies, default=strategies)

        st.divider()
        if st.button("🗑 Delete ALL trades", type="secondary"):
            conn, cursor = get_cursor()
            try:
                cursor.execute("DELETE FROM trades")
                conn.commit()
                st.success("All trades deleted.")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"Failed to delete trades: {e}")
            finally:
                cursor.close()
                conn.close()

    filtered = trades.copy()
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        s, e = date_range
        filtered = filtered[(filtered["trade_date"].dt.date >= s) &
                            (filtered["trade_date"].dt.date <= e)]
    if sel_sym:
        filtered = filtered[filtered["symbol"].isin(sel_sym)]
    if sel_ses:
        filtered = filtered[filtered["session"].isin(sel_ses)]
    if sel_str:
        filtered = filtered[filtered["strategy"].isin(sel_str)]
    return filtered


# ─── Banner ────────────────────────────────────────────────────────────────────

def render_banner(s: dict) -> None:
    pnl_cls = "pos" if s["net_pnl"] >= 0 else "neg"
    pf_str = "∞" if s["profit_factor"] == float("inf") else f"{s['profit_factor']:.2f}"
    avg_r_str = f"{s['avg_r']:.2f}R" if s["total"] > 0 else "—"

    if s["streak_type"] == "win":
        streak_html = f'<span class="streak-win">🔥 {s["streak"]} win streak</span>'
    elif s["streak_type"] == "loss":
        streak_html = f'<span class="streak-loss">⚠ {s["streak"]} loss streak</span>'
    else:
        streak_html = f'<span class="streak-neutral">No streak</span>'

    st.markdown(f"""
    <div class="banner">
      <div>
        <div class="banner-title">📊 Structure Sniper — Trading Journal</div>
        <div class="banner-sub">
          {s['total']} closed trades &nbsp;|&nbsp;
          {s['wins']}W / {s['losses']}L &nbsp;|&nbsp;
          {streak_html}
        </div>
      </div>
      <div class="banner-stats">
        <div class="bstat">
          <div class="bstat-value {pnl_cls}">{s['net_pnl']:,.2f}</div>
          <div class="bstat-label">Net PnL</div>
        </div>
        <div class="bstat">
          <div class="bstat-value">{s['win_rate']:.1f}%</div>
          <div class="bstat-label">Win Rate</div>
        </div>
        <div class="bstat">
          <div class="bstat-value">{avg_r_str}</div>
          <div class="bstat-label">Avg R</div>
        </div>
        <div class="bstat">
          <div class="bstat-value">{pf_str}</div>
          <div class="bstat-label">Profit Factor</div>
        </div>
        <div class="bstat">
          <div class="bstat-value neg">{s['max_dd']:,.2f}</div>
          <div class="bstat-label">Max Drawdown</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─── KPI row ───────────────────────────────────────────────────────────────────

def render_kpis(s: dict) -> None:
    pnl_cls = "pos" if s["net_pnl"] >= 0 else "neg"
    pf_str = "∞" if s["profit_factor"] == float("inf") else f"{s['profit_factor']:.2f}"

    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">Total Trades</div>
        <div class="kpi-value">{s['total']}</div>
        <div class="kpi-sub">{s['wins']}W &nbsp;·&nbsp; {s['losses']}L</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Win Rate</div>
        <div class="kpi-value">{s['win_rate']:.1f}%</div>
        <div class="kpi-sub">of closed trades</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Net PnL</div>
        <div class="kpi-value {pnl_cls}">{s['net_pnl']:,.2f}</div>
        <div class="kpi-sub">cumulative</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Avg R-Multiple</div>
        <div class="kpi-value">{s['avg_r']:.2f}R</div>
        <div class="kpi-sub">per trade</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Profit Factor</div>
        <div class="kpi-value">{pf_str}</div>
        <div class="kpi-sub">gross profit ÷ loss</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Max Drawdown</div>
        <div class="kpi-value neg">{s['max_dd']:,.2f}</div>
        <div class="kpi-sub">peak-to-trough</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Log Trade tab ─────────────────────────────────────────────────────────────

def tab_log_trade(all_trades: pd.DataFrame) -> bool:
    st.markdown('<div class="section-header">Log a New Trade</div>', unsafe_allow_html=True)

    with st.form("add_trade_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        trade_date = c1.date_input("Date", value=date.today())
        symbol = c2.text_input("Symbol", placeholder="EURUSD, GBPUSD …")
        market = c3.selectbox("Market", ["Forex", "Crypto", "Stocks", "Futures", "Indices", "Other"])

        c4, c5, c6 = st.columns(3)
        timeframe = c4.text_input("Timeframe", placeholder="H1, H4, D1 …")
        session = c5.text_input("Session", placeholder="London, New York …")
        strategy = c6.selectbox(
            "Strategy",
            ["Strategy A — Trend Continuation",
             "Strategy B — Consolidation Breakout",
             "Strategy C — Trend Line Rejection",
             "Other"],
        )

        c7, c8, c9 = st.columns(3)
        direction = c7.selectbox("Direction", ["Long", "Short"])
        status = c8.selectbox("Status", ["Closed", "Open"])
        position_size = c9.number_input("Position Size", min_value=0.0001,
                                        value=1.0, step=0.1, format="%.4f")

        c10, c11, c12 = st.columns(3)
        entry_price = c10.number_input("Entry Price", min_value=0.0, value=0.0, format="%.6f")
        stop_loss = c11.number_input("Stop Loss", min_value=0.0, value=0.0, format="%.6f")
        take_profit = c12.number_input("Take Profit", min_value=0.0, value=0.0, format="%.6f")

        c13, c14 = st.columns(2)
        exit_price = c13.number_input("Exit Price", min_value=0.0, value=0.0, format="%.6f")
        fees = c14.number_input("Fees / Commission", min_value=0.0, value=0.0, format="%.2f")

        notes = st.text_area(
            "Trade Notes",
            placeholder=(
                "Why did you take this trade?\n"
                "Which strategy condition triggered the entry?\n"
                "How was your execution? What can you improve?"
            ),
            height=130,
        )
        submitted = st.form_submit_button("💾 Save Trade", type="primary")

    if not submitted:
        return False

    symbol = symbol.strip().upper()
    if not symbol:
        st.error("Symbol is required.")
        return False
    if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
        st.error("Entry, stop loss and take profit must all be greater than zero.")
        return False

    norm_exit = None if status == "Open" else (float(exit_price) if exit_price > 0 else None)
    errors = validate_trade(direction, entry_price, stop_loss, take_profit,
                            position_size, status, norm_exit)
    if errors:
        for e in errors:
            st.error(e)
        return False

    metrics = calculate_trade_metrics(direction, entry_price, norm_exit,
                                      stop_loss, take_profit, position_size, fees, status)
    save_trade({
        "trade_date": trade_date.isoformat(), "symbol": symbol, "market": market,
        "timeframe": timeframe.strip().upper(), "session": session.strip(),
        "strategy": strategy.strip(), "direction": direction, "status": status,
        "entry_price": entry_price, "exit_price": norm_exit,
        "stop_loss": stop_loss, "take_profit": take_profit,
        "position_size": position_size, "fees": fees,
        "gross_pnl": metrics["gross_pnl"], "net_pnl": metrics["net_pnl"],
        "risk_amount": metrics["risk_amount"], "planned_rr": metrics["planned_rr"],
        "r_multiple": metrics["r_multiple"], "outcome": metrics["outcome"],
        "notes": notes.strip(), "created_at": datetime.utcnow().isoformat(),
    })
    st.success(f"✅ Trade saved — {symbol} {direction} {status}")
    return True


def tab_update_open(all_trades: pd.DataFrame) -> bool:
    st.markdown('<div class="section-header">Close an Open Trade</div>', unsafe_allow_html=True)
    open_trades = all_trades[all_trades["status"] == "Open"].copy() if not all_trades.empty else pd.DataFrame()

    if open_trades.empty:
        st.info("No open trades. Log a new trade above.")
        return False

    open_trades = open_trades.sort_values(["trade_date", "id"], ascending=[False, False])
    lookup = {int(r["id"]): r for _, r in open_trades.iterrows()}

    def label(tid):
        t = lookup[tid]
        d = pd.to_datetime(t["trade_date"]).date() if pd.notna(t["trade_date"]) else "?"
        return f"#{tid} | {d} | {t['symbol']} | {t['direction']} | Entry {float(t['entry_price']):.5f}"

    sel_id = st.selectbox("Select open trade", list(lookup.keys()), format_func=label)
    sel = lookup[int(sel_id)]

    st.caption(f"SL: {float(sel['stop_loss']):.5f}  ·  TP: {float(sel['take_profit']):.5f}  ·  Size: {float(sel['position_size']):.4f}")

    with st.form("close_trade_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        exit_p = c1.number_input("Exit Price", min_value=0.0,
                                 value=float(sel["entry_price"]), format="%.6f")
        close_fees = c2.number_input("Total Fees", min_value=0.0,
                                     value=float(sel["fees"] or 0), format="%.2f")
        append = st.checkbox("Append note to existing notes", value=True)
        close_note = st.text_area("Close note (optional)", height=80)
        submit = st.form_submit_button("✅ Close Trade", type="primary")

    if not submit:
        return False

    errors = validate_trade(str(sel["direction"]), float(sel["entry_price"]),
                            float(sel["stop_loss"]), float(sel["take_profit"]),
                            float(sel["position_size"]), "Closed", float(exit_p))
    if errors:
        for e in errors:
            st.error(e)
        return False

    try:
        close_open_trade(int(sel_id), float(exit_p), float(close_fees), close_note, append)
        st.success(f"Trade #{sel_id} closed successfully.")
        return True
    except ValueError as exc:
        st.error(str(exc))
        return False


# ─── Advanced analytics tab ────────────────────────────────────────────────────

def tab_advanced(closed: pd.DataFrame) -> None:
    if closed.empty:
        st.info("No closed trades yet.")
        return

    st.markdown('<div class="section-header">Expectancy by Strategy</div>', unsafe_allow_html=True)

    rows = []
    for name, grp in closed.groupby(closed["strategy"].apply(normalize_label)):
        t = len(grp)
        w = int((grp["net_pnl"] > 0).sum())
        l_ = int((grp["net_pnl"] < 0).sum())
        wr = safe_div(w, t)
        lr = safe_div(l_, t)
        aw = float(grp.loc[grp["net_pnl"] > 0, "net_pnl"].mean() or 0)
        al = abs(float(grp.loc[grp["net_pnl"] < 0, "net_pnl"].mean() or 0))
        exp_pnl = wr * aw - lr * al
        exp_r = float(grp["r_multiple"].dropna().mean() or 0)
        rows.append({"Strategy": name, "Trades": t, "Wins": w, "Losses": l_,
                     "Win %": round(wr * 100, 1), "Avg Win": round(aw, 2),
                     "Avg Loss": round(al, 2), "Expectancy PnL": round(exp_pnl, 2),
                     "Expectancy R": round(exp_r, 2)})

    if rows:
        st.dataframe(pd.DataFrame(rows).sort_values("Expectancy PnL", ascending=False),
                     use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">R-Multiple Distribution</div>', unsafe_allow_html=True)
    st.plotly_chart(chart_r_histogram(closed), use_container_width=True)

    st.markdown('<div class="section-header">Monthly Performance Heat-Map</div>', unsafe_allow_html=True)
    st.plotly_chart(chart_monthly_heatmap(closed), use_container_width=True)

    st.markdown('<div class="section-header">Session & Strategy Breakdown</div>', unsafe_allow_html=True)
    ca, cb = st.columns(2)
    ca.plotly_chart(chart_session_pnl(closed), use_container_width=True)
    cb.plotly_chart(chart_strategy_pnl(closed), use_container_width=True)


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide",
                       page_icon="📊", initial_sidebar_state="collapsed")
    initialize_db()

    all_trades = load_trades()
    closed_all = (all_trades[all_trades["status"] == "Closed"]
                  if not all_trades.empty else pd.DataFrame())

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_banner(compute_summary(closed_all))

    # ── Apply filters ONCE here — sidebar widgets created only once ──
    filtered = apply_filters(all_trades) if not all_trades.empty else all_trades
    closed_filtered = (filtered[filtered["status"] == "Closed"]
                       if not filtered.empty else pd.DataFrame())

    tab_ov, tab_log, tab_hist, tab_adv = st.tabs([
        "📊  Overview",
        "➕  Log Trade",
        "📋  Trade History",
        "🔬  Advanced Analytics",
    ])

    # ── Overview ──────────────────────────────────────────────────────
    with tab_ov:
        render_kpis(compute_summary(closed_filtered))
        if closed_filtered.empty:
            st.info("No closed trades yet. Head to **Log Trade** to add your first trade.")
        else:
            c1, c2 = st.columns(2)
            c1.plotly_chart(chart_equity(closed_filtered),   use_container_width=True)
            c2.plotly_chart(chart_drawdown(closed_filtered), use_container_width=True)
            c3, c4 = st.columns(2)
            c3.plotly_chart(chart_rolling_wr(closed_filtered), use_container_width=True)
            c4.plotly_chart(chart_r_hist(closed_filtered),     use_container_width=True)

    # ── Log Trade ─────────────────────────────────────────────────────
    with tab_log:
        saved = tab_log_trade(all_trades)
        if saved:
            all_trades = load_trades()
        st.divider()
        updated = tab_update_open(all_trades)
        if updated:
            all_trades = load_trades()

    # ── Trade History ─────────────────────────────────────────────────
    with tab_hist:
        st.markdown('<div class="section-header">Your Trade History</div>',
                    unsafe_allow_html=True)
        styled_trade_table(filtered)

    # ── Advanced Analytics ────────────────────────────────────────────
    with tab_adv:
        tab_advanced(closed_filtered)
        st.markdown('<div class="section-header">Export</div>',
                    unsafe_allow_html=True)
        export_csv_button(filtered)


if __name__ == "__main__":
    main()
