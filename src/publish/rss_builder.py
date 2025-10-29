"""
RSS 2.0 feed builder for podcast.
"""
from datetime import datetime
from pathlib import Path
from typing import List
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from xml.dom import minidom

from .episode_meta import EpisodeMeta
from ..shared.logger import get_logger
from ..shared.settings import get_settings

logger = get_logger(__name__)


class PodcastRSSBuilder:
    """Build RSS 2.0 feed for podcast."""

    def __init__(
        self,
        title: str = "Synthetic Newsroom",
        link: str = "https://example.com",
        description: str = "AI daily debate podcast",
        language: str = "ja",
        author: str = "Synthetic Newsroom AI",
        image_url: str = None
    ):
        """
        Initialize RSS builder.

        Args:
            title: Podcast title
            link: Podcast website URL
            description: Podcast description
            language: Language code
            author: Author/creator name
            image_url: Podcast cover image URL
        """
        self.title = title
        self.link = link
        self.description = description
        self.language = language
        self.author = author
        self.image_url = image_url

    def build_feed(self, episodes: List[EpisodeMeta]) -> str:
        """
        Build RSS feed XML.

        Args:
            episodes: List of EpisodeMeta (should be sorted newest first)

        Returns:
            RSS XML string
        """
        # Create root RSS element
        rss = Element('rss', {
            'version': '2.0',
            'xmlns:itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
            'xmlns:atom': 'http://www.w3.org/2005/Atom'
        })

        # Create channel
        channel = SubElement(rss, 'channel')

        # Add channel metadata
        SubElement(channel, 'title').text = self.title
        SubElement(channel, 'link').text = self.link
        SubElement(channel, 'description').text = self.description
        SubElement(channel, 'language').text = self.language

        # iTunes-specific tags
        SubElement(channel, 'itunes:author').text = self.author
        SubElement(channel, 'itunes:summary').text = self.description
        SubElement(channel, 'itunes:explicit').text = 'no'

        # Podcast image
        if self.image_url:
            image = SubElement(channel, 'itunes:image', {'href': self.image_url})
            image_elem = SubElement(channel, 'image')
            SubElement(image_elem, 'url').text = self.image_url
            SubElement(image_elem, 'title').text = self.title
            SubElement(image_elem, 'link').text = self.link

        # Last build date
        SubElement(channel, 'lastBuildDate').text = self._format_rfc822(datetime.now())

        # Add episodes
        for episode in episodes:
            self._add_episode(channel, episode)

        # Convert to pretty XML string
        xml_str = self._prettify_xml(rss)
        return xml_str

    def _add_episode(self, channel: Element, episode: EpisodeMeta) -> None:
        """Add episode item to channel."""
        item = SubElement(channel, 'item')

        # Basic metadata
        SubElement(item, 'title').text = episode.title
        SubElement(item, 'description').text = episode.description
        SubElement(item, 'pubDate').text = self._format_rfc822(episode.pub_date)
        SubElement(item, 'guid', {'isPermaLink': 'false'}).text = episode.episode_id

        # Enclosure (audio file)
        SubElement(item, 'enclosure', {
            'url': episode.audio_url,
            'length': str(episode.audio_file_size),
            'type': 'audio/mpeg'
        })

        # iTunes-specific
        SubElement(item, 'itunes:duration').text = self._format_duration(episode.duration_seconds)
        SubElement(item, 'itunes:summary').text = episode.description
        SubElement(item, 'itunes:explicit').text = 'no'

        # Add source article links in description
        if episode.source_articles:
            sources_text = "\n\n参照記事:\n" + "\n".join(episode.source_articles)
            item.find('description').text += sources_text

    def _format_rfc822(self, dt: datetime) -> str:
        """Format datetime as RFC 822."""
        return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')

    def _format_duration(self, seconds: int) -> str:
        """Format duration as HH:MM:SS."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _prettify_xml(self, elem: Element) -> str:
        """Return pretty-printed XML string."""
        rough_string = tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

    def save_feed(self, episodes: List[EpisodeMeta], output_path: Path) -> Path:
        """
        Build and save RSS feed to file.

        Args:
            episodes: List of episodes
            output_path: Output file path

        Returns:
            Path to saved RSS file
        """
        logger.info(f"Building RSS feed with {len(episodes)} episodes")

        xml_content = self.build_feed(episodes)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        logger.info(f"RSS feed saved: {output_path}")
        return output_path


def build_podcast_rss(episodes: List[EpisodeMeta], output_path: Path) -> Path:
    """
    Convenience function to build RSS from settings and episodes.

    Args:
        episodes: List of EpisodeMeta
        output_path: Output RSS file path

    Returns:
        Path to saved RSS file
    """
    settings = get_settings()

    builder = PodcastRSSBuilder(
        title=settings.rss.site_title,
        link=settings.rss.site_link,
        description=settings.rss.site_description,
        language=settings.rss.language,
        author=settings.rss.author,
        image_url=settings.rss.image_url
    )

    return builder.save_feed(episodes, output_path)
