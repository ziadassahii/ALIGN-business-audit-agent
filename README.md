# ALIGN

> **AI reads. Code checks. A person decides.**

🚀 **[Live Demo](https://align-business-audit-agent-jjgk2t5kyk484y5uw5uckr.streamlit.app/?theme=light)**

Your company may be telling customers three different things. ALIGN reads your policy documents, pulls out every checkable rule, proves each quote exists in its source, finds the rules that disagree, links them to your real orders, and drafts exact text fixes that a human approves.
## What makes it trustworthy

- **Every claim is checked.** A rule only counts if its quote is found word for word in the source file.
- **Fixes are patches, not prose.** Each fix is a visible diff on the original sentence; nothing is applied until you tick "Approve".
- **Numbers are labelled.** Fees in your data are shown as data, cost per order as *assumed*, process savings as *hypothesis*.
- **Works without a key.** An offline rules engine runs the same pipeline, and also takes over if an API call fails.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Python 3.10+
pip install -r requirements.txt
streamlit run app.py
```

Pick a demo scenario in the sidebar (**Sales discount authority**, the default, or **Free delivery thresholds**) and click **Run the audit**. The sample files live in `sample_data/`; you can upload your own policies (.txt, .md, .pdf) and a table of what actually happened (.csv) instead. Light and dark mode are the two buttons at the top of the page
(`?theme=dark` in the URL opens dark directly).

## Use Claude

Either paste a key in the sidebar (used for that session only), or put it on the server:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then edit
```

On Streamlit Community Cloud, paste `ANTHROPIC_API_KEY = "sk-ant-..."` into *Settings > Secrets*.
The server key is never sent to the browser, and each session gets a few runs on it before asking for its own key.
Model: `claude-sonnet-5-5` (override with `ALIGN_MODEL`).

## How it works

`extract` (Claude, one call per document, structured output) → `verify_quotes` → `cross_check` →
`link_to_orders` (pandas) → `resolve` (canonical value + exact patch) → `scan_process`.
Code: `engine.py` (pipeline, no UI), `app.py` (Streamlit UI and theme).

## Tests

```bash
pip install pytest && pytest -q
```

## Limits worth knowing

- One number per rule. The gap is "above the lowest value, up to the highest"; a rule worded "at least X" would put a record exactly at X on the wrong side.
- Records above every document's value (for example discounts over 15%) are not counted as part of the gap.
- The money analysis needs a CSV with a numeric column the rule applies to (and a deal or order value column for discounts).
- The offline engine is tuned for threshold-style sentences; Claude mode handles free-form wording.
- Dollar totals are for the records in the file, not a monthly or yearly forecast.
