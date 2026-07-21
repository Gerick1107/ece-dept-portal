from app.publications.utils.link_filters import (
    article_has_blocked_repository_link,
    has_blocked_repository_link,
    venue_is_preprint_or_unlisted,
)


def test_blocks_repository_iiitd_links():
    assert has_blocked_repository_link("https://repository.iiitd.edu.in/xmlui/handle/123")
    assert article_has_blocked_repository_link(
        {"link": "https://repository.iiitd.edu.in/xmlui/handle/123"}
    )
    assert not has_blocked_repository_link("https://arxiv.org/abs/2601.07210")


def test_preprint_or_unlisted_venue():
    assert venue_is_preprint_or_unlisted("arXiv preprint", None, None)
    assert venue_is_preprint_or_unlisted("arXiv e-prints", None, None)
    assert venue_is_preprint_or_unlisted(None, None, None)
    assert venue_is_preprint_or_unlisted("", "", "")
    assert not venue_is_preprint_or_unlisted("IEEE Transactions", None, None)
