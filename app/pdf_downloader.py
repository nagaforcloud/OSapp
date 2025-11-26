# app/pdf_downloader.py
"""
PDF Downloader module for the Onestream RAG application.
Handles downloading of PDF documentation from OneStream sites and community forums.
"""

import os
import requests
import time
import hashlib
import re
from urllib.parse import urljoin, urlparse
from typing import Set, Optional, List, Tuple
from pathlib import Path

# Try to import optional dependencies
try:
    from googlesearch import search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    search = None
    GOOGLE_SEARCH_AVAILABLE = False
    print("Warning: googlesearch-python not installed. Google search functionality will be disabled.")

try:
    from bs4 import BeautifulSoup
    BEAUTIFUL_SOUP_AVAILABLE = True
except ImportError:
    BeautifulSoup = None
    BEAUTIFUL_SOUP_AVAILABLE = False
    print("Warning: beautifulsoup4 not installed. Community forum scraping will be disabled.")

try:
    import pdfkit
    PDFKIT_AVAILABLE = True
    PDFKIT_CONFIG = None
except ImportError:
    pdfkit = None
    PDFKIT_AVAILABLE = False
    print("Warning: pdfkit not installed. HTML to PDF conversion will be disabled.")

# Try to import the enhanced community scraper
try:
    from enhanced_community_scraper import EnhancedCommunityScraper
    ENHANCED_SCRAPER_AVAILABLE = True
except ImportError:
    EnhancedCommunityScraper = None
    ENHANCED_SCRAPER_AVAILABLE = False
    print("Info: enhanced_community_scraper not available. Using basic scraping.")

class PDFDownloaderError(Exception):
    """Custom exception for PDF downloader errors."""
    pass

class PDFDownloader:
    """PDF downloader for OneStream documentation and community forums."""
    
    def __init__(self, download_folder: str = "downloaded_pdfs_from_search"):
        """
        Initialize the PDF downloader.
        
        Args:
            download_folder: Folder to save downloaded PDFs
        """
        self.download_folder = download_folder
        self.html_folder = os.path.join(download_folder, "community_html")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.max_results = 100
        
        # Create directories
        os.makedirs(self.download_folder, exist_ok=True)
        os.makedirs(self.html_folder, exist_ok=True)
        
        # Configuration for search
        self.search_query_pdf = "site:documentation.onestream.com filetype:pdf"
        self.community_base_url = "https://community.onestreamsoftware.com"
        self.community_categories = [
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
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """
        Calculate the MD5 hash of a file's content for duplicate detection.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash of the file or None if error
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def is_duplicate_content(self, new_file_path: str, existing_files_hashes: Set[str]) -> bool:
        """
        Check if the content of new_file_path matches any existing file content.
        
        Args:
            new_file_path: Path to the new file
            existing_files_hashes: Set of existing file hashes
            
        Returns:
            Whether the file is a duplicate
        """
        new_hash = self.calculate_file_hash(new_file_path)
        if new_hash is None:
            return False
        if new_hash in existing_files_hashes:
            return True
        else:
            existing_files_hashes.add(new_hash)
            return False
    
    def search_and_download_pdfs(self, query: Optional[str] = None, 
                                max_results: Optional[int] = None) -> Tuple[int, int, int, int]:
        """
        Search Google for PDFs and download them.
        
        Args:
            query: Search query (uses default if None)
            max_results: Maximum results to fetch (uses default if None)
            
        Returns:
            Tuple of (downloaded_count, failed_count, duplicate_url_count, duplicate_content_count)
        """
        if not GOOGLE_SEARCH_AVAILABLE:
            raise PDFDownloaderError("Google search functionality is not available. Please install googlesearch-python.")
        
        query = query or self.search_query_pdf
        max_results = max_results or self.max_results
        
        print(f"Searching Google for: '{query}' (Requesting up to {max_results} results)")
        
        pdf_urls = []
        try:
            search_results = search(query, num_results=max_results, sleep_interval=2.0)
            for url in search_results:
                if url.lower().endswith('.pdf'):
                    if 'Guide' in url or 'guide' in url:  # optional filter
                        pdf_urls.append(url)
        except Exception as e:
            raise PDFDownloaderError(f"Error during Google search: {e}")
        
        print(f"Found {len(pdf_urls)} PDF URLs via Google search.")
        
        downloaded_urls: Set[str] = set()
        downloaded_content_hashes: Set[str] = set()
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
                response = requests.get(pdf_url, headers=self.headers, stream=True, timeout=60)
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
                file_path = os.path.join(self.download_folder, filename)
                temp_path = file_path + ".tmp"
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                
                if self.is_duplicate_content(temp_path, downloaded_content_hashes):
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
        
        return downloaded_count, failed_count, duplicate_url_count, duplicate_content_count
    
    def scrape_community_threads_and_save_pdfs(self, comprehensive: bool = True, 
                                             specific_url: Optional[str] = None) -> int:
        """
        Scrape OneStream community forum threads and save as PDFs.
        
        Args:
            comprehensive: Whether to use enhanced scraping (True) or basic scraping (False)
            specific_url: Specific URL to scrape (optional)
            
        Returns:
            Number of successfully scraped and converted threads
        """
        if comprehensive and ENHANCED_SCRAPER_AVAILABLE:
            print("Using enhanced community scraper for comprehensive coverage")
            try:
                scraper = EnhancedCommunityScraper(
                    base_url=self.community_base_url,
                    download_folder=self.download_folder
                )
                
                # If a specific URL is provided, scrape just that thread
                if specific_url:
                    print(f"Scraping specific URL: {specific_url}")
                    success = scraper.scrape_specific_thread(specific_url)
                    return 1 if success else 0
                
                # For comprehensive scraping, process more categories and threads
                return scraper.scrape_community_threads_comprehensive(
                    max_categories=20,  # Process up to 20 categories
                    max_threads_per_category=20  # Process up to 20 threads per category
                )
            except Exception as e:
                print(f"Enhanced scraper failed, falling back to basic scraper: {e}")
        
        # Fallback to basic scraping
        if not BEAUTIFUL_SOUP_AVAILABLE:
            raise PDFDownloaderError("Community scraping functionality is not available. Please install beautifulsoup4.")
        
        print("Using basic community scraper")
        
        visited_urls: Set[str] = set()
        content_hashes: Set[str] = set()
        scraped_count = 0
        
        session = requests.Session()
        session.headers.update(self.headers)
        
        # Add more categories for better coverage
        extended_categories = self.community_categories + [
            "/category/workflow",
            "/category/security",
            "/category/api",
            "/category/integration",
            "/category/performance",
            "/category/troubleshooting"
        ]
        
        for category in extended_categories:
            category_url = self.community_base_url + category
            print(f"Processing Category: {category}")
            
            try:
                response = session.get(category_url, timeout=15)  # Increased timeout
                if response.status_code == 403:
                    print(f"  Access denied to {category_url}. Login required.")
                    continue
                response.raise_for_status()
            except Exception as e:
                print(f"  Failed to load category {category_url}: {e}")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            thread_links = []
            
            # Enhanced selectors to find more thread links
            selectors = [
                'a[href*="/t/"]',
                '.topic-list a',
                '.discussion a',
                '.post-title a',
                'h3 a',
                '.title a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href', '')
                    if re.match(r'/t/[^/]+/\d+', href):  # Matches /t/topic-title/12345
                        full_url = urljoin(self.community_base_url, href)
                        if full_url not in visited_urls:
                            thread_links.append(full_url)
                            visited_urls.add(full_url)
            
            print(f"  Found {len(thread_links)} unique threads.")
            
            # Process more threads per category
            for thread_url in thread_links[:30]:  # Limit to 30 threads per category
                try:
                    print(f"  Scraping thread: {thread_url}")
                    resp = session.get(thread_url, timeout=20)  # Increased timeout
                    if resp.status_code != 200:
                        print(f"    Failed to load thread (status {resp.status_code})")
                        continue
                    
                    thread_soup = BeautifulSoup(resp.content, 'html.parser')
                    
                    # Enhanced title extraction
                    title_elem = (
                        thread_soup.find('h1') or 
                        thread_soup.find('title') or 
                        thread_soup.find(class_=re.compile(r'title|heading'))
                    )
                    title = (title_elem.get_text(strip=True) if title_elem else "No Title").replace('/', '_')
                    
                    # Enhanced post extraction with multiple selectors
                    post_selectors = [
                        'div.post',
                        '.post-body',
                        '.comment',
                        '.discussion-post',
                        '.message'
                    ]
                    
                    posts = []
                    for selector in post_selectors:
                        posts.extend(thread_soup.select(selector))
                    
                    if not posts:
                        print("    No posts found with standard selectors, trying generic approach")
                        # Try to find any content divs
                        content_divs = thread_soup.find_all('div', class_=re.compile(r'content|text|body'))
                        posts.extend(content_divs)
                    
                    if not posts:
                        print("    No posts found. Likely requires login or different structure.")
                        continue
                    
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>{title}</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                            .post {{ margin-bottom: 30px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }}
                            .post-header {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; }}
                            .username {{ font-weight: bold; color: #005ea2; }}
                            .timestamp {{ font-size: 0.85em; color: #666; margin-left: 15px; }}
                            .content {{ margin-top: 15px; padding: 0 10px; }}
                            h1 {{ color: #003366; }}
                            .source {{ font-size: 0.9em; color: #666; margin-bottom: 20px; }}
                        </style>
                    </head>
                    <body>
                        <h1>{title}</h1>
                        <div class="source"><em>Source: <a href='{thread_url}'>{thread_url}</a></em></div>
                    """
                    
                    # Enhanced post processing
                    for i, post in enumerate(posts):
                        # Try multiple selectors for username
                        username_elem = (
                            post.find(class_=re.compile(r'username|author|user')) or
                            post.find('span', class_=re.compile(r'name')) or
                            post.find('strong') or
                            post.find('b')
                        )
                        username = username_elem.get_text(strip=True) if username_elem else f"User {i+1}"
                        
                        # Try multiple selectors for timestamp
                        timestamp_elem = (
                            post.find('time') or
                            post.find(class_=re.compile(r'time|date|timestamp')) or
                            post.find(attrs={'datetime': True})
                        )
                        timestamp = timestamp_elem.get('datetime', '') if timestamp_elem else ""
                        
                        # Try multiple selectors for content
                        content_elem = (
                            post.find(class_=re.compile(r'content|body|text|message')) or
                            post.find('p') or
                            post
                        )
                        content = content_elem.prettify() if hasattr(content_elem, 'prettify') else str(content_elem)
                        
                        html_content += f"""
                        <div class="post">
                            <div class="post-header">
                                <span class="username">{username}</span>
                                <span class="timestamp">{timestamp}</span>
                            </div>
                            <div class="content">{content}</div>
                        </div>
                        """
                    
                    html_content += "</body></html>"
                    
                    # Save HTML first
                    safe_title = re.sub(r'[^\w\-_]', '_', title)[:100]
                    if not safe_title:
                        safe_title = f"thread_{scraped_count + 1}"
                    html_file = os.path.join(self.html_folder, f"{safe_title}.html")
                    pdf_file = os.path.join(self.download_folder, f"{safe_title}.pdf")
                    
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # Check for content duplicate before PDF creation
                    if self.is_duplicate_content(html_file, content_hashes):
                        os.remove(html_file)
                        print(f"    Skipping (Content duplicate): {pdf_file}")
                        continue
                    
                    # Convert HTML to PDF
                    try:
                        if PDFKIT_AVAILABLE:
                            pdfkit.from_file(html_file, pdf_file, configuration=PDFKIT_CONFIG)
                            print(f"    ✅ Saved as PDF: {pdf_file}")
                        else:
                            print(f"    ✅ Saved as HTML: {html_file} (pdfkit not available)")
                        scraped_count += 1
                    except Exception as e:
                        print(f"    ❌ PDF conversion failed: {e}")
                        # Keep HTML file even if PDF conversion fails
                        print(f"    ✅ Saved as HTML: {html_file}")
                        scraped_count += 1
                        
                    # Rate limiting to avoid server blocking
                    time.sleep(1.5)
                        
                except Exception as e:
                    print(f"    Error processing {thread_url}: {e}")
                    continue
        
        return scraped_count
    
    def get_downloaded_files(self) -> List[str]:
        """
        Get list of downloaded PDF files.
        
        Returns:
            List of PDF file paths
        """
        pdf_files = []
        for file_path in Path(self.download_folder).iterdir():
            if file_path.suffix.lower() == '.pdf':
                pdf_files.append(str(file_path))
        return pdf_files
    
    def get_download_stats(self) -> dict:
        """
        Get statistics about downloaded files.
        
        Returns:
            Dictionary with download statistics
        """
        pdf_files = self.get_downloaded_files()
        total_size = sum(os.path.getsize(f) for f in pdf_files if os.path.exists(f))
        
        return {
            "total_files": len(pdf_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "download_folder": self.download_folder
        }
