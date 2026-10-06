"""Build a single cold-start assembly against the actual game .NET 3.5 profile."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

from manifest import CSC, GAME, HERE, MODULES, OLD_PLUGINS, PERSON, PERSON_FILES, UI, UI_PAYLOAD, WORK, references


def run(argv: list[str], log: Path) -> None:
    p = subprocess.run(argv, capture_output=True, timeout=180)
    output = p.stdout.decode("mbcs", "replace") + p.stderr.decode("mbcs", "replace")
    print(output, end="", flush=True)
    log.write_text(output, encoding="utf-8")
    if p.returncode:
        raise RuntimeError(f"compiler exit={p.returncode}")


def baseline() -> None:
    target = HERE / "BASELINE.zip"
    if target.exists():
        return
    paths = [GAME / "BepInEx/plugins" / n for n in OLD_PLUGINS] + [UI_PAYLOAD,
        UI / "Quest3TriggerUI.cs", WORK / "Quest3TriggerUI工程/build_payload.py",
        WORK / "版本管理/更新运行快照.ps1"]
    hashes = {}
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            name = path.relative_to(GAME).as_posix()
            data = path.read_bytes()
            archive.writestr(name, data)
            hashes[name] = hashlib.sha256(data).hexdigest()
    (HERE / "INPUT_HASHES.json").write_text(json.dumps(hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert all(hashlib.sha256(archive.read(n)).hexdigest() == h for n, h in hashes.items())


def support() -> tuple[Path, str]:
    pack = HERE / "support.bin.gz"
    # Frozen input allows future DLL-only builds without the old deployment directories.
    if pack.exists() and (HERE / "support.index").exists() and "--refresh-support" not in sys.argv:
        return pack, hashlib.sha256(pack.read_bytes()).hexdigest()[:16]
    files: dict[str, bytes] = {}
    plugin = GAME / "BepInEx/plugins/BundleDiskCache"
    deployed = json.loads((plugin / "DEPLOYED_MANIFEST.json").read_text(encoding="utf-8-sig"))
    for name in deployed:
        if name == "BundleDiskCache.dll" or "MANIFEST" in name:
            continue
        path = (plugin / name).resolve()
        if name.startswith("../../BundleDiskCacheRuntime/"):
            key = "python/" + name.removeprefix("../../BundleDiskCacheRuntime/")
        else:
            key = "bundle/" + name.replace("\\", "/")
        files[key] = path.read_bytes()
    for name in ("bc7_pending_convert.ps1", "Bc7Compat.exe"):
        files["bc7/" + name] = (GAME / "BepInEx/plugins/Quest3TriggerUI" / name).read_bytes()
    files["python/python312._pth"] = b"python312.zip\nDLLs\n.\n../bundle\n"
    with pack.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as output:
            output.write(struct.pack("<i", len(files)))
            for name, data in sorted(files.items()):
                encoded = name.encode("utf-8")
                output.write(struct.pack("<i", len(encoded)))
                output.write(encoded)
                output.write(struct.pack("<i", len(data)))
                output.write(data)
    (HERE / "SUPPORT.json").write_text(json.dumps({k: len(v) for k, v in files.items()}, indent=2) + "\n")
    (HERE / "support.index").write_text("\n".join(k + "|" + str(len(v)) for k, v in sorted(files.items())), encoding="utf-8")
    return pack, hashlib.sha256(pack.read_bytes()).hexdigest()[:16]


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")
    return path


def settings() -> str:
    with zipfile.ZipFile(HERE / "BASELINE.zip") as archive:
        s = archive.read("工作区/Quest3TriggerUI工程/plugin_sources/Quest3TriggerUI.cs").decode("utf-8-sig")
    # Entire assignment statements, not individual lines: descriptions contain semicolons.
    pattern = r'\b(\w+)\.(\w+)\s*=\s*Config\.Bind(?:<[^>]+>)?\((?:"(?:\\.|[^"\\])*"|[^;"])*\);'
    rows = [m.group(0) for m in re.finditer(pattern, s) if m.group(1) in MODULES]
    if len(rows) != 67:
        raise RuntimeError("Memory config assignment count changed: " + str(len(rows)))
    return "\n".join(rows).replace("Config.Bind", "Bind")


def main() -> None:
    baseline()
    pack, stamp = support()
    output = HERE
    if "--output-dir" in sys.argv:
        output = Path(sys.argv[sys.argv.index("--output-dir") + 1]).resolve()
        if not output.is_relative_to(WORK.resolve()):
            raise ValueError("Build output must stay in the workspace")
    output.mkdir(parents=True, exist_ok=True)
    generated = output / "generated"
    sources = []
    for name in MODULES:
        text = (UI / (name + ".cs")).read_text(encoding="utf-8-sig")
        if name == "TextureCacheBc7Convert":
            text = text.replace('Path.Combine(Path.Combine(BepInEx.Paths.PluginPath, "Quest3TriggerUI"), "bc7_pending_convert.ps1")',
                                'Path.Combine(VaM.Memory.SupportFiles.Directory, "bc7/bc7_pending_convert.ps1")')
        sources.append(write(generated / (name + ".cs"), text))
    for name in PERSON_FILES:
        sources.append(PERSON / name)
    sources += [PERSON.parent / "external_v2/PreparedUnitProtocol.Net35.cs"]
    sources += [WORK / "morph_fixed_lexeme_review_20261005/src" / n for n in
                ("FixedMorphLexemes.Net35.cs", "PackageFixedLexemePatch.Net35.cs")]
    sources += [WORK / "cua_preload_lease_20261003/MODIFIED_FILE.cs",
                WORK / "var_entry_lazy_flags/MODIFIED_FILE.cs",
                WORK / "bundle_disk_cache_20261004/BundleDiskCache.cs",
                WORK / "bundle_disk_cache_relative_path_20261004/MODIFIED_FILE.cs"]
    compiler = (WORK / "script_compiler_cleanup_20261003/MODIFIED_FILE.cs").read_text(encoding="utf-8-sig")
    compiler = compiler[:compiler.index("    [BepInPlugin(")] + "}\n"
    sources.append(write(generated / "ScriptCompilerCleanup.cs", compiler))
    config = "using BepInEx.Configuration;\nusing Quest3TriggerUI;\nnamespace VaM.Memory { public sealed partial class MemoryPlugin { private void BindModules() {\n"
    config += settings() + "\n} } }\n"
    sources.append(write(generated / "Settings.cs", config))
    sources.append(write(generated / "AssemblyInfo.cs", 'using System.Reflection;\nusing System.Runtime.CompilerServices;\n'
        '[assembly: AssemblyVersion("1.5.0.0")]\n[assembly: InternalsVisibleTo("LifecycleTests")]\n'
        '[assembly: InternalsVisibleTo("IntegrationTests")]\n[assembly: InternalsVisibleTo("UnifiedTests")]\n'
        'namespace VaM.Memory { public static class BuildInfo { public const string SupportVersion = "' + stamp + '"; } }\n'))
    sources += sorted((HERE / "runtime").glob("*.cs"))
    compiler_worker = WORK / "compiler_cached_worker_20261006"
    # This remains a single installed DLL; the executable is an inert embedded resource.
    run([sys.executable, str(compiler_worker / "validate.py"), "build"], output / "COMPILER_BUILD.log")
    sources += [compiler_worker / name for name in ("CompilerProtocol.cs", "CompilerService.cs", "CompilerHooks.cs")]
    dll = output / "VaM.Memory.dll"
    args = [str(CSC), "/nologo", "/nostdlib+", "/unsafe+", "/optimize+", "/target:library",
            "/out:" + str(dll), "/resource:" + str(pack) + ",VaM.Memory.Support",
            "/resource:" + str(HERE / "support.index") + ",VaM.Memory.SupportIndex"]
    args += ["/resource:" + str(compiler_worker / "VaM.CompilerWorker.exe") + ",VaM.Memory.CompilerWorker",
             "/resource:" + str(compiler_worker / "worker_runner.py") + ",VaM.Memory.CompilerRunner"]
    args += ["/reference:" + str(p) for p in references()]
    args += [str(p) for p in sources]
    rsp = output / "build.rsp"
    rsp.write_text("\n".join('"' + a + '"' for a in args[1:]), encoding="utf-8-sig")
    run([str(CSC), "/noconfig", "@" + str(rsp)], output / "BUILD.log")
    (output / "MODIFIED_FILE.dll").write_bytes(dll.read_bytes())
    print(f"BUILD_PASS dll={dll.name} modules={len(MODULES)} bytes={dll.stat().st_size} profile=VaMNet35")


if __name__ == "__main__":
    main()
