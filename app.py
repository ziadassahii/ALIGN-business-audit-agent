import hashlib, html, math, os, time
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import engine

st.set_page_config(page_title="ALIGN", page_icon="📎", layout="wide")
E = html.escape

MAX_DOC_CHARS = 60_000      # per document: keeps demo cost and latency bounded
MAX_DOCS = 12
MAX_SERVER_KEY_RUNS = 6     # per browser session, when the demo's own key is used
TABLE_ROWS = 200

SCENARIOS = {"Sales discount authority": "discount", "Free delivery thresholds": "delivery"}

def load_scenario(name):
    p = Path(__file__).parent / "sample_data" / SCENARIOS[name]
    return {f.name: f.read_text() for f in sorted(p.glob("*.txt"))}, pd.read_csv(next(p.glob("*.csv")))

# ---------------- theme ----------------
# Streamlit cannot switch its own theme at runtime (no API; the config hack changes it for every
# visitor). So the app owns one palette per mode and injects it as CSS variables on every run.
PALETTES = {
    "light": dict(bg="#faf9f5", card="#ffffff", subtle="#e8e6dc", ink="#141413", muted="#5c5b56",
                  clay="#c4623f", accent="#a8512f", on_accent="#ffffff", pen="#2b5780", olive="#556a3c",
                  hl="#f2d47a", border="rgba(20,20,19,.25)", shadow="#e8e6dc", scheme="light"),
    "dark":  dict(bg="#161615", card="#20201e", subtle="#2b2b28", ink="#f4f3ee", muted="#a9a79f",
                  clay="#e08466", accent="#e08466", on_accent="#161615", pen="#86abd0", olive="#9db97a",
                  hl="#6b561c", border="rgba(244,243,238,.24)", shadow="#2b2b28", scheme="dark"),
}
ss = st.session_state
if "theme" not in ss:
    ss.theme = st.query_params.get("theme", "light")
    if ss.theme not in PALETTES:
        ss.theme = "light"

def set_theme(name):
    ss.theme = name
    st.query_params["theme"] = name

P = PALETTES[ss.theme]

def css(p, active):
    v = "".join(f"--{k.replace('_', '-')}:{val};" for k, val in p.items() if k != "scheme")
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Fraunces:ital,opsz,wght,SOFT,WONK@0,9..144,300..800,0..100,0..1&family=Lora:ital,wght@0,400..700;1,400..700&display=swap');
:root {{ {v} color-scheme: {p['scheme']}; }}

/* ---- Streamlit chrome ---- */
#MainMenu, footer, [data-testid="stDeployButton"] {{ visibility: hidden; }}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background: var(--bg) !important; color: var(--ink); }}
[data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {{ background: var(--subtle) !important; }}
.stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp summary,
[data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"], [data-testid="stSliderThumbValue"],
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"] {{ color: var(--ink); }}
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"] {{ background: var(--card) !important; border-color: var(--border) !important; }}
.stApp [data-baseweb="input"] input {{ color: var(--ink) !important; -webkit-text-fill-color: var(--ink); background: transparent !important; }}
[data-testid="stFileUploaderDropzone"] {{ background: var(--card) !important; border: 1px dashed var(--border); }}
[data-testid="stFileUploaderDropzone"] * {{ color: var(--ink); }}
[data-testid="stFileUploaderDropzone"] button {{ background: var(--subtle); color: var(--ink); border: 1px solid var(--border); }}
button[data-baseweb="tab"] p {{ color: var(--muted); font-family: Fraunces, serif; font-weight: 600; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color: var(--ink); }}
[data-testid="stExpander"] details {{ background: var(--card); border: 1px solid var(--border); border-radius: 4px; }}
.block-container {{ max-width: 1100px; padding-top: 3.2rem; padding-bottom: 5rem; }}

/* ---- buttons ---- */
.stButton>button, .stDownloadButton>button {{
  border: 1.5px solid var(--ink); background: var(--ink); color: var(--bg) !important;
  padding: .8rem 1.5rem; box-shadow: 4px 4px 0 var(--clay); border-radius: 4px;
  transition: transform .12s, box-shadow .12s; }}
.stButton>button:hover, .stDownloadButton>button:hover {{ transform: translate(2px, 2px); box-shadow: 2px 2px 0 var(--clay); background: var(--ink); color: var(--bg) !important; }}
.stButton>button:focus-visible, .stDownloadButton>button:focus-visible {{ outline: 3px solid var(--pen); outline-offset: 2px; }}
.stButton>button p, .stDownloadButton>button p {{ color: var(--bg) !important; font-family: Fraunces, serif; font-weight: 600; font-size: 1.05rem; }}
.stButton>button:disabled {{ opacity: .45; box-shadow: none; }}

/* theme switch: two small buttons, the active one is filled */
.st-key-theme_light button, .st-key-theme_dark button {{
  background: transparent; box-shadow: none; padding: .35rem .8rem; border: 1.5px solid var(--border); }}
.st-key-theme_light button p, .st-key-theme_dark button p {{ color: var(--ink) !important; font-size: .95rem; }}
.st-key-theme_light button:hover, .st-key-theme_dark button:hover {{ background: var(--subtle); box-shadow: none; transform: none; }}
.st-key-theme_{active} button {{ background: var(--accent) !important; border-color: var(--accent) !important; }}
.st-key-theme_{active} button p, .st-key-theme_{active} button span {{ color: var(--on-accent) !important; }}

/* ---- ALIGN components ---- */
.stApp .pen {{ font-family: Caveat, cursive; font-size: 1.45rem; color: var(--pen); margin: 0; line-height: 1.2; }}
.stApp .wm {{ font-family: Fraunces, serif; font-weight: 800; font-size: 1.6rem; font-variation-settings:'WONK' 1,'SOFT' 100; margin: 0; color: var(--ink); }}
.stApp .hd {{ font-family: Fraunces, serif; font-weight: 600; font-size: 2.7rem; line-height: 1.08; letter-spacing: -.02em; max-width: 27ch; margin: .3rem 0 .9rem; font-variation-settings:'WONK' 1,'SOFT' 60; color: var(--ink); }}
.stApp .sub {{ max-width: 62ch; line-height: 1.55; margin: 0 0 1rem; color: var(--muted); }}
.stApp .big {{ font-family: Fraunces, serif; font-weight: 300; font-size: 4.4rem; line-height: 1; color: var(--accent); margin: 0; }}
.stApp .note {{ font-size: .92rem; color: var(--muted); margin: .2rem 0; }}

.slips {{ display: flex; gap: 20px; flex-wrap: wrap; margin: 1.1rem 0 1.5rem; }}
.stApp .slip {{ background: var(--card); color: var(--ink); width: 245px; max-width: 100%; padding: 13px 15px; border: 1px solid var(--border); box-shadow: 3px 4px 0 var(--shadow); border-radius: 4px; }}
.stApp .slip .t {{ font-family: Caveat, cursive; font-size: 1.3rem; color: var(--pen); line-height: 1; }}
.stApp .slip p {{ margin: .3rem 0 0; font-size: .95rem; line-height: 1.45; color: var(--ink); }}
.stApp .slip mark {{ background: var(--hl); padding: 0 4px; font-weight: 700; color: var(--ink); border-radius: 2px; }}
.stApp .slip .v {{ font-family: Caveat, cursive; color: var(--olive); font-size: 1.1rem; }}
.stApp .slip .v.x {{ color: var(--accent); }}

.stApp .stamp {{ display: inline-block; border: 2px solid var(--accent); color: var(--accent); padding: 1px 10px; font-weight: 700; transform: rotate(-2deg); margin-right: 10px; font-size: .95rem; border-radius: 3px; animation: thunk .35s ease-out both; }}
.stApp .stamp.t {{ border-color: var(--pen); color: var(--pen); }}
.stApp .stamp.ok {{ border-color: var(--olive); color: var(--olive); }}
@keyframes thunk {{ from {{ transform: rotate(-2deg) scale(1.5); opacity: 0; }} to {{ transform: rotate(-2deg) scale(1); opacity: 1; }} }}
@media (prefers-reduced-motion: reduce) {{ .stamp {{ animation: none; }} .stButton>button {{ transition: none; }} }}

.stApp .case h3 {{ font-family: Fraunces, serif; font-size: 1.7rem; font-weight: 600; margin: 1rem 0 .2rem; color: var(--ink); }}
.ledger {{ border-top: 1.5px solid var(--ink); margin: 1rem 0; max-width: 640px; }}
.ledger div {{ display: flex; justify-content: space-between; gap: 16px; padding: .5rem 0; border-bottom: 1px solid var(--border); color: var(--ink); }}
.ledger b {{ font-family: Fraunces, serif; font-weight: 600; color: var(--ink); }}
.ledger i {{ font-family: Caveat, cursive; font-size: 1.25rem; color: var(--pen); font-style: normal; }}

.trail {{ border-left: 2px solid var(--ink); margin-left: 6px; padding-left: 18px; }}
.tr {{ display: flex; gap: 14px; padding: .25rem 0; font-size: .95rem; color: var(--ink); }}
.tr .tt {{ color: var(--muted); min-width: 3rem; }}
.tr .tn {{ font-family: 'Courier Prime', monospace; font-weight: 700; min-width: 9.5rem; }}
.tr.bad {{ color: var(--accent); }}

.steps {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 1rem 0; }}
.step {{ background: var(--card); border: 1px solid var(--ink); padding: 8px 14px; color: var(--ink); border-radius: 3px; }}
.step.hot {{ background: var(--hl); transform: rotate(-1.5deg); }}

.tblwrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 4px; background: var(--card); margin: .6rem 0 1rem; }}
.tbl {{ border-collapse: collapse; width: 100%; font-size: .92rem; color: var(--ink); }}
.tbl th {{ text-align: left; font-family: Fraunces, serif; font-weight: 600; background: var(--subtle); padding: .5rem .7rem; white-space: nowrap; }}
.tbl td {{ padding: .45rem .7rem; border-top: 1px solid var(--border); vertical-align: top; }}
.tbl td.q {{ min-width: 18rem; }}
.tbl .yes {{ color: var(--olive); font-weight: 700; }} .tbl .no {{ color: var(--accent); font-weight: 700; }}

.diff, .plain {{ font-family: 'Courier Prime', monospace; font-size: .9rem; background: var(--card); border: 1px solid var(--border); border-radius: 4px; padding: .6rem 0; margin: .4rem 0 1rem; overflow-x: auto; color: var(--ink); }}
.diff div, .plain div {{ padding: 0 .9rem; white-space: pre-wrap; min-height: 1.2em; }}
.diff .add {{ background: color-mix(in srgb, var(--olive) 22%, transparent); }}
.diff .del {{ background: color-mix(in srgb, var(--clay) 22%, transparent); }}
.diff .hunk, .diff .meta {{ color: var(--muted); }}
</style>"""

st.html(css(P, ss.theme))

# ---------------- helpers ----------------
def read_upload(f):
    if f.name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(f).pages)
    return f.read().decode("utf-8", "ignore")

def label(k): return k.rsplit(".", 1)[0].replace("_", " ")
def fv(v, unit): return f"${v:,.0f}" if unit == "usd" else f"{v:g}%" if unit == "percent" else f"{v:,.0f}"

def slip(c, i, hl=True):
    q = E(c["quote"]) if hl else E(c["quote"].split("\n")[0])
    if hl: q = q.replace(E(c["value_text"]), f"<mark>{E(c['value_text'])}</mark>", 1)
    tag = '<span class="v">quote found in source</span>' if c.get("verified", True) else '<span class="v x">not found in source</span>'
    r = [-1.4, .9, -.5, 1.2][i % 4]
    return f'<div class="slip" style="transform:rotate({r}deg)"><div class="t">{E(label(c["source"]))}</div><p>{q}</p>{tag if hl else ""}</div>'

def nice_step(mx, target=6):
    raw = mx / target
    mag = 10 ** math.floor(math.log10(raw))
    return next(m * mag for m in (1, 2, 2.5, 5, 10) if raw <= m * mag)

def tape(vals, pins, lo, hi, n, col, unit, p):
    """Records dotted along the rule's scale, with each document's value pinned on it.
    Colors are concrete hex values: this renders inside an iframe that cannot see the page's CSS variables."""
    W, base, L = 880, 210, 36
    pre, suf = ("$", "") if unit == "usd" else ("", "%") if unit == "percent" else ("", "")
    mx = max(max(vals, default=0), max(v for _, v in pins)) * 1.08 or 1
    step = nice_step(mx)
    mx = step * math.ceil(mx / step)
    X = lambda v: L + (W - 2 * L) * v / mx
    ink, clay, bg = p["ink"], p["clay"], p["bg"]
    s = [f'<svg viewBox="0 0 {W} 275" width="100%" style="max-width:{W}px" role="img" aria-label="Records plotted by {E(col)} against each document\'s value">',
         f'<defs><pattern id="hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="9" stroke="{clay}" stroke-width="1.4" opacity=".55"/></pattern></defs>',
         f'<rect x="{X(lo)}" y="70" width="{X(hi)-X(lo)}" height="{base-70}" fill="url(#hatch)"/>',
         f'<line x1="{L}" x2="{W-L}" y1="{base}" y2="{base}" stroke="{ink}" stroke-width="1.5"/>']
    k = 0
    while k * step <= mx + 1e-9:
        v = k * step
        s.append(f'<text x="{X(v)}" y="{base+22}" text-anchor="middle" font-family="Lora,serif" font-size="13" fill="{ink}">{pre}{v:,g}{suf}</text>')
        k += 1
    for i, (name, v) in enumerate(sorted(pins, key=lambda q: q[1])):
        y = 18 + (i % 3) * 19
        s.append(f'<line x1="{X(v)}" x2="{X(v)}" y1="{y+6}" y2="{base}" stroke="{ink}" stroke-width="1.5"/>'
                 f'<text x="{X(v)}" y="{y}" text-anchor="middle" font-family="Caveat,cursive" font-weight="700" font-size="19" fill="{ink}">{E(label(name))}: {pre}{v:g}{suf}</text>')
    stack = {}
    for v in sorted(vals):
        b = round(X(v) / 12); h = stack.get(b, 0); stack[b] = h + 1
        if h <= 11:
            s.append(f'<circle cx="{X(v)}" cy="{base-9-h*11}" r="5" fill="{clay if lo < v <= hi else bg}" stroke="{ink}" stroke-width="1.4"/>')
    cx = X((lo + hi) / 2)
    s.append(f'<text x="{cx}" y="{base+54}" text-anchor="middle" font-family="Caveat,cursive" font-weight="700" font-size="24" fill="{p["pen"]}">{n} records could get two different answers</text></svg>')
    return "".join(s)

def trace_html(lines):
    return '<div class="trail">' + "".join(
        f'<div class="tr {"" if e["ok"] else "bad"}"><span class="tt">{e["t"]:.1f}s</span><span class="tn">{E(e["tool"])}</span><span>{E(e["detail"])}</span></div>' for e in lines) + "</div>"

def table_html(df, cap=TABLE_ROWS):
    """Plain HTML table: st.dataframe draws on a canvas that ignores our dark palette."""
    head = "".join(f"<th>{E(str(c))}</th>" for c in df.columns)
    rows = "".join("<tr>" + "".join(f"<td>{E(str(x))}</td>" for x in r) + "</tr>" for r in df.head(cap).itertuples(index=False))
    more = f'<p class="note">Showing the first {cap} of {len(df)} rows.</p>' if len(df) > cap else ""
    return f'<div class="tblwrap"><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>{more}'

def claims_html(claims):
    rows = "".join(
        f'<tr><td>{E(label(c["source"]))}</td><td>{E(c["label"])}</td><td>{E(c["value_text"])}</td>'
        f'<td class="{"yes" if c["verified"] else "no"}">{"yes" if c["verified"] else "no"}</td><td class="q">{E(c["quote"])}</td></tr>' for c in claims)
    return ('<div class="tblwrap"><table class="tbl"><thead><tr><th>Source</th><th>Rule</th><th>Value</th><th>Verified</th><th>Quote</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')

def diff_html(text):
    out = []
    for l in text.splitlines():
        k = "add" if l.startswith("+") and not l.startswith("+++") else "del" if l.startswith("-") and not l.startswith("---") else "hunk" if l.startswith("@@") else "meta" if l.startswith(("+++", "---")) else ""
        out.append(f'<div class="{k}">{E(l) or "&nbsp;"}</div>')
    return f'<div class="diff">{"".join(out)}</div>'

def plain_html(text):
    return '<div class="plain">' + "".join(f"<div>{E(l) or '&nbsp;'}</div>" for l in text.splitlines()) + "</div>"

def server_key():
    try:
        k = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        k = ""
    return k or os.getenv("ANTHROPIC_API_KEY", "")

# ---------------- top bar: brand + theme switch ----------------
brand, sp, b1, b2 = st.columns([6, 3, 1.3, 1.3], vertical_alignment="center")
brand.html('<p class="pen">case file no. 1: your own paperwork</p>')
b1.button("Light", key="theme_light", icon=":material/light_mode:", on_click=set_theme, args=("light",))
b2.button("Dark", key="theme_dark", icon=":material/dark_mode:", on_click=set_theme, args=("dark",))

# ---------------- sidebar ----------------
SERVER_KEY = server_key()
with st.sidebar:
    st.html('<p class="wm">align</p>')
    demo = st.checkbox("Use the demo company", True)
    scenario = st.selectbox("Demo scenario", list(SCENARIOS), disabled=not demo)
    uploads = st.file_uploader("Add policies (.txt .md .pdf) or orders (.csv)", accept_multiple_files=True, type=["txt", "md", "pdf", "csv"])
    user_key = st.text_input("Anthropic API key (optional)", type="password",
                             help="Your own key is used for this session only. Leave empty to use the demo's key, or the offline rules engine if there is none.")
    key = user_key.strip() or SERVER_KEY
    own_key = bool(user_key.strip())
    state = "Claude reads your documents (your key)" if own_key else "Claude reads your documents (demo key)" if key else "offline: rules engine only"
    st.html(f'<p class="pen">{E(state)}</p>')
    st.html('<p class="pen">assumptions, yours to change</p>')
    cost = st.slider("Cost per affected order or deal ($)", 0, 300, 120)
    hours = st.slider("Hours recovered per month", 0, 60, 14)
    rate = st.slider("Value of an hour ($)", 10, 200, 60)

docs, orders = load_scenario(scenario) if demo else ({}, pd.DataFrame(columns=["order_value"]))
for f in uploads or []:
    try:
        if f.name.lower().endswith(".csv"):
            orders = pd.read_csv(f)
        else:
            t = read_upload(f)
            if len(t) > MAX_DOC_CHARS:
                st.sidebar.warning(f"{f.name} is longer than {MAX_DOC_CHARS:,} characters and was skipped.")
            elif len(docs) >= MAX_DOCS:
                st.sidebar.warning(f"Only {MAX_DOCS} documents are read per audit; {f.name} was skipped.")
            else:
                docs[f.name] = t
    except Exception as ex:
        st.sidebar.error(f"Could not read {f.name}: {ex}")
sig = hashlib.md5((repr(docs) + orders.to_csv() + str(bool(key))).encode()).hexdigest()
res = ss.get("result") if ss.get("sig") == sig else None

# ---------------- landing ----------------
if res is None:
    st.html('<h1 class="hd">Your company may be telling customers three different things.</h1>')
    st.html(f'<p class="sub">{len(docs)} documents and {len(orders)} orders are on the desk. ALIGN pulls every rule out of the text, '
            'checks each quote against its source, lines the rules up, and finds the orders that got caught in the gaps.</p>')
    if ss.get("result"): st.html('<p class="pen">Sources changed since the last audit. Run it again.</p>')
    st.html('<div class="slips">' + "".join(slip(dict(source=n, quote=t.split("\n")[0].title(), value_text="", verified=True), i, hl=False) for i, (n, t) in enumerate(docs.items())) + "</div>")
    over = bool(key) and not own_key and ss.get("server_runs", 0) >= MAX_SERVER_KEY_RUNS
    if over:
        st.html('<p class="note">The demo key has reached its limit for this session. Add your own key in the sidebar to keep going.</p>')
    if st.button("Run the audit", disabled=not docs or over):
        use_key = key
        if key and not own_key: ss.server_runs = ss.get("server_runs", 0) + 1
        box, lines = st.empty(), []
        pace = 0 if use_key else 0.25   # offline steps are instant; pace them so the trail is readable
        def prog(e):
            lines.append(e); box.html(trace_html(lines)); time.sleep(pace)
        out = engine.run_audit(docs, orders, use_key, prog)
        box.empty()
        ss.result, ss.sig, ss.approved = out, sig, {f["id"] for f in out["findings"]}
        st.rerun()
    st.stop()

# ---------------- results ----------------
F, opp = res["findings"], res["opportunity"]
if res.get("notice"): st.warning(res["notice"])
exposure = sum(f["exposure"] for f in F)
gap_label = "Discount given above the recommended limit, inside the gap" if F and F[0]["exposure_kind"] == "discount" else "Delivery fees already charged inside the gap"
m_conf = sum(f["n"] * cost for f in F)
m_opp = hours * rate if opp else 0
base = exposure + m_conf + m_opp
lo_t, hi_t = exposure + .5 * (m_conf + m_opp), exposure + 1.5 * (m_conf + m_opp)

if len(F) == 1:
    f = F[0]; unit = f["claims"][0]["unit"]
    v = [fv(x, unit) for x in f["vals"]]
    head = f"{f['title']} reads {', '.join(v[:-1])} and {v[-1]}, depending on which document you open."
elif F:
    head = f"{len(F)} rules say different things in different documents."
else:
    head = "No contradictions found in these sources."
nver = sum(c["verified"] for c in res["claims"])
st.html(f'<h1 class="hd">{E(head)}</h1><p class="sub">Checked {len(res["claims"])} rules across {res["n_docs"]} documents. '
        f'{nver} quotes were found word-for-word in their source. {len(res["cleared"])} look-alike conflict(s) were cleared.</p>')
st.html(f'<p class="big">${base:,.0f}</p><p class="sub">for the {res["n_orders"]} records and assumptions on this page. Plausible range ${lo_t:,.0f} to ${hi_t:,.0f}. '
        'Scale it to your real monthly order volume before quoting it.</p>'
        '<div class="ledger">'
        + (f'<div><span>{gap_label}</span><span><b>${exposure:,.0f}</b> <i>in your data</i></span></div>' if exposure else "")
        + (f'<div><span>Cost of affected records ({sum(f["n"] for f in F)} × ${cost:,.0f})</span><span><b>${m_conf:,.0f}</b> <i>assumed</i></span></div>' if F else "")
        + (f'<div><span>Process time ({hours} h × ${rate:,.0f})</span><span><b>${m_opp:,.0f}</b> <i>hypothesis</i></span></div>' if opp else "")
        + '</div>')

t1, t2, t3, t4 = st.tabs(["Findings", "Evidence trail", "Fix pack", "Ask ALIGN"])
with t1:
    for f in F:
        unit = f["claims"][0]["unit"]
        st.html(f'<div class="case"><h3><span class="stamp">{E(f["severity"])} severity</span>{E(f["title"])}</h3></div><p class="sub">{E(f["why"])}</p>'
                '<div class="slips">' + "".join(slip(c, i) for i, c in enumerate(f["claims"])) + "</div>")
        if f["column"]:
            ser = orders[f["column"]].dropna().astype(float)
            ser = ser if len(ser) <= 400 else ser.sample(400, random_state=1)
            svg = tape(list(ser), [(c["source"], c["value"]) for c in f["claims"]], f["lo"], f["hi"], f["n"], f["column"], unit, P)
            components.html("<style>@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Lora&display=swap');"
                            "html,body{margin:0;background:transparent}</style>" + svg, height=300)
            st.html(f'<p class="note">Each dot is one record by {E(f["column"])}; equal values stack. Filled dots sit inside the gap between the rules.</p>')
            if f["n"]:
                with st.expander(f"See the {f['n']} affected records"):
                    st.html(table_html(orders.loc[f["row_ids"]]))
        st.html(f'<p class="pen">ALIGN recommends {fv(f["canonical"], unit)} everywhere (confidence {f["confidence"]:.0%})</p><p class="sub">{E(f["rationale"])}</p>')
    if opp:
        hot = set(opp["hot_steps"])
        st.html(f'<div class="case"><h3><span class="stamp t">worth testing</span>{E(opp["title"])}</h3></div>'
                '<div class="steps">' + "".join(f'<div class="step {"hot" if s in hot else ""}">{i+1}. {E(s)}</div>' for i, s in enumerate(opp["steps"])) + '</div>'
                f'<p class="pen">the highlighted steps may not need to wait on each other</p><p class="sub">{E(opp["rationale"])}</p>')
    if res["cleared"]:
        st.html('<div class="case"><h3><span class="stamp ok">checked, fine</span>Looked like conflicts, are not</h3></div>'
                + "".join(f'<p class="sub"><b>{E(c["label"])}.</b> {E(c["why"])}</p>' for c in res["cleared"]))
with t2:
    st.html(trace_html(res["trace"]))
    st.html(claims_html(res["claims"]))
with t3:
    approved = set()
    for f in F:
        st.html(f'<p class="pen">{E(f["title"])}</p>')
        if st.checkbox("Approve this fix", value=f["id"] in ss.get("approved", set()), key=f"ap_{f['id']}"): approved.add(f["id"])
        for p in f["patches"]:
            if p["changed"]: st.html(diff_html(p["diff"]))
            else: st.html(f'<p class="note">{E(p["source"])} already says the recommended value.</p>')
    if opp: st.html('<p class="pen">experiment pack</p>' + plain_html(opp["experiment"]))
    summary = engine.report_md(res, approved, cost, hours, rate)
    a, b = st.columns(2)
    a.download_button("Download aligned files and report", engine.export_zip(res, approved, docs, summary), "ALIGN_fix_pack.zip", mime="application/zip")
    b.download_button("Download report only", summary, "ALIGN_report.md")
with t4:
    if not key:
        st.html('<p class="sub">Add an Anthropic API key in the sidebar to ask follow-up questions, like <i>which fix should we ship first?</i></p>')
    else:
        history = ss.setdefault("qa", {}).setdefault(sig, [])
        with st.form("ask_form", clear_on_submit=True):   # a form: one API call per submit, not one per rerun
            q = st.text_input("Ask about this audit", placeholder="Which fix should we ship first, and why?")
            sent = st.form_submit_button("Ask")
        if sent and q.strip():
            try:
                history.append((q.strip(), engine.ask(key, res, q.strip())))
            except Exception as ex:
                st.error(f"{type(ex).__name__}: {str(ex)[:200]}")
        for question, answer in reversed(history):
            st.html(f'<p class="pen">{E(question)}</p><div class="slip" style="width:auto;max-width:700px"><p>{E(answer)}</p></div>')
st.html('<p></p>')
if st.button("Start a new audit"):
    for k in ("result", "sig", "approved"): ss.pop(k, None)
    st.rerun()
