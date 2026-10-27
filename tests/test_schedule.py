import unittest
from unittest import mock

from aichivist import schedule
from helpers import SandboxTest


class ScheduleTest(SandboxTest):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(schedule.Path, "home", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.inbox = self.root / "Downloads"
        self.inbox.mkdir()

    def test_macos_writes_a_launch_agent_and_loads_it(self):
        planned = schedule.job([self.inbox], 25, "08:30", platform="darwin")
        ran = []

        schedule.install(planned, run=lambda c: ran.append(c) or 0)

        plist = self.root / "Library/LaunchAgents" / f"{schedule.LABEL}.plist"
        text = plist.read_text()
        self.assertIn("<integer>8</integer>", text)
        self.assertIn(f"<string>{self.inbox}</string>", text)
        self.assertEqual(ran[-1][:2], ["launchctl", "bootstrap"])

    def test_linux_writes_a_systemd_timer(self):
        planned = schedule.job([self.inbox], 25, "09:00", platform="linux")

        schedule.install(planned, run=lambda c: 0)

        timer = (self.root / ".config/systemd/user/aichivist-watch.timer").read_text()
        self.assertIn("OnCalendar=*-*-* 09:00:00", timer)

    def test_windows_uses_the_task_scheduler(self):
        planned = schedule.job([self.inbox], 25, "07:05", platform="win32")

        self.assertEqual(planned.files, {})
        self.assertIn("/ST", planned.commands[0])
        self.assertIn("07:05", planned.commands[0])

    def test_uninstall_removes_what_install_wrote(self):
        schedule.install(schedule.job([self.inbox], 25, "09:00", platform="linux"), run=lambda c: 0)

        schedule.uninstall(schedule.removal(platform="linux"), run=lambda c: 0)

        self.assertFalse((self.root / ".config/systemd/user/aichivist-watch.timer").exists())

    def test_failed_activation_is_reported(self):
        with self.assertRaises(OSError):
            schedule.install(schedule.job([self.inbox], 25, "09:00", platform="linux"), run=lambda c: 1)

    def test_wrong_time_is_rejected(self):
        with self.assertRaises(ValueError):
            schedule.job([self.inbox], 25, "9 am")


if __name__ == "__main__":
    unittest.main()
