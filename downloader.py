"""
File Downloader - Downloads student assignment files
"""
import os
import requests


def download_file(file_url, save_dir="assignments/"):
    """
    Download a file from URL and save to directory
    Returns: filepath of saved file
    """
    os.makedirs(save_dir, exist_ok=True)
    filename = file_url.split("/")[-1].split("?")[0]
    filepath = os.path.join(save_dir, filename)

    print(f"📥 Downloading {filename}...")
    r = requests.get(file_url)
    with open(filepath, "wb") as f:
        f.write(r.content)

    print(f"✅ Saved to {filepath}")
    return filepath


def download_submission_files(submission_details):
    """
    Download all files for a submission
    Returns: list of downloaded file paths
    """
    exercise = submission_details["exercise"]
    file_links = exercise.get("file_details", [])
    
    if not file_links:
        print("⚠️  No files found for this submission")
        return []
    
    downloaded = []
    for file_info in file_links:
        filepath = download_file(file_info["file_path"])
        downloaded.append(filepath)
    
    return downloaded

