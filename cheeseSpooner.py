import re 
import json
from collections import defaultdict
import pandas as pd

course_unlocks = defaultdict(list) 

files = [
    "courses_from_rishum.json",
    "courses_from_rishum2.json",
    "courses_from_rishum3.json",
]
courses_from_rishum = []
for file in files:
    with open(file, "r", encoding="utf-8") as f:
        courses_from_rishum.extend(json.load(f))

Courses = pd.DataFrame(courses_from_rishum)
Courses.drop(columns=["schedule"], inplace=True)
Courses = pd.json_normalize(Courses["general"])
Courses.drop(columns=["מועד ב", "מועד א", "מסגרת לימודים", "אחראים", "הערות", "בוחן מועד א", "בוחן מועד ב"], inplace=True)
Courses["מקצועות ללא זיכוי נוסף (מוכלים)"] = Courses["מקצועות ללא זיכוי נוסף (מוכלים)"].combine_first(Courses["מקצועות ללא זיכוי נוסף (מכילים)"])
Courses.drop(columns=["מקצועות ללא זיכוי נוסף (מכילים)"], inplace=True)

# Check for duplicate courses based on "מספר מקצוע"
if Courses["מספר מקצוע"].duplicated().any():
    duplicates = Courses[Courses["מספר מקצוע"].duplicated(keep=False)]["מספר מקצוע"].unique()
    print("Warning: Duplicate courses found for course number(s):", duplicates)

# 1. parse prerequisites into lists (vectorized)
Courses = Courses.copy()
Courses['parsed_prereqs'] = Courses['מקצועות קדם'].str.findall(r'\d{8}')

# 2. explode into long form (one row per course–prereq link)
exploded = (
    Courses[['מספר מקצוע', 'parsed_prereqs']]
      .explode('parsed_prereqs')
      .dropna(subset=['parsed_prereqs'])
      .rename(columns={'מספר מקצוע':'course', 'parsed_prereqs':'prereq'})
)

# 3. group by prereq to get list of courses that block it
blocked_index = exploded.groupby('prereq')['course'].agg(list)  # Series: prereq → [courses]

# 4. map back: for each course_number, grab its blocked list (or empty)
Courses['מקצועות חסומים'] = (
    Courses['מספר מקצוע']
           .map(blocked_index)           # lookup in our inverted index
           .apply(lambda x: x if isinstance(x, list) else [])
)

# 5. clean up
Courses = Courses.drop(columns=['parsed_prereqs'])


# your list of columns to transform
keys_to_process = [
    "מקצועות קדם",
    "מקצועות ללא זיכוי נוסף",
    "מקצועות ללא זיכוי נוסף (מוכלים)",
    "מקצועות צמודים"
]

# compile once for speed
pattern = re.compile(r'\d{8}')

# fill NaN with empty string, then extract all 8-digit codes as a list
for key in keys_to_process:
    Courses[key] = (
        Courses[key]
          .fillna("")              # avoid errors on NaN
          .astype(str)             # ensure it’s string
          .str.findall(pattern)    # → list of matches
    )

Courses["שם מקצוע"] = Courses["שם מקצוע"].str.replace(r"[':\^]", "", regex=True)

# add a new column 'tag' that concatenates the course number and course name
Courses["tag"] = Courses.apply(lambda row: f"{row['מספר מקצוע']} - {row['שם מקצוע']}", axis=1)

keys_to_process.append("מקצועות חסומים")

num_to_tag = dict(zip(Courses["מספר מקצוע"], Courses["tag"]))

for key in keys_to_process:
    Courses[key]  = Courses[key].apply(
        lambda x: sorted(set(x), key=x.index)
    )
    Courses[key] = Courses[key].apply(
        lambda codes: [num_to_tag.get(code, code) for code in codes]
    )


json.dump(Courses.to_dict(orient="records"), open("Courses3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=4)


    
    
# for course in courses_from_rishum: 
#     course_number = course["general"].get("מספר מקצוע")
#     prerequisites = course["general"].get("מקצועות קדם", "")

#     prerequisites = re.findall(r"\d{8}", prerequisites)

#     for prereq in prerequisites:
#         course_unlocks[prereq].append(course_number)





