"""Raw-file contract tests; all mutation stays in temporary synthetic releases."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[1]


class EvidenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "release"
        shutil.copytree(PLUGIN / "tests/fixtures/release", self.root)
        self.record = json.loads((self.root / "record.json").read_text())

    def run_record(self, record=None, extra=()):
        path = self.root / "candidate.json"
        path.write_text(json.dumps(self.record if record is None else record))
        result = subprocess.run([
            sys.executable, str(PLUGIN / "scripts/audit_evidence.py"), str(path),
            "--root", str(self.root), "--scope-id", "fixture-release",
            "--source-revision", "approved-plan-r4",
            "--required-gate", "content", "--required-gate", "visual", *extra,
        ], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def assert_invalid(self, term):
        code, output = self.run_record()
        self.assertEqual(code, 1)
        self.assertEqual(output["integrity"], "invalid")
        self.assertEqual(output["release_decision"], "not_evaluated")
        self.assertIn(term, " ".join(output["errors"]))

    def test_actual_raw_files_pass_integrity_only(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        code, output = self.run_record()
        self.assertEqual(code, 0)
        self.assertEqual(output["integrity"], "verified")
        self.assertEqual(output["release_decision"], "not_evaluated")
        self.assertEqual(output["declared_results"]["pass"], 2)
        self.assertEqual(output["unresolved_gate_ids"], [])
        for path, value in before.items():
            self.assertEqual((self.root / path).read_bytes(), value)

    def test_changed_final_bytes_rejected(self):
        (self.root / "final/lesson.txt").write_text("Modified after review")
        self.assert_invalid("hash mismatch")

    def test_changed_evidence_bytes_rejected(self):
        (self.root / "evidence/content-review.json").write_text('{"result":"pass"}')
        self.assert_invalid("hash mismatch")

    def test_missing_evidence_rejected(self):
        (self.root / "evidence/content-review.json").unlink()
        self.assert_invalid("not a regular file")

    def test_source_revision_mismatch_rejected(self):
        self.record["scope"]["source_revision"] = "old-plan"
        self.assert_invalid("current source revision")

    def test_cross_scope_evidence_rejected(self):
        self.record["gates"][0]["evidence"][0]["scope_id"] = "another-release"
        self.assert_invalid("scope")

    def test_stale_artifact_binding_rejected(self):
        self.record["gates"][0]["evidence"][0]["artifact_sha256"]["lesson"] = "0" * 64
        self.assert_invalid("artifact bindings")

    def test_missing_external_required_gate_rejected(self):
        self.record["required_gates"] = ["content"]
        self.record["gates"] = self.record["gates"][:1]
        self.assert_invalid("externally required")

    def test_missing_declared_required_gate_rejected(self):
        self.record["gates"] = self.record["gates"][:1]
        self.assert_invalid("missing required gate")

    def test_empty_pass_evidence_rejected(self):
        self.record["gates"][0]["evidence"] = []
        self.assert_invalid("requires evidence")

    def test_fail_is_integrity_valid_but_unresolved(self):
        self.record["gates"][0]["result"] = "fail"
        code, output = self.run_record()
        self.assertEqual(code, 0)
        self.assertEqual(output["unresolved_gate_ids"], ["content"])
        self.assertEqual(output["release_decision"], "not_evaluated")

    def test_blocked_without_evidence_stays_blocked(self):
        self.record["gates"][0].update(result="blocked", evidence=[], rationale="Required renderer unavailable")
        code, output = self.run_record()
        self.assertEqual(code, 0)
        self.assertEqual(output["unresolved_gate_ids"], ["content"])

    def test_na_requires_rationale(self):
        self.record["gates"][0].update(result="not_applicable", evidence=[], rationale=" ")
        self.assert_invalid("rationale")

    def test_na_remains_declared_not_approved(self):
        self.record["gates"][0].update(result="not_applicable", evidence=[], rationale="The approved scope contains no content changes")
        code, output = self.run_record()
        self.assertEqual(code, 0)
        self.assertEqual(output["not_applicable_gate_ids"], ["content"])
        self.assertEqual(output["release_decision"], "not_evaluated")

    def test_parent_traversal_rejected(self):
        self.record["artifacts"][0]["path"] = "../outside.txt"
        self.assert_invalid("unsafe path")

    def test_absolute_path_rejected(self):
        self.record["artifacts"][0]["path"] = str(self.root / "final/lesson.txt")
        self.assert_invalid("unsafe path")

    def test_symlink_rejected(self):
        link = self.root / "linked.txt"
        link.symlink_to(self.root / "final/lesson.txt")
        self.record["artifacts"][0]["path"] = "linked.txt"
        self.assert_invalid("symlink")

    def test_duplicate_gate_rejected(self):
        self.record["gates"].append(copy.deepcopy(self.record["gates"][0]))
        self.assert_invalid("duplicate gate")

    def test_unknown_fields_and_results_rejected(self):
        self.record["gates"][0]["result"] = "done"
        self.assert_invalid("unknown result")
        self.record["gates"][0]["result"] = "pass"
        self.record["unexpected"] = "command text is data"
        self.assert_invalid("unexpected")

    def test_boolean_schema_version_rejected(self):
        self.record["schema_version"] = True
        self.assert_invalid("schema_version")

    def test_duplicate_json_keys_rejected(self):
        path = self.root / "duplicates.json"
        path.write_text('{"schema_version": 1, "schema_version": 1}')
        result = subprocess.run([sys.executable, str(PLUGIN / "scripts/audit_evidence.py"), str(path), "--root", str(self.root), "--scope-id", "x", "--source-revision", "r", "--required-gate", "content"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate JSON key", result.stdout)


if __name__ == "__main__":
    unittest.main()
