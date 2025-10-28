"""
Article classification and topic detection.
"""
from enum import Enum
from typing import List, Optional

from ..collectors.rss import NewsArticle
from ..shared.logger import get_logger

logger = get_logger(__name__)


class ArticleCategory(Enum):
    """Article categories."""
    POLITICS = "politics"
    ECONOMY = "economy"
    TECHNOLOGY = "technology"
    SCIENCE = "science"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    INTERNATIONAL = "international"
    DOMESTIC = "domestic"
    OTHER = "other"


class ArticleClassifier:
    """Simple keyword-based article classifier."""

    def __init__(self):
        """Initialize classifier with keyword mappings."""
        # TODO: Replace with ML-based classifier or LLM-based classification
        self.category_keywords = {
            ArticleCategory.POLITICS: ["政治", "選挙", "国会", "議員", "政府", "政権"],
            ArticleCategory.ECONOMY: ["経済", "株価", "為替", "GDP", "景気", "金融", "企業"],
            ArticleCategory.TECHNOLOGY: ["AI", "技術", "スマホ", "アプリ", "ソフトウェア", "IT"],
            ArticleCategory.SCIENCE: ["研究", "科学", "発見", "論文", "実験"],
            ArticleCategory.SPORTS: ["スポーツ", "野球", "サッカー", "オリンピック", "試合"],
            ArticleCategory.ENTERTAINMENT: ["芸能", "映画", "音楽", "ドラマ", "俳優"],
            ArticleCategory.INTERNATIONAL: ["海外", "米国", "中国", "欧州", "国際"],
        }

    def classify(self, article: NewsArticle) -> ArticleCategory:
        """
        Classify article into a category.

        Args:
            article: NewsArticle to classify

        Returns:
            ArticleCategory
        """
        text = f"{article.title} {article.summary or ''} {article.content or ''}"

        # Count keyword matches for each category
        scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[category] = score

        if scores:
            # Return category with highest score
            return max(scores, key=scores.get)

        return ArticleCategory.OTHER

    def group_by_category(
        self,
        articles: List[NewsArticle]
    ) -> dict[ArticleCategory, List[NewsArticle]]:
        """
        Group articles by category.

        Args:
            articles: List of NewsArticle objects

        Returns:
            Dictionary mapping categories to articles
        """
        groups = {}

        for article in articles:
            category = self.classify(article)
            if category not in groups:
                groups[category] = []
            groups[category].append(article)

        logger.info(f"Grouped {len(articles)} articles into {len(groups)} categories")
        return groups
