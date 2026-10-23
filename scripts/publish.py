"""Select a tested, owner-created Plous release PR for bottle publication."""

import base64
import json
import os
from pathlib import Path
import re
import subprocess


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path], text=True))


def formula_version(formula):
    versions = re.findall(
        r'^  url "https://github\.com/simjay/plous/archive/refs/tags/v([0-9]+\.[0-9]+\.[0-9]+)\.tar\.gz"$',
        formula, re.MULTILINE)
    if len(versions) != 1 or re.search(r"^\s*version\b", formula, re.MULTILINE):
        raise ValueError("Formula must infer its version from one Plous release source URL")
    return versions[0]


def verify_packages(tag, formula, artifacts):
    if formula_version(formula) != tag[1:]:
        raise ValueError("Formula version and source URL must match the release branch")
    expected = {f"bottles_{os_name}" for os_name in
                ["macos-15", "macos-15-intel", "ubuntu-24.04", "ubuntu-24.04-arm"]}
    available = {item["name"] for item in artifacts if not item["expired"]}
    if not expected <= available:
        raise ValueError("All four tested bottle artifacts must be available")


def validate(repo, pr, run, files, release, current_version=None):
    owner = repo.split("/")[0]
    if pr["state"] != "open" or pr["draft"]:
        raise ValueError("Pull request must be open and ready")
    if (pr["user"]["login"] != owner or pr["head"]["repo"]["full_name"] != repo
            or pr["base"]["repo"]["full_name"] != repo or pr["base"]["ref"] != "main"):
        raise ValueError("Only owner-created release branches in this tap may publish automatically")
    match = re.fullmatch(r"plous-(v[0-9]+\.[0-9]+\.[0-9]+)", pr["head"]["ref"])
    if not match:
        raise ValueError("Expected a Plous release branch")
    tag = match[1]
    if (run["event"] != "pull_request" or run["conclusion"] != "success"
            or run["head_sha"] != pr["head"]["sha"]
            or run["head_repository"]["full_name"] != repo
            or run["path"] != ".github/workflows/tests.yml"):
        raise ValueError("The current PR commit must pass the complete Homebrew test workflow")
    if len(files) != 1 or files[0]["filename"] != "Formula/plous.rb" or files[0]["status"] not in {"added", "modified"}:
        raise ValueError("A release PR may only add or update Formula/plous.rb")
    if release["tag_name"] != tag or release["draft"] or release["prerelease"]:
        raise ValueError("A published stable Plous release is required")
    if current_version and tuple(map(int, current_version.split("."))) >= tuple(map(int, tag[1:].split("."))):
        raise ValueError("The tap already contains this release or a newer one")
    return pr["number"], pr["head"]["sha"]


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    if os.environ["GITHUB_EVENT_NAME"] == "workflow_run":
        event_run = event["workflow_run"]
        branch = event_run["head_branch"]
        if not re.fullmatch(r"plous-v[0-9]+\.[0-9]+\.[0-9]+", branch):
            print("This is not an automated Plous release PR.")
            return
        prs = api(f"repos/{repo}/pulls?head={repo.split('/')[0]}:{branch}&base=main&state=open")
        if not prs:
            print("The release PR is already closed.")
            return
        if len(prs) != 1:
            raise ValueError("Expected exactly one release PR")
        number = prs[0]["number"]
    else:
        number = int(event["inputs"]["pull_request"])
    pr = api(f"repos/{repo}/pulls/{number}")
    sha = pr["head"]["sha"]
    expected = event.get("inputs", {}).get("head_sha")
    if expected and expected != sha:
        raise ValueError("The PR has changed since the requested commit")
    if os.environ["GITHUB_EVENT_NAME"] == "workflow_run" and event_run["head_sha"] != sha:
        print("The PR has newer changes; wait for their tests.")
        return
    runs = api(f"repos/{repo}/actions/workflows/tests.yml/runs?event=pull_request&head_sha={sha}")["workflow_runs"]
    if not runs:
        raise ValueError("No Homebrew tests found for this commit")
    files = api(f"repos/{repo}/pulls/{number}/files?per_page=100")
    tag = pr["head"]["ref"].removeprefix("plous-")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError("Expected a Plous release branch")
    release = api(f"repos/simjay/plous/releases/tags/{tag}")
    formula = api(f"repos/{repo}/contents/Formula/plous.rb?ref={sha}")
    text = base64.b64decode(formula["content"]).decode()
    artifacts = api(f"repos/{repo}/actions/runs/{runs[0]['id']}/artifacts?per_page=100")["artifacts"]
    verify_packages(tag, text, artifacts)
    root = api(f"repos/{repo}/git/trees/main?recursive=1")
    current = None
    if any(entry["path"] == "Formula/plous.rb" for entry in root["tree"]):
        content = api(f"repos/{repo}/contents/Formula/plous.rb?ref=main")
        current = formula_version(base64.b64decode(content["content"]).decode())
    number, sha = validate(repo, pr, runs[0], files, release, current)
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"pull_request={number}\nhead_sha={sha}\n")


if __name__ == "__main__":
    main()
