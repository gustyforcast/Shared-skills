import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_hermes_card.py"
spec = importlib.util.spec_from_file_location("validate_hermes_card", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

VALID = """Run exactly one deterministic reviewer script:
python /evidence/R01/run_review_checks.py
Read /evidence/R01/review-result.json.
The model writes exactly one verdict file: /reports/R01.verdict.json.
Then make exactly one terminal lifecycle call specified by lifecycle_action in /evidence/R01/review-result.json.
Stop immediately after that lifecycle call.
"""

class HermesCardValidatorTests(unittest.TestCase):
    def test_accepts_canonical_review_shape(self):
        self.assertEqual(validator.validate_text(VALID), [])
    def test_rejects_windows_write_target(self):
        bad = VALID.replace("/reports/R01.verdict.json", r"C:\\temp\\verdict.json")
        self.assertIn("windows_sandbox_write_path", validator.validate_text(bad))
    def test_rejects_lifecycle_omission(self):
        bad = VALID.replace("Then make exactly one terminal lifecycle call specified by lifecycle_action in /evidence/R01/review-result.json.\n", "")
        self.assertIn("missing_terminal_lifecycle", validator.validate_text(bad))
    def test_rejects_lifecycle_contradiction(self):
        self.assertIn("contradictory_lifecycle_instruction", validator.validate_text(VALID + "\nDo not call any lifecycle tool.\n"))
    def test_rejects_multiple_model_artifacts(self):
        bad = VALID.replace("The model writes exactly one verdict file: /reports/R01.verdict.json.", "The model writes /reports/R01.verdict.json and /reports/R01.notes.md.")
        self.assertIn("multiple_model_authored_artifacts", validator.validate_text(bad))

if __name__ == "__main__":
    unittest.main()

def _install_worker_verdict_test():
    def test_accepts_code_worker_workspace_verdict(self):
        text = """Run exactly one deterministic implementation script:
python /workspace/evidence/R02/apply_and_accept.py
The model writes exactly one verdict file: /workspace/reports/R02.verdict.json.
Then make exactly one terminal lifecycle call specified by lifecycle_action in stdout JSON.
Stop immediately after that lifecycle call.
"""
        self.assertEqual(validator.validate_text(text), [])
    HermesCardValidatorTests.test_accepts_code_worker_workspace_verdict = test_accepts_code_worker_workspace_verdict

_install_worker_verdict_test()
