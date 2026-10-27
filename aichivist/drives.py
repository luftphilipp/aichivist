"""Drive health via SMART (smartctl, all systems) or macOS diskutil – best effort. No data never counts as healthy."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple, Optional

SMART_TIMEOUT = 30  # seconds; USB bridges can be slow to answer


class DriveHealth(NamedTuple):
    status: str  # "passed", "failed" or "unknown"
    detail: str
    device: Optional[str] = None
    power_on_hours: Optional[int] = None
    temperature: Optional[int] = None


UNKNOWN = DriveHealth("unknown", "not checked")


def device_for(path: Path) -> Optional[str]:
    """The block device a path lives on (macOS/Linux, via df); None on Windows or when it cannot be found."""
    if sys.platform.startswith("win"):
        return None
    try:
        out = subprocess.run(["df", "-P", str(path)], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    lines = out.strip().splitlines()
    device = lines[1].split()[0] if len(lines) > 1 else ""
    return device if device.startswith("/dev/") else None


def whole_disk(device: str) -> str:
    """Partition → physical disk: /dev/disk4s2 → /dev/disk4, /dev/sda1 → /dev/sda, /dev/nvme0n1p2 → /dev/nvme0n1."""
    for pattern in (r"^(/dev/disk\d+)", r"^(/dev/nvme\d+n\d+)", r"^(/dev/[a-z]+?)\d*$"):
        match = re.match(pattern, device)
        if match:
            return match.group(1)
    return device


def _diskutil_status(disk: str) -> Optional[str]:
    if sys.platform != "darwin" or not shutil.which("diskutil"):
        return None
    try:
        out = subprocess.run(["diskutil", "info", disk], capture_output=True, text=True, timeout=SMART_TIMEOUT).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"SMART Status:\s*(.+)", out)
    return match.group(1).strip() if match else None


def _smartctl(disk: str) -> Optional[DriveHealth]:
    try:
        done = subprocess.run(["smartctl", "-j", "-H", "-A", disk], capture_output=True, text=True,
                              timeout=SMART_TIMEOUT)
        data = json.loads(done.stdout or "{}")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None
    passed = data.get("smart_status", {}).get("passed")
    if passed is None:
        return None
    return DriveHealth("passed" if passed else "failed", "SMART (smartctl)", disk,
                       data.get("power_on_time", {}).get("hours"), data.get("temperature", {}).get("current"))


def health(path: Path) -> DriveHealth:
    device = device_for(path)
    disk = whole_disk(device) if device else None
    if disk and shutil.which("smartctl"):
        result = _smartctl(disk)
        if result:
            return result
        return DriveHealth("unknown", "smartctl got no data (needs admin rights, or the USB enclosure blocks SMART)",
                           disk)
    verdict = _diskutil_status(disk) if disk else None
    if verdict in ("Verified", "Failing"):
        return DriveHealth("passed" if verdict == "Verified" else "failed", f"diskutil: {verdict}", disk)
    return DriveHealth("unknown", "install smartmontools (smartctl) to read drive health", disk)
