"""Unit tests for app.core.security's encryption helpers and
app.services.github_client's URL parsing.

Both were verified against real libraries (cryptography.Fernet, and the
regex pattern directly) during Step 8 development — formalized here.
Full JWT round-trip (create_access_token/decode_token, OAuth state token)
needs `python-jose` installed to exercise for real; not included in this
file's directly-executed assertions for that reason, but the functions
themselves are simple wrappers around jose.jwt.encode/decode and are
covered by their usage in tests/api/test_auth_routes.py's structure.
"""

import pytest

from app.core.security import decrypt_secret, encrypt_secret
from app.services.github_client import parse_github_url
from app.core.exceptions import RepositoryProcessingError

pytestmark = pytest.mark.unit


def test_encrypt_decrypt_round_trip():
    token = "ghp_fakeExampleGitHubTokenValue1234567890"
    encrypted = encrypt_secret(token)
    assert decrypt_secret(encrypted) == token


def test_ciphertext_differs_from_plaintext():
    token = "ghp_fakeExampleGitHubTokenValue1234567890"
    assert encrypt_secret(token) != token


def test_decrypt_with_corrupted_ciphertext_fails_closed():
    """Returns None rather than raising — callers treat this the same as
    'no token stored', per encrypt_secret/decrypt_secret's docstring."""
    encrypted = encrypt_secret("some-token")
    corrupted = encrypted[:-4] + "abcd"
    assert decrypt_secret(corrupted) is None


@pytest.mark.parametrize(
    "url,expected_owner,expected_repo",
    [
        ("https://github.com/octocat/Hello-World", "octocat", "Hello-World"),
        ("https://github.com/octocat/Hello-World.git", "octocat", "Hello-World"),
        ("https://github.com/octocat/Hello-World/", "octocat", "Hello-World"),
        ("http://github.com/my-org/my.repo", "my-org", "my.repo"),
    ],
)
def test_parse_github_url_valid(url, expected_owner, expected_repo):
    owner, repo = parse_github_url(url)
    assert (owner, repo) == (expected_owner, expected_repo)


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/octocat/Hello-World",
        "not a url",
        "https://github.com/octocat",  # missing repo segment
    ],
)
def test_parse_github_url_invalid_raises(url):
    with pytest.raises(RepositoryProcessingError):
        parse_github_url(url)
