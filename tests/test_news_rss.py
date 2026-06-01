import pathlib
from backend.providers import news_rss as news

XML = (pathlib.Path(__file__).parent / "fixtures" / "sample_rss.xml").read_text()


def test_parse_items_newest_first():
    items = news.items_from_feed_text(XML, source="Test")
    assert items[0]["title"] == "Headline Two"  # newer pubDate first
    assert items[0]["source"] == "Test" and items[0]["link"] == "http://x/2"


def test_cap():
    items = news.merge_and_cap(
        [{"title": "a", "ts": 1}, {"title": "b", "ts": 2}, {"title": "c", "ts": 3}],
        max_items=2,
    )
    assert len(items) == 2 and items[0]["title"] == "c"
