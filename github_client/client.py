"""GitHub API client for fetching PR data."""

import re
from typing import Optional
from github import Github
from config import settings
from core.models import PRInfo, FileDiff


class GitHubClient:
    """GitHub API client for fetching PR data."""

    def __init__(self):
        self._github: Optional[Github] = None
        if settings.has_github:
            self._github = Github(settings.GITHUB_TOKEN)

    @staticmethod
    def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
        """Extract owner, repo, and PR number from a GitHub PR URL.

        Supports:
        - https://github.com/owner/repo/pull/123
        - owner/repo#123
        - owner/repo/pull/123
        """
        match = re.match(
            r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url
        )
        if match:
            return match.group(1), match.group(2), int(match.group(3))

        match = re.match(r"([^/]+)/([^#]+)#(\d+)", pr_url)
        if match:
            return match.group(1), match.group(2), int(match.group(3))

        match = re.match(r"([^/]+)/([^/]+)/pull/(\d+)", pr_url)
        if match:
            return match.group(1), match.group(2), int(match.group(3))

        raise ValueError(f"Cannot parse PR URL: {pr_url}")

    def fetch_pr(self, pr_url: str) -> tuple[PRInfo, list[FileDiff]]:
        """Fetch PR metadata and file diffs."""
        owner, repo, number = self.parse_pr_url(pr_url)

        if not self._github:
            raise RuntimeError(
                "GitHub token not configured. Set GITHUB_TOKEN in .env"
            )

        repo_obj = self._github.get_repo(f"{owner}/{repo}")
        pr = repo_obj.get_pull(number)

        pr_info = PRInfo(
            url=pr_url,
            owner=owner,
            repo=repo,
            number=number,
            title=pr.title or "",
            author=pr.user.login if pr.user else "",
            description=pr.body or "",
            base_branch=pr.base.ref if pr.base else "main",
            head_branch=pr.head.ref if pr.head else "",
        )

        files = []
        for f in pr.get_files():
            files.append(
                FileDiff(
                    filename=f.filename,
                    status=f.status or "modified",
                    patch=f.patch or "",
                    additions=f.additions,
                    deletions=f.deletions,
                )
            )

        return pr_info, files

    def post_review_comment(self, pr_url: str, body: str) -> bool:
        """Post a review comment on the PR."""
        try:
            owner, repo, number = self.parse_pr_url(pr_url)
            if not self._github:
                print("GitHub token not configured, cannot post comment.")
                return False
            repo_obj = self._github.get_repo(f"{owner}/{repo}")
            pr = repo_obj.get_pull(number)
            pr.create_issue_comment(body)
            return True
        except Exception as e:
            print(f"Failed to post comment: {e}")
            return False
