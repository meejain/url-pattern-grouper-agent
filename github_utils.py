
from github import Github
import os

def download_json_file(token, repo_name, file_path):
    g = Github(token)
    repo = g.get_repo(repo_name)
    file_content = repo.get_contents(file_path)
    with open("site-urls.json", "w") as f:
        f.write(file_content.decoded_content.decode())
    return "site-urls.json"

def upload_excel_file(token, repo_name, file_path, commit_message):
    g = Github(token)
    repo = g.get_repo(repo_name)
    with open(file_path, "rb") as f:
        content = f.read()
    try:
        contents = repo.get_contents(file_path)
        repo.update_file(contents.path, commit_message, content, contents.sha)
    except:
        repo.create_file(file_path, commit_message, content)
