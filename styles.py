"""
CampusConnect - Complete blue and white theme
SRM University-AP
"""

CSS = r"""
<style>

/* =====================================================
   1. GLOBAL COLOURS AND PAGE BACKGROUND
   ===================================================== */

:root {
    color-scheme: light;
}

html, body, .stApp {
    background-color: #EAF4FF !important;
    color: #172F49 !important;
    font-family: "Segoe UI", Arial, sans-serif !important;
}

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background-color: #EAF4FF !important;
    color: #172F49 !important;
}

[data-testid="stHeader"] {
    background-color: transparent !important;
}

.block-container {
    max-width: 1500px !important;
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
}

/* =====================================================
   2. SIDEBAR
   ===================================================== */

[data-testid="stSidebar"] {
    background-color: #DCEEFF !important;
    border-right: 1px solid #C3DDF5 !important;
}

[data-testid="stSidebar"] > div {
    background-color: #DCEEFF !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] div {
    color: #172F49 !important;
}

/* Sidebar navigation buttons */
[data-testid="stSidebar"] button {
    color: #172F49 !important;
    border-radius: 9px !important;
}

/* Sidebar alerts and signed-in information */
[data-testid="stSidebar"] [data-testid="stAlert"],
[data-testid="stSidebar"] [data-testid="stNotification"] {
    background-color: #FFFFFF !important;
    color: #172F49 !important;
    border: 1px solid #C3DDF5 !important;
    border-radius: 10px !important;
}

[data-testid="stSidebar"] [data-testid="stAlert"] *,
[data-testid="stSidebar"] [data-testid="stNotification"] * {
    color: #172F49 !important;
}

/* =====================================================
   3. CAMPUSCONNECT BRAND HEADER
   ===================================================== */

.cc-brand {
    padding: 0.4rem 0.2rem 1rem 0.2rem;
}

.cc-brand b {
    font-size: 1.35rem;
    color: #0B2A6F;
    font-weight: 800;
}

.cc-brand span {
    display: block;
    font-size: 0.78rem;
    color: #475569;
}

.cc-hero {
    background: linear-gradient(
        120deg,
        #0B2A6F 0%,
        #1D4ED8 55%,
        #3B82F6 100%
    );
    color: #FFFFFF;
    padding: 1.6rem 1.8rem;
    border-radius: 16px;
    margin-bottom: 1.2rem;
}

.cc-hero,
.cc-hero * {
    color: #FFFFFF !important;
}

.cc-hero .t {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.1;
}

.cc-hero .s {
    font-size: 1.05rem;
    opacity: 0.98;
    margin-top: 0.25rem;
}

.cc-hero .u {
    font-size: 0.85rem;
    opacity: 0.9;
    margin-top: 0.5rem;
}

/* =====================================================
   4. PAGE HEADINGS AND NORMAL TEXT
   ===================================================== */

h1, h2, h3, h4, h5, h6 {
    color: #172F49 !important;
    font-weight: 750 !important;
    letter-spacing: -0.02em;
}

[data-testid="stMain"] p,
[data-testid="stMain"] label,
[data-testid="stMain"] span,
[data-testid="stMain"] li {
    color: #172F49;
}

[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label {
    color: #172F49 !important;
    font-weight: 650 !important;
}

/* =====================================================
   5. FORM CONTAINERS
   ===================================================== */

[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: rgba(255, 255, 255, 0.35) !important;
    border: 1px solid #B8D3EC !important;
    border-radius: 14px !important;
    padding: 0.4rem !important;
}

/* =====================================================
   6. TEXT INPUTS, TEXT AREAS AND NUMBER INPUTS
   ===================================================== */

.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    border: 1px solid #94A3B8 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    font-size: 1rem !important;
}

/* Input focus */
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus,
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    border: 1.5px solid #2563EB !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12) !important;
}

/* Placeholder text */
input::placeholder,
textarea::placeholder {
    color: #64748B !important;
    -webkit-text-fill-color: #64748B !important;
    opacity: 1 !important;
}

/* =====================================================
   7. DROPDOWNS - ITEM CATEGORY AND LOCATIONS
   ===================================================== */

/* Force every visible dropdown layer to white */
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
[data-testid="stSelectbox"] [data-baseweb="select"] > div > div > div,
[data-testid="stMultiSelect"] [data-baseweb="select"],
[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div > div {
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    border-color: #94A3B8 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

/* Dropdown text must be black */
[data-testid="stSelectbox"] [data-baseweb="select"] *,
[data-testid="stMultiSelect"] [data-baseweb="select"] * {
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
}

/* Dropdown arrow */
[data-testid="stSelectbox"] [data-baseweb="select"] svg,
[data-testid="stMultiSelect"] [data-baseweb="select"] svg {
    fill: #172F49 !important;
    color: #172F49 !important;
}

/* Dropdown focus */
[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within,
[data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12) !important;
}

/* =====================================================
   8. DATE AND TIME INPUTS
   ===================================================== */

/* Date/time outer boxes and inner wrappers */
[data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stDateInput"] [data-baseweb="input"] > div,
[data-testid="stTimeInput"] [data-baseweb="input"],
[data-testid="stTimeInput"] [data-baseweb="input"] > div {
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    border: 1px solid #94A3B8 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

/* Date/time actual text */
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input {
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    border: none !important;
}

/* Calendar and clock icons */
[data-testid="stDateInput"] svg,
[data-testid="stTimeInput"] svg {
    color: #172F49 !important;
    fill: #172F49 !important;
}

/* =====================================================
   9. DROPDOWN POPUP OPTIONS
   ===================================================== */

[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="option"] {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

[data-baseweb="popover"] [role="option"] * {
    color: #000000 !important;
}

/* =====================================================
   10. BUTTONS
   ===================================================== */

.stButton button,
.stFormSubmitButton button,
.stDownloadButton button,
[data-testid="stFormSubmitButton"] button {
    background-color: #FFFFFF !important;
    color: #172F49 !important;
    border: 1px solid #1D4ED8 !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 0.45rem 1.1rem !important;
    box-shadow: none !important;
}

.stButton button p,
.stFormSubmitButton button p,
.stDownloadButton button p {
    color: #172F49 !important;
    font-weight: 700 !important;
}

.stButton button:hover,
.stFormSubmitButton button:hover,
.stDownloadButton button:hover {
    background-color: #DBEAFE !important;
    color: #172F49 !important;
    border-color: #1D4ED8 !important;
}

/* =====================================================
   11. RADIO BUTTONS AND CHECKBOXES
   ===================================================== */

[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {
    color: #172F49 !important;
}

[data-testid="stRadio"] p,
[data-testid="stCheckbox"] p {
    color: #172F49 !important;
}

/* =====================================================
   12. CAMPUSCONNECT STATISTICS AND CARDS
   ===================================================== */

.cc-page-title {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.8rem;
}

.cc-stat {
    background: #FFFFFF;
    border: 1px solid #DBEAFE;
    border-left: 5px solid #1D4ED8;
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.cc-stat .v {
    font-size: 1.9rem;
    font-weight: 800;
    color: #0B2A6F;
    line-height: 1.1;
}

.cc-stat .l {
    font-size: 0.85rem;
    color: #475569;
}

.cc-stat.warn {
    border-left-color: #D97706;
}

.cc-stat.bad {
    border-left-color: #DC2626;
}

.cc-note {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    color: #172F49;
}

.cc-demo {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 10px;
    padding: 0.55rem;
}

.cc-match {
    background: #FFFFFF;
    border: 1px solid #DBEAFE;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.cc-match .top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

.cc-match .name {
    font-weight: 700;
    font-size: 1.05rem;
    color: #0B2A6F;
}

.cc-match .meta {
    color: #475569;
    font-size: 0.88rem;
}

.cc-match .score {
    font-size: 1.7rem;
    font-weight: 800;
    color: #1D4ED8;
    text-align: right;
}

.cc-match .score small {
    display: block;
    font-size: 0.72rem;
    font-weight: 600;
    color: #475569;
}

.cc-bar {
    height: 8px;
    border-radius: 6px;
    background: #E2E8F0;
    margin: 0.7rem 0 0.4rem 0;
    overflow: hidden;
}

.cc-bar > div {
    height: 100%;
    background: linear-gradient(90deg, #60A5FA, #1D4ED8);
}

.cc-break {
    font-size: 0.8rem;
    color: #475569;
}

.cc-badge {
    display: inline-block;
    padding: 0.12rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 650;
}

.cc-low {
    background: #DCFCE7;
    color: #166534;
}

.cc-medium {
    background: #FEF3C7;
    color: #92400E;
}

.cc-flow {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    margin: 0.5rem 0 1rem 0;
}

.cc-step {
    background: #1D4ED8;
    color: #FFFFFF;
    border-radius: 8px;
    padding: 0.35rem 0.7rem;
    font-size: 0.85rem;
}

.cc-arrow {
    color: #1D4ED8;
    font-weight: 800;
}

/* =====================================================
   13. TABLES AND DATAFRAMES
   ===================================================== */

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background-color: #FFFFFF !important;
    border: 1px solid #DBEAFE !important;
    border-radius: 10px !important;
    overflow: hidden;
}

/* =====================================================
   14. ALERTS AND NOTIFICATIONS
   ===================================================== */

[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: 1px solid #BFDBFE !important;
}

/* =====================================================
   15. DIVIDERS AND SCROLLBARS
   ===================================================== */

hr {
    border-color: #B8D3EC !important;
}

::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #EAF4FF;
}

::-webkit-scrollbar-thumb {
    background: #A8C7E8;
    border-radius: 8px;
}

/* =====================================================
   16. RESPONSIVE DESIGN
   ===================================================== */

@media (max-width: 640px) {
    .cc-hero {
        padding: 1.2rem;
    }

    .cc-hero .t {
        font-size: 1.5rem;
    }

    .cc-match .top {
        flex-direction: column;
        align-items: flex-start;
    }

    .cc-match .score {
        text-align: left;
    }
}

</style>
"""