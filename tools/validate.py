"""Integration packaging checks plus existing original-Mono regressions; no game process."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from manifest import CSC, GAME, HERE, MONO, OLD_PLUGINS, PERSON, UI_PAYLOAD, WORK, references

RUNS: list[dict[str, object]] = []
TEST = HERE / "test_runtime"
MEMORY = HERE / "VaM.Memory.dll"
NEW_UI = HERE / "ui_build/Quest3TriggerUI_payload_v1005MemoryExternal.dll"
if not NEW_UI.exists():
    # The one-time UI migration artifact can be cleaned after deployment.
    NEW_UI = UI_PAYLOAD


def run(argv: list[object], label: str, inputs: str) -> str:
    args = list(map(str, argv))
    p = subprocess.run(args, cwd=TEST, capture_output=True, timeout=180,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8", "PERSON_PREPARED_PYTHON": sys.executable})
    codec = "mbcs" if Path(args[0]).name.lower() == "csc.exe" else "utf-8"
    output = p.stdout.decode(codec, "replace")
    errors = p.stderr.decode(codec, "replace")
    row = dict(stage=label, command=subprocess.list2cmdline(args), cwd=str(TEST), input=inputs,
               stdout=output, stderr=errors, exitStatus=p.returncode)
    RUNS.append(row)
    (HERE / "EXECUTION.json").write_text(json.dumps(RUNS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output, end="", flush=True)
    if errors:
        print(errors, end="", file=sys.stderr, flush=True)
    if p.returncode or "Unhandled Exception:" in output + errors:
        raise RuntimeError(label + " exit=" + str(p.returncode))
    return output


def compile_test(name: str, sources: list[Path], extra: list[str] | None = None) -> Path:
    exe = TEST / (name + ".exe")
    args = [str(CSC), "/nologo", "/noconfig", "/nostdlib+", "/unsafe+", "/optimize+", "/out:" + str(exe)]
    args += ["/reference:" + str(p) for p in references()]
    args += extra or []
    run(args + list(map(str, sources)), "COMPILE_" + name, "Actual game reference assemblies; fixtures remain in helper only")
    return exe


def mono(exe: Path, args: list[object], label: str, inputs: str) -> str:
    return run([sys.executable, MONO, exe, *args], label, inputs)


def layout(mode: str) -> Path:
    root = HERE / ("layout_" + mode)
    if mode != "modified":
        with zipfile.ZipFile(HERE / "BASELINE.zip") as archive:
            for name in archive.namelist():
                if name.startswith("BepInEx/plugins/"):
                    path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(archive.read(name))
    else:
        target = root / "BepInEx/plugins/VaMMemory/VaM.Memory.dll"
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(MEMORY, target)
        target = root / "BepInEx/plugins/Quest3TriggerUI/Quest3TriggerUI.payload.dll.disabled"
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(NEW_UI, target)
    return root


def prepare() -> None:
    TEST.mkdir(exist_ok=True)
    for name in ("UnityEngine.CoreModule.dll", "UnityEngine.AssetBundleModule.dll"):
        shutil.copyfile(WORK / "scene_prefab_presence_fix_20261002" / name, TEST / name)
    shutil.copyfile(MEMORY, TEST / "VaM.Memory.dll")
    shutil.copyfile(GAME / "BepInEx/core/Mono.Cecil.dll", TEST / "Mono.Cecil.dll")


def main() -> None:
    mode = sys.argv[1]
    prepare()
    audit = compile_test("LayoutProbe", [HERE / "tests/LayoutProbe.cs"], ["/reference:" + str(TEST / "Mono.Cecil.dll")])
    root = layout(mode)
    if mode == "rollback":
        # Restore another modified layout, never the deployed/main modified artifact.
        root = layout("modified")
        copy = HERE / "layout_rollback_copy"
        if copy.exists():
            # Reuse only this generated copy; verify old owned files before replacing them.
            with zipfile.ZipFile(HERE / "BASELINE.zip") as archive:
                for name in archive.namelist():
                    path = copy / name
                    if path.exists():
                        assert path.read_bytes() == archive.read(name), str(path)
            for name in OLD_PLUGINS:
                (copy / "BepInEx/plugins" / name).unlink(missing_ok=True)
            shutil.copytree(root, copy, dirs_exist_ok=True)
        else:
            shutil.copytree(root, copy)
        run([r"C:\Program Files\Git\bin\bash.exe", HERE / "ROLLBACK.sh", copy], "ROLLBACK_COMMAND", "Independent modified deployment-layout copy")
        root = copy
    layout_args = [mode, root, WORK / "Quest3TriggerUI工程/memory_modules.txt"]
    if mode == "modified":
        layout_args.append(layout("baseline") / "BepInEx/plugins/Quest3TriggerUI/Quest3TriggerUI.payload.dll.disabled")
    mono(audit, layout_args, mode.upper(), "Explicit six legacy plugins/UI versus single-DLL migration layout; all migrated implementations checked; original DLL install order preserved")
    if mode != "modified":
        (HERE / (mode.upper() + "_RESULT.json")).write_text(json.dumps(RUNS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    removed = compile_test("RemovedProbe", [HERE / "tests/RemovedProbe.cs"])
    # New process: does not load the unified assembly just because it exists beside the helper.
    mono(removed, [NEW_UI], "REMOVED_DLL", "Optional UI bridge without loading or referencing VaM.Memory")
    core = compile_test("UnifiedTests", [HERE / "tests/UnifiedTests.cs"], ["/reference:" + str(MEMORY)])
    mono(core, [TEST / "core"], "CORE", "67 existing settings, cross-generation UI detach, actual native staging, embedded helper extraction/repair")
    support = Path((TEST / "core/support-path.txt").read_text(encoding="utf-8"))
    runtime, tool = support / "python/python.exe", support / "bundle/MODIFIED_FILE.py"
    run([runtime, "-B", tool, "--help"], "BUNDLED_IMPORTS", "Relocated private runtime; imports fingerprint/unityfs/lz4 from embedded files")
    # Real original Person coroutines/pool/removal; native engine leaves simulated, unchanged tests.
    names = "IntegrationTests.cs NativeFixture.cs IoFixture.cs CoroutineFixture.cs FixtureAnchors.cs EntryFixture.cs".split()
    exe = compile_test("IntegrationTests", [PERSON / n for n in names], ["/define:UNIFIED", "/reference:" + str(MEMORY)])
    mono(exe, ["MODIFIED", MEMORY, "Quest3TriggerUI"], "PERSON_INTEGRATION", "Same production DLL supplies previous patches AND Person runtime; no old DLL loaded")
    exe = compile_test("LifecycleTests", [PERSON / "LifecycleTests.cs", PERSON / "NativeFixture.cs"], ["/define:OWNED", "/reference:" + str(MEMORY)])
    for value in ("MODIFIED", "FAULT", "BULK_FAULT"):
        mono(exe, [value], "PERSON_" + value, "Original pool/Remove/bulk, five real Mono threads; Unity destruction simulated")
    cua_source = (WORK / "cua_preload_lease_20261003/ColdTests.cs").read_text(encoding="utf-8-sig")
    # Fake native requests have no Unity native handle; their finalizer is a fixture leaf too.
    marker = 'var obj=FormatterServices.GetUninitializedObject(type);'
    if marker not in cua_source:
        raise RuntimeError("CUA fixture construction anchor changed")
    cua_source = cua_source.replace(marker, marker + 'if(obj is AsyncOperation)GC.SuppressFinalize(obj);', 1)
    cua_fixture = TEST / "ColdTests.cs"; cua_fixture.write_text(cua_source, encoding="utf-8-sig")
    exe = compile_test("UnifiedTests", [cua_fixture], ["/reference:" + str(MEMORY)])
    for order in ("FIRST", "LAST"):
        mono(exe, ["MODIFIED", order], "CUA_" + order, "Original cold request workers/callbacks and path-alias release; native IO leaves simulated")
    samples = TEST / "samples"; samples.mkdir(exist_ok=True)
    with zipfile.ZipFile(WORK / "morph_next_slice_review_20261005/VaM_Morph_NextSlice_Review_20261005.zip") as archive:
        for name in archive.namelist():
            if name.startswith("samples/vmi_fixture_line_") and name.endswith(".json"):
                (samples / Path(name).name).write_bytes(archive.read(name))
    review = WORK / "morph_fixed_lexeme_review_20261005"
    exe = compile_test("ReviewRunner", [review / "ReviewRunner.cs", review / "tests/RealMethodProbe.Net35.cs"], ["/reference:" + str(MEMORY)])
    for order in ("probe", "probe_reverse"):
        mono(exe, [order, MEMORY, samples], "MORPH_" + order, "Actual JSON.Parse/LoadMeta/Clone, same parent nodes, mutations, culture/escape/concurrency and unpatch restoration")
    # Converter/backend relocation: use a small, exact original UnityFS fixture, no game data modified.
    sys.path.insert(0, str(support / "bundle")); sys.path.insert(0, str(WORK / "bundle_disk_cache_20261004"))
    import fixtures
    game = TEST / "fixture_game"
    package = game / "AddonPackages/路径 空间/test.var"; package.parent.mkdir(parents=True, exist_ok=True)
    data = fixtures.bundle(bytes(range(256)) * 12288)
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Custom/Assets/test.assetbundle", data)
    exe = compile_test("PathTests", [WORK / "bundle_disk_cache_relative_path_20261004/PathTests.cs"])
    mono(exe, ["modified", MEMORY, runtime, tool, game, len(data)], "BUNDLE_RELOCATION", "Actual embedded runtime/converter and original backend; relative/absolute/Unicode/cwd/error paths")
    print("REGRESSION_PASS integratedDll=True oldPluginDependencies=0 gameLaunches=0")
    (HERE / "MODIFIED_RESULT.json").write_text(json.dumps(RUNS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
