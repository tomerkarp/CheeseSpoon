import json

# 1. Load the JSON array from file
with open("Courses3.json", "r", encoding="utf-8") as f:
    data = json.load(f)

merged = {}
for item in data:
    key = item["מספר מקצוע"]
    if key not in merged:
        # First time seeing this course—just copy it
        merged[key] = item.copy()
    else:
        existing = merged[key]
        for field, value in item.items():
            # If it's a string field, replace only if existing is empty and new is non-empty
            if isinstance(value, str):
                if (not existing.get(field)) and value:
                    existing[field] = value
            # If it's a list field, concatenate and drop duplicates, preserving order
            elif isinstance(value, list):
                combined = existing.get(field, []) + value
                # dict.fromkeys preserves order and removes duplicates
                existing[field] = list(dict.fromkeys(combined))

# 2. Convert back to a list and dump to output.json
merged_list = list(merged.values())
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(merged_list, f, ensure_ascii=False, indent=2)
