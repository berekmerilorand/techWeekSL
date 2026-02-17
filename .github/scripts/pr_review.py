"""Automated PR review using Claude CLI.

Fetches PR diffs from GitHub, sends them to Claude for analysis,
and posts inline review comments back on the PR.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from github import Github
from github.PullRequest import PullRequest

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "")

LOGGER = logging.getLogger(__name__)

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "comments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "line": {"type": "integer"},
                    "body": {"type": "string"},
                },
                "required": ["path", "line", "body"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["comments", "summary"],
}

SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".tar",
    ".gz",
    ".pdf",
    ".pyc",
    ".pyo",
    ".so",
    ".exe",
}

SKIP_PATHS = {
    "poetry.lock",
    "package-lock.json",
    "requirements.txt",
    ".gitignore",
}

SIGNATURE = "\n\n---\n*Review by Claude* 🤖"


@dataclass
class ReviewComment:
    path: str
    line: int
    body: str


def should_review_file(filename: str) -> bool:
    if filename in SKIP_PATHS:
        return False
    ext = Path(filename).suffix.lower()
    return ext not in SKIP_EXTENSIONS


def gather_pr_context(pr: PullRequest) -> list[dict]:
    file_infos = []
    for f in pr.get_files():
        if not should_review_file(f.filename):
            continue
        if not f.patch:
            continue
        file_infos.append(
            {
                "filename": f.filename,
                "patch": f.patch,
                "status": f.status,
            }
        )
    return file_infos


def build_prompt(pr: PullRequest, file_infos: list[dict], guidelines: str) -> str:
    diffs = "\n\n".join(
        f"### {f['filename']} ({f['status']})\n```diff\n{f['patch']}\n```"
        for f in file_infos
    )

    return f"""\
You are reviewing pull request #{pr.number}: "{pr.title}"

PR description:
{pr.body or "(no description)"}

## Project guidelines
{guidelines}

## Diffs to review
{diffs}

## Instructions
Review the diffs above. Only comment on things that truly matter:
- Bugs, logic errors, or security issues
- Missing error handling or edge cases
- Violations of project guidelines that affect correctness
- Code that will cause real problems

Do NOT comment on:
- Code not changed in this PR
- Cosmetic or stylistic issues (formatting, naming, import order)
- Minor preferences or "nice to have" improvements
- Positive feedback or praise

Be pragmatic. Fewer high-quality comments are better than many nitpicks.

For each issue, provide the exact file path and the line number from the NEW
version of the file (the + side of the diff). Only reference lines that appear
in the diff with a + prefix.

If the PR looks good, return an empty comments array and a short summary."""


def invoke_claude(prompt: str, model: Optional[str] = None) -> dict:
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(REVIEW_SCHEMA),
        "--allowedTools",
        "",
    ]
    if model:
        cmd.extend(["--model", model])

    LOGGER.info("Invoking Claude CLI...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        LOGGER.error("Claude CLI stderr: %s", result.stderr)
        raise RuntimeError(f"Claude CLI exited with code {result.returncode}")

    response = json.loads(result.stdout)
    if response.get("is_error"):
        raise RuntimeError(f"Claude error: {response.get('result', 'unknown')}")

    structured = response.get("structured_output")
    if structured is not None:
        return structured

    result_text = response.get("result", "")
    if result_text:
        return json.loads(result_text)

    raise RuntimeError("No review output from Claude CLI")


def validate_comments(
    comments: list[dict], valid_files: set[str]
) -> list[ReviewComment]:
    validated = []
    for c in comments:
        path = c.get("path", "")
        line = c.get("line")
        body = c.get("body", "")

        if path not in valid_files:
            LOGGER.warning("Dropping comment for unknown file: %s", path)
            continue
        if not isinstance(line, int) or line < 1:
            LOGGER.warning("Dropping comment with invalid line in %s", path)
            continue
        if not body.strip():
            continue

        validated.append(ReviewComment(path=path, line=line, body=body))
    return validated


def post_review(
    pr: PullRequest, comments: list[ReviewComment], summary: str, dry_run: bool = False
):
    if dry_run:
        LOGGER.info("=== DRY RUN ===")
        LOGGER.info("Summary: %s", summary)
        for c in comments:
            LOGGER.info("  %s:%d — %s", c.path, c.line, c.body)
        return

    review_comments = [
        {"path": c.path, "line": c.line, "side": "RIGHT", "body": c.body + SIGNATURE}
        for c in comments
    ]

    body = "" if review_comments else summary + SIGNATURE
    latest_commit = list(pr.get_commits())[-1]

    pr.create_review(
        commit=latest_commit,
        body=body,
        comments=review_comments,
    )
    LOGGER.info("Posted review with %d comment(s) on PR #%d", len(comments), pr.number)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review a PR using Claude CLI")
    parser.add_argument("pr_number", type=int, help="Pull request number")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if not GITHUB_TOKEN:
        LOGGER.error("GITHUB_TOKEN is not set")
        return 1

    # Load review guidelines
    guidelines_path = Path(__file__).parent.parent.parent / "REVIEW_GUIDELINES.md"
    guidelines = (
        guidelines_path.read_text()
        if guidelines_path.exists()
        else "No specific guidelines."
    )

    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)
    pr = repo.get_pull(args.pr_number)

    LOGGER.info("Reviewing PR #%d: %s", pr.number, pr.title)
    file_infos = gather_pr_context(pr)
    LOGGER.info("Found %d reviewable file(s)", len(file_infos))

    if not file_infos:
        LOGGER.info("Nothing to review.")
        return 0

    prompt = build_prompt(pr, file_infos, guidelines)
    result = invoke_claude(prompt, model=args.model)

    valid_files = {f["filename"] for f in file_infos}
    comments = validate_comments(result.get("comments", []), valid_files)
    summary = result.get("summary", "")

    post_review(pr, comments, summary, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
