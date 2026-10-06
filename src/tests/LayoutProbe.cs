using System;
using System.IO;
using System.Linq;
using Mono.Cecil;

internal static class LayoutProbe
{
    private static void Require(bool condition, string message)
    { if (!condition) throw new Exception(message); }
    private static bool MemoryInstaller(TypeDefinition type)
    {
        return type.FullName.EndsWith(".PackageJsonWeakRetention") || type.FullName.EndsWith(".ScenePrefabPresence") ||
            type.FullName.EndsWith(".TextureDecodeBudget") || type.FullName.EndsWith(".MorphTargetStringReuse");
    }
    private static void CheckInstallOrder(AssemblyDefinition memory, string[] names, string originalPath)
    {
        string[] moved = names.Where(n => n.Length > 0 && !n.StartsWith("#"))
            .Select(Path.GetFileNameWithoutExtension).ToArray();
        using (var original = AssemblyDefinition.ReadAssembly(originalPath))
        {
            var oldPlugin = original.MainModule.Types.Single(t => t.Name == "Quest3TriggerUIPlugin" && t.Namespace.StartsWith("Quest3TriggerUI.v"));
            var newPlugin = memory.MainModule.Types.Single(t => t.FullName == "VaM.Memory.MemoryPlugin");
            Func<MethodDefinition, string[]> installs = method => method.Body.Instructions
                .Select(i => i.Operand as MethodReference).Where(m => m != null && m.Name == "Install" && moved.Contains(m.DeclaringType.Name))
                .Select(m => m.DeclaringType.Name).ToArray();
            string[] before = installs(oldPlugin.Methods.Single(m => m.Name == "Awake"));
            string[] after = installs(newPlugin.Methods.Single(m => m.Name == "InstallModules"));
            Require(before.SequenceEqual(after), "original DLL install order changed");
            Console.WriteLine("INSTALL_PARITY_PASS modules=" + before.Length + " originalDll=True orderPreserved=True graftPreserved=" + before.Contains("GraftBoundaryTiles"));
        }
    }
    public static int Main(string[] args)
    {
        try
        {
            string mode = args[0], root = args[1];
            string folder = Path.Combine(root, "BepInEx/plugins");
            string[] active = Directory.GetFiles(folder, "*.dll", SearchOption.AllDirectories);
            bool unified = mode == "modified";
            Require(active.Length == (unified ? 1 : 6), "active memory DLL count");
            string uiPath = Path.Combine(folder, "Quest3TriggerUI/Quest3TriggerUI.payload.dll.disabled");
            using (var ui = AssemblyDefinition.ReadAssembly(uiPath))
            {
                int implementations = ui.MainModule.Types.Count(t => MemoryInstaller(t));
                Require(implementations == (unified ? 0 : 4), "old UI memory installers removed");
                Require(!ui.MainModule.AssemblyReferences.Any(r => r.Name == "VaM.Memory"), "UI has no mandatory memory dependency");
                string[] names = File.ReadAllLines(args[2]);
                if (unified)
                {
                    var plugin = ui.MainModule.Types.Single(t => t.Name == "Quest3TriggerUIPlugin" && t.Namespace.StartsWith("Quest3TriggerUI.v"));
                    foreach (var pair in new[] { new[] { "Awake", "Attach" }, new[] { "UpdateInner", "Tick" }, new[] { "OnDestroy", "Detach" } })
                        Require(plugin.Methods.Single(m => m.Name == pair[0]).Body.Instructions.Any(i =>
                            i.Operand is MethodReference && ((MethodReference)i.Operand).DeclaringType.Name == "MemoryRuntimeLink" &&
                            ((MethodReference)i.Operand).Name == pair[1]), "UI bridge lifecycle missing: " + pair[0]);
                    foreach (string name in names)
                    {
                        if (name.StartsWith("#") || name.Length == 0) continue;
                        string typeName = Path.GetFileNameWithoutExtension(name);
                        foreach (var type in ui.MainModule.Types.Where(t => t.Name == typeName))
                            Require(!type.Methods.Any(m => m.Name == "Install" || m.Name == "Shutdown"), "UI installer remains: " + typeName);
                    }
                }
                if (unified)
                {
                    using (var memory = AssemblyDefinition.ReadAssembly(active[0]))
                    {
                        Require(memory.Name.Name == "VaM.Memory", "stable assembly identity");
                        int plugins = memory.MainModule.Types.Count(t => t.CustomAttributes.Any(a => a.AttributeType.FullName == "BepInEx.BepInPlugin"));
                        Require(plugins == 1, "one BepInEx entry");
                        Require(memory.MainModule.Types.Count(MemoryInstaller) == 4, "all previous core implementations present");
                        Require(memory.MainModule.Resources.Count == 2, "embedded tools and index");
                        Require(!memory.MainModule.AssemblyReferences.Any(r => r.Name.Contains("PersonPrepared") || r.Name.Contains("PackageFixedLexemes") || r.Name.StartsWith("Quest3TriggerUI")), "no old DLL dependency");
                        foreach (string name in names)
                            if (!name.StartsWith("#") && name.Length > 0)
                            {
                                string[] expected = name == "SceneJsonStreamInput.cs" ? new[] { "BufferedChars", "Utf16Spool" } :
                                    name == "NativeRasterLease.cs" ? new[] { "NativeCacheBuffer" } : new[] { Path.GetFileNameWithoutExtension(name) };
                                foreach (string type in expected)
                                    Require(memory.MainModule.Types.Any(t => t.Name == type), "migrated module missing: " + type);
                            }
                        CheckInstallOrder(memory, names, args[3]);
                    }
                }
            }
            Console.WriteLine("LAYOUT_PASS mode=" + mode + " activeMemoryDlls=" + active.Length + " uiMemoryInstallers=" + (unified ? 0 : 4) +
                " standalone=" + (unified ? "True" : "False") + " exit=0");
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
