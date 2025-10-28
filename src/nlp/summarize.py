"""
Article summarization and debate topic extraction using LLMs.
"""
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI

from ..collectors.rss import NewsArticle
from ..shared.logger import get_logger
from ..shared.retry import retry_on_api_error
from ..shared.settings import get_settings

logger = get_logger(__name__)


@dataclass
class DebateTopic:
    """Debate topic extracted from news articles."""
    title: str
    summary: str
    key_points: List[str]
    source_articles: List[str]  # Article titles


class ArticleSummarizer:
    """Summarize articles and extract debate topics."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize summarizer.

        Args:
            api_key: OpenAI API key (uses settings if not provided)
        """
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key

        if not self.api_key:
            logger.warning("No OpenAI API key provided, summarization will be limited")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)

    def summarize_article(self, article: NewsArticle, max_length: int = 200) -> str:
        """
        Create a short summary of an article.

        Args:
            article: NewsArticle to summarize
            max_length: Maximum summary length in characters

        Returns:
            Summary text
        """
        # Fallback to simple truncation if no API
        if not self.client:
            content = article.content or article.summary or article.title
            return content[:max_length] + "..." if len(content) > max_length else content

        try:
            return self._summarize_with_llm(article, max_length)
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}, using fallback")
            content = article.content or article.summary or article.title
            return content[:max_length] + "..." if len(content) > max_length else content

    @retry_on_api_error(max_attempts=3)
    def _summarize_with_llm(self, article: NewsArticle, max_length: int) -> str:
        """Summarize using LLM."""
        content = article.content or article.summary or article.title

        prompt = f"""以下のニュース記事を{max_length}文字以内で要約してください。
重要なポイントを簡潔にまとめてください。

記事タイトル: {article.title}
本文:
{content[:2000]}  # Limit input to avoid token limits
"""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはニュース記事を要約する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    def create_debate_topic(self, articles: List[NewsArticle]) -> DebateTopic:
        """
        Create a debate topic from multiple articles.

        Args:
            articles: List of related news articles

        Returns:
            DebateTopic for discussion
        """
        if not self.client:
            # Fallback: simple aggregation
            return DebateTopic(
                title=f"今日のニュース討論: {articles[0].title}",
                summary=articles[0].summary or articles[0].title,
                key_points=[a.title for a in articles[:3]],
                source_articles=[a.title for a in articles]
            )

        try:
            return self._create_topic_with_llm(articles)
        except Exception as e:
            logger.warning(f"LLM topic creation failed: {e}, using fallback")
            return DebateTopic(
                title=f"今日のニュース討論: {articles[0].title}",
                summary=articles[0].summary or articles[0].title,
                key_points=[a.title for a in articles[:3]],
                source_articles=[a.title for a in articles]
            )

    @retry_on_api_error(max_attempts=3)
    def _create_topic_with_llm(self, articles: List[NewsArticle]) -> DebateTopic:
        """Create debate topic using LLM."""
        # Prepare article summaries
        article_texts = []
        for i, article in enumerate(articles[:5], 1):
            content = article.content or article.summary or article.title
            article_texts.append(f"{i}. {article.title}\n{content[:500]}")

        articles_summary = "\n\n".join(article_texts)

        prompt = f"""以下のニュース記事から、AIエージェント同士が討論するためのトピックを作成してください。

記事:
{articles_summary}

以下の形式で出力してください:
タイトル: [討論のタイトル]
要約: [トピックの簡潔な説明]
論点:
- [論点1]
- [論点2]
- [論点3]
"""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは討論トピックを作成する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.5
        )

        # Parse response (simple parsing)
        result = response.choices[0].message.content
        lines = result.strip().split('\n')

        title = "今日のニュース討論"
        summary = ""
        key_points = []

        for line in lines:
            if line.startswith("タイトル:"):
                title = line.replace("タイトル:", "").strip()
            elif line.startswith("要約:"):
                summary = line.replace("要約:", "").strip()
            elif line.startswith("- ") or line.startswith("・"):
                key_points.append(line.lstrip("- ・").strip())

        return DebateTopic(
            title=title,
            summary=summary or articles[0].title,
            key_points=key_points or [a.title for a in articles[:3]],
            source_articles=[a.title for a in articles]
        )
