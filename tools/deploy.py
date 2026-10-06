"""Install the tested single DLL and one-time UI bridge, preserving every existing setting."""
from __future__ import annotations

import configparser
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from manifest import GAME, HERE, LIVE, OLD_PLUGINS, UI_PAYLOAD, WORK


def config() -> None:
    target = GAME / "BepInEx/config/vam.memory.cfg"
    if target.exists():
        return
    old = configparser.ConfigParser(interpolation=None, strict=False)
    old.optionxform = str
    old.read(GAME / "BepInEx/config/local.vam.quest3-trigger-ui.cfg", encoding="utf-8-sig")
    new = configparser.ConfigParser(interpolation=None); new.optionxform = str
    code = (HERE / "generated/Settings.cs").read_text(encoding="utf-8-sig")
    matches = re.findall(r'\w+\.\w+\s*=\s*Bind(?:<[^>]+>)?\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*("(?:\\.|[^"\\])*"|[^,]+)\s*,', code)
    assert len(matches) == 67
    for section, key, default in matches:
        if not new.has_section(section):
            new.add_section(section)
        value = old.get(section, key, fallback=None)
        if value is None:
            default = default.strip()
            value = json.loads(default) if default.startswith('"') else default.removesuffix("f")
        new.set(section, key, value)
    for section, key, previous, previous_section in (
        ("Person", "PreparedOwnership", "vam.personprepared.integration.cfg", "Integration"),
        ("Morph", "FixedLexemes", "vam.package.fixedlexemes.cfg", "Optimization"),
    ):
        prior = configparser.ConfigParser(interpolation=None)
        prior.read(GAME / "BepInEx/config" / previous, encoding="utf-8-sig")
        new.add_section(section)
        new.set(section, key, prior.get(previous_section, "Enabled", fallback="true"))
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# Unified memory module settings, imported from the existing configuration.\n")
        new.write(stream)


def snapshot_list() -> list[str]:
    script = WORK / "版本管理/更新运行快照.ps1"
    original = script.read_text(encoding="utf-8-sig")
    removed = []
    lines = []
    prefixes = ["BepInEx\\plugins\\" + n.replace("/", "\\") for n in OLD_PLUGINS]
    prefixes += ["BepInEx\\plugins\\BundleDiskCache\\", "BepInEx\\BundleDiskCacheRuntime\\",
                 "BepInEx\\config\\vam.personprepared.integration.cfg", "BepInEx\\config\\vam.package.fixedlexemes.cfg"]
    for line in original.splitlines():
        value = line.strip().strip(",").strip("'")
        if any(value.startswith(prefix) for prefix in prefixes):
            removed.append(value)
        else:
            lines.append(line)
    marker = " 'BepInEx\\plugins\\Quest3TriggerUI\\Quest3TriggerUI.HotLoader.dll',"
    pos = lines.index(marker)
    additions = [" 'BepInEx\\plugins\\VaMMemory\\VaM.Memory.dll',", " 'BepInEx\\config\\vam.memory.cfg',"]
    if additions[0] not in lines:
        lines[pos:pos] = additions
    end = lines.index(")")
    lines[end - 1] = lines[end - 1].rstrip(",")
    script.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    # The snapshot is a runnable layout, not merely a manifest; remove known stale entries.
    base = (WORK / "运行快照").resolve()
    for name in removed:
        path = (base / name).resolve()
        assert path.is_relative_to(base)
        path.unlink(missing_ok=True)
    return removed


def main() -> None:
    for mode in ("BASELINE", "MODIFIED", "ROLLBACK"):
        rows = json.loads((HERE / (mode + "_RESULT.json")).read_text(encoding="utf-8"))
        assert rows and all(row["exitStatus"] == 0 and "Unhandled Exception:" not in row["stdout"] + row["stderr"] for row in rows)
    inputs = json.loads((HERE / "INPUT_HASHES.json").read_text(encoding="utf-8"))
    for path in [GAME / "BepInEx/plugins" / n for n in OLD_PLUGINS] + [UI_PAYLOAD]:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == inputs[path.relative_to(GAME).as_posix()], str(path)
    # The game was closed by the user. Do not launch it or write over loaded modules.
    result = subprocess.run(["powershell", "-NoProfile", "-Command", "if (Get-Process -Name VaM -ErrorAction SilentlyContinue) { exit 7 }"], capture_output=True)
    assert result.returncode == 0, "Game is still running"
    config()
    candidate = HERE / "MODIFIED_FILE.dll"
    assert candidate.read_bytes() == (HERE / "VaM.Memory.dll").read_bytes()
    LIVE.parent.mkdir(parents=True, exist_ok=True)
    staging = LIVE.with_suffix(".dll.new")
    shutil.copyfile(candidate, staging); staging.replace(LIVE)
    shutil.copyfile(HERE / "ui_build/Quest3TriggerUI_payload_v1005MemoryExternal.dll", UI_PAYLOAD)
    for name in OLD_PLUGINS:
        path = (GAME / "BepInEx/plugins" / name).resolve()
        assert path.is_relative_to(GAME.resolve())
        path.unlink()
    removed = snapshot_list()
    assert LIVE.read_bytes() == candidate.read_bytes()
    assert all(not (GAME / "BepInEx/plugins" / n).exists() for n in OLD_PLUGINS)
    row = dict(dll=str(LIVE), bytes=LIVE.stat().st_size, legacyDllsRemoved=6, uiVersion="4.6.302",
               configPreserved=True, snapshotEntriesRemoved=removed, gameStarted=False, startupPending=True)
    (HERE / "DEPLOYMENT.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("DEPLOY_PASS singleMemoryDll=True legacyDllsRemoved=6 uiMemoryEntrypointsRemoved=True configPreserved=True activation=nextStart")


if __name__ == "__main__":
    main()
