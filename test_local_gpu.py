import contextlib
import io
from pathlib import Path
import runpy
import subprocess
import unittest
from unittest.mock import Mock, patch


MODULE = runpy.run_path(str(Path(__file__).with_name("mytask")), run_name="mytask_test")
GLOBALS = MODULE["cmd_gpus"].__globals__
GPU_INFO = {
    "ok": True,
    "probe_source": "torch",
    "gpus": [{
        "gpu_index": "0", "gpu_name": "Test GPU", "gpu_util": None,
        "memory_free_mib": 80, "memory_total_mib": 100,
    }],
}


class LocalGpuTests(unittest.TestCase):
    def render(self, args, info=GPU_INFO, inventory=None):
        local = Mock(return_value=info)
        remote = Mock(return_value=inventory or {})
        output = io.StringIO()
        with patch.dict(GLOBALS, probe_local_gpu=local, worker_inventory=remote):
            with contextlib.redirect_stdout(output):
                MODULE["cmd_gpus"](args)
        return output.getvalue(), local, remote

    def test_default_lists_local_and_remote(self):
        text, local, _ = self.render([], inventory={"123": {"gpu_count": 1, "gpu_type": "Remote GPU"}})
        self.assertIn("local", text)
        self.assertIn("Test GPU", text)
        self.assertIn("Remote GPU", text)
        local.assert_called_once()

    def test_local_only_skips_worker_discovery(self):
        text, _, remote = self.render(["local", "--detail"])
        remote.assert_not_called()
        self.assertIn("free=80.0%", text)
        self.assertIn("util=unknown", text)
        self.assertIn("source=torch", text)

    def test_explicit_remote_does_not_probe_local(self):
        text, local, _ = self.render(["123"], inventory={"123": {"gpu_count": 1, "gpu_type": "Remote GPU"}})
        local.assert_not_called()
        self.assertNotIn("local", text)
        self.assertIn("Remote GPU", text)

    def test_local_failure_keeps_remote_results(self):
        text, _, _ = self.render(
            [], info={"ok": False, "error": "CUDA unavailable"},
            inventory={"123": {"gpu_count": 1, "gpu_type": "Remote GPU"}},
        )
        self.assertIn("CUDA unavailable", text)
        self.assertIn("Remote GPU", text)

    def test_probe_uses_current_python(self):
        result = subprocess.CompletedProcess([], 0, 'MYTASK_GPU_PROBE_JSON={"ok": true, "gpus": []}\n')
        with patch.object(MODULE["subprocess"], "run", return_value=result) as run:
            self.assertTrue(MODULE["probe_local_gpu"]()["ok"])
        self.assertEqual(run.call_args.args[0][0], MODULE["sys"].executable)
        self.assertEqual(run.call_args.kwargs["timeout"], 20)

    def test_probe_timeout(self):
        with patch.object(MODULE["subprocess"], "run", side_effect=subprocess.TimeoutExpired("probe", 20)):
            self.assertFalse(MODULE["probe_local_gpu"]()["ok"])


if __name__ == "__main__":
    unittest.main()
