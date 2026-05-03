"""AI Report Generator — animated self-contained HTML financial dashboard.

Produces a fully standalone HTML file with:
  - Animated KPI cards (fade + scale-in)
  - Chart.js interactive charts with smooth animations
  - AI analysis sections with structured insights
  - DO / DON'T advisory cards (parsed from analyst output)
  - 30/60/90-day action plan grid
  - Zero external dependencies beyond Chart.js CDN
"""

import io
import json
import logging
import re
from typing import Any, Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

FINANCIAL_COLUMNS = {"revenue", "burn_rate", "headcount", "cac", "ltv"}

COLORS = [
    "#6366f1", "#f43f5e", "#3ECF8E", "#f59e0b", "#a855f7",
    "#06b6d4", "#ec4899", "#14b8a6", "#f97316", "#8b5cf6",
]


def _detect_csv_type(df: pd.DataFrame) -> str:
    cols = {c.lower().strip() for c in df.columns}
    return "financial" if FINANCIAL_COLUMNS.issubset(cols) else "generic"


def _safe_val(v: Any) -> Any:
    if isinstance(v, float) and (v != v or abs(v) > 1e15):
        return None
    return v


def _safe_list(lst: list) -> list:
    return [_safe_val(v) for v in lst]


def _fmt(n: float) -> str:
    n = float(n)
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.0f}K"
    return f"${n:.0f}"


def _fmt_plain(n: float) -> str:
    n = float(n)
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n/1_000:.0f}K"
    return f"{n:.1f}"


# ── Chart.js block builder ─────────────────────────────────────────────────────

def _chart_js_block(chart_id: str, chart_type: str, data: dict, options: dict) -> str:
    index_axis = f"indexAxis: '{options['indexAxis']}'," if options.get("indexAxis") else ""
    y_cb = options.get("yAxisCallback", "")
    if y_cb == "currency":
        y_fmt = "callback: v => v>=1e6?'$'+(v/1e6).toFixed(1)+'M':v>=1e3?'$'+(v/1e3).toFixed(0)+'K':'$'+v"
    elif y_cb == "percent":
        y_fmt = "callback: v => v.toFixed(1)+'%'"
    else:
        y_fmt = "callback: v => v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':v"

    return f"""
  (function(){{
    const el = document.getElementById('{chart_id}');
    if (!el) return;
    new Chart(el, {{
      type: '{chart_type}',
      data: {json.dumps(data)},
      options: {{
        {index_axis}
        responsive: true, maintainAspectRatio: false,
        animation: {{ duration: 900, easing: 'easeInOutQuart' }},
        plugins: {{
          legend: {{ labels: {{ color: '#d1d5db', font: {{ size: 11 }} }} }},
          tooltip: {{
            backgroundColor:'#1a1a2e',titleColor:'#f9fafb',bodyColor:'#d1d5db',
            borderColor:'#2d2d4e',borderWidth:1,padding:10,
          }}
        }},
        scales: {{
          x: {{ grid:{{color:'rgba(255,255,255,0.03)'}}, ticks:{{color:'#6b7280',maxRotation:40,font:{{size:9}}}} }},
          y: {{ grid:{{color:'rgba(255,255,255,0.03)'}}, ticks:{{{y_fmt},color:'#6b7280',font:{{size:9}}}} }},
        }}
      }}
    }});
  }})();"""


# ── Analysis text parser ───────────────────────────────────────────────────────

def _parse_sections(text: str) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current = "intro"
    sections[current] = []
    for line in text.strip().split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r"^#{1,3}\s", s):
            current = re.sub(r"^#{1,3}\s*", "", s).strip()
            sections[current] = []
        else:
            sections.setdefault(current, []).append(s)
    return sections


def _lines_to_html(lines: List[str]) -> str:
    out, in_ul = [], False
    for line in lines:
        if line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            item = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line[2:].strip())
            out.append(f"<li>{item}</li>")
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            item = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line)
            out.append(f"<p>{item}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def _analysis_to_html(text: str) -> Tuple[str, str, str, str, str, str]:
    """Parse analysis markdown into (main_html, plan_30, plan_60, plan_90, do_html, dont_html)."""
    sections = _parse_sections(text)

    plan_30_keys = [k for k in sections if "30" in k]
    plan_60_keys = [k for k in sections if "60" in k]
    plan_90_keys = [k for k in sections if "90" in k]
    do_keys      = [k for k in sections if "must do" in k.lower() or "✅" in k]
    dont_keys    = [k for k in sections if "avoid" in k.lower() or "❌" in k]

    excluded = set(plan_30_keys + plan_60_keys + plan_90_keys + do_keys + dont_keys)

    main_html = ""
    for heading, lines in sections.items():
        if heading == "intro" or heading in excluded:
            continue
        main_html += f'<h3>{heading}</h3>\n{_lines_to_html(lines)}\n'

    def _action_items(keys: list) -> str:
        for k in keys:
            lines = sections.get(k, [])
            if lines:
                return _lines_to_html(lines)
        return "<ul><li>No specific actions generated.</li></ul>"

    def _plain_items(keys: list) -> List[str]:
        items: List[str] = []
        for k in keys:
            for line in sections.get(k, []):
                if line.startswith("- ") or line.startswith("* "):
                    items.append(line[2:].strip())
                elif line.strip():
                    items.append(line.strip())
        return items

    def _items_html(items: List[str]) -> str:
        if not items:
            return ""
        out = []
        for item in items[:5]:
            item = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", item)
            out.append(f"<div class='advice-item'>{item}</div>")
        return "\n".join(out)

    return (
        main_html,
        _action_items(plan_30_keys),
        _action_items(plan_60_keys),
        _action_items(plan_90_keys),
        _items_html(_plain_items(do_keys)),
        _items_html(_plain_items(dont_keys)),
    )


# ── Financial report ───────────────────────────────────────────────────────────

def _financial_report(df: pd.DataFrame, analysis: str) -> str:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # Fill missing financial columns with zeros so the report renders even with partial data
    for col in ("revenue", "burn_rate", "headcount", "cac", "ltv"):
        if col not in df.columns:
            df[col] = 0.0

    df = df.dropna(subset=["revenue"]).reset_index(drop=True)
    if df.empty:
        return _generic_report(df, "financial_data.csv", analysis)

    latest = df.iloc[-1]
    first  = df.iloc[0]

    def _f(col): return float(latest.get(col, 0) or 0)
    def _fi(col): return float(first.get(col, 0) or 0)

    rev_growth = ((_f("revenue") - _fi("revenue")) / _fi("revenue") * 100) if _fi("revenue") > 0 else 0
    ltv_cac    = _f("ltv") / _f("cac") if _f("cac") > 0 else 0
    burn_mult  = _f("burn_rate") / _f("revenue") if _f("revenue") > 0 else 0

    months     = [str(m) for m in df["month"].tolist()]
    revenues   = _safe_list(df["revenue"].fillna(0).tolist())
    burns      = _safe_list(df["burn_rate"].fillna(0).tolist())
    cacs       = _safe_list(df["cac"].fillna(0).tolist())
    ltvs       = _safe_list(df["ltv"].fillna(0).tolist())
    headcounts = _safe_list(df["headcount"].fillna(0).astype(int).tolist())

    growth_rates, growth_months = [], []
    for i in range(1, len(revenues)):
        prev = revenues[i - 1] or 0
        curr = revenues[i] or 0
        growth_months.append(months[i])
        growth_rates.append(round((curr - prev) / prev * 100, 1) if prev > 0 else 0)

    kpis = [
        {"label": "Latest MRR",  "value": _fmt(_f("revenue")),   "sub": f"{rev_growth:+.0f}% total growth",  "color": "#6366f1", "icon": "💰"},
        {"label": "Burn Rate",   "value": _fmt(_f("burn_rate")),  "sub": f"Burn multiple: {burn_mult:.1f}x",  "color": "#f43f5e", "icon": "🔥"},
        {"label": "LTV / CAC",   "value": f"{ltv_cac:.1f}x",     "sub": f"Target: > 3.0x",                   "color": "#3ECF8E", "icon": "📈"},
        {"label": "Team Size",   "value": str(int(_f("headcount"))), "sub": f"Started at {int(_fi('headcount'))}", "color": "#f59e0b", "icon": "👥"},
    ]

    charts_html = ""
    charts_js   = ""

    specs = [
        ("chart_rev_burn", "Revenue vs Burn Rate", "line", 2, {
            "labels": months,
            "datasets": [
                {"label": "Revenue",   "data": revenues, "borderColor": "#6366f1",
                 "backgroundColor": "rgba(99,102,241,0.10)", "fill": True, "tension": 0.4, "pointRadius": 3},
                {"label": "Burn Rate", "data": burns,    "borderColor": "#f43f5e",
                 "backgroundColor": "rgba(244,63,94,0.08)",  "fill": True, "tension": 0.4, "pointRadius": 3},
            ]
        }, {"yAxisCallback": "currency"}),
        ("chart_growth", "MoM Revenue Growth (%)", "bar", 1, {
            "labels": growth_months,
            "datasets": [{
                "label": "Growth %",
                "data": growth_rates,
                "backgroundColor": ["#3ECF8E" if g >= 0 else "#f43f5e" for g in growth_rates],
                "borderRadius": 6,
            }]
        }, {"yAxisCallback": "percent"}),
        ("chart_cac_ltv", "LTV vs CAC per Month", "bar", 1, {
            "labels": months,
            "datasets": [
                {"label": "LTV", "data": ltvs, "backgroundColor": "#3ECF8E", "borderRadius": 5},
                {"label": "CAC", "data": cacs, "backgroundColor": "#f59e0b", "borderRadius": 5},
            ]
        }, {"yAxisCallback": "currency"}),
        ("chart_headcount", "Team Growth", "line", 1, {
            "labels": months,
            "datasets": [{
                "label": "Headcount",
                "data": headcounts,
                "borderColor": "#a855f7",
                "backgroundColor": "rgba(168,85,247,0.12)",
                "fill": True, "tension": 0.4, "pointRadius": 4,
            }]
        }, {}),
    ]

    for cid, ctitle, ctype, cspan, cdata, copts in specs:
        span_cls = "col-span-2" if cspan == 2 else ""
        charts_html += (
            f'<div class="chart-card {span_cls}">'
            f'<div class="chart-title">{ctitle}</div>'
            f'<canvas id="{cid}"></canvas></div>\n'
        )
        charts_js += _chart_js_block(cid, ctype, cdata, copts)

    main_analysis, plan_30, plan_60, plan_90, do_html, dont_html = _analysis_to_html(analysis)
    period = f"{months[0]} → {months[-1]}" if months else ""

    return _render_html(
        title="Financial Performance Report",
        subtitle=f"{len(df)} months of data · {period}",
        report_type="Financial Analytics",
        kpis=kpis,
        charts_html=charts_html,
        charts_js=charts_js,
        main_analysis=main_analysis,
        plan_30=plan_30, plan_60=plan_60, plan_90=plan_90,
        do_html=do_html, dont_html=dont_html,
    )


# ── Generic CSV report ─────────────────────────────────────────────────────────

def _generic_report(df: pd.DataFrame, filename: str, analysis: str) -> str:
    num_cols = df.select_dtypes(include="number").columns.tolist()
    obj_cols = df.select_dtypes(include="object").columns.tolist()

    kpis = [{"label": "Total Records", "value": f"{len(df):,}", "sub": f"{len(df.columns)} columns", "color": "#6366f1", "icon": "📊"}]
    for col in num_cols[:3]:
        s = df[col].dropna()
        if len(s):
            kpis.append({
                "label": col.replace("_", " ").title(),
                "value": _fmt_plain(s.mean()) if s.mean() > 100 else f"{s.mean():.1f}",
                "sub": f"Max: {_fmt_plain(s.max())}",
                "color": COLORS[len(kpis) % len(COLORS)],
                "icon": ["💡", "⚡", "🎯"][len(kpis) % 3],
            })

    charts_html = ""
    charts_js   = ""

    if obj_cols and num_cols:
        cat, num = obj_cols[0], num_cols[0]
        top = df.groupby(cat)[num].sum().nlargest(15)
        labels = [str(l)[:28] for l in top.index.tolist()]
        values = _safe_list([round(float(v), 2) for v in top.values.tolist()])
        data = {
            "labels": labels,
            "datasets": [{"label": num.replace("_", " ").title(), "data": values,
                          "backgroundColor": COLORS[:len(labels)], "borderRadius": 5}]
        }
        charts_html += (
            '<div class="chart-card col-span-2">'
            f'<div class="chart-title">Top 15 by {num.replace("_"," ").title()}</div>'
            '<canvas id="chart_top15"></canvas></div>\n'
        )
        charts_js += _chart_js_block("chart_top15", "bar", data, {"indexAxis": "y"})

    for i, num_col in enumerate(num_cols[1:3], start=1):
        if obj_cols:
            top = df.groupby(obj_cols[0])[num_col].mean().nlargest(10)
            labels = [str(l)[:20] for l in top.index.tolist()]
            values = _safe_list([round(float(v), 2) for v in top.values.tolist()])
            data = {
                "labels": labels,
                "datasets": [{"label": num_col.replace("_", " ").title(), "data": values,
                              "backgroundColor": COLORS[i % len(COLORS)], "borderRadius": 5}]
            }
            cid = f"chart_col{i}"
            charts_html += (
                f'<div class="chart-card">'
                f'<div class="chart-title">{num_col.replace("_"," ").title()} Distribution</div>'
                f'<canvas id="{cid}"></canvas></div>\n'
            )
            charts_js += _chart_js_block(cid, "bar", data, {})

    main_analysis, plan_30, plan_60, plan_90, do_html, dont_html = _analysis_to_html(analysis)

    return _render_html(
        title="Data Analysis Report",
        subtitle=f"{filename} · {len(df):,} records · {len(df.columns)} columns",
        report_type="Business Intelligence",
        kpis=kpis,
        charts_html=charts_html,
        charts_js=charts_js,
        main_analysis=main_analysis,
        plan_30=plan_30, plan_60=plan_60, plan_90=plan_90,
        do_html=do_html, dont_html=dont_html,
    )


# ── KPI cards ──────────────────────────────────────────────────────────────────

def _kpi_cards_html(kpis: list) -> str:
    html = ""
    for i, k in enumerate(kpis):
        html += f"""
    <div class="kpi-card fade-item" style="--accent:{k['color']};--delay:{i*0.1:.1f}s">
      <div class="kpi-icon">{k.get('icon','📊')}</div>
      <div class="kpi-label">{k['label']}</div>
      <div class="kpi-value">{k['value']}</div>
      <div class="kpi-sub">{k['sub']}</div>
    </div>"""
    return html


# ── HTML shell ─────────────────────────────────────────────────────────────────

def _render_html(
    title: str, subtitle: str, report_type: str,
    kpis: list, charts_html: str, charts_js: str,
    main_analysis: str, plan_30: str, plan_60: str, plan_90: str,
    do_html: str, dont_html: str,
) -> str:
    kpi_html = _kpi_cards_html(kpis)

    # DO/DON'T section — only render if we have content
    do_dont_section = ""
    if do_html or dont_html:
        do_section = do_html or "<div class='advice-item'>Follow the strategic recommendations above.</div>"
        dont_section = dont_html or "<div class='advice-item'>Avoid accumulating burn without proportional revenue growth.</div>"
        do_dont_section = f"""
<div class="sec-title">Advisor Directives — What To Do &amp; Avoid</div>
<div class="do-dont-grid fade-item">
  <div class="do-card">
    <div class="card-badge badge-do">✅ Must Do This Quarter</div>
    <div class="advice-list">{do_section}</div>
  </div>
  <div class="dont-card">
    <div class="card-badge badge-dont">❌ Avoid These Mistakes</div>
    <div class="advice-list">{dont_section}</div>
  </div>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — FoundrAI</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#07070f;--surface:#0e0e1c;--surface2:#13131f;
  --border:#1c1c2e;--text:#e2e8f0;--muted:#6b7280;
  --accent:#6366f1;--green:#3ECF8E;--red:#f43f5e;--amber:#f59e0b;
}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;line-height:1.65}}

/* ── Animations ── */
@keyframes fade-up{{
  from{{opacity:0;transform:translateY(16px)}}
  to{{opacity:1;transform:translateY(0)}}
}}
@keyframes hdr-glow{{
  0%,100%{{opacity:.6}} 50%{{opacity:1}}
}}
@keyframes pulse-dot{{
  0%,100%{{transform:scale(1);opacity:1}} 50%{{transform:scale(1.4);opacity:.7}}
}}
/* 'both' fill-mode: applies 'from' during delay (hidden) and 'to' after end (visible) — no JS needed */
.fade-item{{
  animation:fade-up .6s ease both;
  animation-delay:var(--delay,0s);
}}

/* ── Header ── */
.header{{
  background:linear-gradient(135deg,#08081a 0%,#110a24 45%,#071214 100%);
  padding:48px 56px 38px;border-bottom:1px solid var(--border);
  position:relative;overflow:hidden;
}}
.header::before{{
  content:'';position:absolute;inset:0;
  background:
    radial-gradient(ellipse 70% 55% at 70% 30%,rgba(99,102,241,.18) 0%,transparent 65%),
    radial-gradient(ellipse 40% 40% at 20% 80%,rgba(6,182,212,.08) 0%,transparent 60%);
  animation:hdr-glow 6s ease-in-out infinite;
  pointer-events:none;
}}
.header::after{{
  content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(99,102,241,.4),transparent);
}}
.header-inner{{position:relative;max-width:1440px;margin:0 auto}}
.badge{{
  display:inline-flex;align-items:center;gap:7px;margin-bottom:20px;
  padding:5px 16px;border-radius:100px;
  background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.28);
  font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#a5b4fc;
}}
.badge-dot{{width:6px;height:6px;border-radius:50%;background:#6366f1;animation:pulse-dot 2s ease-in-out infinite}}
.header h1{{font-size:36px;font-weight:800;letter-spacing:-.035em;line-height:1.15;margin-bottom:8px}}
.header h1 span{{
  background:linear-gradient(135deg,#6366f1 0%,#a855f7 40%,#06b6d4 80%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}
.header-sub{{color:var(--muted);font-size:14px;margin-bottom:24px}}
.header-meta{{display:flex;flex-wrap:wrap;gap:24px}}
.meta{{font-size:11px;color:var(--muted)}}
.meta strong{{color:#94a3b8}}

/* ── Layout ── */
.main{{max-width:1440px;margin:0 auto;padding:48px 56px}}

/* ── Section titles ── */
.sec-title{{
  font-size:10px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;
  color:var(--muted);margin-bottom:20px;display:flex;align-items:center;gap:12px;
}}
.sec-title::after{{content:'';flex:1;height:1px;background:var(--border)}}

/* ── KPI Grid ── */
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:18px;margin-bottom:48px}}
.kpi-card{{
  background:var(--surface);border:1px solid var(--border);border-radius:18px;
  padding:26px 24px;cursor:default;
  border-top:2px solid var(--accent);
  transition:transform .2s,border-color .2s,box-shadow .2s;
}}
.kpi-card:hover{{transform:translateY(-3px);border-color:var(--accent);box-shadow:0 8px 32px rgba(99,102,241,.12)}}
.kpi-icon{{font-size:24px;margin-bottom:12px}}
.kpi-label{{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:5px}}
.kpi-value{{font-size:32px;font-weight:800;letter-spacing:-.04em;color:var(--accent);margin-bottom:5px;line-height:1}}
.kpi-sub{{font-size:11px;color:var(--muted)}}

/* ── Charts Grid ── */
.charts-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:22px;margin-bottom:48px}}
@media(max-width:780px){{.charts-grid{{grid-template-columns:1fr}}.col-span-2{{grid-column:span 1!important}}}}
.chart-card{{
  background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:26px;
  transition:border-color .2s;
}}
.chart-card:hover{{border-color:rgba(99,102,241,.3)}}
.chart-card.col-span-2{{grid-column:span 2}}
.chart-title{{font-size:12px;font-weight:600;color:#94a3b8;margin-bottom:16px;letter-spacing:.02em}}
canvas{{height:240px!important}}
.col-span-2 canvas{{height:280px!important}}

/* ── Analysis card ── */
.analysis-card{{
  background:var(--surface);border:1px solid var(--border);border-radius:20px;
  padding:38px 42px;margin-bottom:48px;
}}
.analysis-card h2{{font-size:20px;font-weight:700;margin-bottom:26px}}
.analysis-body h3{{
  color:#a5b4fc;font-size:14px;font-weight:700;
  margin:24px 0 10px;padding-left:14px;
  border-left:3px solid var(--accent);
}}
.analysis-body p{{color:#94a3b8;font-size:13.5px;margin-bottom:12px;line-height:1.7}}
.analysis-body ul{{margin:6px 0 16px 22px}}
.analysis-body li{{color:#94a3b8;font-size:13.5px;margin-bottom:6px;line-height:1.6}}
.analysis-body strong{{color:#e2e8f0}}

/* ── DO / DON'T grid ── */
.do-dont-grid{{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-bottom:48px}}
@media(max-width:780px){{.do-dont-grid{{grid-template-columns:1fr}}}}
.do-card,.dont-card{{
  border-radius:18px;padding:30px;
}}
.do-card{{
  background:linear-gradient(135deg,rgba(62,207,142,.06) 0%,rgba(62,207,142,.02) 100%);
  border:1px solid rgba(62,207,142,.2);
}}
.dont-card{{
  background:linear-gradient(135deg,rgba(244,63,94,.06) 0%,rgba(244,63,94,.02) 100%);
  border:1px solid rgba(244,63,94,.2);
}}
.card-badge{{
  display:inline-flex;align-items:center;gap:8px;margin-bottom:20px;
  padding:6px 14px;border-radius:10px;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
}}
.badge-do{{background:rgba(62,207,142,.15);color:#3ECF8E;border:1px solid rgba(62,207,142,.25)}}
.badge-dont{{background:rgba(244,63,94,.15);color:#f87171;border:1px solid rgba(244,63,94,.25)}}
.advice-list{{display:flex;flex-direction:column;gap:10px}}
.advice-item{{
  font-size:13px;color:#94a3b8;line-height:1.6;
  padding:12px 16px;border-radius:10px;background:rgba(255,255,255,.025);
  border-left:3px solid;
}}
.do-card .advice-item{{border-color:rgba(62,207,142,.4)}}
.dont-card .advice-item{{border-color:rgba(244,63,94,.4)}}
.advice-item strong{{color:#e2e8f0}}

/* ── Action Plan grid ── */
.action-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:48px}}
@media(max-width:780px){{.action-grid{{grid-template-columns:1fr}}}}
.action-card{{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:30px}}
.action-badge{{
  display:inline-flex;align-items:center;gap:6px;margin-bottom:18px;
  padding:5px 14px;border-radius:8px;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
}}
.badge-30{{background:rgba(99,102,241,.15);color:#a5b4fc;border:1px solid rgba(99,102,241,.22)}}
.badge-60{{background:rgba(168,85,247,.15);color:#d8b4fe;border:1px solid rgba(168,85,247,.22)}}
.badge-90{{background:rgba(6,182,212,.15);color:#67e8f9;border:1px solid rgba(6,182,212,.22)}}
.action-card ul{{list-style:none;margin-top:4px}}
.action-card li{{
  padding:10px 0;border-bottom:1px solid var(--border);
  font-size:13px;color:#94a3b8;line-height:1.55;
  display:flex;align-items:flex-start;gap:10px;
}}
.action-card li::before{{content:'→';color:var(--accent);flex-shrink:0;margin-top:1px;font-weight:700}}
.action-card li:last-child{{border-bottom:none}}
.action-card strong{{color:#e2e8f0}}

/* ── Footer ── */
.footer{{
  text-align:center;padding:30px;
  border-top:1px solid var(--border);
  font-size:11px;color:var(--muted);letter-spacing:.05em;
}}
.footer strong{{color:var(--accent)}}
</style>
</head>
<body>

<div class="header">
<div class="header-inner">
  <div class="badge"><span class="badge-dot"></span> FoundrAI Financial Intelligence</div>
  <h1><span>{title}</span></h1>
  <p class="header-sub">{subtitle}</p>
  <div class="header-meta">
    <div class="meta"><strong>Report Type</strong> {report_type}</div>
    <div class="meta"><strong>Engine</strong> Orchestrator + Analyst Agents</div>
    <div class="meta"><strong>Powered by</strong> Groq LLaMA 3.3</div>
    <div class="meta" id="gen-ts"><strong>Generated</strong> —</div>
  </div>
</div>
</div>

<div class="main">

<div class="sec-title">Key Performance Indicators</div>
<div class="kpi-grid">{kpi_html}</div>

<div class="sec-title">Data Visualizations</div>
<div class="charts-grid">
{charts_html}
</div>

<div class="sec-title">AI Analysis &amp; Strategic Insights</div>
<div class="analysis-card fade-item" style="--delay:0.2s">
  <h2>Executive Report</h2>
  <div class="analysis-body">{main_analysis}</div>
</div>

{do_dont_section}

<div class="sec-title">30 / 60 / 90-Day Action Plan</div>
<div class="action-grid">
  <div class="action-card fade-item" style="--delay:0.1s">
    <div class="action-badge badge-30">⚡ First 30 Days</div>
    {plan_30}
  </div>
  <div class="action-card fade-item" style="--delay:0.2s">
    <div class="action-badge badge-60">🔧 Days 31–60</div>
    {plan_60}
  </div>
  <div class="action-card fade-item" style="--delay:0.3s">
    <div class="action-badge badge-90">🚀 Days 61–90</div>
    {plan_90}
  </div>
</div>

</div>

<div class="footer">
  Generated by <strong>FoundrAI</strong> · Data Analyst Agent · Powered by Groq LLaMA 3.3 · For founder use only
</div>

<script>
document.getElementById('gen-ts').innerHTML =
  '<strong>Generated</strong> ' + new Date().toLocaleString();
{charts_js}
</script>
</body>
</html>"""


# ── Public entry points ────────────────────────────────────────────────────────

def generate_report(csv_bytes: bytes, filename: str, groq_client=None) -> str:
    """Parse CSV/Excel bytes and return a self-contained HTML report string."""
    from pathlib import Path as _Path

    ext = _Path(filename).suffix.lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(csv_bytes))
        else:
            df = pd.read_csv(io.BytesIO(csv_bytes))
    except Exception as exc:
        logger.error("File parse failed (%s): %s", filename, exc)
        return (
            "<html><body style='background:#07070f;color:#e2e8f0;font-family:sans-serif;padding:40px'>"
            f"<h2>Error parsing file</h2><p>{exc}</p></body></html>"
        )
    if df.empty:
        return (
            "<html><body style='background:#07070f;color:#e2e8f0;font-family:sans-serif;padding:40px'>"
            "<h2>Empty dataset</h2></body></html>"
        )

    from backend.agents.data_analyst_agent import run as analyst_run
    analysis = analyst_run(df, groq_client)
    report_type = _detect_csv_type(df)
    if report_type == "financial":
        return _financial_report(df, analysis)
    return _generic_report(df, filename, analysis)


def generate_report_from_df(df: pd.DataFrame, analysis_markdown: str) -> str:
    """Build HTML report from a pre-loaded DataFrame and pre-computed analysis.

    Used by /charts/auto-report which fetches data from DB and runs the
    two-pass data_analyst_agent separately for richer analysis.
    """
    if df.empty:
        return (
            "<html><body style='background:#07070f;color:#e2e8f0;font-family:sans-serif;padding:40px'>"
            "<h2>No data available</h2></body></html>"
        )
    report_type = _detect_csv_type(df)
    if report_type == "financial":
        return _financial_report(df, analysis_markdown)
    return _generic_report(df, "financial_data.csv", analysis_markdown)
