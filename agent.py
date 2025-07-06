
from group_urls import group_urls_from_json
from github_utils import download_json_file, upload_excel_file
import os

def main():
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    REPO = "your-username/your-repo"
    JSON_PATH = "site-urls.json"

    download_json_file(GITHUB_TOKEN, REPO, JSON_PATH)
    output_file = group_urls_from_json(JSON_PATH)
    upload_excel_file(GITHUB_TOKEN, REPO, "grouped_urls.xlsx", "Grouped URLs exported via agent")

if __name__ == "__main__":
    main()
