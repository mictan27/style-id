import pytest

from styleid_api.urls import canonicalise_url_local, domain_of


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://Shop.Example.com/products/tee/", "https://shop.example.com/products/tee"),
        ("https://www.shop.example.com/products/tee", "https://shop.example.com/products/tee"),
        ("https://shop.example.com:443/p/tee?utm_source=ig", "https://shop.example.com/p/tee"),
        ("https://shop.example.com/p?b=2&a=1&fbclid=x#frag", "https://shop.example.com/p?a=1&b=2"),
        ("shop.example.com/p", "https://shop.example.com/p"),
        ("https://shop.example.com", "https://shop.example.com/"),
        ("https://shop.example.com:8443/p", "https://shop.example.com:8443/p"),
    ],
)
def test_canonicalise(raw: str, expected: str) -> None:
    assert canonicalise_url_local(raw) == expected


def test_domain_of() -> None:
    assert domain_of("https://shop.example.com/p") == "shop.example.com"
