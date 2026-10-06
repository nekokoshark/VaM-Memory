# VaM Memory

**Virt-A-Mate 1.22.0.12** 的内存优化补丁集：一个统一的 BepInEx 插件 DLL（`VaM.Memory.dll`）+ 打过补丁的 Mono GC 运行库（`mono.dll`）。

> English summary: memory-retention patch set for Virt-A-Mate 1.22.0.12 — a single BepInEx plugin that retires stale references (destroyed-instance roots, preset-owner caches, AssetBundle leases, texture staging arenas), plus a binary-patched embedded Mono runtime whose Boehm GC reclaims native pages instead of monotonically growing the heap.

## 组成

| 组件 | 位置 | 说明 |
|---|---|---|
| `VaM.Memory.dll` | `BepInEx/plugins/VaMMemory/` | 应用层补丁集（Harmony 前缀/后缀 + 反射），.NET 3.5，76 个模块按 config 开关装配 |
| `mono.dll` | `Mono/EmbedRuntime/` | VaM 自带 Mono 运行库的二进制补丁版：空块退休、分配器生命周期、温页、回收排序四层补丁 |

## 当前版本 1.5.0 做什么

- **加载回收事务**：自动加载/人物收尾变成带完成债和版本凭据的回收事务——合并重复请求，等图片交接、缓存写盘、暂存消费、旧对象撤根和 Person drain 后再执行原 UUA/GC
- **TextureStagingArena**：纹理缓存读取/冷解码/共享/上传的原生暂存迁入独立分配器——分配器独占页面与预算，消费者持独立租约，最后退出才退页；收尾事务主动退还闲置 native 页
- **实例退出撤根**：`JSONStorableDynamic.UnloadInstance` 成功后撤去描述符→旧控制器/预设列表→旧皮肤/网格的根链
- **预设缓存所有者退出**：实例销毁后从其 Atom 的预设管理器五个私有缓存列表和 `regularStorables` 索引中摘除死亡记录
- **编译缓存 worker**：插件编译转原 Mono 有界 worker，256MiB 软预算，磁盘字节码模板缓存
- 以及此前整合的：Var 条目惰性标志、脚本编译瞬态清理、CUA 预载租约、Bundle 磁盘缓存、人物 prepared 生命周期等模块——见 `docs/CHANGELOG.md`

## mono.dll 补丁链（4 层）

基于 VaM 1.22.0.12 自带的 Mono EmbedRuntime（原版 SHA256 `160f224e…`），共叠加 4 层补丁，当前 SHA256 `16aaf4bd…`：

1. **空闲块退休**：native free-block age 阈值收紧（1 字节改动），GC 后空块更早退还给 OS
2. **分配器生命周期**：GC 收尾排序可回收小页（较密优先）、原空块合并前移、退提交只提交所需前缀、扩堆小请求按需求+seed；256MiB 整块提交储备
3. **温页**：64KiB 小页温区候选——真实 Mono 对照小页提交 174731→10931（仅 helper 级数据）
4. **回收排序**：`order_reclaim` 全局准入改独立 kind/size 校验

每层均有隔离测试（原 Mono 对照/故障注入/副本回滚），证据见 `docs/mono-patches/`。

## 安装与卸载

```
1. 完全退出 VaM
2. 备份原 <VaM>/Mono/EmbedRuntime/mono.dll
3. 覆盖 mono.dll，放入 BepInEx/plugins/VaMMemory/VaM.Memory.dll
4. 启动；配置自动生成于 BepInEx/config/vam.memory.cfg
卸载：换回原版 mono.dll，把 VaMMemory 目录移出 plugins
```

## 警告

- **mono.dll 补丁只适用于 VaM 1.22.0.12 自带的这一个 Mono 构建**——任何其他版本/其他游戏的 Mono 都不要覆盖
- 项目处于实测阶段：大量验证是隔离测试/夹具级，"物理内存水位收敛"未经充分实机验收
- 二进制补丁无源码可审（原始 patch 文档在 `docs/mono-patches/`），介意者只用 DLL 即可
- VaM.Memory.dll 与 Quest3TriggerUI 仓库共享约 76 个模块源码（`src/modules/`）；单独使用时独立工作

## 目录结构

```
src/runtime/   VaM.Memory 自身源码（插件入口、模块装配、回收事务、暂存器、UI 桥）
src/modules/   编入 DLL 的功能模块（与 Quest3TriggerUI 插件源码共享）
src/person/    人物 prepared 生命周期适配层
src/tests/     布局探针与统一测试
tools/         本地构建/校验/部署脚本（依赖本机路径布局，供参考）
docs/          路线图、更新日志、mono 补丁链证据
```
