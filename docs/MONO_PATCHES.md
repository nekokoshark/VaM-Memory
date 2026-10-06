# mono.dll 补丁链

VaM 1.22.0.12 自带 `Mono/EmbedRuntime/mono.dll`（原版 SHA256 `160f224ead92…`）上的四层累积二进制补丁。当前部署版 SHA256 `16AAF4BD…`。

## 链

| 序 | 任务 | 基线→修改 | 内容 |
|---|---|---|---|
| 1 | mono_retire_fast | `160f224e`→`cd7ab354` | native free-block 退休：`nativeAgeThreshold` 6→1（RVA 0x15FCC7 处 `fa`→`ff`，单字节）；GC 后空块更快退还给 OS |
| 2 | mono_allocator_lifecycle | `cd7ab354`→`d89ccf26` | GC 收尾排序可回收小页入 pending 链（较密优先、kind2/3 保持）；原空块合并前移；普通退提交大空块仅提交所需前缀；扩堆小请求按需求/可复用容量+≤2MiB seed；256MiB 整块提交储备沿用。**注意**：首版 F3F46BBA 因 4096 区段表超限在游戏中报致命错，已回退后重发 D89CCF26（撤销按空闲总量缩扩堆、恢复 speculative/fallback 参数、不扩区段表） |
| 3 | mono_warm_pages | `d89ccf26`→`1c023c25` | 64KiB 小页温区：保留大请求精确前缀、原扩堆/4096 区段/256MiB 储备；真实 Mono 对照小页提交约 174731→10931、方法中位 9968→850ms（仅 helper 级） |
| 4 | mono_reclaim_cohorts | `1c023c25`→`16aaf4bd` | `order_reclaim` 全局准入改独立 kind/size 校验；page_bound=registered heap/4096；原标记/对象身份/TLS/锁/黑名单/原扩堆/4096 区段上限/温区/256MiB 储备全保持 |

`mono_reclaim_controller`（`cd7ab354`→`85db66a5`）是并行候选，**不在**部署链内。

## 证据格式

每层目录下两份文件：

- `*_PATCH.json` — 机器可读的补丁描述：基线/修改哈希、callsite/stub/controller/state RVA、新增节区表、call site 清单
- `*_VERIFICATION.txt` — 隔离测试原始输出：原 Mono 对照、故障注入、独立副本回滚、真实 Windows 退提交/并发/固定地址用例

## 诚实的边界

- 全部为**隔离测试**（合成真实类型图、真实 Mono 独立进程）；fixture 的"载荷归零"≠游戏物理内存下降
- `mono_allocator_lifecycle` 曾出过真实游戏回归（GC heap sections 报错）并被回滚修正——补丁有风险自担
- 适用性严格绑定这一个 Mono 构建；VaM 更新后必须重新验证原版哈希
