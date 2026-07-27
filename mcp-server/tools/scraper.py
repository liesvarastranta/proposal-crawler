import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse

import yaml

logger = logging.getLogger(__name__)

SOURCES_PATH = Path(__file__).parent.parent.parent / "config" / "sources.yaml"


def _load_sources_config() -> dict:
    return yaml.safe_load(SOURCES_PATH.read_text())


async def scrape_page(url: str) -> dict:
    config = _load_sources_config()
    policy = config.get("default_policy", {})

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

        async with AsyncWebCrawler() as crawler:
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=policy.get("timeout_seconds", 30000),
                word_count_threshold=10,
            )
            result = await crawler.arun(url=url, config=crawl_config)

            if result.success and result.markdown:
                return {
                    "success": True,
                    "url": url,
                    "markdown": result.markdown[:10000],
                    "error": None,
                    "engine": "crawl4ai",
                }
            raise RuntimeError(result.error_message or "Crawl4AI returned empty content")
    except Exception as e:
        logger.warning("Crawl4AI failed for %s: %s", url, e)

    try:
        from firecrawl import Firecrawl

        fc = Firecrawl()
        result = fc.scrape_url(url, params={"formats": ["markdown"]})

        return {
            "success": True,
            "url": url,
            "markdown": result.get("markdown", "")[:10000],
            "error": None,
            "engine": "firecrawl",
        }
    except Exception as e:
        logger.error("Firecrawl also failed for %s: %s", url, e)
        return {
            "success": False,
            "url": url,
            "markdown": "",
            "error": str(e),
            "engine": None,
        }


def check_robotstxt(url: str) -> bool:
    from urllib.robotparser import RobotFileParser

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        return rp.can_fetch("*", url)
    except Exception:
        return True


def hash_content(title: str, url: str) -> str:
    return hashlib.sha256(f"{title}{url}".encode()).hexdigest()
