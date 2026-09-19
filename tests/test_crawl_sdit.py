import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup

# Ensure scripts directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))

from crawl_sdit import (
    SDITCrawler,
    clean_text_content,
    determine_category_and_subcategory,
    generate_keywords,
    is_allowed_domain,
    is_unwanted_file,
    is_whitelisted_path,
    make_unique_title,
    normalize_url,
    repair_mojibake,
)


class TestSDITCrawler(unittest.TestCase):

    def test_domain_restriction(self):
        """Test domain restriction rules."""
        self.assertTrue(is_allowed_domain("https://sdit.ac.in/about/"))
        self.assertTrue(is_allowed_domain("https://www.sdit.ac.in/campus/"))
        self.assertFalse(is_allowed_domain("https://google.com"))
        self.assertFalse(is_allowed_domain("https://vtu.ac.in/syllabus"))
        self.assertFalse(is_allowed_domain("https://facebook.com/sditmangaluru"))

    def test_url_normalization(self):
        """Test URL normalization and fragment stripping."""
        self.assertEqual(normalize_url("https://sdit.ac.in/about/#section1"), "https://sdit.ac.in/about/")
        self.assertEqual(normalize_url("HTTPS://SDIT.AC.IN/CAMPUS"), "https://sdit.ac.in/campus/")
        self.assertEqual(normalize_url("https://sdit.ac.in/page?ref=123"), "https://sdit.ac.in/page/")

    def test_unwanted_file_and_query_filtering(self):
        """Test filtering of images, PDFs, assets, admin paths, and query strings."""
        self.assertTrue(is_unwanted_file("https://sdit.ac.in/logo.png"))
        self.assertTrue(is_unwanted_file("https://sdit.ac.in/document.pdf"))
        self.assertTrue(is_unwanted_file("https://sdit.ac.in/style.css"))
        self.assertTrue(is_unwanted_file("https://sdit.ac.in/wp-admin/index.php"))
        self.assertTrue(is_unwanted_file("https://sdit.ac.in/wp-login.php"))
        self.assertTrue(is_unwanted_file("https://sdit.ac.in/search?s=test"))
        self.assertFalse(is_unwanted_file("https://sdit.ac.in/about/"))

    def test_whitelist_paths(self):
        """Test whitelist path matches."""
        self.assertTrue(is_whitelisted_path("/about/"))
        self.assertTrue(is_whitelisted_path("/computer-science-engineering/"))
        self.assertTrue(is_whitelisted_path("/contact-us/"))
        self.assertFalse(is_whitelisted_path("/random-unrelated-page/"))

    def test_mojibake_repair(self):
        """Test repair of UTF-8 double-encoding artifacts."""
        bad_str = "Itâ€™s SDITâ€œs best course"
        repaired = repair_mojibake(bad_str)
        self.assertEqual(repaired, "It's SDIT\"s best course")

    def test_html_content_extraction(self):
        """Test extraction of clean content without headers, footers, navs, or scripts."""
        sample_html = """
        <html>
            <head><title>Sample SDIT Page</title></head>
            <body>
                <header><h1>Header Title</h1><nav><a href="#">Home</a></nav></header>
                <div class="main-content">
                    <h1>Main Heading</h1>
                    <p>This is a test paragraph explaining SDIT features.</p>
                    <ul>
                        <li>Feature 1</li>
                        <li>Feature 2</li>
                    </ul>
                </div>
                <footer><p>Copyright 2026</p></footer>
                <script>console.log('strip me');</script>
            </body>
        </html>
        """
        soup = BeautifulSoup(sample_html, "html.parser")
        extracted = clean_text_content(soup)

        self.assertIn("Main Heading", extracted)
        self.assertIn("This is a test paragraph explaining SDIT features.", extracted)
        self.assertIn("Feature 1", extracted)
        self.assertNotIn("Header Title", extracted)
        self.assertNotIn("Copyright 2026", extracted)
        self.assertNotIn("strip me", extracted)

    def test_unique_title_generation(self):
        """Test unique title generation and duplicate collision handling."""
        used_titles = set()
        t1 = make_unique_title("About Us - SDIT", "/about/", used_titles)
        t2 = make_unique_title("About Us - SDIT", "/about-the-placement/", used_titles)
        t3 = make_unique_title("About Us - SDIT", "/about/", used_titles)

        self.assertEqual(t1, "About Us")
        self.assertNotEqual(t1, t2)
        self.assertNotEqual(t1, t3)
        self.assertNotEqual(t2, t3)
        self.assertEqual(len(used_titles), 3)

    def test_json_schema_validation(self):
        """Test schema structure of generated records against ingest.py expected keys."""
        used_titles = set()
        title = make_unique_title("Computer Science - SDIT", "/computer-science-engineering/", used_titles)
        cat, subcat = determine_category_and_subcategory("/computer-science-engineering/", title, "CSE branch info")
        kw = generate_keywords(title, cat, subcat)

        record = {
            "category": cat,
            "subcategory": subcat,
            "title": title,
            "content": "Detailed computer science description.",
            "source": "SDIT Official Website",
            "source_url": "https://sdit.ac.in/computer-science-engineering/",
            "academic_year": None,
            "metadata": {
                "keywords": kw,
                "retrieved_at": "2026-09-09T00:00:00Z"
            }
        }

        # Keys required by ingest.py
        required_keys = {"category", "subcategory", "title", "content", "source", "source_url", "academic_year", "metadata"}
        self.assertTrue(required_keys.issubset(record.keys()))
        self.assertIsInstance(record["metadata"]["keywords"], list)

    @patch("requests.Session.get")
    def test_mocked_crawl(self, mock_get):
        """Test full crawler workflow using mocked HTTP responses."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>About SDIT - Shree Devi Institute</title></head>
            <body>
                <main>
                    <h1>About Shree Devi Institute of Technology</h1>
                    <p>SDIT Kenjar Mangaluru is a premier engineering college in VTU Belagavi.</p>
                </main>
            </body>
        </html>
        """
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.apparent_encoding = "utf-8"
        mock_get.return_value = mock_response

        out_raw_test = "data/raw/test_sdit"
        out_json_test = "data/processed/test_crawled_knowledge_base.json"

        crawler = SDITCrawler(
            start_url="https://sdit.ac.in/about/",
            max_pages=1,
            delay=0.0,
            out_raw=out_raw_test,
            out_json=out_json_test
        )
        crawler.crawl()

        self.assertEqual(crawler.stats["fetched"], 1)
        self.assertEqual(crawler.stats["records_created"], 1)
        self.assertTrue(os.path.exists(out_json_test))

        with open(out_json_test, "r", encoding="utf-8") as f:
            records = json.load(f)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["category"], "college_info")
            self.assertIn("SDIT Kenjar Mangaluru", records[0]["content"])

        # Cleanup test files
        if os.path.exists(out_json_test):
            os.remove(out_json_test)
        if os.path.exists(out_raw_test):
            for file in os.listdir(out_raw_test):
                os.remove(os.path.join(out_raw_test, file))
            os.rmdir(out_raw_test)


if __name__ == "__main__":
    unittest.main()
