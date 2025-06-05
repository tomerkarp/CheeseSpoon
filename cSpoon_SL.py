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
st.markdown(
    """
    <style>
      /* This targets the main app container in recent Streamlit versions */
      div[data-testid="stAppViewContainer"] {
        direction: rtl !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <style>
    /* Float every stButton wrapper to the right */
    div.stButton {
    float: right !important;
    }
    /* Select the first button inside any stButton block */
    div.stButton > button:first-child {
      background: none !important;
      dir: rtl !important;
      border: none !important;
      padding: 0 !important;
      font-size: inherit !important;
      direction: rtl !important;
      text-align: right !important;
      unicode-bidi: embed !important;
      cursor: pointer !important;
    }
    /* On hover, darken the link like a normal <a> */
    div.stButton > button:first-child:hover {
      text-decoration: underline !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


df = pd.read_json("Courses3.json", encoding="utf-8")
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
if "old_choice" not in st.session_state:
    st.session_state["old_choice"] = None
if "clicked" not in st.session_state:
    st.session_state["clicked"] = False

choice = st_sb(get_courses, placeholder="Search cours by number or name ...")

# params = st.query_params
# tag_param = params.get("tag", None)

if st.session_state["clicked"] and st.session_state["old_choice"] == choice:
    st.session_state["old_choice"] = choice
    choice = st.session_state["choice"]
    
elif st.session_state["old_choice"] != choice:
    st.session_state["old_choice"] = choice
    st.session_state["choice"] = choice
    st.session_state["clicked"] = False
    


if choice: 
    
    filtered = df[df["tag"] == choice]



else:
    filtered = pd.DataFrame() #empty

def on_click(tag: str):
    st.session_state["clicked"] = True
    st.session_state["choice"] = tag


def render_course(r: pd.Series):
    st.markdown(f"## {r['מספר מקצוע']} - {r['שם מקצוע']}\n")

    st.markdown(f"**פקולטה:** {r['פקולטה']}")
    st.markdown(f"**נק״ז:** {r['נקודות']}")
    st.markdown("---")
    st.markdown("### סילבוס:") 
    st.markdown(f" {r["סילבוס"]} \n")

    def list_section(title: str, items: list):
        if not items: return
        st.markdown(f"### {title}")
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
                st.button(label, key = f"link_{code}", 
                          on_click=on_click, args=(label,))
            else:
                st.markdown(f"{label}")  
        st.markdown("")
    
    list_section("מקצועות קדם:", r["מקצועות קדם"])
    list_section("מקצועות חסומים:", r["מקצועות חסומים"])
    list_section("מקצועות ללא זיכוי נוסף:", r["מקצועות ללא זיכוי נוסף"])
    list_section("מקצועות ללא זיכוי נוסף (מוכלים):", r["מקצועות ללא זיכוי נוסף (מוכלים)"])
    list_section("מקצועות צמודים:", r["מקצועות צמודים"])
    st.markdown("---")
    


for _, row in filtered.iterrows():
    render_course(row)