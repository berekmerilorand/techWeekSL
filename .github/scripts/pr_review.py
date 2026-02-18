"""Automated PR review script.

Fetches a pull request from GitHub, sends the diffs to the Claude CLI
for analysis against CLAUDE.md guidelines, and posts inline review
comments back on the PR.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import tempfile

from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository

GITHUB_TOKEN = os.environ.get("SL_GITHUB_TOKEN", "")
REPO_NAME = "berekmerilorand/techWeekSL"

PR_URL_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
)

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
    ".otf",
    ".mp3",
    ".mp4",
    ".webm",
    ".ogg",
    ".wav",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".pdf",
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".dat",
}

SKIP_PATHS = {
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".gitignore",
}

SKIP_PATH_PREFIXES = (
    "packages/app/tubescreamer/migrations/",
    ".tox/",
    ".env/",
    "node_modules/",
)

BATCH_CHAR_LIMIT = 150_000

SIGNATURE = "\n\n---\n*Review by Claude*"


@dataclass
class ReviewComment:
    path: str
    line: int
    body: str


def parse_pr_arg(value: str) -> tuple[str, int]:
    """Parse a PR number or GitHub PR URL into (repo_name, pr_number)."""
    match = PR_URL_PATTERN.match(value)
    if match:
        repo_name = f"{match.group('owner')}/{match.group('repo')}"
        return repo_name, int(match.group("number"))

    try:
        return REPO_NAME, int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Expected a PR number or GitHub PR URL, got: {value}"
        )


def fetch_pull_request(repo_name: str, pr_number: int) -> PullRequest:
    repo = Github(GITHUB_TOKEN).get_repo(repo_name)
    return repo.get_pull(pr_number)


def should_review_file(filename: str) -> bool:
    if filename in SKIP_PATHS:
        return False
    if any(filename.startswith(prefix) for prefix in SKIP_PATH_PREFIXES):
        return False
    extension = Path(filename).suffix.lower()
    if extension in SKIP_EXTENSIONS:
        return False
    return True


def gather_pr_context(pull_request: PullRequest) -> list[dict]:
    file_infos = []
    for pr_file in pull_request.get_files():
        if not should_review_file(pr_file.filename):
            LOGGER.debug("Skipping %s", pr_file.filename)
            continue
        if not pr_file.patch:
            LOGGER.debug("Skipping %s (no patch)", pr_file.filename)
            continue
        file_infos.append(
            {
                "filename": pr_file.filename,
                "patch": pr_file.patch,
                "status": pr_file.status,
            },
        )
    return file_infos


def build_review_prompt(
    pull_request: PullRequest,
    file_infos: list[dict],
    claude_md: str,
) -> str:
    diff_sections = []
    for info in file_infos:
        diff_sections.append(
            f"### {info['filename']} ({info['status']})\n"
            f"```diff\n{info['patch']}\n```"
        )
    diffs_text = "\n\n".join(diff_sections)

    return f"""Respond ONLY with valid JSON matching this schema, no markdown fences, no preamble:
{{"comments": [{{"path": "file.py", "line": 10, "body": "description"}}], "summary": "text"}}

You are reviewing pull request #{pull_request.number}: "{pull_request.title}"

PR description:
{pull_request.body or "(no description)"}

## Project guidelines (CLAUDE.md)

{claude_md}

## Diffs to review

{diffs_text}

## Instructions

Review the diffs above. Only comment on things that truly matter:
- Bugs, logic errors, or security issues
- Violations of the project guidelines that affect correctness or maintainability
- Code smells that will cause real problems (e.g. mocking DB objects in tests)

Do NOT comment on:
- Code that was not changed in this PR
- Cosmetic or stylistic issues (naming, formatting, import order, docstrings, comments)
- Missing type hints unless they cause ambiguity
- Anything auto-formatters (black, isort) handle
- Minor preferences or "nice to have" improvements
- Positive feedback or praise

Be pragmatic. When in doubt, don't comment. Fewer high-quality comments are
better than many nitpicks.

For each issue, provide the exact file path and the line number from the NEW
version of the file (the line number shown after the + in the diff hunk header).
Only reference lines that appear in the diff with a + prefix.

If the PR looks good and follows all guidelines, return an empty comments array
and a short summary saying so."""


def invoke_claude(prompt: str, model: Optional[str] = None) -> dict:
    # Write prompt to temp file to avoid CLI argument limits
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        # Try to find claude in PATH, fallback to known installation location
        home = os.path.expanduser("~")
        local_bin_path = os.path.join(home, ".local", "bin", "claude")

        # First check the common installation path
        if os.path.exists(local_bin_path) and os.access(local_bin_path, os.X_OK):
            claude_bin = local_bin_path
            LOGGER.info("Using Claude CLI from: %s", claude_bin)
        else:
            # Try to find in PATH
            which_result = subprocess.run(
                ["which", "claude"], capture_output=True, text=True
            )
            if which_result.returncode == 0:
                claude_bin = which_result.stdout.strip()
                LOGGER.info("Found Claude CLI in PATH: %s", claude_bin)
            else:
                raise RuntimeError(
                    f"Claude CLI not found. Checked {local_bin_path} and PATH. "
                    f"Make sure Claude CLI is installed."
                )

        cmd = [
            claude_bin,
            "-p",
            "--output-format",
            "json",
            "--dangerously-skip-permissions",
        ]
        if model:
            cmd.extend(["--model", model])

        LOGGER.info("Invoking Claude CLI...")

        with open(prompt_file, "r") as stdin_file:
            result = subprocess.run(
                cmd,
                stdin=stdin_file,
                capture_output=True,
                text=True,
                timeout=600,
            )
    finally:
        os.unlink(prompt_file)

    if result.returncode != 0:
        LOGGER.error("Claude CLI stderr: %s", result.stderr)
        raise RuntimeError(f"Claude CLI exited with code {result.returncode}")

    response = json.loads(result.stdout)

    if response.get("is_error"):
        error_msg = response.get("result", "unknown")
        if "Credit balance is too low" in error_msg or "balance" in error_msg.lower():
            raise RuntimeError(
                f"Anthropic API error: {error_msg}. "
                f"Please add credits to your Anthropic account at https://console.anthropic.com/settings/billing"
            )
        raise RuntimeError(f"Claude error: {error_msg}")

    result_text = response.get("result", "")
    if not result_text:
        raise RuntimeError("No review output from Claude CLI")

    cleaned = re.sub(r"^```json\s*", "", result_text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def review_in_batches(
    pull_request: PullRequest,
    file_infos: list[dict],
    claude_md: str,
    model: Optional[str] = None,
) -> dict:
    if not file_infos:
        return {"comments": [], "summary": "No reviewable files in this PR."}

    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_size = 0

    for info in file_infos:
        patch_size = len(info["patch"])
        if current_batch and current_size + patch_size > BATCH_CHAR_LIMIT:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(info)
        current_size += patch_size

    if current_batch:
        batches.append(current_batch)

    LOGGER.info(
        "Reviewing %d files in %d batch(es)",
        len(file_infos),
        len(batches),
    )

    all_comments = []
    summaries = []

    for batch_index, batch in enumerate(batches):
        LOGGER.info(
            "Processing batch %d/%d (%d files)",
            batch_index + 1,
            len(batches),
            len(batch),
        )
        prompt = build_review_prompt(pull_request, batch, claude_md)
        result = invoke_claude(prompt, model)
        all_comments.extend(result.get("comments", []))
        summaries.append(result.get("summary", ""))

    summary = "\n\n".join(summaries) if len(summaries) > 1 else summaries[0]
    return {"comments": all_comments, "summary": summary}


def validate_comments(
    comments: list[dict],
    valid_files: set[str],
) -> list[ReviewComment]:
    validated = []
    for comment in comments:
        path = comment.get("path", "")
        line = comment.get("line")
        body = comment.get("body", "")

        if path not in valid_files:
            LOGGER.warning("Dropping comment for unknown file: %s", path)
            continue
        if not isinstance(line, int) or line < 1:
            LOGGER.warning("Dropping comment with invalid line %s in %s", line, path)
            continue
        if not body.strip():
            LOGGER.warning("Dropping empty comment for %s:%d", path, line)
            continue

        validated.append(ReviewComment(path=path, line=line, body=body))
    return validated


def post_review(
    pull_request: PullRequest,
    comments: list[ReviewComment],
    summary: str,
    dry_run: bool = False,
) -> None:
    if dry_run:
        LOGGER.info("=== DRY RUN — review will NOT be posted ===")
        LOGGER.info("Summary: %s", summary)
        for comment in comments:
            LOGGER.info("  %s:%d — %s", comment.path, comment.line, comment.body)
        LOGGER.info("Total: %d comment(s)", len(comments))
        return

    review_comments = []
    for comment in comments:
        review_comments.append(
            {
                "path": comment.path,
                "line": comment.line,
                "side": "RIGHT",
                "body": comment.body + SIGNATURE,
            },
        )

    # Skip the summary body when all feedback is already in inline comments
    body = "" if review_comments else summary + SIGNATURE

    latest_commit = list(pull_request.get_commits())[-1]

    pull_request.create_review(
        commit=latest_commit,
        body=body,
        comments=review_comments,
    )
    LOGGER.info(
        "Posted review with %d comment(s) on PR #%d",
        len(comments),
        pull_request.number,
    )


def review_pr(args: argparse.Namespace) -> None:
    claude_md_path = Path(__file__).parent / "CLAUDE.md"
    claude_md = claude_md_path.read_text()

    repo_name, pr_number = parse_pr_arg(args.pr_ref)

    LOGGER.info("Fetching PR #%d from %s", pr_number, repo_name)
    pull_request = fetch_pull_request(repo_name, pr_number)
    LOGGER.info("PR: %s", pull_request.title)

    file_infos = gather_pr_context(pull_request)
    LOGGER.info("Found %d reviewable file(s)", len(file_infos))

    if not file_infos:
        LOGGER.info("Nothing to review.")
        return

    result = review_in_batches(
        pull_request,
        file_infos,
        claude_md,
        model=args.model,
    )

    valid_files = {info["filename"] for info in file_infos}
    comments = validate_comments(result["comments"], valid_files)
    summary = result.get("summary", "")

    post_review(
        pull_request,
        comments,
        summary,
        dry_run=args.dry_run,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review a GitHub pull request using Claude against CLAUDE.md guidelines.",
    )
    parser.add_argument(
        "pr_ref",
        help="Pull request number or full GitHub PR URL (e.g. https://github.com/owner/repo/pull/123)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the review without posting it to GitHub",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Claude model to use (e.g. sonnet, opus)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stdout,
    )

    if not GITHUB_TOKEN:
        LOGGER.error("TS_GITHUB_TOKEN environment variable is not set")
        return 1

    try:
        review_pr(args)
    except Exception:
        LOGGER.exception("Review failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
