"""
RSS feed collector for news articles.
(Using xml.etree instead of feedparser due to dependency issues)
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from ..shared.logger import get_logger
from ..shared.retry import retry_on_network_error

logger = get_logger(__name__)


@dataclass
class NewsArticle:
    """News article data structure."""
    title: str
    url: str
    published: Optional[datetime]
    summary: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None


class RSSCollector:
    """RSS feed collector."""

    def __init__(self, user_agent: str = "SyntheticNewsroom/1.0"):
        """
        Initialize RSS collector.

        Args:
            user_agent: User agent string for requests
        """
        self.user_agent = user_agent

    @retry_on_network_error(max_attempts=3)
    def fetch_feed(self, feed_url: str, max_articles: int = 5) -> List[NewsArticle]:
        """
        Fetch articles from RSS feed using xml.etree.

        Args:
            feed_url: RSS feed URL
            max_articles: Maximum number of articles to fetch

        Returns:
            List of NewsArticle objects

        Raises:
            ValueError: If feed is invalid or empty
        """
        logger.info(f"Fetching RSS feed: {feed_url}")

        # Fetch RSS feed
        headers = {'User-Agent': self.user_agent}
        response = requests.get(feed_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse XML
        root = ET.fromstring(response.content)

        # Find channel (RSS 2.0) or feed (Atom)
        channel = root.find('channel')
        if channel is None:
            # Try Atom format
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            items = root.findall('atom:entry', namespace)[:max_articles]
            source_title = root.findtext('atom:title', default=None, namespaces=namespace)
        else:
            # RSS 2.0 format
            items = channel.findall('item')[:max_articles]
            source_title = channel.findtext('title')

        if not items:
            raise ValueError(f"No entries found in feed: {feed_url}")

        articles = []
        for item in items[:max_articles]:
            try:
                # RSS 2.0 format
                title = item.findtext('title', default="Untitled")
                link = item.findtext('link', default="")
                pub_date_str = item.findtext('pubDate')
                summary_text = item.findtext('description')

                # Parse publication date
                published = None
                if pub_date_str:
                    try:
                        published = parsedate_to_datetime(pub_date_str)
                    except:
                        pass

                # Clean summary
                summary = self._clean_html(summary_text) if summary_text else None

                # Create article object
                article = NewsArticle(
                    title=title,
                    url=link,
                    published=published,
                    summary=summary,
                    source=source_title
                )

                articles.append(article)
                logger.debug(f"Collected article: {article.title}")

            except Exception as e:
                logger.warning(f"Failed to parse entry: {e}")
                continue

        logger.info(f"Collected {len(articles)} articles from RSS feed")
        return articles

    def _clean_html(self, html_text: str) -> str:
        """
        Clean HTML tags from text.

        Args:
            html_text: HTML text

        Returns:
            Cleaned text
        """
        soup = BeautifulSoup(html_text, "html.parser")
        return soup.get_text(strip=True)
