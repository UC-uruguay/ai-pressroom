"""
Article content extractor using requests + BeautifulSoup.
(newspaper3k alternative due to compatibility issues)
"""
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ..shared.logger import get_logger
from ..shared.retry import retry_on_network_error
from .rss import NewsArticle

logger = get_logger(__name__)


class ArticleExtractor:
    """Extract full article content from URLs."""

    def __init__(self, language: str = "ja", timeout: int = 10):
        """
        Initialize article extractor.

        Args:
            language: Article language (default: Japanese)
            timeout: Request timeout in seconds
        """
        self.language = language
        self.timeout = timeout

    @retry_on_network_error(max_attempts=3)
    def extract(self, article: NewsArticle) -> NewsArticle:
        """
        Extract full content from article URL.

        Args:
            article: NewsArticle with URL

        Returns:
            NewsArticle with content populated

        Note:
            Falls back to summary if extraction fails.
            This is a simple extractor using BeautifulSoup.
            For production, consider using newspaper3k alternative or custom parsers.
        """
        if not article.url:
            logger.warning(f"No URL for article: {article.title}")
            return article

        try:
            logger.debug(f"Extracting content from: {article.url}")

            # Fetch the article
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; SyntheticNewsroom/1.0)'}
            response = requests.get(article.url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # Parse HTML (using html.parser - lxml not required)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style tags
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            # Try to find main content
            # This is a simple heuristic - improve for production
            content_candidates = []

            # Look for common article containers
            for selector in ['article', 'main', '.article-content', '.post-content', 'div[itemprop="articleBody"]']:
                elements = soup.select(selector)
                if elements:
                    content_candidates.extend(elements)

            if content_candidates:
                # Get text from the first candidate
                text = content_candidates[0].get_text(strip=True, separator='\n')
            else:
                # Fallback: get all paragraph text
                paragraphs = soup.find_all('p')
                text = '\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])

            # Update article content
            if text and len(text) > 100:  # Minimum viable content length
                article.content = text
                logger.debug(f"Extracted {len(article.content)} characters")
            else:
                logger.warning(f"Insufficient content extracted, using summary fallback")
                article.content = article.summary or article.title

        except Exception as e:
            logger.warning(f"Failed to extract article content: {e}")
            # Fallback to summary or title
            article.content = article.summary or article.title

        return article

    def extract_batch(self, articles: list[NewsArticle]) -> list[NewsArticle]:
        """
        Extract content from multiple articles.

        Args:
            articles: List of NewsArticle objects

        Returns:
            List of NewsArticle objects with content
        """
        logger.info(f"Extracting content from {len(articles)} articles")

        extracted = []
        for article in articles:
            try:
                extracted.append(self.extract(article))
            except Exception as e:
                logger.error(f"Failed to extract {article.url}: {e}")
                # Add article with fallback content
                article.content = article.summary or article.title
                extracted.append(article)

        logger.info(f"Successfully extracted {len(extracted)} articles")
        return extracted
