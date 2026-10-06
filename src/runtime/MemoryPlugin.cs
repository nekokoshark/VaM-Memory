using System;
using System.IO;
using BepInEx;
using BepInEx.Configuration;
using Quest3TriggerUI;
using VaM.PersonPrepared.Runtime;
using VaM.MorphFixedLexemes;

namespace VaM.Memory
{
    [BepInPlugin("vam.memory", "VaM Memory", "1.5.0")]
    public sealed partial class MemoryPlugin : BaseUnityPlugin
    {
        private ConfigFile legacy;
        private bool started, person;
        private int startupFailures;
        private long reportAt;
        private string lastPerson;

        private ConfigEntry<T> Bind<T>(string section, string key, T value, string description)
        {
            T inherited = legacy.Bind<T>(section, key, value, description).Value;
            return Config.Bind<T>(section, key, inherited, description);
        }

        private bool ExistingSwitch(string path, string section, bool value)
        {
            var old = new ConfigFile(Path.Combine(Paths.ConfigPath, path), false);
            old.SaveOnConfigSet = false;
            return old.Bind<bool>(section, "Enabled", value).Value;
        }

        private void Awake()
        {
            // Process lifetime: disk updates/removal become effective only on the next start.
            Quest3TriggerUIPlugin.Instance = this;
            Quest3TriggerUIPlugin.Log = Logger;
            legacy = new ConfigFile(Path.Combine(Paths.ConfigPath, "local.vam.quest3-trigger-ui.cfg"), false);
            legacy.SaveOnConfigSet = false;
            BindModules();
            legacy = null;
            InstallModule("VarEntryLazyFlags", VarEntryLazyFlags.Install);
            ScriptCompilerCleanup.Feature.Logger = message => Logger.LogInfo(message);
            InstallModule("ScriptCompilerCleanup", ScriptCompilerCleanup.Feature.Install);
            CuaPreloadFix.Feature.Logger = message => Logger.LogInfo(message);
            InstallModule("CuaPreloadLease", CuaPreloadFix.Feature.Install);
            InstallModules();
            if (Config.Bind("ResourceLifetime", "EventRootRetirement", true, "Retire exact destroyed-instance descriptor roots after explicit unload.").Value)
                InstallModule("InstanceRootRetirement", InstanceRootRetirement.Install);
            if (Config.Bind("ResourceLifetime", "PresetOwnerRetirement", true, "Retire destroyed instance registrations from preset-owned lists and indexes.").Value)
                InstallModule("PresetOwnerRetirement", PresetOwnerRetirement.Install);
            InstallModule("BundleDiskCache", delegate
            {
                string support = SupportFiles.Extract(Path.Combine(Paths.BepInExRootPath, "cache/VaMMemory/support"));
                VamBundleDiskCache.Backend.Configure(Path.Combine(support, "python/python.exe"),
                    Path.Combine(support, "bundle/MODIFIED_FILE.py"), Path.Combine(Paths.BepInExRootPath, "cache/BundleDiskCache"));
                VamBundleDiskCache.Feature.Logger = message => Logger.LogInfo(message);
                VamBundleDiskCache.Feature.Install();
            });
            if (Config.Bind("Compiler", "IsolatedWorker", true, "Compile scripts in a bounded original-Mono worker; effective next startup.").Value)
                InstallModule("CompilerWorker", delegate
                {
                    CompilerRuntime.Install(Config.Bind("Compiler", "BytecodeCache", true, "Cache code templates, preserving distinct loaded assemblies/statics.").Value,
                        Config.Bind("Compiler", "WorkerBudgetMiB", 256, "Worker private-memory soft budget; 128 to 512 MiB, checked after each request.").Value,
                        message => Logger.LogInfo(message));
                });
            if (Config.Bind("Morph", "FixedLexemes", ExistingSwitch("vam.package.fixedlexemes.cfg", "Optimization", true), "Reuse fixed Morph JSON tokens.").Value)
                InstallModule("FixedLexemes", PackageFixedLexemePatch.Install);
            if (Config.Bind("Person", "PreparedOwnership", ExistingSwitch("vam.personprepared.integration.cfg", "Integration", true), "Transfer prepared Person acquisitions to the real Atom.").Value)
            {
                InstallModule("PersonPrepared", delegate
                { RuntimeControl.InstallForIntegration(); RuntimeControl.OpenForIntegration(); person = true; });
            }
            if (Config.Bind("Reclamation", "LoadTailTransactions", true,
                "Coalesce automatic cleanup after consumers/writers/retirement drain; no long-idle handoff. Effective next startup.").Value)
                InstallModule("LoadReclamation", LoadReclamation.Install);
            started = true;
            Logger.LogInfo("[vam-memory] active version=1.5.0 entry=single lifetime=process config=preserved uninstall=nextStart startupFailures=" + startupFailures);
        }

        private void InstallModule(string name, Action action)
        {
            try { action(); }
            catch (Exception error)
            {
                startupFailures++;
                Logger.LogError("[vam-memory] module=" + name + " startup failed: " + error);
            }
        }

        private void Update()
        {
            if (!started) return;
            TickModules();
            InstanceRootRetirement.Tick();
            PresetOwnerRetirement.Tick();
            if (UnityEngine.Time.frameCount % 300 == 0) VamBundleDiskCache.Feature.Sweep();
            if (person) RuntimeControl.Pump();
            LoadReclamation.Tick();
            if (!person) return;
            long now = DateTime.UtcNow.Ticks;
            if (now < reportAt) return;
            reportAt = now + TimeSpan.TicksPerSecond * 5;
            string snapshot = RuntimeControl.Snapshot();
            if (snapshot == lastPerson) return;
            lastPerson = snapshot;
            Logger.LogInfo("[PersonPrepared] " + snapshot);
        }

        private void OnApplicationQuit()
        {
            if (!started) return;
            LoadReclamation.Stop();
            MaterialTextureIntent.StopAccepting();
            TextureCacheBc7Convert.OnExit();
            VamBundleDiskCache.Backend.Stop();
            CompilerRuntime.Stop();
            if (person) RuntimeControl.CloseEntry();
        }
    }
}
