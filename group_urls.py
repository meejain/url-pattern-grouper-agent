
import json
import pandas as pd
from collections import defaultdict
from urllib.parse import urlparse

def extract_group_key(path):
    # Grouping by first 2 segments of the URL path
    parts = path.strip("/").split("/")
    return "/".join(parts[:2])

def group_urls_from_json(json_path: str, output_path: str = "grouped_urls.xlsx"):
    with open(json_path, "r") as f:
        data = json.load(f)

    urls = data.get("urls", [])
    grouped = defaultdict(list)

    for entry in urls:
        path = urlparse(entry['url']).path
        key = extract_group_key(path)
        grouped[key].append(entry)

    final_output = []
    group_num = 1
    for key, entries in grouped.items():
        if len(entries) > 5:  # Only include groups with more than 5 URLs
            for entry in entries:
                final_output.append({
                    "URL": entry["url"],
                    "Source": entry.get("source", ""),
                    "Group": f"Group {group_num}"
                })
            group_num += 1

    df = pd.DataFrame(final_output)
    df.to_excel(output_path, index=False)
    return output_path
