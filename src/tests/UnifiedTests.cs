using System;
using System.IO;
using System.Reflection;
using System.Runtime.Serialization;
using BepInEx;
using BepInEx.Configuration;
using Quest3TriggerUI;
using VaM.Memory;

internal static class UnifiedTests
{
    private const BindingFlags All = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance;
    private static int checks;
    private static void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
    private static void Settings(string root)
    {
        string previousPath = Path.Combine(root, "legacy.cfg"), nextPath = Path.Combine(root, "memory.cfg");
        if (File.Exists(nextPath)) File.Delete(nextPath);
        string text = "[TextureLoading]\nDecodeBudgetMiB = 3073\nNativeCacheReadBuffers = false\n[PresetLoading]\nHandSwapGCToIdle = false\n";
        File.WriteAllText(previousPath, text);
        var previous = new ConfigFile(previousPath, false); previous.SaveOnConfigSet = false;
        var next = new ConfigFile(nextPath, false); next.SaveOnConfigSet = false;
        var plugin = (MemoryPlugin)FormatterServices.GetUninitializedObject(typeof(MemoryPlugin));
        typeof(BaseUnityPlugin).GetField("<Config>k__BackingField", All).SetValue(plugin, next);
        typeof(MemoryPlugin).GetField("legacy", All).SetValue(plugin, previous);
        typeof(MemoryPlugin).GetMethod("BindModules", All).Invoke(plugin, null);
        Check(TextureDecodeBudget.BudgetMiB.Value == 3073, "configured budget preserved");
        Check(!NativeCacheBuffer.Enabled.Value && !PresetSweepGate.SwapGcToIdle.Value, "false settings and GC policy preserved");
        Check(File.ReadAllText(previousPath) == text, "legacy config not rewritten");
        Check(next.Count == 67, "all original memory settings migrated");
        TextureDecodeBudget.BudgetMiB.Value = 2027;
        typeof(MemoryPlugin).GetMethod("BindModules", All).Invoke(plugin, null);
        Check(TextureDecodeBudget.BudgetMiB.Value == 2027, "unified user value wins on next bind");
        next.Save();
    }
    private static void Bridge()
    {
        object a = new object(), b = new object();
        UiBridge.Attach(a, () => true, () => true, () => { });
        Check(UiBridge.SceneActive && UiBridge.VrActivity, "UI state delegated");
        UiBridge.Attach(b, () => false, () => false, () => { });
        UiBridge.Detach(a);
        Check(!UiBridge.SceneActive && typeof(UiBridge).GetField("owner", All).GetValue(null) == b, "old UI tail cannot detach new generation");
        UiBridge.Detach(b);
        Check(typeof(UiBridge).GetField("owner", All).GetValue(null) == null && TextureCacheEstimate.Probe == null, "UI roots cleared on detach");
    }
    private static void Buffers(string root)
    {
        var config = new ConfigFile(Path.Combine(root, "buffers.cfg"), false); config.SaveOnConfigSet = false;
        NativeCacheBuffer.Enabled = config.Bind("Test", "Enabled", true);
        NativeCacheBuffer.BudgetMiB = config.Bind("Test", "Budget", 128);
        NativeCacheBuffer.IdleMiB = config.Bind("Test", "Idle", 64);
        NativeCacheBuffer.MaxFileMiB = config.Bind("Test", "Max", 512);
        string file = Path.Combine(root, "large.cache");
        using (var stream = File.Create(file)) { stream.SetLength(17 * 1048576); stream.WriteByte(71); }
        var request = new ImageLoaderThreaded.QueuedImage();
        Check(NativeCacheBuffer.TryStage(request, file), "large native staging uses actual file");
        Check(NativeCacheBuffer.StagedLength(request) == 17 * 1048576, "native length preserved");
        NativeCacheBuffer.Release(request);
        Check((long)typeof(NativeCacheBuffer).GetField("_liveBytes", All).GetValue(null) == 0 &&
            (long)typeof(NativeCacheBuffer).GetField("_idleBytes", All).GetValue(null) == 0, "large native buffer leaves no idle capacity");
        File.Delete(file);
    }
    public static int Main(string[] args)
    {
        try
        {
            typeof(Paths).GetMethod("SetExecutablePath", All).Invoke(null, new object[] {
                Path.Combine(args[0], "VaM.exe"), Path.Combine(args[0], "BepInEx"), Path.Combine(args[0], "VaM_Data/Managed") });
            Directory.CreateDirectory(args[0]); Settings(args[0]); Bridge(); Buffers(args[0]);
            string support = SupportFiles.Extract(Path.Combine(args[0], "support"));
            string python = Path.Combine(support, "python/python.exe");
            Check(File.Exists(python) && File.ReadAllText(Path.Combine(support, "python/python312._pth")).Contains("../bundle"), "relocated Python imports its bundled tools");
            DateTime stamp = File.GetLastWriteTimeUtc(python);
            Check(SupportFiles.Extract(Path.Combine(args[0], "support")) == support && File.GetLastWriteTimeUtc(python) == stamp, "second start does not unpack again");
            string repair = Path.Combine(support, "bundle/fingerprint.py"); File.Delete(repair);
            SupportFiles.Extract(Path.Combine(args[0], "support"));
            Check(File.Exists(repair), "missing support repaired from single DLL");
            File.WriteAllText(Path.Combine(args[0], "support-path.txt"), support);
            Console.WriteLine("UNIFIED_CORE_PASS settings=67 configPreserved=True uiGenerationIsolation=True nativeBufferReturn=True toolsSelfContained=True checks=" + checks);
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
