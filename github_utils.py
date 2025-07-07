from github import Github
from github.ContentFile import ContentFile
import os

def download_json_file(token, repo_name, file_path):
    g = Github(token)
    repo = g.get_repo(repo_name)
    contents = repo.get_contents(file_path)
    file_content = contents if isinstance(contents, ContentFile) else contents[0]
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
        file_content = contents if isinstance(contents, ContentFile) else contents[0]
        repo.update_file(file_content.path, commit_message, content, file_content.sha)
    except:
        repo.create_file(file_path, commit_message, content)
