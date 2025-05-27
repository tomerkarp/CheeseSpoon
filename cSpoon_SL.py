import streamlit as st
import pandas as pd
import urllib.parse
from streamlit_searchbox import st_searchbox as st_sb
from rapidfuzz import process, fuzz

st.markdown(
    """
    <style>
    /* Apply RTL + right-align to every element in every markdown block */
    div[data-testid="stMarkdownContainer"] * {
        direction: rtl !important;
        unicode-bidi: embed !important;
        text-align: right !important;
    }
    /* Tweak list padding so bullets still indent from the right */
    div[data-testid="stMarkdownContainer"] ul {
        padding-right: 1.5em !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



df = pd.read_json("Courses2.json", encoding="utf-8")
df["מספר מקצוע"] = df["מספר מקצוע"].astype(str).str.zfill(8)

@st.cache_data
def get_courses(query: str):
    # return list of courses matching the query
    choices = df["tag"].astype(str).unique()
    matches = process.extract(
        query,
        choices,
        scorer=fuzz.WRatio,
        limit=10
    )
    return [match[0] for match in matches if match[1] >= 60]


choice = st_sb(get_courses, placeholder="Search cours by number or name ...")

params = st.query_params
tag_param = params.get("tag", None)

if choice: 
    st.query_params.clear() 
    filtered = df[df["tag"] == choice]


elif tag_param:
    filtered = df[df["מספר מקצוע"] == tag_param]
else:
    filtered = pd.DataFrame() #empty


def render_course(r: pd.Series):
    st.markdown(f"## {r['מספר מקצוע']} - {r['שם מקצוע']}\n")

    st.markdown(f"**פקולטה:** {r['פקולטה']}")
    st.markdown(f"**נק״ז:** {r['נקודות']}")
    st.markdown("---")
    st.markdown("### סילבוס:") 
    st.markdown(f" {r["סילבוס"]} \n")

    def list_section(title: str, items: list):
        if not items: return
        html = f"<h4 style='margin-bottom:0'>{title}</h4>\n<ul>"
        for item in items:
            code = item.split(" - ")[0].strip()
            if " - "  in item:
                label, linkable = item, True
            else:
                matching = df.loc[df["מספר מקצוע"] == code, "tag"]
                if not matching.empty:
                    label ,linkable = matching.iat[0], True
                else:
                    label, linkable = code, False

            if linkable:
                href = f"/?tag={urllib.parse.quote(code)}"
                html += (
                    f"<li>"
                    f"<a href='{href}' target='_self'>{label}</a>"
                    f"</li>"
                )
            else:
                html += f"<li>{label}</li>\n"   
        html += "</ul>"
        st.markdown(html, unsafe_allow_html=True)
    
    list_section("מקצועות קדם:", r["מקצועות קדם"])
    list_section("מקצועות חסומים:", r["מקצועות חסומים"])
    list_section("מקצועות ללא זיכוי נוסף:", r["מקצועות ללא זיכוי נוסף"])
    list_section("מקצועות ללא זיכוי נוסף (מוכלים):", r["מקצועות ללא זיכוי נוסף (מוכלים)"])
    list_section("מקצועות צמודים:", r["מקצועות צמודים"])
    st.markdown("---")
    


for _, row in filtered.iterrows():
    render_course(row)