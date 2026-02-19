# डाउनलोडर: वेबसाइट → सभी Google Drive नोट्स ऑटो डाउनलोड
# Works only if the Drive files/folders are PUBLIC (Anyone with link)

import os
import re
import requests
from bs4 import BeautifulSoup
import gdown

BASE_URL = "https://kurukshetra-warriors.onrender.com/notes/"
DOWNLOAD_DIR = "downloaded_notes"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_drive_links(url):
    """Extract all Google Drive links from a webpage"""
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    drive_links = []
    for a in soup.find_all("a", href=True):
        link = a["href"]
        if "drive.google.com" in link:
            drive_links.append(link)

    return drive_links


def download_drive_link(link):
    """Download file/folder from Google Drive link"""
    try:
        # File link
        file_match = re.search(r"/file/d/(.*?)/", link)
        if file_match:
            file_id = file_match.group(1)
            gdown.download(f"https://drive.google.com/uc?id={file_id}",
                           output=DOWNLOAD_DIR, quiet=False)
            return

        # Folder link
        folder_match = re.search(r"/folders/(.*)", link)
        if folder_match:
            folder_id = folder_match.group(1)
            gdown.download_folder(id=folder_id,
                                  output=DOWNLOAD_DIR,
                                  quiet=False,
                                  use_cookies=False)
            return

        print(f"Skipped (unsupported): {link}")

    except Exception as e:
        print(f"Failed: {link}\nError: {e}")


def main():
    print("Extracting Google Drive links...")
    links = get_drive_links(BASE_URL)

    print(f"Found {len(links)} Drive links\n")

    for i, link in enumerate(links, 1):
        print(f"[{i}/{len(links)}] Downloading...")
        download_drive_link(link)

    print("\nAll downloads completed.")


if __name__ == "__main__":
    main()
