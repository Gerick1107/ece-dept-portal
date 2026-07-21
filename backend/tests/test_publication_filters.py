from app.publications.utils.link_filters import (
    article_has_blocked_repository_link,
    has_blocked_repository_link,
    is_iiitd_repository_thesis_venue,
    venue_is_preprint_or_unlisted,
)


def test_blocks_repository_iiitd_links():
    assert has_blocked_repository_link("https://repository.iiitd.edu.in/xmlui/handle/123")
    assert article_has_blocked_repository_link(
        {"link": "https://repository.iiitd.edu.in/xmlui/handle/123"}
    )
    assert article_has_blocked_repository_link(
        {"raw_metadata": '{"eprint":"https://repository.iiitd.edu.in/xmlui/handle/999"}'}
    )
    assert not has_blocked_repository_link("https://arxiv.org/abs/2601.07210")


def test_blocks_iiitd_thesis_venues_without_repo_url():
    assert is_iiitd_repository_thesis_venue("IIIT-Delhi, 2026")
    assert is_iiitd_repository_thesis_venue("IIIT Delhi, 2025")
    assert article_has_blocked_repository_link(
        {
            "title": "Towards green and inclusive speech processing",
            "link": "https://scholar.google.com/scholar?cluster=1",
            "journal": "IIIT-Delhi, 2026",
        }
    )
    assert not is_iiitd_repository_thesis_venue("IEEE Transactions on Signal Processing")
    assert not article_has_blocked_repository_link(
        {"link": "https://ieeexplore.ieee.org/document/1", "journal": "IEEE Access"}
    )


def test_preprint_or_unlisted_venue():
    assert venue_is_preprint_or_unlisted("arXiv preprint", None, None)
    assert venue_is_preprint_or_unlisted("arXiv e-prints", None, None)
    assert venue_is_preprint_or_unlisted(None, None, None)
    assert venue_is_preprint_or_unlisted("", "", "")
    assert not venue_is_preprint_or_unlisted("IEEE Transactions", None, None)
