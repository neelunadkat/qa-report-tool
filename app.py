"""
app.py — Streamlit Web Interface
─────────────────────────────────────────────────────────────────
QA Quality Circle Report Generator
Encircle Technologies — QA Team Tool

This file turns your existing Python scripts into a browser-based
web app. Deploy it free on Streamlit Cloud.

Users: open the app URL → paste Google Sheet link → click Generate → download PDF.
No Python, no terminal, no setup on their side.
─────────────────────────────────────────────────────────────────
"""

import streamlit as st
import gspread
import json
import tempfile
import os
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import date

from classifier import classify_issue
from pdf_builder import build_pdf

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QA Report Generator — Encircle Technologies",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("## 📋 QA Quality Circle Report Generator")
st.markdown(
    "<p style='color:#6B6B6B;margin-top:-12px;margin-bottom:24px'>"
    "Encircle Technologies &nbsp;·&nbsp; QA Team Tool</p>",
    unsafe_allow_html=True,
)

# ── How to use (collapsible) ────────────────────────────────────────────────────
with st.expander("ℹ️  How to use this tool"):
    st.markdown("""
**Step 1 — Share your Google Sheet**
- Open the Google Sheet you want to report on
- Click Share → add this email as Viewer:
  `qa-report-bot@<your-project>.iam.gserviceaccount.com`
  *(check with your QA Team Lead for the exact email)*

**Step 2 — Paste the sheet URL below**

**Step 3 — Click Generate Report**

**Step 4 — Download the PDF**

The report will include all issues with Status = **REVIEWED** only.
""")

# ── Sheet URL input ─────────────────────────────────────────────────────────────
st.markdown("#### Paste your Google Sheet URL")
sheet_url = st.text_input(
    label="Google Sheet URL",
    placeholder="https://docs.google.com/spreadsheets/d/...",
    label_visibility="collapsed",
)

# ── Optional: custom sheet tab name ────────────────────────────────────────────
with st.expander("⚙️  Advanced options"):
    sheet_tab = st.text_input(
        "Sheet tab name",
        value="Quality Circle",
        help="The exact name of the tab in your Google Sheet that contains the issues."
    )
    status_filter = st.text_input(
        "Status filter",
        value="REVIEWED",
        help="Only issues with this status will be included in the report."
    )

# defaults are set inside the expander via value=, no else needed

st.markdown("---")


# ── Generate button ─────────────────────────────────────────────────────────────
if st.button("🚀  Generate Report", type="primary", use_container_width=True):

    # Validate URL
    if not sheet_url.strip():
        st.error("❌  Please paste a Google Sheet URL above.")
        st.stop()
    if "docs.google.com/spreadsheets" not in sheet_url:
        st.error("❌  That doesn't look like a Google Sheets URL. Please check and try again.")
        st.stop()

    try:
        # ── Step 1: Connect to Google Sheets ───────────────────────────────────
        with st.status("Connecting to Google Sheets...", expanded=True) as status:

            # Load credentials from Streamlit Secrets
            # In Streamlit Cloud: Settings → Secrets → add GOOGLE_CREDENTIALS
            # Load credentials from Streamlit Secrets (native TOML format)
            # Paste your credentials.json fields directly in Streamlit > Secrets as TOML
            # e.g:  type = "service_account"
            #        project_id = "qa-report-tool"
            #        private_key = "-----BEGIN PRIVATE KEY-----\n..."
            #        client_email = "qa-report-bot@..."   etc.
            creds_data = {k: v for k, v in st.secrets.items()}
            creds = Credentials.from_service_account_info(
                creds_data,
                scopes=[
                    "https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive",
                ],
            )
            client = gspread.authorize(creds)

            # ── Step 2: Load spreadsheet ────────────────────────────────────────
            st.write("📄  Loading spreadsheet...")
            try:
                spreadsheet = client.open_by_url(sheet_url.strip())
            except gspread.exceptions.SpreadsheetNotFound:
                st.error(
                    "❌  Spreadsheet not found. Make sure you shared the sheet "
                    "with the service account email (see How to use above)."
                )
                st.stop()

            project_name = spreadsheet.title

            try:
                worksheet = spreadsheet.worksheet(sheet_tab)
            except gspread.exceptions.WorksheetNotFound:
                available = [ws.title for ws in spreadsheet.worksheets()]
                st.error(
                    f"❌  Tab '{sheet_tab}' not found in this spreadsheet. "
                    f"Available tabs: {', '.join(available)}"
                )
                st.stop()

            all_values = worksheet.get_all_values()

            # ── Step 3: Parse data ──────────────────────────────────────────────
            st.write("🔍  Parsing issues...")
            df = pd.DataFrame(all_values)

            if df.shape[1] < 6:
                st.error("❌  Sheet doesn't have enough columns. Expected at least 6 (Page, Bug, Screenshot, Device, Status, Developer/Designer).")
                st.stop()

            df = df.rename(columns={
                df.columns[0]: 'Page',
                df.columns[1]: 'Bug',
                df.columns[2]: 'Screenshot',
                df.columns[3]: 'Device',
                df.columns[4]: 'Status',
                df.columns[5]: 'Category',
            })

            # Forward-fill page names
            current_page = None
            page_col = []
            for _, row in df.iterrows():
                if str(row['Page']).strip() in ('Page', 'page', ''):
                    page_col.append(None)
                    continue
                status_val = str(row['Status']).strip()
                if row['Page'] and status_val in ('', 'nan', 'None'):
                    val = str(row['Page']).strip()
                    if not val.startswith('http'):
                        current_page = val
                    page_col.append(None)
                else:
                    page_col.append(current_page)

            df['PageName'] = page_col

            # Filter to selected status
            reviewed = df[df['Status'].str.strip() == status_filter].copy()
            reviewed = reviewed[reviewed['Bug'].notna() & (reviewed['Bug'].str.strip() != '')]

            if reviewed.empty:
                st.warning(
                    f"⚠️  No issues with status '{status_filter}' found in this sheet. "
                    f"Check the status filter or the sheet content."
                )
                st.stop()

            # ── Step 4: Classify issues ─────────────────────────────────────────
            st.write("🗂️  Classifying issues by category...")
            reviewed['IssueType'] = reviewed.apply(
                lambda r: classify_issue(str(r['Bug']), str(r['Category'])), axis=1
            )
            reviewed['Category'] = reviewed['Category'].str.strip()

            def norm_cat(c):
                c = str(c).strip()
                if c.lower() == 'developer': return 'Developer'
                if c.lower() == 'designer':  return 'Designer'
                if c.lower() == 'both':      return 'Both'
                return c
            reviewed['Category'] = reviewed['Category'].apply(norm_cat)

            # ── Step 5: Aggregate ───────────────────────────────────────────────
            total    = len(reviewed)
            dev_cnt  = len(reviewed[reviewed['Category'] == 'Developer'])
            des_cnt  = len(reviewed[reviewed['Category'] == 'Designer'])
            both_cnt = len(reviewed[reviewed['Category'] == 'Both'])

            type_summary = reviewed.groupby(['IssueType', 'Category']).size().unstack(fill_value=0)
            for c in ['Developer', 'Designer', 'Both']:
                if c not in type_summary.columns: type_summary[c] = 0
            type_summary['Total'] = type_summary[['Developer', 'Designer', 'Both']].sum(axis=1)
            type_summary = type_summary[['Total', 'Developer', 'Designer', 'Both']].sort_values('Total', ascending=False)

            page_summary = reviewed.groupby(['PageName', 'Category']).size().unstack(fill_value=0)
            for c in ['Developer', 'Designer', 'Both']:
                if c not in page_summary.columns: page_summary[c] = 0
            page_summary['Total'] = page_summary[['Developer', 'Designer', 'Both']].sum(axis=1)
            page_summary = page_summary[['Total', 'Developer', 'Designer', 'Both']].sort_values('Total', ascending=False)

            stats = {
                'total':       total,
                'developer':   dev_cnt,
                'designer':    des_cnt,
                'both':        both_cnt,
                'by_type':     type_summary,
                'by_page':     page_summary,
                'reviewed_df': reviewed,
            }

            # ── Step 6: Build PDF ───────────────────────────────────────────────
            st.write("📄  Building PDF report...")
            today_str = date.today().strftime("%Y-%m-%d")
            safe_name = project_name.replace(' ', '_').replace('/', '-')
            pdf_filename = f"{safe_name}_QA_Report_{today_str}.pdf"

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                build_pdf(project_name, stats, tmp.name)
                pdf_bytes = open(tmp.name, "rb").read()
            os.unlink(tmp.name)

            status.update(label="✅  Report ready!", state="complete")

        # ── Show summary metrics ────────────────────────────────────────────────
        st.markdown(f"### {project_name} — Report Summary")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total reviewed",   total)
        col2.metric("Developer issues", dev_cnt,  f"{round(dev_cnt/total*100,1)}%"  if total else "")
        col3.metric("Designer issues",  des_cnt,  f"{round(des_cnt/total*100,1)}%"  if total else "")
        col4.metric("Both",             both_cnt, f"{round(both_cnt/total*100,1)}%" if total else "")

        st.markdown("**Issues by category:**")
        st.dataframe(
            type_summary.reset_index().rename(columns={'IssueType': 'Category'}),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")

        # ── Download button ─────────────────────────────────────────────────────
        st.download_button(
            label="⬇️  Download PDF Report",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            use_container_width=True,
        )

        st.success(
            f"✅  PDF ready — **{pdf_filename}**  \n"
            f"Click the button above to download."
        )

    except Exception as e:
        err = str(e)
        if "secrets" in err.lower() or "service_account" in err.lower() or "credentials" in err.lower():
            st.error(
                "❌  Credentials error. Go to Streamlit Cloud → App Settings → Secrets "
                "and make sure all fields from your credentials.json are pasted in TOML format. "
                "See the 'How to use this tool' section above for the exact format."
            )
        else:
            st.error(f"❌  Something went wrong: {e}")
        with st.expander("Error details (share with QA Team Lead)"):
            import traceback
            st.code(traceback.format_exc())


# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='color:#9E9E9E;font-size:12px;text-align:center'>"
    "QA Report Tool &nbsp;·&nbsp; Encircle Technologies &nbsp;·&nbsp; "
    "Built by QA Team Lead &nbsp;·&nbsp; Free on Streamlit Cloud"
    "</p>",
    unsafe_allow_html=True,
)
