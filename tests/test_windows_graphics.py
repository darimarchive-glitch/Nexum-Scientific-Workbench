"""Driver selection must recover from unavailable/crashing native drivers."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('windows_graphics', Path(__file__).parents[1] / 'nexum/windows_graphics.py')
graphics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graphics)


class WindowsGraphicsTests(unittest.TestCase):
    def select(self, runner, requested='auto'):
        with tempfile.TemporaryDirectory() as folder:
            return graphics.select_mode('C:/Nexum/Nexum.exe', requested, folder, runner)

    def test_native_success_does_not_load_software(self):
        runner = Mock(return_value=Mock(returncode=0))
        self.assertEqual(self.select(runner), 'native')
        self.assertEqual(runner.call_count, 1)

    def test_native_crash_falls_back(self):
        runner = Mock(side_effect=[Mock(returncode=0xc0000005), Mock(returncode=0)])
        self.assertEqual(self.select(runner), 'software')
        self.assertEqual([c.args[0][-1] for c in runner.call_args_list], ['native', 'software'])

    def test_hung_native_driver_falls_back(self):
        runner = Mock(side_effect=[subprocess.TimeoutExpired('Nexum', 25), Mock(returncode=0)])
        self.assertEqual(self.select(runner), 'software')

    def test_explicit_software_skips_native(self):
        runner = Mock(return_value=Mock(returncode=0))
        self.assertEqual(self.select(runner, 'software'), 'software')
        self.assertEqual(runner.call_count, 1)

    def test_both_failed_is_actionable(self):
        with self.assertRaisesRegex(RuntimeError, 'Diagnóstico:'):
            self.select(Mock(return_value=Mock(returncode=1)))

    def test_missing_software_driver_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(graphics.os.environ):
            with self.assertRaisesRegex(RuntimeError, 'Reinstale'):
                graphics.configure('software', folder)


if __name__ == '__main__':
    unittest.main()
