# Plous Homebrew tap

Homebrew packages for [Plous](https://github.com/simjay/plous), a Kubernetes lifecycle tool for your terminal.

Installation requires a published Plous formula in this tap. If none is available yet, use the [source installation guide](https://github.com/simjay/plous/blob/main/docs/getting-started/README.md).

## Install and update

Once published, on macOS or Linux with Homebrew installed:

```sh
brew install simjay/tap/plous
```

To update:

```sh
brew update
brew upgrade plous
```

Bottles target macOS 15 and newer on Apple Silicon and Intel, and Homebrew-supported Linux on ARM64 and x86-64. Homebrew builds from source if no compatible bottle is available; source builds require Go. Plous uses your existing kubeconfig. Claude Code and Codex remain optional, separately installed tools.

## Publishing

Plous's release workflow creates a `plous-vMAJOR.MINOR.PATCH` branch and PR that changes only `Formula/plous.rb`. The source formula is generated from the release tag and source checksum; its template lives in the Plous repository. Do not maintain a second template here.

`brew test-bot` builds and tests all four platforms. After success, `brew pr-pull` verifies the PR's author, repository, changed file, release, version, and tested commit. It uploads bottles and pushes the formula plus bottle metadata to `main`. It uses the tap's `GITHUB_TOKEN`; no additional secret is needed here. Repository rules must permit the publishing workflow to push to `main`.

Do not merge release PRs manually. Failed builds leave the previous version available. To recover a failed publication, rerun **brew pr-pull** with the PR number and expected head SHA. It still requires successful tests for that commit. Full release instructions are in [Releasing Plous](https://github.com/simjay/plous/blob/main/docs/contributing/releases.md).

Run publication policy tests with `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`.
