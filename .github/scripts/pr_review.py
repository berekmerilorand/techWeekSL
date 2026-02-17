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
    # Ensure API key is available
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    # Try to use Anthropic SDK if available, otherwise fall back to CLI
    try:
        import anthropic
        return _invoke_claude_sdk(prompt, api_key, model)
    except ImportError:
        LOGGER.warning("Anthropic SDK not available, falling back to CLI")
        return _invoke_claude_cli(prompt, api_key, model)


def _invoke_claude_sdk(prompt: str, api_key: str, model: Optional[str] = None) -> dict:
    """Use Anthropic Python SDK directly (faster and more reliable)"""
    import anthropic
    import re

    if model is None:
        model = "claude-3-5-sonnet-20241022"

    LOGGER.info("Invoking Claude API with model %s...", model)
    LOGGER.debug("Prompt length: %d characters", len(prompt))

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0,
            system="You are a code reviewer. Analyze the PR and return ONLY valid JSON matching the required schema. Do not include markdown formatting or explanations.",
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nIMPORTANT: Return ONLY a JSON object matching this exact schema (no markdown, no code blocks):\n{json.dumps(REVIEW_SCHEMA, indent=2)}"
                }
            ]
        )

        # Extract text from response
        content_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                content_text += block.text

        LOGGER.debug("Raw API response (first 500 chars): %s", content_text[:500])

        # Try to parse JSON, handling potential markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            # Try to parse entire response as JSON
            result = json.loads(content_text.strip())

        # Validate required fields
        if "comments" not in result or "summary" not in result:
            raise ValueError(f"Response missing required fields. Got keys: {list(result.keys())}")

        LOGGER.info("Successfully parsed review with %d comments", len(result.get("comments", [])))
        return result

    except json.JSONDecodeError as e:
        LOGGER.error("Failed to parse Claude response as JSON: %s", e)
        LOGGER.error("Response content (first 1000 chars): %s", content_text[:1000])
        # Return empty review rather than failing
        return {"comments": [], "summary": "Error parsing Claude response - review skipped"}
    except Exception as e:
        LOGGER.error("Error calling Claude API: %s", e)
        raise RuntimeError(f"Claude API error: {e}")


def _invoke_claude_cli(prompt: str, api_key: str, model: Optional[str] = None) -> dict:
    """Fallback: Use Claude CLI (slower, may timeout)"""
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
    LOGGER.debug("Command: %s", " ".join(cmd[:4]) + " ... (truncated)")
    LOGGER.debug("Prompt length: %d characters", len(prompt))

    # Pass environment variables explicitly to subprocess
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = api_key

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
    except subprocess.TimeoutExpired as e:
        LOGGER.error("Claude CLI timed out after 600 seconds")
        LOGGER.error("Partial stdout: %s", e.stdout[:500] if e.stdout else "(none)")
        LOGGER.error("Partial stderr: %s", e.stderr[:500] if e.stderr else "(none)")
        # Return empty review rather than failing completely
        return {"comments": [], "summary": "Claude CLI timed out - review skipped"}

    if result.returncode != 0:
        LOGGER.error("Claude CLI stderr: %s", result.stderr)
        # Return empty review rather than failing
        return {"comments": [], "summary": f"Claude CLI error (exit code {result.returncode}) - review skipped"}

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

    from github import Auth
    auth = Auth.Token(GITHUB_TOKEN)
    gh = Github(auth=auth)
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
