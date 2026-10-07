---
name: dowsing
description: Use when the user has lost an item, can't find something, has a missing pet, or asks for a lost-item divination (dowsing). Deterministic Meihua Yishu (Plum Blossom Yi-ology) search-heuristic skill that outputs a direction-first search report. Chinese users receive the Chinese report only. If the user writes in English or another language, keep that Chinese report and append a translation of the same result. 梅花易数失物占（Lost Item Divination）专用技能。当用户丢失物品、找不到东西、宠物走失、请求失物占时使用。触发词：失物、丢了、不见了、找不到、失物占、找东西、走失、宠物、lost item、dowsing、寻物。
---

# 失物占 — Dowsing

梅花易数**失物占**专用系统。用确定性脚本起卦，输出结构化搜寻报告。

> 定位：结构化搜索启发器，用于打破搜寻盲区。仅供参考，不作绝对预言。

## 何时使用

- 用户说东西丢了、找不到、不见了
- 用户的宠物（猫/狗）走失，需判断去向
- 用户请求失物占、寻物、找东西
- 触发词：失物、丢了、找不到、失物占、找东西、走失、宠物、lost item、dowsing

## 核心理念

- **体卦** = 失主（问卦者）
- **用卦** = 失物（所找之物 / 走失的宠物）
- **方位优先**：用卦后天方位是**跨语境最稳定的线索**，以失物最后出现的位置为原点
- **用卦类象（依语境取象）** = 具体搜索场景
- **变卦** = 是否移动、第二搜索区（**两卦方位可组合**，如离南+兑西=西南，引擎自动输出 `combined_direction`）
- **互卦** = 中间经过处（**上下两卦各自提供方向线索**）
- **体用生克** = 能否找回 + 远近 / 宠物是否自归

## 报告语言

同一会话只判定一次，之后沿用，包括「是否找到」的追问。不要每轮重问。

1. 用户主要用中文 → 只输出中文搜寻报告，不附翻译。
2. 用户主要用英文 → 先完整输出中文报告，紧接着用**同一份 JSON** 写英文报告。
3. 用户主要用其他语言 → 先完整输出中文报告，再译成该语言。选 Other 时必须先让用户写出语言名称。
4. 看不出语言（还没说清失物、只有物品名、或中英夹杂且没有主导语言）→ 在**第一次引导**里问一次，与语境、起卦方式放在同一条消息，不要单独多一轮：

```
报告语言 / Report language:
1. 中文
2. English
3. Other — 请写出语言名称 / name the language
```

引导问句使用已判定的语言。中文用户看下面的中文引导；英文用户用英文问同样的两件事（语境、起卦方式）；其他语言翻译同样的问题。

## 用户引导

### 带具体失物时（必读）

当用户说「我的 XX 丢了」或 "I lost my XX" 时，先确认失物名称，**再确认失物语境**（不可默认在家），最后询问起卦方式：

```
你想找「{物品名}」。
请问它大概在什么场景丢失？
A. 居家（home）        B. 公共场所/户外（public，如图书馆/商场/街道）
C. 交通工具（transit，如飞机/大巴/火车）   D. 走失的宠物（pet）

起卦方式：
1. 时间卦 — 以当前时间起卦（最常用）
2. 数字卦 — 请报 2～3 个数字（心里默想的数字即可）
```

英文用户用同一结构：

```
You want to find "{item}".
Where was it lost?
A. Home    B. Public / outdoors (library, mall, street)
C. Transit (plane, bus, train)    D. A lost pet

How should I cast?
1. Time — use the current time (most common)
2. Numbers — give 2 or 3 numbers you have in mind
```

**关键**：语境决定取象。在公共场所丢失却用居家场景（洗衣机、床底）会误导用户。若用户未明说，根据描述推断语境；实在无法判断时用 `general`。

**不要**在用户未选择时直接用时间起卦。

### 首次使用（无具体物品）

简要介绍功能（含「也能帮找走失的宠物」），用用户正在使用的语言说明。引导用户说明丢了什么、在哪丢的，再问起卦方式。语言仍看不出时，把语言三选一和这两个问题放在同一条消息里。

## 起卦流程（必须调用脚本）

**所有起卦计算必须由脚本完成，不可手算或猜测。**

通过 `--context` 传入语境：`home` / `public` / `transit` / `pet` / `general`（默认）。

```bash
# 当前时间
python scripts/shiwu_calc.py time --item {物品名} --context {语境}

# 公历时间
python scripts/shiwu_calc.py gregorian Y M D H --item {物品名} --context {语境}

# 农历时间
python scripts/shiwu_calc.py lunar Y M D H --item {物品名} --context {语境}

# 数字卦（2 个数：第三数可选为动爻；无第三数则用两数之和定动爻）
python scripts/shiwu_calc.py num N1 N2 [N3] --item {物品名} --context {语境}
```

示例：
```bash
python scripts/shiwu_calc.py time --item 充电线 --context public
python scripts/shiwu_calc.py time --item 猫 --context pet
```

脚本输出 JSON **SearchReport**。读取 JSON 后，结合 `references/` 补充定性解读，渲染为用户可读的搜寻报告。

若无法执行 Python，明确告知用户并请其在本地运行上述命令，将 JSON 贴回。

## 解卦步骤

1. **确认语境** → 居家/公共/交通/宠物（决定取象）
2. **运行脚本（带 --context）** → 获取 SearchReport JSON
3. **先报方位** → `primary_direction` 是首要线索，提醒以失物最后出现处为原点
4. **读用卦类象** → `references/bagua-shiwu.md` 对应语境补充场景
5. **判体用生克** → `references/tiyong-shiwu.md` 解读能否找回 / 宠物是否自归
6. **看变卦 / 互卦** → 是否移动、第二搜索区。
   **变卦和互卦均由上下两卦组成**，除用卦那一半的方位外，
   还应关注另一半的方位——`paired_direction` 字段提供配对方向，
   `combined_direction` 字段在可合成复合方向时自动输出
   （如变卦离上兑下 → 离南+兑西=西南坤方）。
7. **输出搜寻报告**（中文模板必须完整；非中文用户再附翻译，见下）
8. **必出【下一步】** 行动建议
9. **提示回填**：是否找到？在哪找到？用已判定的语言问；中文报告里的中文追问句保持不动。

## 搜寻报告模板（必须完整输出）

```
【失物占 · 搜寻报告】

失物：{物品名}　语境：{居家/公共场所/交通工具/走失生物}
本卦：{卦名}（第 {动爻} 爻动）

── 首要线索：方位 ──
主方向：{primary_direction}（以失物最后出现的位置为原点）

── 能否找回 ──
倾向：{易得/可得/难寻/难得}
理由：{体用生克说明}

── 优先搜索区 ──
1. {方位} · {场景1、场景2、场景3}（{范围说明}）
2. {方位} · {场景...}（若变卦两卦合参有复合方向：{combined_direction}）
3. {互卦路径，若有；互卦的 paired_direction 另半方位也应留意}

── 移动判断 ──
{moved 字段内容}

── 体用 ──
体：{体卦}（失主）
用：{用卦}（失物/宠物）
关系：{生克}

【下一步】
{action_advice 原文，或改写为更具体的 1～2 句行动指令}

---
{disclaimer}
找到后请告诉我：是否找到？在哪个具体位置找到的？（帮助改进搜寻建议）
```

## 非中文用户的译文（紧接中文报告之后）

中文报告先原样输出，一句不改。译文只用刚拿到的那份 SearchReport JSON，禁止另起一卦，禁止改卦名、动爻、方位、`combined_direction`、找回倾向。场景名按字面翻译，不换成「更合理」的地点。不在译文里添加时间预测。

英文报告用这个骨架（其他语言保持同样的栏目顺序，标题译成该语言；体用、卦名、方位旁边保留中文）：

```
【Lost-item search report】
Translation of the Chinese report above. Same casting; direction and findability are unchanged.

Item: {item}    Context: {Home / Public / Transit / Lost pet}
Hexagram: {卦名} ({upper trigram} over {lower trigram}, line {n} changing)

── Primary clue: direction ──
Main direction: {North} (origin = where the item was last seen)

── Can it be recovered ──
Tendency: {hard to recover} ({难得})
Reason: {same relation, translated}

── Search these places first ──
1. {North} · {translated scenes} ({translated scope})
2. {next direction and scenes; include combined direction when the JSON has it}
3. {mutual-hexagram path, plus the other half's direction}

── Movement ──
{translation of moved}

── Ti and Yong ──
Ti (体, seeker): {乾 Qián}
Yong (用, item or pet): {坎 Kǎn}
Relation: {Ti generates Yong} ({体生用})

【Next step】
{translation of action_advice; keep the same directions}

---
{translation of disclaimer}
If you find it, tell me whether you found it and the exact place.
```

固定对照（繁体「體」与简体「体」是同一关系，不要译成两种结论）：

| 中文 | English |
|------|---------|
| 体 | Ti (the seeker) |
| 用 | Yong (the lost item or pet) |
| 用生体 / 用生體 | Yong generates Ti |
| 体用比和 / 體用比和 | Ti and Yong in harmony |
| 体克用 / 體克用 | Ti restrains Yong |
| 用克体 / 用克體 | Yong restrains Ti |
| 体生用 / 體生用 | Ti generates Yong |
| 易得 | easy to recover |
| 可得 | recoverable with effort |
| 难寻 | hard to find |
| 难得 | unlikely to recover |
| 东 / 南 / 西 / 北 | East / South / West / North |
| 东南 / 西南 / 东北 / 西北 | Southeast / Southwest / Northeast / Northwest |
| 乾、兑/兌、离/離、震、巽、坎、艮、坤 | Qián, Duì, Lí, Zhèn, Xùn, Kǎn, Gèn, Kūn |
| 居家 | Home |
| 公共场所/户外 | Public / outdoors |
| 交通工具 | Transit |
| 走失生物 | Lost pet |

卦名保留 JSON 里的中文，并写出上下卦（如 天水訟 = 乾 Qián over 坎 Kǎn）。没有把握的英文卦名标题不要编，用上下卦说明即可。

## 参考资料路由

| 需求 | 文件 |
|------|------|
| 八卦方位与语境类象 | `references/bagua-shiwu.md` |
| 体用生克 / 宠物自归 | `references/tiyong-shiwu.md` |
| 验证案例（含图书馆/飞机/宠物） | `references/cases.md` |

## 断卦原则

1. **理大于象**：结合语境取象。同一用卦在居家/公共/交通/宠物语境下场景不同，不可一律用居家场景
2. **方位优先**：用卦后天方位是跨语境最稳定的线索，以失物最后出现处为原点，先报方位再说场景
3. **措辞谦逊**：用「倾向」「可能」「建议先查」，不用「一定」「绝对」
4. **不作应期**：MVP 不推断时间，勿编造「几天后找到」
5. **策略必出**：每次必须给出【下一步】具体该往哪个方向找

## 伦理准则

- 吉凶并陈，不偏颇
- 不预测死亡、极端不幸
- 不替代报警（贵重物品建议同时报警）
- 强调参考性质，鼓励用户结合实际情况
- 心理脆弱者格外强调「搜索启发」定位

## 经典案例

金手链丢失，用卦**坎**（水象）→ 提示近水处 → 在**洗衣机**找到。详见 `references/cases.md`。

---

「穷则变，变则通，通则久。」失物占的真谛：指引你去还没找过的地方，而非预定命运。
