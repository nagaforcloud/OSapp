"""
PDF download script for the Onestream RAG application.
Downloads PDF documentation from OneStream sites and scrapes community forum threads to save as PDFs.
"""

# --- Extended Script: Download PDFs + Community Threads as PDFs ---
import os
import requests
from urllib.parse import urljoin, urlparse
import time
import hashlib
import re
from datetime import datetime

# Requires: pip install googlesearch-python beautifulsoup4 pdfkit
try:
    from googlesearch import search
except ImportError:
    raise ImportError("Please install googlesearch-python: pip install googlesearch-python")

from bs4 import BeautifulSoup
try:
    import pdfkit
    PDFKIT_CONFIG = None
    # Optional: specify path on Windows
    # config = pdfkit.configuration(wkhtmltopdf='C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe')
except ImportError:
    pdfkit = None
    print("Warning: pdfkit not installed. Cannot generate PDFs from HTML.")

# --- Configuration ---
SEARCH_QUERY_PDF = "site:documentation.onestream.com filetype:pdf"
COMMUNITY_BASE_URL = "https://community.onestreamsoftware.com"
COMMUNITY_CATEGORIES = [
    "/category/your-community",
    "/category/Advanced",
    "/category/Bulletins",
    "/category/Guides",
    "/category/Partner Onboarding",
    "/category/Start a Project",
    "/category/Dashboards",
    "/category/Extenders",
    "/category/Finance",
    "/category/Reports",
    "/category/webinars",
    "/category/Data Management",
    "/category/Metadata",
    "/category/Consolidation",
    "/category/Fact or Fiction Trivia",
    "/category/Methodology",
    "/category/User Interface",
    "/category/Cube View",
    "/category/Excel Add In"
]
DOWNLOAD_FOLDER = "downloaded_pdfs_from_search"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
HTML_FOLDER = os.path.join(DOWNLOAD_FOLDER, "community_html")
os.makedirs(HTML_FOLDER, exist_ok=True)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

MAX_RESULTS = 100  # or whatever number you want

# --- Helper Functions for Duplicate Detection ---
def calculate_file_hash(file_path):
    """Calculates the MD5 hash of a file's content."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"    Error calculating hash for {file_path}: {e}")
        return None

def is_duplicate_content(new_file_path, existing_files_hashes):
    """Checks if the content of new_file_path matches any existing file content."""
    new_hash = calculate_file_hash(new_file_path)
    if new_hash is None:
        return False
    if new_hash in existing_files_hashes:
        return True
    else:
        existing_files_hashes.add(new_hash)
        return False

# --- Google Search and Download PDFs (Existing Function) ---
def search_and_download_pdfs(query, download_folder, headers, max_results):
    print(f"Searching Google for: '{query}' (Requesting up to {max_results} results)")
    pdf_urls = []
    try:
        search_results = search(query, num_results=max_results, sleep_interval=2.0)
        for url in search_results:
            if url.lower().endswith('.pdf'):
                if 'Guide' in url or 'guide' in url:  # optional filter
                    pdf_urls.append(url)
    except Exception as e:
        print(f"Error during Google search: {e}")
        return

    print(f"\nFound {len(pdf_urls)} PDF URLs via Google search.")
    downloaded_urls = set()
    downloaded_content_hashes = set()
    duplicate_url_count = 0
    duplicate_content_count = 0
    downloaded_count = 0
    failed_count = 0

    for pdf_url in pdf_urls:
        if pdf_url in downloaded_urls:
            print(f"  Skipping (URL duplicate): {pdf_url}")
            duplicate_url_count += 1
            continue
        downloaded_urls.add(pdf_url)

        try:
            print(f"  Downloading: {pdf_url}")
            response = requests.get(pdf_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()

            filename = None
            cd = response.headers.get('content-disposition')
            if cd:
                fname = re.findall('filename=(.+)', cd)
                if fname:
                    filename = fname[0].strip('"')
            if not filename:
                filename = os.path.basename(urlparse(pdf_url).path) or f"doc_{downloaded_count+1}.pdf"
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            filename = "".join(c for c in filename if c.isalnum() or c in ' ._-')[:255]
            file_path = os.path.join(download_folder, filename)
            temp_path = file_path + ".tmp"

            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)

            if is_duplicate_content(temp_path, downloaded_content_hashes):
                os.remove(temp_path)
                print(f"    Skipping (Content duplicate): {filename}")
                duplicate_content_count += 1
                continue

            os.replace(temp_path, file_path)
            print(f"    Saved: {filename}")
            downloaded_count += 1
            time.sleep(1.0)

        except Exception as e:
            print(f"    Failed: {e}")
            failed_count += 1

    print(f"\nPDF Download Summary:")
    print(f"  Downloaded: {downloaded_count}, Failed: {failed_count}, "
          f"URL Duplicates: {duplicate_url_count}, Content Duplicates: {duplicate_content_count}")

# --- NEW: Scrape Community Forum Threads and Save as PDF ---
def scrape_community_threads_and_save_pdfs():
    if not pdfkit:
        print("Skipping community thread scraping: pdfkit not available.")
        return

    print("\n" + "="*60)
    print("Scraping OneStream Community Forum Threads")
    print("="*60)

    visited_urls = set()
    content_hashes = set()
    scraped_count = 0

    session = requests.Session()
    session.headers.update(HEADERS)

    for category in COMMUNITY_CATEGORIES:
        category_url = COMMUNITY_BASE_URL + category
        print(f"\n--- Processing Category: {category} ---")

        try:
            response = session.get(category_url, timeout=10)
            if response.status_code == 403:
                print(f"  Access denied to {category_url}. Login required.")
                continue
            response.raise_for_status()
        except Exception as e:
            print(f"  Failed to load category {category_url}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        thread_links = []

        for link in soup.find_all('a', href=True):
            href = link['href']
            if re.match(r'/t/[^/]+/\d+', href):  # Matches /t/topic-title/12345
                full_url = urljoin(COMMUNITY_BASE_URL, href)
                if full_url not in visited_urls:
                    thread_links.append(full_url)
                    visited_urls.add(full_url)

        print(f"  Found {len(thread_links)} unique threads.")

        for thread_url in thread_links:
            try:
                print(f"  Scraping thread: {thread_url}")
                resp = session.get(thread_url, timeout=15)
                if resp.status_code != 200:
                    print(f"    Failed to load thread (status {resp.status_code})")
                    continue

                thread_soup = BeautifulSoup(resp.content, 'html.parser')

                # Extract title
                title_elem = thread_soup.find('h1') or thread_soup.find('title')
                title = (title_elem.get_text(strip=True) if title_elem else "No Title").replace('/', '_')

                # Extract posts
                posts = thread_soup.find_all('div', class_='post')
                if not posts:
                    print("    No posts found. Likely requires login.")
                    continue

                html_content = f"""
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>{title}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; }}
                        .post {{ margin-bottom: 30px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }}
                        .username {{ font-weight: bold; color: #005ea2; }}
                        .timestamp {{ font-size: 0.8em; color: #666; }}
                        .content {{ margin-top: 10px; line-height: 1.5; }}
                        h1 {{ color: #003366; }}
                    </style>
                </head>
                <body>
                    <h1>{title}</h1>
                    <p><em>Source: <a href='{thread_url}'>{thread_url}</a></em></p>
                """

                for post in posts:
                    username_elem = post.find('span', class_='username')
                    username = username_elem.get_text(strip=True) if username_elem else "Unknown User"

                    timestamp_elem = post.find('time')
                    timestamp = timestamp_elem['datetime'] if timestamp_elem else ""

                    content_elem = post.find('div', class_='post-content')
                    content = content_elem.prettify() if content_elem else "<p>[No content]</p>"

                    html_content += f"""
                    <div class="post">
                        <div class="username">{username}</div>
                        <div class="timestamp">{timestamp}</div>
                        <div class="content">{content}</div>
                    </div>
                    """

                html_content += "</body></html>"

                # Save HTML first
                safe_title = re.sub(r'[^\w\-_]', '_', title)[:100]
                html_file = os.path.join(HTML_FOLDER, f"{safe_title}.html")
                pdf_file = os.path.join(DOWNLOAD_FOLDER, f"{safe_title}.pdf")

                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                # Check for content duplicate before PDF creation
                if is_duplicate_content(html_file, content_hashes):
                    os.remove(html_file)
                    print(f"    Skipping (Content duplicate): {pdf_file}")
                    continue

                # Convert HTML to PDF
                try:
                    pdfkit.from_file(html_file, pdf_file, configuration=PDFKIT_CONFIG)
                    print(f"    ✅ Saved as PDF: {pdf_file}")
                    scraped_count += 1
                except Exception as e:
                    print(f"    ❌ PDF conversion failed: {e}")

            except Exception as e:
                print(f"    Error processing {thread_url}: {e}")

    print(f"\nCommunity Scraping Summary:")
    print(f"  Successfully converted {scraped_count} threads to PDF.")

# --- Main Execution ---
if __name__ == "__main__":
    # Step 1: Download official PDFs
    #search_and_download_pdfs(SEARCH_QUERY_PDF, DOWNLOAD_FOLDER, HEADERS, MAX_RESULTS)

    # Step 2: Scrape community threads and save as PDFs
    scrape_community_threads_and_save_pdfs()

    print(f"\n✅ All files saved in: {os.path.abspath(DOWNLOAD_FOLDER)}")
