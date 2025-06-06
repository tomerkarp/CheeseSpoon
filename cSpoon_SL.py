import urllib.request
import streamlit as st
import pandas as pd
from streamlit_searchbox import st_searchbox as st_sb
from rapidfuzz import process, fuzz
import requests 
import re
import time
import json
from dotenv import load_dotenv
import os
import concurrent.futures  # added to allow parallel API calls
import logging 



load_dotenv()
github_api_key = os.getenv("GITHUB_API_KEY")



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

headers = None

if  github_api_key:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization" :f"token {github_api_key}"
    }


session = requests.Session()
session.headers.update(headers)


df = pd.read_json("Courses4.json", encoding="utf-8")
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


@st.cache_data(show_spinner=False)
def get_semesters_from_github(course_num: str) -> list[tuple[str, str]]:
    """
    Call GitHub contents API to list subdirectories under:
      /repos/michael-maltsev/technion-histograms/contents/<course_num>
    Return a sorted list of semester-folder names (e.g. ["202301","202401",...]).
    If the folder doesn’t exist or an error occurs, return [].
    """
    api_url = (
        f"https://api.github.com/repos/"
        f"michael-maltsev/technion-histograms/contents/{course_num}"
        "?ref=main"
    )
    try:
        resp = session.get(api_url, timeout=5)
        if resp.status_code != 200:
            logging.error(f"Error fetching semesters for {course_num}: {resp.status_code}")
            return []
        contents = resp.json()
        semesters: list[(str, str)] = []
        for item in contents:
            if item.get("type") == "dir":
                item_name = item.get("name")
                sem_name = f"שנת {item_name[:4]} סמסטר {item_name[-1]}"  # Format as YYYYMM
                semesters.append((item_name, sem_name))
        if not semesters:
            logging.error(f"לא נמצאו סמסטרים עבור הקורס {course_num}.")
            return []
        # Sort descending so latest semester appears first
        semesters.sort(key=lambda x: x[0], reverse=True)
        return semesters
    except Exception as e:
        logging.error(f"Error fetching semesters for {course_num}. was: {e}")
        return []
    
@st.cache_data(show_spinner=False)    
def get_exams_from_github(course_num: str, semester: str) -> list[str]:
    """
    Fetch the histogram image for the given course and semester from GitHub.
    Returns the URL of the image.
    """
    api_url = (
        f"https://api.github.com/repos/"
        f"michael-maltsev/technion-histograms/contents/{course_num}/{semester}"
        "?ref=main"
    )
    try:
        resp = session.get(api_url, timeout=5)

        if resp.status_code != 200:
            logging.error(f"Error fetching grades for {course_num} in {semester}: {resp.status_code}")
            return []
        exams = []
        contents = resp.json()
        for item in contents:
            name = item.get("name") 
            if re.search(r"^(Exam|Final)\w+\.json$", name):
                rename = re.sub(r"\.json$", "", name)
                exams.append(rename)
        if not exams:
            logging.error(f"לא נמצאו ציונים עבור הקורס {course_num} בסמסטר {semester}.")
            return []
        return exams
    except Exception as e:
        logging.error(f"Error fetching grades for {course_num} in {semester}. was: {e}")
        return []
    
@st.cache_data(show_spinner=False)
def get_grade_info_from_github(course_num: str, semester: str, exam_name: str) -> tuple[dict[str, str], str]:
    """
    Fetch the histogram image for the given course and semester from GitHub.
    Returns the URL of the image.
    """
    api_url = (
        f"https://api.github.com/repos/"
        f"michael-maltsev/technion-histograms/contents/{course_num}/{semester}"
        "?ref=main"
    )
    try:
        resp = session.get(api_url, timeout=5)
        if resp.status_code != 200:
            logging.error(f"Error fetching histogram for {course_num} in {semester}: {resp.status_code}")
            return ({}, "")
        contents = resp.json()
        content = None
        for item in contents:
            if item.get("name") == f"{exam_name}.json":
                content_url = item.get("download_url")
                with urllib.request.urlopen(content_url) as response:
                    content = json.load(response)
            if item.get("name") == f"{exam_name}.png":
                img_url = item.get("download_url")
        if not content or not img_url:
            logging.error(f"לא נמצאו נתונים עבור {exam_name} בקורס {course_num} בסמסטר {semester}.")
            return ({}, "")
        return (content, img_url)
    
    except Exception as e:
        logging.error(f"Error fetching histogram for {course_num} in {semester}. was: {e}")
        return ({}, "")

@st.cache_data(show_spinner=False)
def get_average_from_github(course_num: str, semester: str, exam_name: str) -> dict[str, str]:

    api_url = (
        f"https://api.github.com/repos/"
        f"michael-maltsev/technion-histograms/contents/{course_num}/{semester}"
        "?ref=main"
    )
    try:
        resp = session.get(api_url, timeout=5)
        if resp.status_code != 200:
            logging.error(f"Error fetching histogram for {course_num} in {semester}: {resp.status_code}")
            return {}
        contents = resp.json()
        content = None
        for item in contents:
            if item.get("name") == f"{exam_name}.json":
                content_url = item.get("download_url")
                with urllib.request.urlopen(content_url) as response:
                    content = json.load(response)

        return content
    
    except Exception as e:
        logging.error(f"Error fetching histogram for {course_num} in {semester}. was: {e}")
        return {}
    


@st.cache_data(show_spinner=False)    
def get_overall_average_from_github(course_num: str) -> str:
    try:
        grades = []
        semesters = get_semesters_from_github(course_num)
        semesters = [sem[0] for sem in semesters]  
        semesters = list(filter(lambda x: int(x) >= 202100, semesters))
        # Process only first 3 semesters to limit API calls
        semesters = semesters[:3]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for semester in semesters:
                exams = get_exams_from_github(course_num, semester)
                count = 0
                for exam in exams:
                    if exam.startswith("Final") and count < 2:  # get up to 2 exams per semester
                        futures.append(executor.submit(get_average_from_github, course_num, semester, exam))
                        count += 1
            for future in concurrent.futures.as_completed(futures):
                info = future.result()
                median = info.get("median", 0.0)
                if median:
                    grades.append(float(median))
        return sum(grades) / len(grades) if grades else 0.0
    except Exception as e:
        logging.error(f"Error fetching overall average for {course_num}. was: {e}")
        return 0.0

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


show_mean = st.checkbox("הצג ממוצע קורסים", value=True)

def on_click(tag: str):
    st.session_state["clicked"] = True
    st.session_state["choice"] = tag


def render_course(r: pd.Series):
    st.markdown(f"## {r['מספר מקצוע']} - {r['שם מקצוע']}\n")

    st.markdown(f"**פקולטה:** {r['פקולטה']}")
    st.markdown(f"**נק״ז:** {r['נקודות']}")
    if show_mean:
        median = get_overall_average_from_github(r["מספר מקצוע"])
        if median:
            st.markdown(f"**ממוצע ציונים:** {median:.2f}")
        else:
            st.markdown(f"**ממוצע ציונים:** לא זמין")
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

#┌───────────────────────────────────────────────────────────────────────────┐
    def render_histogram(r: pd.Series):
        course_num = r["מספר מקצוע"]
        semesters = get_semesters_from_github(course_num)
        if not semesters:
            st.error(f"לא נמצאו סמסטרים עבור הקורס {course_num}.")
            return
        
        sem_choice = st.selectbox("בחר סמסטר להצגת היסטוגרמה:", options=semesters, format_func=lambda x: x[1])[0]
        if not sem_choice:
            st.error(f"לא נבחר סמסטר עבור הקורס {course_num}.")
            return
        exams = get_exams_from_github(course_num, sem_choice)
        if not exams:
            st.error(f"לא נמצאו ציונים עבור הקורס {course_num} בסמסטר {sem_choice}.")
            return
        exam_choice = st.selectbox("בחר מבחן להצגת היסטוגרמה:", options=exams, format_func=lambda x: x.replace("_", " ").title())
        if not exam_choice:
            st.error(f"לא נבחר מבחן עבור הקורס {course_num} בסמסטר {sem_choice}.")
            return
        grade_info, img_url = get_grade_info_from_github(course_num, sem_choice, exam_choice)
        if not grade_info or not img_url:
            st.error(f"לא נמצאו נתונים עבור {exam_choice} בקורס {course_num} בסמסטר {sem_choice}.")
            return
        
        st.table(grade_info)
        st.image(
            img_url,
            caption="Histogram of final exam grades",
            use_container_width=True,
        )

    # In the render_course function, replace the $SELECTION_PLACEHOLDER$ code with:
    render_histogram(r)
#└───────────────────────────────────────────────────────────────────────────┘

for _, row in filtered.iterrows():
    render_course(row)