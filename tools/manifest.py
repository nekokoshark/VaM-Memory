"""Explicit migration inventory; canonical sources stay in their existing projects."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
GAME = WORK.parent
UI = WORK / "Quest3TriggerUI工程/plugin_sources"
CSC = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
MONO = WORK / "cold_start_gc_crash_20261002/mono_exec.py"
LIVE = GAME / "BepInEx/plugins/VaMMemory/VaM.Memory.dll"
MODULES = """
BodySmootherCompatibility ClothingScriptAssemblyReuse PackageJsonWeakRetention
MorphTargetStringReuse JointLifetimeRetirement AtomPoolHairRetirement
AssetCallbackRetirement AllocatedObjectRetirement FailedAssetOperationRetirement
CancelledBundleDependencyRetirement FailedDynamicBundleLeaseRetirement
InterruptedDynamicBundleRetirement CancelledCuaRequestRetirement SkinBlendTiled
DrawCameraArrayReuse GraftBoundaryTiles AudioEncodedStream AudioPcmChunks
LegacyMorphFilterStreaming SceneJsonRuntime DependencyErrorPropagation
ScenePrefabPresence ScenePreloadLease RefreshDelegateRetirement CatalogueActionRetention
PresetDeltaApply PresetHairRenderBatch PresetSweepGate TextureUploadReuse TextureInFlight
TextureCompletionBudget TextureMetadataReuse TextureScratchLifetime TextureCacheWriteBudget
TextureCacheBc7Convert AudioCacheJanitor WardrobeJanitor ColdRasterDecode SceneOrphanSweep
TextureDecodeBudget TextureOrphanSweeper BumpNormalRowConverter PresetCleanupCoalescer
PresetInstanceReuse StaleTextureRequestGuard DecodedBufferPool TextureCacheByteReuse
ColdTextureBufferLayout ColdRasterBump ColdTextureHeader NativeCacheBuffer InstanceAssetLedger
GpuPhysicsRetentionProbe GpuResourceProbe MeshOwnerRetentionProbe MemoryRetentionReport
MemoryProbe MonoGcProbe Bc7CacheCompatibility Bc7CacheLoadCompatibility SkinBlendByteInputs
SoftBodySkinReuse TextureCacheStreamIO MorphFilterMethodAudit JsonStreamParser SceneJsonStreamInput
PathReplacementStream DelegateSnapshot NativeRasterLease TextureCacheEstimate UuaGate UuaTypeCensus
CatalogueRetirement LoadWindow TextureStagingArena TextureStagingLease
""".split()
PERSON = WORK / "person_prepared_adapter_20261005/integrated_runtime"
PERSON_FILES = """
MODIFIED_FILE.cs StableDrain.Net35.cs OriginalBackend.cs ReturnWitness.cs RegistrationProbe.cs
BulkJournal.cs LifecycleHooks.cs BundleReceipts.cs AsyncWork.cs PlanRegistry.cs PlanHooks.cs
SceneHooks.cs RuntimeControl.cs
""".split()
OLD_PLUGINS = [
    "VarEntryLazyFlags/VarEntryLazyFlags.dll",
    "CuaPreloadLease/CuaPreloadLease.dll",
    "ScriptCompilerTransientCleanup/ScriptCompilerTransientCleanup.dll",
    "BundleDiskCache/BundleDiskCache.dll",
    "PersonPreparedPreview/PersonPrepared.Lifecycle.dll",
    "PackageFixedLexemes/PackageFixedLexemes.dll",
]
UI_PAYLOAD = GAME / "BepInEx/plugins/Quest3TriggerUI/Quest3TriggerUI.payload.dll.disabled"


def references() -> list[Path]:
    names = """mscorlib System System.Core System.Drawing Assembly-CSharp mcs Bass.Net ICSharpCode.SharpZipLib
    UnityEngine UnityEngine.CoreModule UnityEngine.UI UnityEngine.UIModule
    UnityEngine.TextRenderingModule UnityEngine.AudioModule UnityEngine.AssetBundleModule
    UnityEngine.ImageConversionModule UnityEngine.IMGUIModule UnityEngine.InputModule
    UnityEngine.VRModule UnityEngine.PhysicsModule UnityEngine.AnimationModule
    UnityEngine.UnityWebRequestWWWModule UnityEngine.UnityWebRequestModule""".split()
    return [GAME / "VaM_Data/Managed" / (n + ".dll") for n in names] + [
        GAME / "BepInEx/core" / n for n in ("BepInEx.dll", "0Harmony.dll")]
