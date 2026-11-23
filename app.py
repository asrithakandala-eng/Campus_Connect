"""CampusConnect - Smart Campus Lost and Found Matcher (SRM University-AP).

Run with:  streamlit run app.py
"""
import html
from datetime import date

import pandas as pd
import streamlit as st

import config
import database as db
import nlp_matching as nlp
import validation as val
from styles import CSS

st.set_page_config(page_title="CampusConnect | SRM University\u2013AP", page_icon="\U0001F393",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource
def bootstrap() -> bool:
    secret = None
    try:
        secret = st.secrets["ADMIN_PASSWORD"]
    except Exception:
        pass
    db.init_db(secret)
    return True


bootstrap()

PAGES = {
    "dashboard": "\U0001F3E0  Dashboard",
    "lost": "\U0001F4DD  Report a Lost Item",
    "found": "\U0001F4E6  Report a Found Item",
    "match": "\U0001F50D  Smart Matches",
    "claim": "\U0001F9FE  Submit a Claim",
    "reports": "\U0001F4CB  All Reports",
    "admin": "\U0001F6E1\uFE0F  Administrator",
    "about": "\u2139\uFE0F  About & Methodology",
}
st.session_state.setdefault("page", "dashboard")
st.session_state.setdefault("admin", None)
st.session_state.setdefault("failed_logins", 0)


def go(page: str):
    st.session_state["page"] = page


# ----------------------------------------------------------------- helpers
def esc(x) -> str:
    return html.escape(str(x))


def title(icon: str, text: str, sub: str = ""):
    st.markdown(f"<div class='cc-page-title'><h2 style='margin:0'>{icon} {esc(text)}</h2></div>", unsafe_allow_html=True)
    if sub:
        st.caption(sub)


def stat(label: str, value, tone: str = ""):
    st.markdown(f"<div class='cc-stat {tone}'><div class='v'>{value}</div><div class='l'>{esc(label)}</div></div>",
                unsafe_allow_html=True)


def badge(level: str) -> str:
    return f"<span class='cc-badge cc-{level.lower()}'>{level} RISK</span>"




def match_cards(df: pd.DataFrame, other: str):
    if df.empty:
        st.info(f"No open {other} reports to compare with yet.")
        return
    for i, r in enumerate(df.itertuples(), 1):
        band = "Strong similarity" if r.score >= 0.6 else "Possible similarity" if r.score >= config.MATCH_THRESHOLD else "Weak similarity"
        st.markdown(
            f"<div class='cc-match'><div class='top'><div>"
            f"<div class='name'>#{i} &nbsp;{esc(r.item_name)} &nbsp;<span style='color:#64748b;font-weight:500'>({esc(r.report_id)})</span></div>"
            f"<div class='meta'>{esc(r.category)} &middot; {esc(r.location)} &middot; {esc(r.date)}</div></div>"
            f"<div class='score'>{r.score * 100:.1f}%<small>Item Matching Score &middot; {band}</small></div></div>"
            f"<div class='cc-bar'><div style='width:{min(r.score, 1) * 100:.0f}%'></div></div>"
            f"<div class='cc-break'>Text (T) {r.text_sim:.2f} &nbsp;|&nbsp; Location (L) {r.loc_sim:.2f} &nbsp;|&nbsp; "
            f"Date (D) {r.date_sim:.2f} &nbsp;&rarr;&nbsp; S = 0.70\u00d7{r.text_sim:.2f} + 0.20\u00d7{r.loc_sim:.2f} + 0.10\u00d7{r.date_sim:.2f}</div></div>",
            unsafe_allow_html=True)
    st.markdown(f"<div class='cc-note'>\u2139\uFE0F {esc(config.MATCH_DISCLAIMER)}</div>", unsafe_allow_html=True)


def open_reports(kind: str) -> pd.DataFrame:
    df = db.list_reports(kind)
    return df[df["status"].isin(["Open", "Claim in Progress"])]


# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"<div class='cc-brand'><b>\U0001F393 {config.APP_NAME}</b><span>{config.UNIVERSITY}</span></div>",
                unsafe_allow_html=True)
    st.radio("Navigate", list(PAGES), format_func=PAGES.get, key="page", label_visibility="collapsed")
    st.divider()
    st.caption("Report lost & found items, get smart matches, and claim belongings safely.")
    if st.session_state.admin:
        st.success(f"Signed in as {st.session_state.admin['username']}")

page = st.session_state["page"]


# ----------------------------------------------------------------- dashboard
def page_dashboard():
    st.markdown(f"<div class='cc-hero'><div class='t'>\U0001F393 {config.APP_NAME}</div>"
                f"<div class='s'>{config.APP_SUBTITLE}</div><div class='u'>{config.UNIVERSITY}</div></div>",
                unsafe_allow_html=True)
    s = db.get_stats()
    c = st.columns(3)
    with c[0]: stat("Total reports", s["reports"])
    with c[1]: stat("Lost items reported", s["lost"], "warn")
    with c[2]: stat("Found items reported", s["found"], "good")
    c = st.columns(3)
    with c[0]: stat("Claims submitted", s["claims"])
    with c[1]: stat(f"Possible matches (score \u2265 {config.MATCH_THRESHOLD:.2f})", s["matches"], "good")
    with c[2]: stat("Claims flagged for suspicious activity", s["flagged"], "bad")

    st.subheader("Quick actions")
    q = st.columns(4)
    q[0].button("\U0001F4DD Report lost item", on_click=go, args=("lost",), key="q1")
    q[1].button("\U0001F4E6 Report found item", on_click=go, args=("found",), key="q2")
    q[2].button("\U0001F50D Find matches", on_click=go, args=("match",), key="q3")
    q[3].button("\U0001F9FE Claim an item", on_click=go, args=("claim",), key="q4")

    st.subheader("Recent reports")
    df = db.list_reports().head(8).copy()
    df["data"] = df["is_demo"].map({1: "Demo", 0: "Real"})
    st.dataframe(df[["report_id", "item_name", "category", "report_type", "location", "date", "status", "data"]],
                 hide_index=True)
    st.button("View all reports \u2192", on_click=go, args=("reports",), key="q5")


# ----------------------------------------------------------------- report forms
def report_form(kind: str):
    lost = kind == "lost"
    title("\U0001F4DD" if lost else "\U0001F4E6", "Report a Lost Item" if lost else "Report a Found Item",
          "Fill in every field. Contact details and the private clue are never shown publicly.")
    if not lost:
        st.markdown("<div class='cc-note'>Describe only <b>publicly visible</b> features in the description. "
                    "Keep one or two unique details (marks, contents, serial endings) for the <b>private clue</b> so the "
                    "real owner can prove ownership.</div>", unsafe_allow_html=True)
    with st.form(f"form_{kind}"):
        a, b = st.columns(2)
        item = a.text_input("Item name *", placeholder="e.g. Black water bottle")
        cat = b.selectbox("Item category *", config.CATEGORIES)
        desc = st.text_area("Item description *", placeholder="Colour, brand, size, shape, anything others can see...")
        a, b = st.columns(2)
        loc = a.selectbox("Last seen location *" if lost else "Found location *", config.LOCATIONS)
        d = b.date_input("Date lost *" if lost else "Date found *", value=date.today(), max_value=date.today())
        a, b = st.columns(2)
        who = a.text_input("Reporter name *" if lost else "Finder name *")
        contact = b.text_input("Contact information *", placeholder="email or phone number")
        clue = st.text_input("Private identifying clue *", 
                             placeholder="Something only the owner would know (kept hidden)")
        submitted = st.form_submit_button("Submit report")
    if not submitted:
        return
    data = dict(item_name=item, category=cat, description=desc, location=loc, date=d,
                person_name=who, contact=contact, private_clue=clue)
    errors = val.validate_report(data)
    if errors:
        for e in errors:
            st.error(e)
        return
    rid = db.add_report(kind, data)
    st.success(f"\u2705 Report submitted successfully! Your report ID is **{rid}**. Please note it down.")
    st.subheader("Top possible matches" + (" among found items" if lost else " among lost items"))
    top = nlp.rank_matches(dict(item_name=item, description=desc, location=loc, date=d),
                           open_reports("found" if lost else "lost"))
    match_cards(top, "found" if lost else "lost")


# ----------------------------------------------------------------- smart matches
def page_match():
    title("\U0001F50D", "Smart Matches", "TF-IDF + cosine similarity ranks the most similar reports.")
    mode = st.radio("Find matches for", ["A lost report", "A found report", "A new description"], horizontal=True)
    if mode == "A new description":
        with st.form("quick_match"):
            a, b = st.columns(2)
            name = a.text_input("Item name")
            loc = b.selectbox("Location", config.LOCATIONS)
            desc = st.text_area("Description")
            d = st.date_input("Date lost", value=date.today(), max_value=date.today())
            go_ = st.form_submit_button("Find matches")
        if go_:
            if len(name.strip()) < 3 or len(desc.strip()) < 10:
                st.error("Please enter an item name (3+ characters) and a description (10+ characters).")
            else:
                match_cards(nlp.rank_matches(dict(item_name=name, description=desc, location=loc, date=d),
                                             open_reports("found")), "found")
        return
    kind = "lost" if mode == "A lost report" else "found"
    pool = db.list_reports(kind)
    if pool.empty:
        st.info("No reports yet.")
        return
    labels = {r.report_id: f"{r.report_id} \u00b7 {r.item_name} \u00b7 {r.location}" for r in pool.itertuples()}
    rid = st.selectbox("Choose a report", list(labels), format_func=labels.get)
    src = pool[pool["report_id"] == rid].iloc[0]
    st.write(f"**{src['item_name']}**: {src['description']}")
    top = nlp.rank_matches(dict(item_name=src["item_name"], description=src["description"],
                                location=src["location"], date=src["date"]),
                           open_reports("found" if kind == "lost" else "lost"))
    st.subheader("Top 3 possible matches")
    match_cards(top, "found" if kind == "lost" else "lost")


# ----------------------------------------------------------------- claims
def page_claim():
    title("\U0001F9FE", "Submit an Ownership Claim", "Every claim is checked and then reviewed by a human administrator.")
    found = open_reports("found")
    if found.empty:
        st.info("There are no found items available to claim right now.")
    else:
        labels = {r.report_id: f"{r.report_id} \u00b7 {r.item_name} \u00b7 {r.location} \u00b7 {r.date}" for r in found.itertuples()}
        fid = st.selectbox("Select the found item *", list(labels), format_func=labels.get)
        item = found[found["report_id"] == fid].iloc[0]
        st.markdown(f"<div class='cc-note'><b>{esc(item['item_name'])}</b> ({esc(fid)}): {esc(item['description'])}</div>",
                    unsafe_allow_html=True)
        with st.form("claim_form"):
            a, b = st.columns(2)
            name = a.text_input("Your name *")
            contact = b.text_input("Contact information *", placeholder="email or phone number")
            lost_id = st.text_input("Your lost report ID (optional)", placeholder="e.g. L-1001")
            desc = st.text_area("Private ownership description *",
                                placeholder="Describe details only the owner would know: marks, contents, damage, stickers...")
            ok = st.form_submit_button("Submit claim")
        if ok:
            lost_id = lost_id.strip().upper()
            data = dict(found_id=fid, claimant_name=name, contact=contact, lost_id=lost_id, ownership_description=desc)
            errors = val.validate_claim(data, True, bool(lost_id) and db.get_report(lost_id) is not None)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                cid = db.add_claim(data)
                st.success(f"\u2705 Claim submitted. Your claim ID is **{cid}** (status: Pending Review). "
                           "An administrator will verify your details before anything is handed over.")
                st.info("Please keep your claim ID and contact details to check your claim status below.")
    with st.expander("Check the status of my claim"):
        cid = st.text_input("Claim ID", key="trk_id", placeholder="e.g. C-1001")
        contact = st.text_input("Contact used in the claim", key="trk_contact")
        if st.button("Check status", key="trk_btn"):
            r = db.claim_status_lookup(cid, contact)
            if r:
                st.success(f"Status: **{r['status']}** (submitted {r['submitted_at']})")
            else:
                st.error("No claim found with that ID and contact.")


# ----------------------------------------------------------------- all reports
def page_reports():
    title("\U0001F4CB", "All Reports", "Public view: contact details and private clues are never shown here.")
    df = db.list_reports()
    c = st.columns([2, 1, 1, 1, 1])
    q = c[0].text_input("Search", placeholder="item name, description or report ID")
    cat = c[1].selectbox("Category", ["All"] + config.CATEGORIES)
    loc = c[2].selectbox("Location", ["All"] + config.LOCATIONS)
    typ = c[3].selectbox("Type", ["All", "Lost", "Found"])
    sta = c[4].selectbox("Status", ["All"] + config.REPORT_STATUSES)
    if q.strip():
        m = (df["item_name"].str.contains(q, case=False, regex=False) | df["description"].str.contains(q, case=False, regex=False)
             | df["report_id"].str.contains(q, case=False, regex=False))
        df = df[m]
    for col, v in (("category", cat), ("location", loc), ("report_type", typ), ("status", sta)):
        if v != "All":
            df = df[df[col] == v]
    df = df.copy()
    df["data"] = df["is_demo"].map({1: "Demo", 0: "Real"})
    st.caption(f"{len(df)} report(s) found")
    st.dataframe(df[["report_id", "item_name", "category", "report_type", "location", "date", "status", "data"]],
                 hide_index=True)


# ----------------------------------------------------------------- admin
def admin_login():
    title("\U0001F6E1\uFE0F", "Administrator Login", "Authorised staff only.")
    if st.session_state.failed_logins >= config.MAX_LOGIN_ATTEMPTS:
        st.error("Too many failed attempts in this session. Please reload the page and try again.")
        return
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")
    if ok:
        user = db.authenticate(u, p)
        if user:
            st.session_state.admin = user
            st.session_state.failed_logins = 0
            st.rerun()
        else:
            st.session_state.failed_logins += 1
            st.error("Invalid username or password.")
    st.caption("Default demo credentials are listed in the README. Change them before real use.")


def page_admin():
    admin = st.session_state.admin
    if not admin or admin.get("role") != "admin":
        admin_login()
        return
    a, b = st.columns([5, 1])
    with a:
        title("\U0001F6E1\uFE0F", "Administrator Dashboard", f"Welcome, {admin['full_name']}")
    if b.button("Sign out"):
        st.session_state.admin = None
        st.rerun()
    st.markdown("<div class='cc-note'>Fraud checks highlight <b>patterns</b> for review. They never reject a claim and "
                "never accuse anyone. A human decision is always required, and the risk level is separate from the item "
                "matching score.</div>", unsafe_allow_html=True)
    tabs = st.tabs(["Overview", "Claims & Review", "Suspicious Activity", "Manage Reports", "Review History"])
    s = db.get_stats()

    with tabs[0]:
        c = st.columns(4)
        with c[0]: stat("Total claims received", s["claims"])
        with c[1]: stat("Low-risk claims", s["low"], "good")
        with c[2]: stat("Medium-risk claims", s["medium"], "warn")
        with c[3]: stat("High-risk claims", s["high"], "bad")
        c = st.columns(4)
        with c[0]: stat("Claims needing manual verification", s["manual"], "warn")
        with c[1]: stat("Lost reports", s["lost"])
        with c[2]: stat("Found reports", s["found"])
        with c[3]: stat("Possible matches", s["matches"], "good")
        st.bar_chart(pd.DataFrame({"claims": [s["low"], s["medium"], s["high"]]}, index=["LOW", "MEDIUM", "HIGH"]))

    with tabs[1]:
        claims = db.list_claims()
        if claims.empty:
            st.info("No claims yet.")
        else:
            f1, f2 = st.columns(2)
            risk_f = f1.selectbox("Filter by risk", ["All", "HIGH", "MEDIUM", "LOW"])
            stat_f = f2.selectbox("Filter by status", ["All"] + config.CLAIM_STATUSES)
            view = claims
            if risk_f != "All":
                view = view[view["risk_level"] == risk_f]
            if stat_f != "All":
                view = view[view["status"] == stat_f]
            st.dataframe(view[["claim_id", "found_id", "item_name", "claimant_name", "risk_level", "risk_points", "status", "submitted_at"]],
                         hide_index=True)
            if view.empty:
                st.info("No claims match these filters.")
            else:
                cid = st.selectbox("Open a claim", list(view["claim_id"]))
                row = claims[claims["claim_id"] == cid].iloc[0]
                st.markdown(f"### {cid} &nbsp; {badge(row['risk_level'])}", unsafe_allow_html=True)
                L, R = st.columns(2)
                with L:
                    st.markdown("**Claimant**")
                    st.write(f"{row['claimant_name']} \u00b7 {row['contact']}")
                    st.write(f"Status: **{row['status']}** \u00b7 Submitted: {row['submitted_at']}")
                    st.markdown("**Ownership description given**")
                    st.info(row["ownership_description"])
                with R:
                    found = db.get_report(row["found_id"], admin=True)

                    if found is not None:
                        st.markdown(f"**Found report {row['found_id']}**: {found['item_name']}")
                        st.write(found["description"])
                        st.markdown("**🔒 Finder's private clue (admin only)**")
                        st.warning(found.get("private_clue") or "No private clue available.")
                    else:
                        st.warning("The linked found report could not be retrieved.")

                    if pd.notna(row["lost_id"]) and str(row["lost_id"]).strip():
                        lost = db.get_report(row["lost_id"], admin=True)

                        if lost is not None:
                            st.markdown(f"**🔒 Linked lost report {row['lost_id']}: private clue (admin only)**")
                            st.warning(lost.get("private_clue") or "No private clue available.")
                        else:
                            st.info("The linked lost report could not be retrieved.")
                st.markdown("**Why this risk level?**")
                flags = db.list_flags(cid)
                if flags.empty:
                    st.success("No suspicious indicators found. Information is reasonably consistent.")
                else:
                    for f in flags.itertuples():
                        st.markdown(f"- **{f.indicator}** (severity {f.severity}): {f.detail}")
                st.markdown("**Administrator decision**")
                with st.form(f"review_{cid}"):
                    action = st.selectbox("Action", list(config.REVIEW_ACTIONS))
                    note = st.text_area("Note (required for reject / request information)")
                    go_ = st.form_submit_button("Record decision")
                if go_:
                    if action in ("Reject claim", "Request additional information") and len(note.strip()) < 5:
                        st.error("Please add a short note explaining this decision.")
                    else:
                        new = db.record_review(cid, admin["username"], action, note)
                        st.success(f"Decision recorded. {cid} is now **{new}**.")
                        st.rerun()

    with tabs[2]:
        st.subheader("Suspicious activity history")
        flags = db.list_flags()
        if flags.empty:
            st.info("No suspicious indicators recorded.")
        else:
            st.dataframe(flags.rename(columns={"risk_level": "claim_risk"}), hide_index=True)
            st.caption("Indicators are patterns for review, not proof of wrongdoing.")

    with tabs[3]:
        kind = st.radio("Report type", ["found", "lost"], horizontal=True, format_func=str.title)
        df = db.admin_reports(kind)
        st.dataframe(df, hide_index=True)
        if not df.empty:
            c = st.columns([2, 2, 1])
            rid = c[0].selectbox("Report", list(df["report_id"]), key="mr_id")
            new = c[1].selectbox("New status", config.REPORT_STATUSES, key="mr_status")
            if c[2].button("Update", key="mr_btn"):
                db.set_report_status(kind, rid, new)
                st.success(f"{rid} is now '{new}'.")
                st.rerun()
        st.caption("Mark a found item 'Returned' only after the owner has been verified in person.")

    with tabs[4]:
        h = db.list_review_history()
        if h.empty:
            st.info("No review decisions recorded yet.")
        else:
            st.dataframe(h, hide_index=True)


# ----------------------------------------------------------------- about
def flow(steps):
    inner = "<span class='cc-arrow'>\u2192</span>".join(f"<span class='cc-step'>{esc(s)}</span>" for s in steps)
    st.markdown(f"<div class='cc-flow'>{inner}</div>", unsafe_allow_html=True)


def page_about():
    title("\u2139\uFE0F", "About & Project Methodology")
    st.subheader("Project introduction")
    st.write("CampusConnect is a lost-and-found platform for SRM University\u2013AP. Students report lost and found "
             "belongings; the system suggests likely matches using NLP and flags unusual ownership claims for an "
             "administrator to review.")
    st.subheader("Problem statement")
    st.write("Campus lost-and-found is usually manual: notices on boards and group chats, no reliable way to link a "
             "lost report to a found one, and little protection against someone claiming an item that is not theirs.")
    st.subheader("Objectives")
    st.markdown("- Make reporting lost and found items quick and structured.\n"
                "- Automatically rank the most similar reports using TF-IDF and cosine similarity.\n"
                "- Highlight suspicious claim patterns for human review.\n"
                "- Keep private clues and contact details confidential.\n"
                "- Keep a permanent, auditable record of every review decision.")
    st.subheader("Technologies used")
    st.markdown("Python \u00b7 Streamlit (UI) \u00b7 SQLite (storage) \u00b7 Pandas (data handling) \u00b7 "
                "Scikit-learn (TF-IDF, cosine similarity) \u00b7 Python rule logic (fraud detection) \u00b7 "
                "PBKDF2-HMAC-SHA256 (password hashing)")
    st.subheader("NLP implementation")
    st.write("Each description (item name + public description) is lowercased, stripped of punctuation, cleaned of "
             "stop words (such as 'the', 'with', 'near') and lightly stemmed so 'earbuds' and 'earbud' match.")
    st.subheader("TF-IDF")
    st.write("Term Frequency\u2013Inverse Document Frequency turns each cleaned description into a numeric vector. Words "
             "that are distinctive (e.g. 'casio', 'hoodie') get more weight than words that appear in almost every report.")
    st.subheader("Cosine similarity")
    st.write("The cosine of the angle between two TF-IDF vectors measures how similar the descriptions are, from 0 "
             "(nothing in common) to 1 (identical wording).")
    st.subheader("Matching formula")
    st.latex(r"S = 0.70\,T + 0.20\,L + 0.10\,D")
    st.markdown("- **T**: text similarity (TF-IDF cosine).\n"
                "- **L**: location similarity: 1.0 same place, 0.5 same campus zone, 0 otherwise.\n"
                f"- **D**: date proximity: 1.0 on the same day, falling to 0 at {config.DATE_WINDOW_DAYS} days apart.")
    st.info(config.MATCH_DISCLAIMER)
    st.subheader("Matching workflow")
    flow(["User Input", "Python & NLP Processing", "TF-IDF Vectorization", "Cosine Similarity", "Ranked Matching Results"])
    st.subheader("Fraud detection methodology")
    st.write("Rule-based checks run on every claim before an administrator sees it:")
    st.markdown("- Private clue comparison with the found report (and the linked lost report, if given).\n"
                "- Contradictions between lost and found reports, and incomplete ownership descriptions.\n"
                "- Several people claiming the same item, or near-identical claim descriptions.\n"
                "- Repeated unsuccessful claims and unusual bursts of submissions from one account.")
    st.markdown("Each indicator has a severity (1 or 2). **LOW**: no indicators. **MEDIUM**: at least one indicator, "
                "so extra verification is recommended. **HIGH**: several indicators together. The reasons are always "
                "shown. A flag is a reason to look closer, never proof, and the system never rejects a claim on its own.")
    st.warning("Claim Risk Level and Item Matching Score are two separate results and are never combined.")
    st.subheader("Claim verification workflow")
    flow(["Claim Submission", "Information Verification", "Fraud Detection Checks", "Risk Classification",
          "Administrator Review", "Final Decision"])
    st.subheader("Database structure")
    st.markdown("| Table | Purpose |\n|---|---|\n"
                "| `lost_reports` / `found_reports` | Reports with unique IDs (L-1001, F-1001...) and private clues |\n"
                "| `users` | Claimant accounts, identified by contact |\n"
                "| `admins` | Administrator accounts with salted password hashes |\n"
                "| `claims` | Ownership claims linked to a found report (and optionally a lost report) |\n"
                "| `fraud_flags` | Indicators and reasons behind each risk level |\n"
                "| `review_history` | Every administrator decision with its date |")
    st.subheader("System workflow")
    st.write("Report \u2192 automatic matching \u2192 owner submits a claim \u2192 fraud checks \u2192 administrator verifies "
             "in person \u2192 item marked Returned.")
    st.subheader("Limitations")
    st.markdown("- Matching depends on the wording of descriptions; it does not understand synonyms or images.\n"
                "- Fraud rules are simple heuristics and can produce false alarms or miss cases.\n"
                "- Claimants are identified only by the contact they type; there is no student login yet.\n"
                "- SQLite on Streamlit Community Cloud is not guaranteed to persist across restarts.\n"
                "- Demo records are synthetic and say nothing about real campus performance.")
    st.subheader("Future enhancements")
    st.markdown("- Secure student login\n- Image-based item recognition\n- Email and notification alerts\n"
                "- Permanent cloud database\n- Mobile application\n- Advanced fraud detection\n"
                "- University administrator integration\n- Real-time status tracking")


{
    "dashboard": page_dashboard,
    "lost": lambda: report_form("lost"),
    "found": lambda: report_form("found"),
    "match": page_match,
    "claim": page_claim,
    "reports": page_reports,
    "admin": page_admin,
    "about": page_about,
}[page]()
