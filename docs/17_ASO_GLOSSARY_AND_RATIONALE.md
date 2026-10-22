# ASO Compass：ASO 原理、医学意义与术语导读

> **用途：研究和教育，不用于临床决策。** 本文帮助没有医学或生物学背景的读者理解
> ASO Compass 的英文界面、结果和证据边界。它不是诊断、治疗或用药指南。

## English abstract

**ASO** means **antisense oligonucleotide**. ASOs are short, synthetic nucleic-acid molecules
designed to bind selected RNA sequences. Depending on their chemistry and binding site, they can
promote RNA degradation, alter pre-mRNA splicing, or block an RNA interaction. ASO Compass does
not design an ASO. It organizes saved target-disease, variant, mechanism, constraint, drug, and
trial evidence into deterministic research tracks for manual review. A track is a hypothesis—not
proof of causality, safety, efficacy, or clinical suitability.

## 1. 名称是什么意思？

**ASO = Antisense Oligonucleotide = 反义寡核苷酸。**

ASO 是一小段人工合成的 DNA 或 RNA 类分子，按照互补序列与指定 RNA 结合。可以把它
想象成一张带有精确地址的“分子便利贴”：它先找到目标 RNA，再改变该 RNA 的命运或
处理方式。

根据 ASO 的序列、化学结构和结合位置，它可能：

- 促使目标 RNA 被降解，从而减少蛋白质；
- 改变 pre-mRNA 剪接，例如促进外显子包含或跳过；
- 遮挡 RNA 上的关键位置，阻止翻译或其他分子结合；
- 在特定剪接设计中恢复更多有效蛋白质。

因此，**ASO Compass** 可以意译为“反义寡核苷酸研究导航仪”。`Compass` 强调它用于
导航证据和研究方向，而不是给出临床治疗答案。

## 2. 为什么应用以 ASO 为主题？

单纯知道“某个基因与某种疾病有关”还不够。对于 RNA 靶向干预，首先必须判断疾病机制：

```text
疾病与基因存在关联
        │
        ├─ 异常功能太强或产生有毒产物？ ──→ 研究 knockdown
        │
        ├─ 正常功能不足？                ──→ 研究恢复表达或功能
        │
        ├─ RNA 剪接错误？                ──→ 研究 splice correction
        │
        └─ 方向仍不明确？                ──→ 不指定干预方向，人工复核
```

同一个基因如果机制不同，合理方向可能完全相反：有毒的功能获得可能适合降低表达；
功能缺失或单倍剂量不足却通常不应继续降低表达。这种对“方向”的高度依赖，正是
ASO Compass 同时检查遗传关联、变异类型、遗传方式、基因约束和既有 ASO 先例的原因。

项目继承自 `ASO Target Finder v4.1`，目标是透明地探索疾病相关基因、机制、安全信号、
治疗先例和潜在 ASO 研究策略。科学范围和简化规则见
[`01_PRODUCT_AND_SCIENCE.md`](01_PRODUCT_AND_SCIENCE.md)。

### 2.1 机制与可能研究方向

| 疾病机制 | 通俗理解 | 可能的 ASO 研究方向 | 关键限制 |
|---|---|---|---|
| **GoF — gain of function** | 异常蛋白功能过强或出现有毒的新功能 | 降解 RNA，减少异常蛋白 | 还要确认正常蛋白能否安全减少 |
| **DN — dominant negative** | 异常蛋白干扰正常蛋白 | 考虑降低异常 RNA | 全面降低可能同时损失正常蛋白；等位基因特异性很重要 |
| **Splicing defect** | RNA 被错误“剪辑” | 调节或纠正剪接 | 必须存在可操作的 RNA 位点，并通过实验验证 |
| **LoF — loss of function** | 正常蛋白不足或失去功能 | 某些情况下恢复剪接或有效表达 | LoF 不自动证明上调或剪接纠正可行 |
| **Unknown mechanism** | 只知道有关联，不知道应增还是减 | 暂不指定方向 | 应回到原始证据人工研究 |

### 2.2 已有医学先例说明这不是纯理论概念

- **Tofersen** 与 SOD1-ALS 有关，通过靶向 `SOD1` mRNA 减少 SOD1 蛋白产生。
- **Nusinersen** 调节 `SMN2` pre-mRNA 剪接，以增加有效 SMN 蛋白。
- 一些 Duchenne muscular dystrophy ASO 通过 exon skipping 改变 RNA 阅读框。

这些例子说明 ASO 可以走不同路线：`RNA degradation → 蛋白质减少`，也可以
`splice modulation → 有效蛋白质恢复或增加`。存在先例不表示同类策略对另一个基因、
疾病或患者同样安全有效。

## 3. 从 DNA 到疾病表型

```text
DNA
 └─ Gene 基因：说明书中的一段
     └─ pre-mRNA：未经剪辑的 RNA
         ├─ Splicing：选择并拼接 RNA 片段
         └─ mRNA：成熟的工作副本
             └─ Protein 蛋白质：执行功能的分子机器
                 └─ Cell function / phenotype：细胞功能与可观察表型
```

| English term | 中文 | 通俗解释与医学意义 |
|---|---|---|
| **DNA** | 脱氧核糖核酸 | 细胞中的“总说明书”。不同细胞读取其中不同部分。 |
| **Gene** | 基因 | DNA 中具有功能的一段信息，通常产生 RNA，许多基因进一步指导蛋白质产生。基因不是蛋白质本身。 |
| **Gene symbol** | 基因符号 | 基因的标准简称，例如 `SCN1A`、`SNX27`、`SOD1`。它们是名称，不是数据库编号。 |
| **Gene ID** | 基因编号 | 数据库为基因分配的稳定标识，例如以 `ENSG` 开头的 Ensembl Gene ID。 |
| **RNA** | 核糖核酸 | DNA 信息的工作副本或功能分子；ASO 的主要作用对象通常是 RNA。 |
| **pre-mRNA** | 前体信使 RNA | 尚未完成剪接的 RNA，类似未经剪辑的原始录像。 |
| **mRNA** | 信使 RNA | 可指导细胞生产蛋白质的成熟 RNA，类似生产工单。 |
| **Transcript** | 转录本 | 同一基因通过不同起始、终止或剪接方式产生的 RNA 版本。一个基因可有多个转录本。 |
| **Protein** | 蛋白质 | 执行许多细胞功能的分子机器，如酶、受体和离子通道。 |
| **Gene expression** | 基因表达 | 基因产生 RNA 或蛋白质的过程和数量。上调通常表示增加，下调表示减少。 |
| **Phenotype** | 表型 | 可观察或测量的特征，包括症状、生理指标和疾病特征。 |

基因和蛋白质经常使用相似简称，但它们不是同一个实体。规范写作中，人类基因符号通常
使用斜体，蛋白质符号不使用斜体。

## 4. RNA 剪接术语

| English term | 中文 | 通俗解释与医学意义 |
|---|---|---|
| **Exon** | 外显子 | RNA 加工后通常被保留的片段，可类比为影片中留下的镜头。 |
| **Intron** | 内含子 | 通常在 RNA 加工时被移除的片段。 |
| **Splicing** | RNA 剪接 | 从 pre-mRNA 中移除某些部分并连接保留部分的过程。 |
| **Alternative splicing** | 可变剪接 | 同一基因通过不同剪法产生不同 RNA 和蛋白质版本。 |
| **Splice-site variant** | 剪接位点变异 | 发生在剪接关键位置的变异，可能造成外显子错误跳过或内含子错误保留。 |
| **Exon skipping** | 外显子跳跃 | 某个外显子未进入成熟 RNA；它既可能是疾病机制，也可能在特定疾病中被用作干预策略。 |
| **Splice correction** | 剪接纠正 | 使用 ASO 等方法改变错误剪接，希望恢复更正常的 RNA 或有效蛋白质。 |

`Splice/upregulation` 是 ASO Compass 的合并研究轨道，不表示剪接纠正和上调是同一个
生物过程。它的保守含义是：证据较像正常功能不足，因此不应首先假设普通 knockdown；
下一步应研究能否恢复剪接或有效表达。

## 5. 基因变异与致病性

### 5.1 Variant 不等于 disease

**Genetic variant（遗传变异）**是 DNA 序列与参考序列之间的差异，可以类比为说明书中的
文字变化。大多数变异不一定影响健康；必须结合位置、类型、人群频率、实验、家系和临床
证据判断。

| English term | 中文 | 通俗解释与医学意义 |
|---|---|---|
| **Missense variant** | 错义变异 | 替换蛋白质中的一个氨基酸，类似机器的一个零件被换掉；后果可能无害，也可能改变功能。 |
| **Nonsense variant** | 无义变异 | 提前产生停止信号，可能形成过短蛋白质或导致 RNA 被清除。 |
| **Frameshift variant** | 移码变异 | 插入或删除使后续读取框整体错位，通常可能产生较大影响。 |
| **Synonymous variant** | 同义变异 | DNA 改变但编码的氨基酸不变；多数影响较小，但不保证完全无影响。 |
| **Structural variant** | 结构变异 | 较大片段的缺失、重复、倒位或重排。 |
| **Repeat expansion** | 重复序列扩增 | 某段短 DNA 的重复次数异常增加；常规小变异统计可能无法充分捕捉。 |

### 5.2 Pathogenicity 是证据分类

| English term | 中文 | 正确理解 |
|---|---|---|
| **Pathogenic** | 致病性 | 证据支持该特定变异与特定疾病有关；不表示每位携带者的表现完全相同。 |
| **Likely pathogenic** | 可能致病 | 证据较强，但仍有不确定性。 |
| **VUS — variant of uncertain significance** | 临床意义未明变异 | 证据不足；既不能当作致病，也不能当作无害。 |
| **Likely benign** | 可能良性 | 多数证据认为不导致相关疾病。 |
| **Benign** | 良性 | 证据支持该变异不是相关疾病原因。 |

ClinVar 保存提交者对变异—疾病关系的解释及支持证据。不同提交可能冲突，因此应查看
review status、提交日期和原始证据，而不能只读取一个标签。

## 6. 最关键的疾病机制

### Loss of function（LoF，功能缺失）

基因或蛋白质原有功能降低或消失。可理解为机器停止工作，或者生产数量不足。LoF 可能
来自蛋白截短、RNA 被清除或蛋白功能受损。如果疾病因为正常功能不足，继续 knockdown
通常可能适得其反。

### Gain of function（GoF，功能获得）

蛋白质获得异常功能，或原有功能过强、持续活跃。可理解为机器卡在“持续开启”状态，
或开始执行不应执行的操作。有毒 GoF 有时支持降低异常 RNA/蛋白的研究方向。

### Dominant negative（DN，显性负效应）

异常蛋白不仅自己失效，还会干扰正常蛋白，类似一个坏零件把整组正常零件拖垮。全面
knockdown 可能同时损失正常蛋白，因此 allele-specific（等位基因特异性）策略可能更理想。

### Haploinsufficiency（单倍剂量不足）

两个基因拷贝中的一个失效后，另一个正常拷贝产生的蛋白仍不足以维持功能。可类比为两台
泵中一台损坏，剩下一台无法满足需求。这通常增加对进一步 knockdown 的担忧。

### Inheritance（遗传方式）

| English term | 中文 | 通俗解释 |
|---|---|---|
| **Dominant inheritance** | 显性遗传 | 通常一个异常拷贝就可能造成疾病，可涉及 LoF、GoF 或 DN。 |
| **Recessive inheritance** | 隐性遗传 | 通常两个拷贝都受影响才出现疾病，一个正常拷贝往往仍可维持足够功能。 |
| **X-linked** | X 连锁遗传 | 相关基因位于 X 染色体，不同性别可能呈现不同风险和遗传模式。 |

“显性”不等于“严重”，“隐性”也不等于“轻微”；它们描述遗传模式。

## 7. ASO 操作方向

### Knockdown（降低表达／敲低）

减少目标 RNA 或蛋白质，可理解为把音量调低，而不一定完全关闭。它可能适用于有毒 GoF、
DN 或异常蛋白积累，但必须考虑正常蛋白是否必需、降低程度、目标组织和等位基因选择性。

### Upregulation（上调表达）

增加正常 RNA 或有效蛋白质，可能适用于 LoF 或 haploinsufficiency。它不等于“越多越好”，
也不表示任何基因都能通过 ASO 直接、安全地上调。

### Splice modulation / correction（剪接调节／纠正）

ASO 结合 pre-mRNA 的剪接调控区域，改变外显子的包含或跳过。它只在疾病机制、目标 RNA
结构和具体位点适合时才可能有意义。

## 8. ASO Compass 的五种 track

| Track | 中文理解 | 应用中的特定含义 | 不代表什么 |
|---|---|---|---|
| **Knockdown** | 倾向减少 RNA/蛋白 | 保存证据更支持降低方向 | 不代表 knockdown 已被证明安全有效 |
| **Splice/upregulation** | 倾向恢复功能 | 保存证据更像 LoF，下一步研究剪接纠正或恢复表达 | 不代表一定存在可纠正位点或可行上调技术 |
| **Ambiguous** | 机制不明确或冲突 | 证据不能稳定给出方向 | 不代表基因不重要 |
| **Modifier** | 只有关联，方向未知 | 有关联证据，但缺乏足够方向性变异证据 | 不等于已证明的医学“修饰基因” |
| **Insufficient data** | 数据不足 | 可供自动规则分类的记录太少 | 不代表阴性，也不代表基因与疾病无关 |

当前规则的证据优先级为：人工策展覆盖、Gene2Phenotype、ClinVar 启发式、association-only
modifier。LOEUF 只用于安全提醒，不直接决定机制。实现见
[`classification.py`](../backend/app/domain/classification.py)。这些是简化且固定的研究规则，
不是完整疾病生物学模型。

## 9. 分数、候选与筛选

| English term | 中文 | 正确理解 |
|---|---|---|
| **Candidate gene** | 候选基因 | 通过最低关联筛选、值得继续研究的基因，不是已确认治疗靶点。 |
| **Target-disease association** | 靶点—疾病关联 | 公开证据显示基因/靶点与疾病有关；关联不等于因果。 |
| **Overall association score** | 总体关联分数 | 综合多种证据的排序指标，不是治疗成功概率。 |
| **Genetic association score** | 遗传关联分数 | 更强调人类遗传证据；仍不能单独证明干预方向。 |
| **Final call** | 最终机制分类 | 固定规则和证据优先级产生的 track，不是临床结论。 |
| **Confidence tier** | 证据层级 | 描述记录数量、一致性和规则边界，不是患者风险概率。 |
| **Priority shortlist** | 优先审查清单 | 满足应用规则、优先人工检查的候选集合，不是药物推荐名单。 |
| **Shortlist position** | 清单位置 | 应用内部的复核顺序，不是临床疗效排名。 |

Open Targets association score 是基于可用证据的启发式排序值；Open Targets 明确提醒，不应把
它解释成靶点—疾病关联的置信概率。

## 10. 数据完整性与警告

| English term | 中文 | 正确理解 |
|---|---|---|
| **Evidence record** | 证据记录 | 数据库中的一条结构化记录；不一定等于一个独立患者或一项独立研究。 |
| **Complete** | 本次返回完整 | 本次查询没有触发截断，不表示全世界证据已被完整收集。 |
| **Evidence capped / truncated** | 证据达到上限／被截断 | 返回记录超过应用上限，比例和分类可能基于不完整数据，需要人工复核。 |
| **Quick mode** | 快速模式 | 变异和药物富集最多处理 25 个基因，适合演示和初筛。 |
| **Full mode** | 完整模式 | 允许富集更多基因，但仍受数据源和方法限制，并非全部医学证据。 |
| **Warning** | 警告 | 提醒结果存在范围、来源或完整性限制，不自动等于系统失败或阴性结果。 |
| **Manual review** | 人工复核 | 回到原始数据库、论文和变异记录检查机制、证据质量和冲突。 |

Quick mode 的限制定义在 [`runs.py`](../backend/app/schemas/runs.py)。

## 11. 药物和临床开发术语

| English term | 中文 | 正确理解 |
|---|---|---|
| **Therapeutic precedent** | 治疗先例 | 该靶点已有药物或试验活动，可用于了解研究成熟度。 |
| **ASO precedent** | ASO 先例 | 本次检查的数据源中找到靶点相关 ASO 药物或试验。 |
| **Approved drug** | 已批准药物 | 至少在某个适应症获批；不自动表示已获批治疗当前查询疾病。 |
| **Clinical trial** | 临床试验 | 在人体中研究干预的安全性、剂量或效果；存在试验不代表有效。 |
| **Phase 1** | 一期 | 通常重点考察安全性、耐受性和剂量。 |
| **Phase 2** | 二期 | 初步研究疗效并继续评估安全性。 |
| **Phase 3** | 三期 | 通常在更大样本中验证获益和风险。 |
| **Recruiting** | 招募中 | 试验状态，不表示结果为阳性。 |

`ASO precedent found: 0` 只表示在本次数据源、查询范围和匹配方法下没有找到先例，不能证明
世界上不存在相关研究。

## 12. LOEUF 与基因约束

**LOEUF = Loss-of-function Observed/Expected Upper bound Fraction。** 它比较在人群数据中
实际观察到多少预测 LoF 变异与理论预期数量。

- 较低 LOEUF：观察到的 LoF 比预期少，提示该基因较不耐受功能缺失；
- 较高 LOEUF：人群似乎更能容忍该基因的一部分 LoF 变异。

低 LOEUF 会增加对全面 knockdown 的安全担忧，但它不能单独证明某个具体变异致病，也
不能单独决定药物方向或可成药性。ASO Compass 把它作为安全 flag，而不是机制分类器。

## 13. 主要数据源和标识符

| Source / ID | 是什么 | 在应用中的作用或限制 |
|---|---|---|
| **Open Targets** | 综合公开遗传、组学、文献和药物数据的平台 | 提供靶点—疾病关联、分数和药物信息。 |
| **ClinVar** | NCBI 的变异临床解释档案 | 提供提交者的变异分类；不同提交可能冲突。 |
| **EVA** | European Variation Archive | 保存并提供遗传变异数据；档案记录不等于临床确认。 |
| **Gene2Phenotype — G2P** | 专家整理的基因—疾病机制数据 | 可提供 LoF、GoF/DN 和遗传方式，在当前规则中优先于 ClinVar 计数启发式。 |
| **gnomAD** | 大规模人群变异数据库 | 提供 LOEUF 等基因约束指标。 |
| **ClinicalTrials.gov** | 临床试验登记库 | 用于寻找疾病或靶点相关试验；登记不等于阳性结果。 |
| **MONDO ID** | 疾病本体编号 | 例如 `MONDO_0004976`；它是疾病标识，不是基因编号。 |
| **Ensembl Gene ID** | 基因稳定编号 | 通常以 `ENSG` 开头，用于跨数据库关联基因记录。 |

## 14. 应用没有解决什么？

ASO Compass 是靶点假设生成、机制初步分流、证据复核排序和教学工具。它没有充分建模：

- ASO 具体序列和化学修饰；
- RNA 二级结构和目标位点可达性；
- 组织分布、细胞摄取与内体逃逸；
- 给药途径、剂量和药代动力学；
- off-target、免疫反应与毒性；
- 等位基因特异性；
- 不同转录本、蛋白亚型和组织表达；
- 动物实验、患者分层及临床获益。

因此应用输出的是可追溯的**研究假设**，不是 ASO 序列、候选药物、患者治疗建议或安全性
证明。AI 解释也只能解释保存证据，不能改变确定性分数、track 或 shortlist。

## 15. 建议首先掌握的 12 个词

1. **Gene** — 基因
2. **Gene symbol** — 基因符号
3. **mRNA** — 信使 RNA
4. **Protein** — 蛋白质
5. **Variant** — 遗传变异
6. **LoF** — 功能缺失
7. **GoF** — 功能获得
8. **Dominant negative** — 显性负效应
9. **ASO** — 反义寡核苷酸
10. **Knockdown** — 降低表达
11. **Splice correction** — 剪接纠正
12. **Association is not causation** — 关联不等于因果

掌握它们后，可用一句话理解应用：

> ASO Compass 先寻找与疾病有关的基因，再尝试判断疾病更像是异常功能过多、正常功能不足，
> 还是机制仍不明确；随后给出 knockdown、splice/upregulation 或人工复核方向。它不为患者
> 选择治疗方案。

## 16. 延伸阅读

- [NIH/NCATS: Antisense oligonucleotide glossary](https://toolkit.ncats.nih.gov/glossary/antisense-oligonucleotide/)
- [Review: mechanisms of FDA-approved ASO drugs](https://pmc.ncbi.nlm.nih.gov/articles/PMC11695194/)
- [FDA: tofersen for SOD1-ALS](https://www.fda.gov/drugs/news-events-human-drugs/fda-approves-treatment-amyotrophic-lateral-sclerosis-associated-mutation-sod1-gene)
- [MedlinePlus: gene variants](https://medlineplus.gov/genetics/understanding/mutationsanddisorders/genemutation/)
- [MedlinePlus: variant types](https://medlineplus.gov/genetics/understanding/mutationsanddisorders/possiblemutations/)
- [NCBI ClinVar introduction](https://www.ncbi.nlm.nih.gov/clinvar/intro/)
- [Open Targets: target-disease association scores](https://platform-docs.opentargets.org/associations)
- [European Variation Archive](https://www.ebi.ac.uk/eva/)
- [gnomAD constraint study](https://www.nature.com/articles/s41586-020-2308-7)
- [HGNC gene nomenclature guidance](https://pmc.ncbi.nlm.nih.gov/articles/PMC7494048/)

