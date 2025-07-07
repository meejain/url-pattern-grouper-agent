import json
import pandas as pd
from collections import defaultdict
from urllib.parse import urlparse

def extract_group_key(path):
    parts = path.strip("/").split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else parts[0] if parts else "/"

def group_urls_from_json(json_path: str, output_path: str = "grouped_urls.xlsx"):
    with open(json_path, "r") as f:
        data = json.load(f)

    urls = data.get("urls", [])
    grouped = defaultdict(list)

    # Group URLs by pattern
    for entry in urls:
        path = urlparse(entry["url"]).path
        key = extract_group_key(path)
        grouped[key].append(entry)

    all_rows = []
    group_num = 1
    for key, entries in grouped.items():
        assign_group = f"Group {group_num}" if len(entries) > 5 else ""
        if assign_group:
            group_num += 1
        for entry in entries:
            all_rows.append({
                "URL": entry["url"],
                "Source": entry.get("source", ""),
                "Group": assign_group
            })

    # Sort so home page URLs come to top
    def home_first(url):
        path = urlparse(url).path
        return (0 if path in ["/", "", "/index.html"] else 1, path)

    df = pd.DataFrame(all_rows)
    df = df.sort_values(by="URL", key=lambda col: col.map(home_first))
    df.to_excel(output_path, index=False)
    return output_path