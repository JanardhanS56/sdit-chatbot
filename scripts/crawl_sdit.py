#!/usr/bin/env python3
"""
SDIT Tech-Bot — Safe Local-Only Web Crawler

Crawls public pages on https://sdit.ac.in/, cleans content,
and saves formatted records for RAG ingestion via scripts/ingest.py.

Usage:
    python scripts/crawl_sdit.py
    python scripts/crawl_sdit.py --max-pages 20 --delay 2.0
    python scripts/crawl_sdit.py --url https://sdit.ac.in/
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.robotparser
from typing import Dict, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup

DEFAULT_START_URL = "https://sdit.ac.in/"
DEFAULT_USER_AGENT = "SDIT-TechBot-LocalCrawler/1.0"
ALLOWED_DOMAINS = {"sdit.ac.in", "www.sdit.ac.in"}

WHITELIST_PATHS = [
    "/",
    "/about/",
    "/vision-mission/",
    "/eligibility/",
    "/application-form/",
    "/campus/",
    "/contact-us/",
    "/computer-science-engineering/",
    "/information-science-and-engineering/",
    "/cseartificial-intelligence-machine-learning/",
    "/artificial-intelligence-data-science/",
    "/electronics-and-communication-engineering/",
    "/mechanical-engineering/",
    "/civil-engineering/",
    "/aeronautical-engineering/",
    "/m-tech-construction-technology/",
    "/master-of-business-administration/",
    "/master-of-computer-application/",
    "/about-the-placement/",
    "/placement-training/",
    "/category/company/",
]

UNWANTED_PATH_SUBSTRINGS = [
    "wp-login",
    "wp-admin",
    "login",
    "signin",
    "admin",
    "dashboard",
    "search",
]

UNWANTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".mp3", ".webm", ".avi", ".mov",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
}

MOJIBAKE_MAP = {
    "â€™": "'",
    "â€œ": '"',
    "â€": '"',
    "â€˜": "'",
    "â€“": "–",
    "â€\"": "—",
    "â€¦": "...",
    "Â": "",
    "\u00a0": " ",
}


def normalize_url(url: str) -> str:
    """Normalize URL by stripping query string, fragments, lowercasing, and trailing slashes consistency."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lower()
    if not path:
        path = "/"
    elif path != "/":
        path = path.rstrip("/") + "/"
    clean = urllib.parse.urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))
    return clean


def is_allowed_domain(url: str) -> bool:
    """Check if target URL belongs to allowed SDIT domain."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return host in ALLOWED_DOMAINS


def is_unwanted_file(url: str) -> bool:
    """Check if URL points to binary, asset, query string, or admin page."""
    parsed = urllib.parse.urlparse(url)
    if parsed.query:
        return True
    path = parsed.path.lower()
    for ext in UNWANTED_EXTENSIONS:
        if path.endswith(ext):
            return True
    for sub in UNWANTED_PATH_SUBSTRINGS:
        if sub in path:
            return True
    return False


def is_whitelisted_path(path: str) -> bool:
    """Check if path matches or starts with one of the whitelist paths."""
    normalized_path = path.lower()
    if not normalized_path.endswith("/"):
        normalized_path += "/"
    for wp in WHITELIST_PATHS:
        wp_norm = wp.lower()
        if wp_norm == "/" and normalized_path == "/":
            return True
        if wp_norm != "/" and normalized_path.startswith(wp_norm):
            return True
    return False



def repair_mojibake(text: str) -> str:
    """Repair common UTF-8 double-encoding artifacts (mojibake)."""
    for bad, good in MOJIBAKE_MAP.items():
        text = text.replace(bad, good)
    return text


def clean_text_content(soup: BeautifulSoup) -> str:
    """Extract clean text content from BeautifulSoup object, stripping non-content nodes and duplicate blocks."""
    # Clone soup to avoid mutating original
    soup = BeautifulSoup(str(soup), "html.parser")

    # Remove unwanted tags
    for selector in [
        "script", "style", "nav", "header", "footer", "noscript", "iframe", "form",
        ".main-navigation", ".site-footer", ".site-header", ".sidebar", ".widget",
        "#cookie-notice", ".cookie-notice", ".nav-menu", ".menu-container", ".mega-menu"
    ]:
        for el in soup.select(selector):
            el.decompose()

    content_selectors = [
        ".inside-pages",
        ".in-about1",
        ".campus-div1",
        ".placement-div1",
        ".contact-div1",
        "main",
        "article",
        "#content",
    ]
    main_content = next(
        (soup.select_one(selector) for selector in content_selectors if soup.select_one(selector)),
        soup.body or soup,
    )

    # Extract text with line breaks preserved
    lines = []
    seen_lines = set()

    for element in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "tr"]):
        txt = element.get_text(" ", strip=True)
        txt = repair_mojibake(txt)
        txt = html.unescape(txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        if txt and len(txt) > 2:
            formatted_line = f"\n### {txt}\n" if element.name in ["h2", "h3", "h4"] else (f"\n# {txt}\n" if element.name in ["h1", "h5", "h6"] else (f"- {txt}" if element.name == "li" else txt))
            # Deduplicate repeated identical paragraph lines (e.g. from sliders)
            if txt not in seen_lines or element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                lines.append(formatted_line)
                if len(txt) > 20:
                    seen_lines.add(txt)

    if not lines:
        raw_txt = main_content.get_text("\n", strip=True)
        lines = []
        for l in raw_txt.splitlines():
            l_clean = repair_mojibake(html.unescape(l.strip()))
            if l_clean and l_clean not in seen_lines:
                lines.append(l_clean)
                if len(l_clean) > 20:
                    seen_lines.add(l_clean)

    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result



def determine_category_and_subcategory(url_path: str, title: str, text: str) -> Tuple[str, str]:
    """Map URL path and page title to category and subcategory."""
    path = url_path.lower().strip("/")
    path_categories = {
        "vision-mission": ("college_info", "vision_mission"),
        "about": ("college_info", "about"),
        "eligibility": ("admissions", "eligibility"),
        "application-form": ("admissions", "application"),
        "campus": ("facilities", "campus_overview"),
        "contact-us": ("college_info", "contact"),
        "about-the-placement": ("placements", "overview"),
        "placement-training": ("placements", "training"),
        "category/company": ("placements", "recruiters"),
        "computer-science-engineering": ("departments", "cse"),
        "information-science-and-engineering": ("departments", "ise"),
        "cseartificial-intelligence-machine-learning": ("departments", "cse_aiml"),
        "artificial-intelligence-data-science": ("departments", "ai_ds"),
        "electronics-and-communication-engineering": ("departments", "ece"),
        "mechanical-engineering": ("departments", "mechanical"),
        "civil-engineering": ("departments", "civil"),
        "aeronautical-engineering": ("departments", "aeronautical"),
        "m-tech-construction-technology": ("courses", "mtech"),
        "master-of-business-administration": ("courses", "mba"),
        "master-of-computer-application": ("courses", "mca"),
    }
    if path in path_categories:
        return path_categories[path]

    if not path:
        return "college_info", "overview"

    combined = (url_path + " " + title + " " + text[:500]).lower()

    if any(k in combined for k in ["computer science", "cse", "artificial intelligence", "data science"]):
        return "departments", "cse"
    elif any(k in combined for k in ["electronics", "communication", "ece"]):
        return "departments", "ece"
    elif any(k in combined for k in ["mechanical", "me"]):
        return "departments", "me"
    elif any(k in combined for k in ["civil"]):
        return "departments", "civil"
    elif any(k in combined for k in ["aeronautical"]):
        return "departments", "aeronautical"
    elif any(k in combined for k in ["m-tech", "master of business", "master of computer", "mba", "mca"]):
        return "courses", "pg_programs"
    elif any(k in combined for k in ["placement", "company", "recruit"]):
        return "placements", "training"
    elif any(k in combined for k in ["eligibility", "application", "admission"]):
        return "admissions", "procedure"
    elif any(k in combined for k in ["campus", "facility", "hostel", "library", "cafeteria"]):
        return "facilities", "campus_overview"
    elif any(k in combined for k in ["about", "vision", "mission", "contact"]):
        return "college_info", "vision_mission" if "vision" in combined else "about"

    return "academics", "programs"


def generate_keywords(title: str, category: str, subcategory: str) -> List[str]:
    """Generate keywords from title, category, and subcategory."""
    words = re.findall(r"\b[A-Za-z]{3,}\b", title)
    stopwords = {"and", "the", "for", "with", "this", "that", "from", "about", "sdit", "shree", "devi"}
    clean_words = [w for w in words if w.lower() not in stopwords]

    kw = ["SDIT", category, subcategory]
    for w in clean_words:
        if w not in kw and len(kw) < 8:
            kw.append(w)
    return kw


def make_unique_title(title: str, url_path: str, used_titles: Set[str]) -> str:
    """Ensure generated title is non-empty and 100% unique across records."""
    title = title.strip()
    if not title:
        title = "SDIT Information Page"

    # Remove common site title suffixes
    title = re.sub(r"\s*[-|–]\s*(Shree Devi Institute of Technology|SDIT).*", "", title, flags=re.I).strip()
    if not title:
        title = "SDIT Information Page"

    base_title = title
    suffix_counter = 1
    path_slug = [p for p in url_path.strip("/").split("/") if p][-1] if url_path.strip("/") else "home"

    while title in used_titles:
        if suffix_counter == 1 and path_slug and path_slug.lower() not in title.lower():
            title = f"{base_title} ({path_slug.replace('-', ' ').title()})"
        else:
            title = f"{base_title} - Part {suffix_counter + 1}"
        suffix_counter += 1

    used_titles.add(title)
    return title


class SDITCrawler:

    def __init__(self, start_url: str = DEFAULT_START_URL, max_pages: int = 50, delay: float = 1.5,
                 out_raw: str = "data/raw/sdit", out_json: str = "data/processed/crawled_knowledge_base.json"):
        self.start_url = normalize_url(start_url)
        self.max_pages = max_pages
        self.delay = delay
        self.out_raw = out_raw
        self.out_json = out_json

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

        self.robot_parser = urllib.robotparser.RobotFileParser()
        self._init_robots_txt()

        self.to_visit: List[str] = [self.start_url]
        self.visited: Set[str] = set()
        self.used_titles: Set[str] = set()

        self.manifest: List[Dict] = []
        self.cleaned_records: List[Dict] = []

        self.stats = {
            "discovered": 1,
            "fetched": 0,
            "skipped": 0,
            "failed": 0,
            "records_created": 0,
        }

    def _init_robots_txt(self):
        """Fetch and parse robots.txt."""
        robots_url = "https://sdit.ac.in/robots.txt"
        try:
            resp = self.session.get(robots_url, timeout=5)
            if resp.status_code == 200:
                self.robot_parser.parse(resp.text.splitlines())
        except Exception:
            pass

    def is_allowed_by_robots(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        try:
            return self.robot_parser.can_fetch(DEFAULT_USER_AGENT, url)
        except Exception:
            return True

    def fetch_sitemap_urls(self) -> List[str]:
        """Attempt to fetch sitemap.xml for initial link discovery."""
        sitemap_urls = [
            "https://sdit.ac.in/sitemap.xml",
            "https://sdit.ac.in/sitemap_index.xml",
            "https://sdit.ac.in/page-sitemap.xml"
        ]
        found_links = []
        for sm_url in sitemap_urls:
            try:
                resp = self.session.get(sm_url, timeout=5)
                if resp.status_code == 200 and "xml" in resp.headers.get("Content-Type", ""):
                    urls = re.findall(r"<loc>(https://sdit\.ac\.in/[^<]+)</loc>", resp.text)
                    for u in urls:
                        norm = normalize_url(u)
                        if norm not in self.visited and norm not in self.to_visit:
                            found_links.append(norm)
            except Exception:
                continue
        return found_links

    def crawl(self):
        """Main crawl loop."""
        os.makedirs(self.out_raw, exist_ok=True)
        os.makedirs(os.path.dirname(self.out_json), exist_ok=True)

        print(f"=== Starting SDIT Safe Local Crawler ===")
        print(f"Start URL: {self.start_url}")
        print(f"Max Pages: {self.max_pages}")
        print(f"Delay:     {self.delay}s\n")

        # Discover sitemap links if available
        sitemap_links = self.fetch_sitemap_urls()
        if sitemap_links:
            print(f"Discovered {len(sitemap_links)} URLs from sitemap.xml")
            for sl in sitemap_links:
                if sl not in self.to_visit:
                    self.to_visit.append(sl)
            self.stats["discovered"] = len(self.to_visit)

        # Seed whitelist paths
        for wp in WHITELIST_PATHS:
            full_wp = normalize_url(urllib.parse.urljoin(self.start_url, wp))
            if full_wp not in self.to_visit:
                self.to_visit.append(full_wp)
        self.stats["discovered"] = len(self.to_visit)

        while self.to_visit and self.stats["fetched"] < self.max_pages:
            current_url = self.to_visit.pop(0)

            if current_url in self.visited:
                self.stats["skipped"] += 1
                continue

            self.visited.add(current_url)

            # Filtering checks
            if not is_allowed_domain(current_url):
                self.stats["skipped"] += 1
                continue

            parsed_path = urllib.parse.urlparse(current_url).path
            if is_unwanted_file(current_url):
                self.stats["skipped"] += 1
                continue

            if not is_whitelisted_path(parsed_path):
                self.stats["skipped"] += 1
                continue

            if not self.is_allowed_by_robots(current_url):
                print(f"Skipped (robots.txt blocked): {current_url}")
                self.stats["skipped"] += 1
                continue

            print(f"[{self.stats['fetched'] + 1}/{self.max_pages}] Fetching: {current_url}")
            time.sleep(self.delay)

            try:
                resp = self.session.get(current_url, timeout=10)
                status_code = resp.status_code

                if status_code != 200:
                    print(f"  [FAIL] HTTP {status_code}")
                    self.manifest.append({
                        "url": current_url,
                        "http_status": status_code,
                        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "title": None,
                        "extracted_char_count": 0,
                        "raw_file": None,
                        "error": f"HTTP {status_code}"
                    })
                    self.stats["failed"] += 1
                    continue

                # Character encoding detection
                resp.encoding = resp.apparent_encoding or "utf-8"
                html_text = resp.text

                # Save raw HTML
                slug = re.sub(r"[^a-zA-Z0-9_]", "_", parsed_path.strip("/").replace("/", "_")) or "index"
                raw_filename = f"page_{self.stats['fetched'] + 1:03d}_{slug[:30]}.html"
                raw_filepath = os.path.join(self.out_raw, raw_filename)

                with open(raw_filepath, "w", encoding="utf-8") as f:
                    f.write(html_text)

                soup = BeautifulSoup(html_text, "html.parser")
                page_title = soup.title.string if soup.title else ""
                clean_content = clean_text_content(soup)

                # Extract links for traversal
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    abs_url = normalize_url(urllib.parse.urljoin(current_url, href))
                    if abs_url not in self.visited and abs_url not in self.to_visit:
                        if is_allowed_domain(abs_url) and not is_unwanted_file(abs_url):
                            if is_whitelisted_path(urllib.parse.urlparse(abs_url).path):
                                self.to_visit.append(abs_url)
                                self.stats["discovered"] += 1

                self.manifest.append({
                    "url": current_url,
                    "http_status": status_code,
                    "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "title": page_title.strip() if page_title else None,
                    "extracted_char_count": len(clean_content),
                    "raw_file": raw_filepath,
                    "error": None
                })
                self.stats["fetched"] += 1

                # Generate record if content is substantial
                if len(clean_content) >= 80:
                    unique_title = make_unique_title(page_title, parsed_path, self.used_titles)
                    cat, subcat = determine_category_and_subcategory(parsed_path, unique_title, clean_content)
                    keywords = generate_keywords(unique_title, cat, subcat)

                    record = {
                        "category": cat,
                        "subcategory": subcat,
                        "title": unique_title,
                        "content": clean_content,
                        "source": "SDIT Official Website",
                        "source_url": current_url,
                        "academic_year": None,
                        "metadata": {
                            "keywords": keywords,
                            "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        }
                    }
                    self.cleaned_records.append(record)
                    self.stats["records_created"] += 1
                    print(f"  [OK] Record created: '{unique_title}' ({len(clean_content)} chars)")
                else:
                    print(f"  [WARN] Page skipped for low content length ({len(clean_content)} chars)")

            except Exception as e:
                print(f"  [FAIL] Exception: {e}")

                self.manifest.append({
                    "url": current_url,
                    "http_status": None,
                    "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "title": None,
                    "extracted_char_count": 0,
                    "raw_file": None,
                    "error": str(e)
                })
                self.stats["failed"] += 1

        self._save_outputs()
        self._print_summary()

    def _save_outputs(self):
        """Save manifest and processed JSON records."""
        manifest_path = os.path.join(self.out_raw, "crawl_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)

        with open(self.out_json, "w", encoding="utf-8") as f:
            json.dump(self.cleaned_records, f, indent=2, ensure_ascii=False)

    def _print_summary(self):
        """Print execution summary."""
        print("\n" + "=" * 45)
        print("=== SDIT Local Website Crawler Summary ===")
        print(f"Pages Discovered: {self.stats['discovered']}")
        print(f"Pages Fetched:    {self.stats['fetched']}")
        print(f"Pages Skipped:    {self.stats['skipped']}")
        print(f"Pages Failed:     {self.stats['failed']}")
        print(f"Records Created:  {self.stats['records_created']}")
        print(f"Raw Output:       {os.path.abspath(self.out_raw)}")
        print(f"Processed JSON:   {os.path.abspath(self.out_json)}")
        print("=" * 45 + "\n")


def main():
    parser = argparse.ArgumentParser(description="SDIT Safe Local Website Crawler")
    parser.add_argument("--url", default=DEFAULT_START_URL, help="Starting URL to crawl")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum number of pages to fetch")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between HTTP requests in seconds")
    parser.add_argument("--out-raw", default="data/raw/sdit", help="Directory for raw HTML files")
    parser.add_argument("--out-json", default="data/processed/crawled_knowledge_base.json", help="Path for processed JSON output")

    args = parser.parse_args()

    crawler = SDITCrawler(
        start_url=args.url,
        max_pages=args.max_pages,
        delay=args.delay,
        out_raw=args.out_raw,
        out_json=args.out_json
    )
    crawler.crawl()


if __name__ == "__main__":
    main()
