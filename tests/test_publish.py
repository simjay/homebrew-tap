"""Publication checks must reject untested or unrelated PRs."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("publish", Path(__file__).resolve().parents[1] / "scripts/publish.py")
publish = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.repo = "simjay/homebrew-tap"
        self.pr = {
            "number": 7, "state": "open", "draft": False, "user": {"login": "simjay"},
            "head": {"repo": {"full_name": self.repo}, "ref": "plous-v0.0.2", "sha": "abc"},
            "base": {"repo": {"full_name": self.repo}, "ref": "main"},
        }
        self.run = {"event": "pull_request", "conclusion": "success", "head_sha": "abc",
                    "head_repository": {"full_name": self.repo}, "path": ".github/workflows/tests.yml"}
        self.files = [{"filename": "Formula/plous.rb", "status": "modified"}]
        self.release = {"tag_name": "v0.0.2", "draft": False, "prerelease": False}

    def validate(self, current=None):
        return publish.validate(self.repo, self.pr, self.run, self.files, self.release, current)

    def test_tested_release_commit_is_selected(self):
        self.assertEqual(self.validate("0.0.1"), (7, "abc"))

    def test_stale_failed_and_incomplete_runs_are_rejected(self):
        original = deepcopy(self.run)
        for field, value in [("head_sha", "old"), ("conclusion", "failure"), ("conclusion", None),
                             ("event", "push"), ("path", ".github/workflows/unrelated.yml")]:
            self.run = dict(original, **{field: value})
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.validate()

    def test_forks_and_other_authors_are_rejected(self):
        original = deepcopy(self.pr)
        self.pr["head"]["repo"]["full_name"] = "someone/homebrew-tap"
        with self.assertRaises(ValueError):
            self.validate()
        self.pr = original
        self.pr["user"]["login"] = "someone"
        with self.assertRaises(ValueError):
            self.validate()

    def test_unrelated_changes_are_rejected(self):
        self.files.append({"filename": ".github/workflows/publish.yml", "status": "modified"})
        with self.assertRaises(ValueError):
            self.validate()

    def test_draft_pr_and_unpublished_release_are_rejected(self):
        self.pr["draft"] = True
        with self.assertRaises(ValueError):
            self.validate()
        self.pr["draft"] = False
        self.release["draft"] = True
        with self.assertRaises(ValueError):
            self.validate()

    def test_publication_cannot_downgrade_or_overwrite(self):
        for current in ["0.0.2", "0.0.10"]:
            with self.subTest(current=current), self.assertRaises(ValueError):
                self.validate(current)

    def test_formula_version_comes_from_the_release_source(self):
        formula = ('  url "https://github.com/simjay/plous/archive/refs/tags/v0.0.10.tar.gz"\n'
                   '  bottle do\n    root_url "https://example.com/bottles"\n  end\n')
        self.assertEqual(publish.formula_version(formula), "0.0.10")
        self.assertEqual(self.validate(publish.formula_version(formula.replace("0.0.10", "0.0.1"))),
                         (7, "abc"))
        with self.assertRaises(ValueError):
            self.validate(publish.formula_version(formula))

    def test_unknown_ambiguous_or_overridden_formula_versions_are_rejected(self):
        source_url = '  url "https://github.com/simjay/plous/archive/refs/tags/v0.0.2.tar.gz"\n'
        for formula in ['  version "0.0.2"\n', source_url * 2,
                        source_url.replace("simjay/plous", "other/plous"),
                        source_url.replace("v0.0.2", "v0.0.2-rc.1"),
                        source_url + '  version "0.0.3"\n',
                        source_url + '  version "0.0.2"\n']:
            with self.subTest(formula=formula), self.assertRaises(ValueError):
                publish.formula_version(formula)

    def test_all_supported_bottles_must_exist_and_match_the_release(self):
        formula = '  url "https://github.com/simjay/plous/archive/refs/tags/v0.0.2.tar.gz"\n'
        artifacts = [{"name": f"bottles_{name}", "expired": False} for name in
                     ["macos-15", "ubuntu-24.04", "ubuntu-24.04-arm"]]
        publish.verify_packages("v0.0.2", formula, artifacts)
        for missing in artifacts:
            with self.subTest(missing=missing["name"]), self.assertRaisesRegex(ValueError, missing["name"]):
                publish.verify_packages("v0.0.2", formula, [item for item in artifacts if item != missing])
        artifacts[-1]["expired"] = True
        with self.assertRaises(ValueError):
            publish.verify_packages("v0.0.2", formula, artifacts)
        artifacts[-1]["expired"] = False
        with self.assertRaises(ValueError):
            publish.verify_packages("v0.0.3", formula, artifacts)


if __name__ == "__main__":
    unittest.main()
