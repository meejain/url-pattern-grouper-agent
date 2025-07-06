
import json
import pandas as pd
from collections import defaultdict
from urllib.parse import urlparse

def extract_group_key(path):
    parts = path.strip("/").split("/")
    return "/".join(parts[:2])

def group_urls_from_json(json_path: str, output_path: str = "grouped_urls.xlsx"):
    with open(json_path, "r") as f:
        data = json.load(f)

    grouped = defaultdict(list)

    for entry in data:
        path = urlparse(entry['url']).path
        key = extract_group_key(path)
        grouped[key].append(entry['url'])

    final_output = []
    group_num = 1
    for key, urls in grouped.items():
        if len(urls) >= 5:
            for url in urls:
                final_output.append({"URL": url, "Group": f"Group {group_num}"})
            group_num += 1

    df = pd.DataFrame(final_output)
    df.to_excel(output_path, index=False)
    return output_path
