using System;
using System.IO;
using System.Reflection;
using HarmonyLib;

internal static class RemovedProbe
{
    private const BindingFlags All = BindingFlags.Static | BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    public static int Main(string[] args)
    {
        try
        {
            Assembly ui = Assembly.Load(File.ReadAllBytes(args[0]));
            Type link = ui.GetType("Quest3TriggerUI.v1005MemoryExternal.MemoryRuntimeLink", true);
            object token = new object();
            link.GetMethod("Attach", All).Invoke(null, new[] { token });
            if (link.GetField("runtime", All).GetValue(null) != null) throw new Exception("removed runtime was loaded");
            foreach (string name in new[] { "PackageJsonWeakRetention", "ScenePrefabPresence", "TextureDecodeBudget", "MorphTargetStringReuse" })
                if (ui.GetType("Quest3TriggerUI.v1005MemoryExternal." + name) != null) throw new Exception("old implementation remains");
            link.GetMethod("Detach", All).Invoke(null, new[] { token });
            if (Harmony.GetAllPatchedMethods().GetEnumerator().MoveNext()) throw new Exception("UI bridge installed a patch without runtime");
            Console.WriteLine("REMOVAL_PASS optionalUiLoad=True memoryAssemblyLoaded=False memoryHooks=0 uiFallbackInstall=False");
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
