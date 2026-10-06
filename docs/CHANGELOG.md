# VaM Memory 1.2.0：单 DLL 内存补丁

## 1.2.0 预设缓存所有者退出（2026-10-06）

用户短测 1.1.0 无明显异常，但反复换人/场景仍涨内存。本版沿所有权退休路线继续处理：原动态实例成功卸载、旧 Transform 实际销毁后，定位其所在 Atom 已注册的预设管理器，移除五个私有缓存列表及 `regularStorables` 索引中已经销毁的组件记录。旧缓存不再拖住旧衣发/皮肤/网格的大数组；不改借用记录及数组内容，活记录的顺序、身份和预设保存内容保持。

不做每帧全库扫描；有卸载事件才检查相关 Atom。预设保存、加载和锁操作的同步使用栈未退出时延后处理，异常终态恢复使用门槛。原 Destroy、Bundle 计数、人物池、画质和 GC 策略保持。模块默认启用 `ResourceLifetime/PresetOwnerRetirement=true`；更新仍只覆盖唯一 DLL，下次自然启动生效。

原 .NET 3.5 引用编译及原 Mono 原方法测试通过，两种既有补丁安装顺序均覆盖延期销毁、重入、缓存换代、借用记录、活内容、异常与线程边界；副本回滚及卸钩恢复原行为。128 个合成真实类型图的预设根链载荷 537600000→0→537600000 B，待处理队列归零。**该数字不是游戏物理内存下降**；实机增长斜率仍待观察。本轮命令与证据在 `../preset_cache_lifetime_20261006/VERIFICATION.txt`。

## 1.1.0 实例退出撤根（2026-10-06）

成功执行原 `JSONStorableDynamic.UnloadInstance` 后，弱事件队列等待旧 Unity 对象实际销毁，再撤去服装/头发描述符的旧控制器数组引用及人物的两处旧皮肤引用。它切断“描述符→旧控制器/预设列表→旧皮肤/网格→大数组”根链，不再靠全库分页扫描等待；不修改数组内容，不额外 Destroy、不减 Bundle、不主动 GC，不接管人物归池或临时禁用。

原 Mono 调用原游戏卸载方法的定向验证通过：两种既有补丁安装顺序覆盖延迟死亡、部分存活、重载/字段换代、原方法异常、锁与借用数组及非主线程调用，现有清理债务仍正常累积。32 实例夹具的被留住数组载荷为 134400000→0 B，副本回滚恢复 134400000 B；该数字不是 VaM 实测物理下降。新服务待处理队列回到零。

本轮已覆盖同一 DLL，下次自然启动默认启用 `ResourceLifetime/EventRootRetirement=true`；现有配置保持原字节。用户照常做 LDR/Westo 短功能往返即可，检查外观、衣发、锁和预设。命令/原始输出及本轮四工件在 `../dynamic_exit_roots_20261005/VERIFICATION.txt`；1.0.0 整合原始工件保持不变。

## 使用

唯一启用文件：`F:\vam1.22.0.12\BepInEx\plugins\VaMMemory\VaM.Memory.dll`。

- 安装：放入这个 DLL，正常启动游戏。
- 卸载：退出游戏，把 DLL 移到 `BepInEx/plugins` 之外，再启动。仅挪到 plugins 的其他子目录仍会被扫描。
- 更新：退出游戏，用新版覆盖这个 DLL，再启动。不要保留可扫描的旧版 DLL。
- 配置自动生成在 `BepInEx/config/vam.memory.cfg`；本次已导入原设置。移走 DLL 后，配置和磁盘缓存只保留数据，不会自己安装补丁。
- 既有 BepInEx、Harmony、游戏运行库继续使用；本次不改原 GC、画质、人物池策略或原生运行库。

## 本次整合

六个独立内存插件与 UI 载荷的内存实现进入同一个程序集、同一个 BepInEx 入口：PersonPrepared、Morph target/固定词元、包 JSON 批次租约、CUA/动态资产退休、纹理解码预算/缓冲复用、音频/资源退休、VAR 路径惰性字段、编译临时根清理和 Bundle 磁盘缓存。

UI 一次性升级至 4.6.302，仅保留可选桥接；内存模块的安装、更新与尾部处理不再随 UI 热更新重建。旧六个 DLL 已撤掉，旧 UI 不会在统一 DLL 缺席时重新安装内存补丁。以后内存重构只更新统一 DLL，UI 自身的功能更新仍用原流程。

74 个源码单元中包括配套工具/诊断与 partial 文件，不等于 74 个独立优化。未另加内存策略或承诺新的 MiB 收益。这轮解决安装、寿命和版本管理问题，保留原优化效果。

Bundle 转换器、私有 Python 和 BC7 收尾助手内置为资源，首次使用解到 `BepInEx/cache/VaMMemory/support/<版本>`。无需手动复制支持文件；复用完整支持目录，缺失文件从 DLL 恢复。原 Mono 的 GZipStream 缺 MonoPosixHelper，因此使用游戏现有 SharpZipLib 解包，已在原 Mono 执行。

## 验证与后续

实际游戏引用编译通过；原 Mono 的 Person、CUA、JSON/Morph、配置转移、原生缓冲和转换器重定位回归通过。实际原 UI DLL 的内存安装顺序与新宿主一致，GraftBoundaryTiles 原本已启用，不是本次新增优化。UI 在统一 DLL 未加载时可载入桥接，内存 hook 为零；独立副本恢复六插件/原 UI 布局通过。Unity 加载/实例化/销毁部分仍采用既有 helper 替身，不代替下一次游戏的短功能测试。

下一次正常启动日志应出现 `[vam-memory] active version=1.3.0 ... startupFailures=0`、`[compiler-worker] installed ...`、`[instance-roots] installed ...` 和 `[preset-owners] installed ...`。保持原 LDR/Westo 操作即可，留意插件、衣发/外观、锁、预设保存和读取。

## 1.3.0：编译隔离与两项加速

公共插件编译入口使用原Mono有界worker；默认256MiB私有内存软门槛、256次请求后回收。256MiB磁盘缓存复用相同源码/引用/参数的编译模板，但每次仍使用父端确定的独立程序集名称、模块名称和MVID，正常插件加载与static隔离保持。未解析的动态程序集引用保持原编译；调试符号与命中friend访问的名称不做模板改名。

仅更新同一DLL，worker及启动脚本内置、自动解到BepInEx/cache，移走DLL后下次启动不运行。`Compiler/IsolatedWorker`与`BytecodeCache`默认true；旧配置不改写，新增项首次启动生成。GC、画质、人物池和原有优化保持。真实编译/加载helper、代码与边界验证见`../compiler_cached_worker_20261006/VERIFICATION.txt`；不是VaM现场物理内存收益。

## 开发

`python build.py --output-dir <本轮工作区目录>` 构建唯一程序集，避免覆盖旧工件；`manifest.py` 列出原项目中的权威源码，`runtime/` 保存稳定宿主和可选 UI 桥接。1.2.0 执行 `../preset_cache_lifetime_20261006/validate.py BASELINE|MODIFIED|ROLLBACK` 复用真实方法 helper；旧验证器用于相应版本回归。`migrate_ui.py` 和 `deploy.py` 是一次性迁移工具，不是以后更新内存时必须重复的操作。

`ROLLBACK.sh <游戏根或独立布局根>` 恢复本次整合前六插件、UI 载荷/构建入口；`BASELINE.zip` 和 `INPUT_HASHES.json` 保留原字节。已在独立布局副本执行，生产整合版保持启用。完整命令、输入、输出、退出码见 `VERIFICATION.txt`。
