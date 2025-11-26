# app/enhanced_community_scraper.py
"""
Enhanced community scraper for OneStream forums.
This module provides comprehensive scraping capabilities to capture all relevant posts
and discussions from the OneStream community for use in the RAG system.
"""

import os
import requests
import time
import hashlib
import re
from urllib.parse import urljoin, urlparse, parse_qs
from typing import Set, List, Tuple, Optional, Dict, Any
from bs4 import BeautifulSoup
from datetime import datetime
import json

class CommunityScraperError(Exception):
    """Custom exception for community scraper errors."""
    pass

class EnhancedCommunityScraper:
    """Enhanced scraper for OneStream community forums with comprehensive coverage."""
    
    def __init__(self, base_url: str = "https://community.onestreamsoftware.com", 
                 download_folder: str = "downloaded_pdfs_from_search"):
        """
        Initialize the enhanced community scraper.
        
        Args:
            base_url: Base URL for the community forum
            download_folder: Folder to save downloaded content
        """
        self.base_url = base_url.rstrip("/")
        self.download_folder = download_folder
        self.html_folder = os.path.join(download_folder, "community_html")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Create directories
        os.makedirs(self.download_folder, exist_ok=True)
        os.makedirs(self.html_folder, exist_ok=True)
        
        # Enhanced category list with more comprehensive coverage
        self.community_categories = [
            "/categories",  # Main categories page to discover all categories
            "/category/your-community",
            "/category/advanced",
            "/category/bulletins",
            "/category/guides",
            "/category/partner-onboarding",
            "/category/start-a-project",
            "/category/dashboards",
            "/category/extenders",
            "/category/finance",
            "/category/reports",
            "/category/webinars",
            "/category/data-management",
            "/category/metadata",
            "/category/consolidation",
            "/category/fact-or-fiction-trivia",
            "/category/methodology",
            "/category/user-interface",
            "/category/cube-view",
            "/category/excel-add-in",
            "/category/workflow",
            "/category/security",
            "/category/api",
            "/category/integration",
            "/category/performance",
            "/category/troubleshooting",
            "/category/best-practices",
            "/category/news-and-announcements",
            "/category/events",
            "/category/product-suggestions",
            "/category/documentation-feedback"
        ]
        
        # Session with retry strategy
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Tracking for deduplication
        self.visited_urls: Set[str] = set()
        self.content_hashes: Set[str] = set()
        self.scraped_count = 0
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
    
    def _rate_limit(self) -> None:
        """Implement rate limiting to avoid server blocking."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _retry_request(self, url: str, max_retries: int = 3, timeout: int = 15) -> Optional[requests.Response]:
        """
        Make a request with retry logic.
        
        Args:
            url: URL to request
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            
        Returns:
            Response object or None if failed
        """
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                response = self.session.get(url, timeout=timeout)
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limited
                    print(f"  Rate limited, waiting longer... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                elif response.status_code == 403:  # Access denied
                    print(f"  Access denied to {url}")
                    return None
                else:
                    print(f"  HTTP {response.status_code} for {url}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                print(f"  Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def discover_all_categories(self) -> List[str]:
        """
        Discover all available categories from the main categories page.
        
        Returns:
            List of category URLs
        """
        categories = set(self.community_categories)  # Start with known categories
        
        print("Discovering all categories...")
        categories_url = f"{self.base_url}/categories"
        response = self._retry_request(categories_url)
        
        if not response:
            print("  Could not access categories page, using predefined list")
            return list(categories)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all category links
        category_links = soup.find_all('a', href=re.compile(r'/category/'))
        for link in category_links:
            href = link.get('href', '')
            if href and '/category/' in href and not href.startswith('http'):
                full_url = urljoin(self.base_url, href)
                # Extract just the path part for consistency
                path = urlparse(full_url).path
                categories.add(path)
        
        print(f"  Discovered {len(categories)} categories")
        return list(categories)
    
    def get_paginated_urls(self, base_url: str, max_pages: int = 10) -> List[str]:
        """
        Get URLs for all pages in a category or thread.
        
        Args:
            base_url: Base URL to paginate
            max_pages: Maximum number of pages to check
            
        Returns:
            List of paginated URLs
        """
        urls = [base_url]
        
        # Check for pagination links
        response = self._retry_request(base_url)
        if not response:
            return urls
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for pagination controls
        pagination_links = soup.find_all('a', href=re.compile(r'(page=|p=)'))
        
        # Extract page numbers
        page_numbers = set()
        for link in pagination_links:
            href = link.get('href', '')
            # Extract page number from URL parameters
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            
            # Check common pagination parameters
            for param in ['page', 'p']:
                if param in params:
                    try:
                        page_num = int(params[param][0])
                        page_numbers.add(page_num)
                    except (ValueError, IndexError):
                        continue
        
        # Add URLs for discovered pages (up to max_pages)
        for page_num in sorted(page_numbers):
            if page_num <= max_pages:
                paginated_url = f"{base_url}?page={page_num}" if '?' not in base_url else f"{base_url}&page={page_num}"
                urls.append(paginated_url)
        
        # Also try sequential page numbers in case pagination isn't detected
        for i in range(2, min(max_pages + 1, 21)):  # Up to 20 pages
            paginated_url = f"{base_url}?page={i}" if '?' not in base_url else f"{base_url}&page={i}"
            urls.append(paginated_url)
        
        return list(set(urls))  # Remove duplicates
    
    def extract_thread_links(self, category_url: str) -> List[str]:
        """
        Extract all thread links from a category page (including paginated pages).
        
        Args:
            category_url: URL of the category page
            
        Returns:
            List of thread URLs
        """
        thread_links = []
        
        # Get all paginated URLs for this category
        category_pages = self.get_paginated_urls(category_url, max_pages=5)
        print(f"  Checking {len(category_pages)} pages in category")
        
        for page_url in category_pages:
            print(f"    Processing page: {page_url}")
            response = self._retry_request(page_url)
            
            if not response:
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Multiple selectors to catch different forum layouts
            selectors = [
                'a[href*="/t/"]',  # Standard thread links
                'a[href*="/discussions/"]',  # Discussion format like in the task
                '.topic-list a',   # Topic list format
                '.discussion a',   # Discussion format
                '.post-title a',   # Post title format
                'h3 a',            # Title links in h3 tags
                '.title a'         # Title links in title class
            ]
            
            page_thread_links = []
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href', '')
                    # Handle both /t/ and /discussions/ URL formats
                    if re.match(r'/t/[^/]+/\d+', href) or re.match(r'/discussions/[^/]+/\d+', href):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in self.visited_urls:
                            page_thread_links.append(full_url)
                            self.visited_urls.add(full_url)
            
            print(f"      Found {len(page_thread_links)} threads on this page")
            thread_links.extend(page_thread_links)
            
            # Small delay between page requests
            time.sleep(0.5)
        
        return list(set(thread_links))  # Remove duplicates
    
    def extract_post_content(self, soup: BeautifulSoup, thread_url: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extract all post content from a thread page.
        
        Args:
            soup: BeautifulSoup object of the thread page
            thread_url: URL of the thread
            
        Returns:
            Tuple of (title, list of post dictionaries)
        """
        # Extract title with multiple fallbacks
        title_elem = (
            soup.find('h1') or 
            soup.find('title') or 
            soup.find(class_=re.compile(r'title|heading')) or
            soup.find('h2')
        )
        title = (title_elem.get_text(strip=True) if title_elem else "No Title").replace('/', '_')
        
        # Extract posts with comprehensive selectors
        posts = []
        
        # Multiple selectors for different post formats
        post_selectors = [
            'div.post',           # Standard post div
            '.post-body',         # Post body class
            '.comment',           # Comment format
            '.discussion-post',   # Discussion post format
            '.message',           # Message format
            '.reply',             # Reply format
            '[data-post]',        # Data attribute
            '.content'            # Generic content class
        ]
        
        # Try to find posts with each selector
        all_post_elements = []
        for selector in post_selectors:
            post_elements = soup.select(selector)
            all_post_elements.extend(post_elements)
        
        # If no posts found with specific selectors, try broader approach
        if not all_post_elements:
            # Look for elements that might contain posts
            potential_containers = soup.find_all(['div', 'article'], class_=re.compile(r'post|comment|message|reply|discussion', re.I))
            all_post_elements.extend(potential_containers)
        
        # Extract content from each post element
        for i, post_elem in enumerate(all_post_elements):
            try:
                # Extract username with multiple fallbacks
                username_elem = (
                    post_elem.find(class_=re.compile(r'username|author|user')) or
                    post_elem.find('span', class_=re.compile(r'name')) or
                    post_elem.find('strong') or
                    post_elem.find('b')
                )
                username = username_elem.get_text(strip=True) if username_elem else f"User {i+1}"
                
                # Extract timestamp
                timestamp_elem = (
                    post_elem.find('time') or
                    post_elem.find(class_=re.compile(r'time|date|timestamp')) or
                    post_elem.find(attrs={'datetime': True})
                )
                timestamp = timestamp_elem.get('datetime', '') if timestamp_elem else ''
                
                # Extract content with multiple fallbacks
                content_elem = (
                    post_elem.find(class_=re.compile(r'content|body|text|message')) or
                    post_elem.find('p') or
                    post_elem
                )
                
                # Get text content
                if content_elem:
                    # For complex content, get both text and HTML
                    content_text = content_elem.get_text(strip=True, separator='\n')
                    content_html = str(content_elem) if hasattr(content_elem, 'prettify') else str(content_elem)
                else:
                    content_text = "[No content]"
                    content_html = "<p>[No content]</p>"
                
                # Skip empty posts
                if not content_text or len(content_text.strip()) < 10:
                    continue
                
                post_data = {
                    'username': username,
                    'timestamp': timestamp,
                    'content_text': content_text,
                    'content_html': content_html,
                    'position': i + 1
                }
                
                posts.append(post_data)
                
            except Exception as e:
                print(f"    Warning: Could not extract post {i+1}: {e}")
                continue
        
        # If we still have no posts, try extracting all text content
        if not posts:
            print("    No structured posts found, extracting all content")
            all_text = soup.get_text(separator='\n', strip=True)
            if all_text and len(all_text) > 50:
                posts.append({
                    'username': 'System',
                    'timestamp': '',
                    'content_text': all_text[:5000],  # Limit to first 5000 chars
                    'content_html': f'<p>{all_text[:5000]}</p>',
                    'position': 1
                })
        
        return title, posts
    
    def scrape_community_threads_comprehensive(self, max_categories: int = None, 
                                             max_threads_per_category: int = None) -> int:
        """
        Scrape OneStream community forum threads comprehensively.
        
        Args:
            max_categories: Maximum number of categories to process (None for all)
            max_threads_per_category: Maximum threads per category (None for all)
            
        Returns:
            Number of successfully scraped and converted threads
        """
        print("Scraping OneStream Community Forum Threads (Comprehensive Mode)")
        print("=" * 70)
        
        # Discover all categories
        categories = self.discover_all_categories()
        if max_categories:
            categories = categories[:max_categories]
        
        print(f"Processing {len(categories)} categories")
        
        total_scraped = 0
        
        for i, category_path in enumerate(categories):
            category_url = f"{self.base_url}{category_path}"
            print(f"\n--- Processing Category {i+1}/{len(categories)}: {category_path} ---")
            
            try:
                # Extract all thread links from this category
                thread_links = self.extract_thread_links(category_url)
                
                if max_threads_per_category and len(thread_links) > max_threads_per_category:
                    print(f"  Limiting to {max_threads_per_category} threads (found {len(thread_links)})")
                    thread_links = thread_links[:max_threads_per_category]
                
                print(f"  Found {len(thread_links)} threads to process")
                
                # Process each thread
                for j, thread_url in enumerate(thread_links):
                    try:
                        print(f"    Processing thread {j+1}/{len(thread_links)}: {thread_url}")
                        
                        # Get thread content
                        response = self._retry_request(thread_url)
                        if not response:
                            print(f"      Failed to load thread")
                            continue
                        
                        thread_soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Extract title and posts
                        title, posts = self.extract_post_content(thread_soup, thread_url)
                        
                        if not posts:
                            print(f"      No posts found in thread")
                            continue
                        
                        # Create comprehensive HTML content
                        html_content = self.create_html_content(title, posts, thread_url)
                        
                        # Save HTML and convert to PDF
                        safe_title = re.sub(r'[^\w\-_]', '_', title)[:100]
                        if not safe_title:
                            safe_title = f"thread_{j+1}"
                        
                        html_file = os.path.join(self.html_folder, f"{safe_title}.html")
                        pdf_file = os.path.join(self.download_folder, f"{safe_title}.pdf")
                        
                        # Save HTML
                        with open(html_file, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        
                        # Check for content duplicate before PDF creation
                        if self.is_duplicate_content(html_file):
                            os.remove(html_file)
                            print(f"      Skipping (Content duplicate): {pdf_file}")
                            continue
                        
                        # Try to convert to PDF (pdfkit might not be available)
                        try:
                            import pdfkit
                            pdfkit.from_string(html_content, pdf_file)
                            print(f"      ✅ Saved as PDF: {pdf_file}")
                            total_scraped += 1
                        except ImportError:
                            print(f"      ✅ Saved as HTML: {html_file} (pdfkit not available)")
                            total_scraped += 1
                        except Exception as e:
                            print(f"      Saved as HTML (PDF conversion failed): {html_file}")
                            total_scraped += 1
                        
                        # Rate limiting
                        time.sleep(1.0)
                        
                    except Exception as e:
                        print(f"      Error processing thread {thread_url}: {e}")
                        continue
                
            except Exception as e:
                print(f"  Error processing category {category_path}: {e}")
                continue
        
        print(f"\nCommunity Scraping Summary:")
        print(f"  Successfully processed {total_scraped} threads")
        return total_scraped
    
    def create_html_content(self, title: str, posts: List[Dict[str, Any]], thread_url: str) -> str:
        """
        Create comprehensive HTML content from posts.
        
        Args:
            title: Thread title
            posts: List of post dictionaries
            thread_url: URL of the thread
            
        Returns:
            HTML content string
        """
        # Create detailed HTML with styling
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    line-height: 1.6;
                    color: #333;
                }}
                .header {{ 
                    border-bottom: 2px solid #003366; 
                    padding-bottom: 20px; 
                    margin-bottom: 30px;
                }}
                h1 {{ 
                    color: #003366; 
                    margin-top: 0;
                }}
                .source {{ 
                    font-size: 0.9em; 
                    color: #666; 
                    margin-bottom: 20px;
                }}
                .post {{ 
                    margin-bottom: 30px; 
                    padding-bottom: 20px; 
                    border-bottom: 1px solid #eee;
                }}
                .post-header {{ 
                    background-color: #f5f5f5; 
                    padding: 10px 15px; 
                    border-radius: 5px;
                    margin-bottom: 15px;
                }}
                .username {{ 
                    font-weight: bold; 
                    color: #005ea2; 
                    font-size: 1.1em;
                }}
                .timestamp {{ 
                    font-size: 0.85em; 
                    color: #666; 
                    margin-left: 15px;
                }}
                .content {{ 
                    margin-top: 10px; 
                    padding: 0 15px;
                }}
                .post-number {{ 
                    float: right; 
                    color: #999; 
                    font-size: 0.9em;
                }}
                .metadata {{ 
                    font-size: 0.8em; 
                    color: #999; 
                    margin-top: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <div class="source">
                    <em>Source: <a href="{thread_url}">{thread_url}</a></em><br>
                    <em>Scraped on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em>
                </div>
            </div>
        """
        
        # Add all posts
        for post in posts:
            html_content += f"""
            <div class="post">
                <div class="post-header">
                    <span class="username">{post['username']}</span>
                    <span class="timestamp">{post['timestamp']}</span>
                    <span class="post-number">Post #{post['position']}</span>
                </div>
                <div class="content">
                    {post['content_html']}
                </div>
                <div class="metadata">
                    Content length: {len(post['content_text'])} characters
                </div>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        return html_content
    
    def is_duplicate_content(self, file_path: str) -> bool:
        """
        Check if file content is duplicate.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            Whether content is duplicate
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            file_hash = hash_md5.hexdigest()
            
            if file_hash in self.content_hashes:
                return True
            else:
                self.content_hashes.add(file_hash)
                return False
        except Exception as e:
            print(f"    Error checking duplicate for {file_path}: {e}")
            return False
    
    def get_scraping_stats(self) -> dict:
        """
        Get statistics about scraping progress.
        
        Returns:
            Dictionary with scraping statistics
        """
        html_files = []
        pdf_files = []
        
        if os.path.exists(self.html_folder):
            for file_path in os.listdir(self.html_folder):
                if file_path.endswith('.html'):
                    html_files.append(os.path.join(self.html_folder, file_path))
        
        if os.path.exists(self.download_folder):
            for file_path in os.listdir(self.download_folder):
                if file_path.endswith('.pdf'):
                    pdf_files.append(os.path.join(self.download_folder, file_path))
        
        html_size = sum(os.path.getsize(f) for f in html_files if os.path.exists(f))
        pdf_size = sum(os.path.getsize(f) for f in pdf_files if os.path.exists(f))
        
        return {
            "html_files": len(html_files),
            "pdf_files": len(pdf_files),
            "html_size_mb": round(html_size / (1024 * 1024), 2),
            "pdf_size_mb": round(pdf_size / (1024 * 1024), 2),
            "total_scraped": self.scraped_count
        }

    def scrape_specific_thread(self, thread_url: str) -> bool:
        """
        Scrape a specific thread URL and save as HTML/PDF.
        
        Args:
            thread_url: URL of the specific thread to scrape
            
        Returns:
            True if successfully scraped, False otherwise
        """
        print(f"Scraping specific thread: {thread_url}")
        
        try:
            # Get thread content
            response = self._retry_request(thread_url)
            if not response:
                print(f"  Failed to load thread")
                return False
            
            thread_soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title and posts
            title, posts = self.extract_post_content(thread_soup, thread_url)
            
            if not posts:
                print(f"  No posts found in thread")
                return False
            
            # Create comprehensive HTML content
            html_content = self.create_html_content(title, posts, thread_url)
            
            # Save HTML and convert to PDF
            safe_title = re.sub(r'[^\w\-_]', '_', title)[:100]
            if not safe_title:
                safe_title = "specific_thread"
            
            html_file = os.path.join(self.html_folder, f"{safe_title}.html")
            pdf_file = os.path.join(self.download_folder, f"{safe_title}.pdf")
            
            # Save HTML
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Check for content duplicate before PDF creation
            if self.is_duplicate_content(html_file):
                os.remove(html_file)
                print(f"  Skipping (Content duplicate): {pdf_file}")
                return False
            
            # Try to convert to PDF (pdfkit might not be available)
            try:
                import pdfkit
                pdfkit.from_string(html_content, pdf_file)
                print(f"  ✅ Saved as PDF: {pdf_file}")
                return True
            except ImportError:
                print(f"  ✅ Saved as HTML: {html_file} (pdfkit not available)")
                return True
            except Exception as e:
                print(f"  Saved as HTML (PDF conversion failed): {html_file}")
                return True
                
        except Exception as e:
            print(f"  Error processing thread {thread_url}: {e}")
            return False

# Example usage function
def scrape_onestream_community_comprehensive():
    """Example function to demonstrate comprehensive community scraping."""
    try:
        scraper = EnhancedCommunityScraper()
        scraped_count = scraper.scrape_community_threads_comprehensive(
            max_categories=10,  # Limit to first 10 categories for testing
            max_threads_per_category=5  # Limit to 5 threads per category for testing
        )
        print(f"\n✅ Successfully scraped {scraped_count} community threads")
        return scraped_count
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        return 0

if __name__ == "__main__":
    scrape_onestream_community_comprehensive()
