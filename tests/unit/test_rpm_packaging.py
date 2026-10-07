import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash") if os.name != "nt" else "C:/Program Files/Git/bin/bash.exe"
pytestmark = pytest.mark.skipif(not BASH or not Path(BASH).is_file(), reason="Bash required")


@pytest.mark.parametrize("distro,release,alt", [("alt", "alt1", "1"), ("generic", "1", "0")])
def test_real_build_script_passes_profile_to_rpmbuild(tmp_path, distro, release, alt):
    # Exercise orchestration with an existing bundle; rpmbuild is the only mocked build stage.
    commands = tmp_path / "commands"
    commands.mkdir()
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("certificate-analyzer", "certificate-analyzer-gui"):
        path = bundle / name
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
    mock = commands / "rpmbuild"
    mock.write_text('''#!/bin/bash
set -eu
top=""
while [ $# -gt 0 ]; do
  if [ "$1" = --define ]; then
    printf '%s\\n' "$2" >> "$RPM_TEST_LOG"
    case "$2" in "_topdir "*) top="${2#_topdir }" ;; esac
    shift 2
  else
    case "$1" in *.spec) test -f "$1" ;; esac
    shift
  fi
done
test -n "$top"
mkdir -p "$top/RPMS/x86_64"
printf 'test-package' > "$top/RPMS/x86_64/certificate-analyzer-test.rpm"
''', encoding="utf-8")
    mock.chmod(0o755)
    env = os.environ.copy()
    env["RPM_TEST_LOG"] = (tmp_path / "calls.txt").as_posix()
    env["TEST_COMMANDS"] = commands.as_posix()
    output = tmp_path / "output"
    result = subprocess.run(
        [BASH, "-c", 'if command -v cygpath >/dev/null; then TEST_COMMANDS="$(cygpath -u "$TEST_COMMANDS")"; fi; export PATH="$TEST_COMMANDS:$PATH"; exec bash "$@"', "rpm-test",
         "packaging/linux/build-rpm.sh", "--bundle-dir", bundle.as_posix(),
         "--version", "0.2.0", "--distro", distro, "--output-dir", output.as_posix()],
        cwd=PROJECT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    arguments = (tmp_path / "calls.txt").read_text()
    assert f"pkg_release {release}" in arguments
    assert f"altlinux {alt}" in arguments
    assert (output / "certificate-analyzer-test.rpm").read_bytes() == b"test-package"


def test_missing_bundle_argument_has_clear_error():
    result = subprocess.run([BASH, "packaging/linux/build-rpm.sh", "--bundle-dir"], cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert result.returncode != 0
    assert "требуется путь" in result.stderr
