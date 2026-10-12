"""Thin async wrapper around the subset of GitHub's REST/OAuth APIs this
app needs. Deliberately not a full GitHub SDK — five focused methods, each
mapping to one concrete feature (login, private clone, commit hash lookup).
"""

import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.exceptions import RepositoryProcessingError, UnauthorizedError

_GITHUB_API_BASE = "https://api.github.com"
_GITHUB_OAUTH_BASE = "https://github.com/login/oauth"

_GITHUB_URL_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$"
)


@dataclass
class GitHubUser:
    github_id: str
    login: str
    avatar_url: Optional[str]
    email: Optional[str]


def parse_github_url(url: str) -> tuple[str, str]:
    match = _GITHUB_URL_PATTERN.match(url.strip())
    if not match:
        raise RepositoryProcessingError(f"'{url}' doesn't look like a GitHub repository URL")
    return match.group("owner"), match.group("repo")


class GitHubClient:
    def __init__(self):
        settings = get_settings()
        self._client_id = settings.GITHUB_CLIENT_ID
        self._client_secret = settings.GITHUB_CLIENT_SECRET

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        return (
            f"{_GITHUB_OAUTH_BASE}/authorize"
            f"?client_id={self._client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=repo,user:email"
            f"&state={state}"
        )

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{_GITHUB_OAUTH_BASE}/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise UnauthorizedError(
                f"GitHub rejected the OAuth code: {data.get('error_description', 'unknown error')}"
            )
        return access_token

    async def get_authenticated_user(self, access_token: str) -> GitHubUser:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_GITHUB_API_BASE}/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
        if response.status_code != 200:
            raise UnauthorizedError("Failed to fetch GitHub user profile with the provided token")
        data = response.json()
        return GitHubUser(
            github_id=str(data["id"]),
            login=data["login"],
            avatar_url=data.get("avatar_url"),
            email=data.get("email"),
        )

    async def get_default_branch(
        self, owner: str, repo: str, access_token: Optional[str] = None
    ) -> str:
        headers = {"Accept": "application/vnd.github+json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{_GITHUB_API_BASE}/repos/{owner}/{repo}", headers=headers)
        if response.status_code == 404:
            raise RepositoryProcessingError(
                f"Repository {owner}/{repo} not found or not accessible with the current credentials"
            )
        response.raise_for_status()
        return response.json()["default_branch"]

    async def get_latest_commit_sha(
        self, owner: str, repo: str, branch: str, access_token: Optional[str] = None
    ) -> str:
        headers = {"Accept": "application/vnd.github+json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{branch}", headers=headers
            )
        response.raise_for_status()
        return response.json()["sha"]

    async def download_repository_zipball(
        self, owner: str, repo: str, ref: str, access_token: Optional[str] = None
    ) -> bytes:
        """GitHub's zipball endpoint 302-redirects to codeload.github.com —
        follow_redirects=True is required or this silently returns the
        redirect response body instead of the archive."""
        headers = {"Accept": "application/vnd.github+json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
            response = await client.get(
                f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/zipball/{ref}", headers=headers
            )
        if response.status_code == 404:
            raise RepositoryProcessingError(
                f"Repository {owner}/{repo}@{ref} not found or not accessible with the current credentials "
                "(private repositories require connecting GitHub in Settings)"
            )
        response.raise_for_status()
        return response.content


def get_github_client() -> GitHubClient:
    return GitHubClient()
