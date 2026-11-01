from app.services.third_party.meituan_parser import clean_markdown_text, parse_hotels


def test_clean_markdown_text_removes_emphasis_and_escapes():
    raw_name = r"**喆·啡酒店\(北京天安门广场前门大街地铁站店\)**"

    assert clean_markdown_text(raw_name) == "喆·啡酒店(北京天安门广场前门大街地铁站店)"


def test_parse_hotels_persists_plain_name():
    markdown = r"""
## [**喆·啡酒店\(北京天安门广场前门大街地铁站店\)**](https://example.com/hotel)
美团真实评分 4.8
￥399/晚
"""

    hotels = parse_hotels(markdown)

    assert hotels[0]["name"] == "喆·啡酒店(北京天安门广场前门大街地铁站店)"
    assert hotels[0]["price"] == 399
