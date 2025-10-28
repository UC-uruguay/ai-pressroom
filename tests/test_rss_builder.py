"""
Test RSS feed building.
"""
import pytest
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from src.publish.episode_meta import EpisodeMeta
from src.publish.rss_builder import PodcastRSSBuilder


@pytest.fixture
def sample_episodes():
    """Create sample episode metadata."""
    return [
        EpisodeMeta(
            episode_id="episode_20250101",
            title="Test Episode 1",
            description="Test description 1",
            pub_date=datetime(2025, 1, 1, 12, 0, 0),
            audio_url="http://example.com/ep1.mp3",
            audio_file_size=1000000,
            duration_seconds=300,
            source_articles=["http://news.example.com/1"]
        ),
        EpisodeMeta(
            episode_id="episode_20250102",
            title="Test Episode 2",
            description="Test description 2",
            pub_date=datetime(2025, 1, 2, 12, 0, 0),
            audio_url="http://example.com/ep2.mp3",
            audio_file_size=2000000,
            duration_seconds=600,
            source_articles=["http://news.example.com/2"]
        ),
    ]


def test_rss_builder_creates_valid_xml(sample_episodes):
    """Test that RSS builder creates valid XML."""
    builder = PodcastRSSBuilder(
        title="Test Podcast",
        link="http://example.com",
        description="Test Description"
    )

    xml_content = builder.build_feed(sample_episodes)

    # Parse XML to ensure it's valid
    root = ElementTree.fromstring(xml_content)

    assert root.tag == 'rss'
    assert root.attrib['version'] == '2.0'


def test_rss_feed_has_channel(sample_episodes):
    """Test that RSS feed has channel element."""
    builder = PodcastRSSBuilder()
    xml_content = builder.build_feed(sample_episodes)

    root = ElementTree.fromstring(xml_content)
    channel = root.find('channel')

    assert channel is not None
    assert channel.find('title').text == "Synthetic Newsroom"


def test_rss_feed_has_episodes(sample_episodes):
    """Test that RSS feed includes all episodes."""
    builder = PodcastRSSBuilder()
    xml_content = builder.build_feed(sample_episodes)

    root = ElementTree.fromstring(xml_content)
    channel = root.find('channel')
    items = channel.findall('item')

    assert len(items) == 2


def test_episode_has_enclosure(sample_episodes):
    """Test that each episode has enclosure tag."""
    builder = PodcastRSSBuilder()
    xml_content = builder.build_feed(sample_episodes)

    root = ElementTree.fromstring(xml_content)
    channel = root.find('channel')
    item = channel.find('item')
    enclosure = item.find('enclosure')

    assert enclosure is not None
    assert enclosure.attrib['url'] == sample_episodes[0].audio_url
    assert enclosure.attrib['type'] == 'audio/mpeg'
    assert int(enclosure.attrib['length']) == sample_episodes[0].audio_file_size


def test_rss_save_to_file(sample_episodes, tmp_path):
    """Test saving RSS to file."""
    builder = PodcastRSSBuilder()
    output_path = tmp_path / "test_podcast.xml"

    result_path = builder.save_feed(sample_episodes, output_path)

    assert result_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
