import { useState } from "react";

type Language = "en" | "zh";

type LearnProps = {
  disclaimer: string;
  onExample: () => void;
};

const COPY = {
  en: {
    switchLabel: "Tutorial language",
    eyebrow: "Guided application tour",
    title: "A transparent map, not a clinical answer.",
    intro: "Learn ASO Compass as a software evidence pipeline first. You do not need a medical background to follow how a disease query becomes traceable candidate records and cautious research tracks.",
    start: "Open the guided ALS example",
    boundaryTitle: "Four boundaries to remember",
    boundaries: [
      ["Association is not causation", "A score says that public evidence links a gene to a disease. It does not prove that changing the gene will help."],
      ["A track is not a treatment", "A track is a research direction produced by visible rules—not a recommendation for a patient, dose, or therapy."],
      ["Missing is not negative", "A failed, capped, or empty lookup cannot be interpreted as evidence that the biology is absent."],
      ["AI explains; it does not decide", "Generated text can summarize saved evidence, but it cannot change classifications, scores, shortlist order, or warnings."],
    ],
    pipelineTitle: "From query to reviewable evidence",
    pipelineIntro: "Think of each scientific source as a feature provider and every candidate as a versioned record with provenance.",
    pipeline: [
      ["01", "Disease query", "Choose a disease or phenotype identifier. The identifier anchors the analysis to an ontology record."],
      ["02", "Association", "Open Targets supplies genes and association scores that pass the configured filters."],
      ["03", "Enrichment", "ClinVar/EVA, Gene2Phenotype, constraint, drug, and trial sources add mechanism and context."],
      ["04", "Rule engine", "Deterministic precedence and thresholds assign exactly one of five tracks. This is not a machine-learned prediction."],
      ["05", "Human review", "The interface keeps source links, missingness, caps, warnings, and uncertainty next to each result."],
    ],
    tracksEyebrow: "Deterministic outputs",
    tracksTitle: "The five research tracks",
    means: "What it means here",
    notMeans: "What it does not establish",
    tracks: [
      ["Knockdown", "Enough classified records were returned and the loss-of-function fraction is at or below 0.25.", "It does not prove toxic gain of function or that knockdown is safe or effective."],
      ["Splice / upregulation", "Enough records were returned and the loss-of-function fraction is at or above 0.60.", "It does not prove that restoring expression is technically feasible or safe."],
      ["Ambiguous", "The loss-of-function fraction lies between the directional thresholds.", "It is not a tie-breaker or a weaker form of another track."],
      ["Modifier", "Association exists, but returned evidence does not provide a clear directional mechanism.", "It does not mean the gene is unimportant or unrelated to disease."],
      ["Insufficient data", "Fewer than five classified loss-of-function plus missense records were available to the heuristic.", "It is not a negative finding about the gene."],
    ],
    precedence: "Mechanism precedence is: reviewed manual override → Gene2Phenotype → ClinVar heuristic → modifier. LOEUF adds safety context; it does not select the mechanism track.",
    readEyebrow: "Candidate evidence",
    readTitle: "Read a candidate in this order",
    readSteps: [
      ["Final track", "Start with the saved deterministic call, its decision source, and confidence explanation."],
      ["Association scores", "These describe strength of linkage in the retrieved source—not probability of therapeutic success."],
      ["Mechanism evidence", "Compare ClinVar/EVA patterns with Gene2Phenotype mechanism and inheritance fields."],
      ["Evidence count", "Check how many records were expected and returned, and whether enrichment was capped."],
      ["LOEUF", "Use it as constraint and safety context. Lower values indicate less tolerance for loss-of-function variation."],
      ["Therapeutic precedent", "A drug or trial connection supplies context, but may concern another indication and requires manual confirmation."],
      ["Warnings and sources", "Finish with missingness, truncation, retrieval dates, and primary-record links."],
    ],
    exampleEyebrow: "Hands-on walkthrough",
    exampleTitle: "Use the bundled ALS result",
    exampleIntro: "Open the offline example and inspect SOD1, TARDBP, and FUS. For each candidate, answer the same questions before reading any AI explanation.",
    questions: [
      "What is the saved final track?",
      "Which deterministic source selected it?",
      "How many evidence records were returned, and were they capped?",
      "What do the association scores say—and not say?",
      "Is there drug or trial precedent?",
      "Which uncertainty still requires human review?",
    ],
    aiEyebrow: "Optional interpretation",
    aiTitle: "Where the LLM fits",
    aiFlow: ["Saved deterministic record", "Bounded evidence packet", "Structured model output", "Server-side fact and citation validation", "Separately labeled explanation"],
    aiText: "Use AI after you have read the deterministic record. A good explanation restates the saved decision basis, cites supplied source IDs, preserves uncertainty, and clearly says what the evidence does not mean.",
    glossaryEyebrow: "Minimum vocabulary",
    glossaryTitle: "Enough biology to navigate the application",
    glossary: [
      ["Gene", "A DNA region associated with a functional product, often a protein."],
      ["RNA", "A molecule through which genetic information is expressed and processed."],
      ["ASO", "A short synthetic nucleic-acid molecule designed to bind RNA and alter its abundance or processing."],
      ["Variant", "A difference in DNA sequence."],
      ["Loss of function (LoF)", "A consequence category associated with reduced normal gene function."],
      ["Missense", "A DNA change that alters one amino acid in a protein."],
      ["ClinVar / EVA", "Sources of submitted variant records and clinical-significance classifications used by the heuristic."],
      ["Gene2Phenotype (G2P)", "Curated gene–disease mechanism and inheritance evidence."],
      ["LOEUF", "A population constraint measure; lower values indicate less tolerance for loss-of-function variation."],
      ["MONDO", "A disease ontology that provides stable identifiers for disease concepts."],
    ],
    checkEyebrow: "Knowledge check",
    checkTitle: "Test the mental model",
    reveal: "Reveal answer",
    checks: [
      ["Does the candidate with the highest association score automatically become the best therapeutic target?", "No. Association strength is one evidence dimension and is not a calibrated probability of efficacy, safety, or causal direction."],
      ["Does zero returned variant evidence mean the gene has no role in the disease?", "No. It means the checked workflow returned no qualifying records. Missingness, source scope, and unmodeled mechanisms remain important."],
      ["Can an AI summary change a candidate from modifier to knockdown?", "No. AI output is optional commentary. Only the deterministic engine creates the saved classification."],
    ],
    finalNote: "Suggested practice: explain one candidate in your own words before asking the AI explainer. Then compare your explanation with the generated one and inspect every cited source label.",
  },
  zh: {
    switchLabel: "教程语言",
    eyebrow: "应用导览",
    title: "这是一张透明的证据地图，不是临床答案。",
    intro: "请先把 ASO Compass 理解为一条软件证据流水线。即使没有医学背景，也可以理解疾病查询如何变成可追溯的候选基因记录和谨慎的研究轨道。",
    start: "打开 ALS 引导示例",
    boundaryTitle: "需要牢记的四条边界",
    boundaries: [
      ["关联不等于因果", "分数表示公开证据将某个基因与疾病联系起来，但不能证明改变该基因一定有益。"],
      ["研究轨道不等于治疗方案", "轨道是由可见规则产生的研究方向，不是针对患者、剂量或疗法的建议。"],
      ["缺失不等于阴性", "查询失败、结果被截断或没有返回记录，都不能解释为相关生物学不存在。"],
      ["AI 负责解释，不负责决策", "生成文本可以总结已保存的证据，但不能更改分类、分数、候选顺序或警告。"],
    ],
    pipelineTitle: "从查询到可审核证据",
    pipelineIntro: "可以把每个科学数据源看作特征提供方，把每个候选基因看作带有来源记录和版本信息的数据实体。",
    pipeline: [
      ["01", "疾病查询", "选择疾病或表型标识符，用本体记录固定本次分析的疾病概念。"],
      ["02", "关联检索", "Open Targets 提供通过设定阈值的候选基因及关联分数。"],
      ["03", "证据富集", "ClinVar/EVA、Gene2Phenotype、基因约束、药物和试验数据补充机制与背景。"],
      ["04", "规则引擎", "确定性的优先级与阈值把候选基因分到五条轨道之一；这不是机器学习预测。"],
      ["05", "人工审核", "界面把来源链接、缺失、上限、警告和不确定性保留在结果旁边。"],
    ],
    tracksEyebrow: "确定性输出",
    tracksTitle: "五条研究轨道",
    means: "在本应用中的含义",
    notMeans: "不能由此证明",
    tracks: [
      ["敲低（Knockdown）", "返回了足够的分类记录，且功能缺失记录占比不高于 0.25。", "不能证明存在毒性功能获得，也不能证明敲低安全或有效。"],
      ["剪接／上调（Splice / upregulation）", "返回了足够的记录，且功能缺失记录占比不低于 0.60。", "不能证明恢复表达在技术上可行或安全。"],
      ["方向不明确（Ambiguous）", "功能缺失记录占比位于两个方向阈值之间。", "它不是其他轨道的较弱版本，也不是自动决胜规则。"],
      ["修饰因子（Modifier）", "存在疾病关联，但返回证据没有提供清晰的作用方向。", "不表示该基因不重要，也不表示它与疾病无关。"],
      ["数据不足（Insufficient data）", "可供启发式规则使用的功能缺失与错义分类记录合计少于 5 条。", "这不是针对该基因的阴性结论。"],
    ],
    precedence: "机制判定优先级为：经审核的人工覆盖 → Gene2Phenotype → ClinVar 启发式规则 → 修饰因子。LOEUF 只提供安全性背景，不决定机制轨道。",
    readEyebrow: "候选基因证据",
    readTitle: "按这个顺序阅读候选基因",
    readSteps: [
      ["最终轨道", "先查看已保存的确定性分类、判定来源和置信度说明。"],
      ["关联分数", "分数描述数据源中的关联强度，不是治疗成功概率。"],
      ["机制证据", "对照 ClinVar/EVA 模式、Gene2Phenotype 机制和遗传方式字段。"],
      ["证据数量", "检查预期记录数、实际返回数，以及富集是否被限制。"],
      ["LOEUF", "把它作为基因约束与安全性背景；数值越低，通常表示越不耐受功能缺失变异。"],
      ["治疗先例", "药物或试验联系只提供背景，可能来自其他适应证，仍需人工确认。"],
      ["警告与来源", "最后检查缺失、截断、检索日期和原始记录链接。"],
    ],
    exampleEyebrow: "动手练习",
    exampleTitle: "使用内置 ALS 结果",
    exampleIntro: "打开离线示例，查看 SOD1、TARDBP 和 FUS。在阅读任何 AI 解释之前，对每个候选基因回答同一组问题。",
    questions: [
      "保存的最终轨道是什么？",
      "哪个确定性来源决定了该轨道？",
      "返回了多少条证据，结果是否被限制？",
      "关联分数说明了什么，又没有说明什么？",
      "是否存在药物或试验先例？",
      "仍有哪些不确定性需要人工审核？",
    ],
    aiEyebrow: "可选解释层",
    aiTitle: "大语言模型位于哪里",
    aiFlow: ["已保存的确定性记录", "受限的证据包", "结构化模型输出", "服务器端事实与引用验证", "单独标注的生成解释"],
    aiText: "请先阅读确定性记录，再使用 AI。合格的解释应复述已保存的判定依据，引用提供的来源标识，保留不确定性，并明确说明证据不能代表什么。",
    glossaryEyebrow: "最低限度词汇",
    glossaryTitle: "足以浏览本应用的生物学概念",
    glossary: [
      ["基因（Gene）", "与功能产物相关的 DNA 区域，产物通常是蛋白质。"],
      ["RNA", "遗传信息表达和加工过程中使用的一类分子。"],
      ["ASO", "与 RNA 结合并改变其数量或加工过程的短链人工合成核酸。"],
      ["变异（Variant）", "DNA 序列中的差异。"],
      ["功能缺失（LoF）", "与正常基因功能降低相关的一类变异后果。"],
      ["错义变异（Missense）", "导致蛋白质中一个氨基酸发生改变的 DNA 变化。"],
      ["ClinVar / EVA", "提供变异记录及临床意义分类的数据源，本应用的启发式规则会使用这些信息。"],
      ["Gene2Phenotype（G2P）", "经过整理的基因－疾病机制与遗传方式证据。"],
      ["LOEUF", "群体遗传约束指标；数值越低，通常表示越不耐受功能缺失变异。"],
      ["MONDO", "为疾病概念提供稳定标识符的疾病本体。"],
    ],
    checkEyebrow: "知识检查",
    checkTitle: "检验你的理解模型",
    reveal: "查看答案",
    checks: [
      ["关联分数最高的候选基因会自动成为最佳治疗靶点吗？", "不会。关联强度只是一个证据维度，并不是疗效、安全性或因果方向的校准概率。"],
      ["没有返回变异证据，是否表示该基因与疾病无关？", "不是。它只表示当前工作流没有返回符合条件的记录；仍需考虑数据缺失、数据源范围和未建模机制。"],
      ["AI 摘要可以把候选基因从“修饰因子”改成“敲低”吗？", "不可以。AI 输出只是可选解释；只有确定性引擎生成并保存分类。"],
    ],
    finalNote: "建议练习：先用自己的语言解释一个候选基因，再调用 AI 解释器。比较两种解释，并逐一检查生成内容引用的来源标签。",
  },
} as const;

export default function Learn({ disclaimer, onExample }: LearnProps) {
  const [language, setLanguage] = useState<Language>("en");
  const copy = COPY[language];

  return <main id="main" className="learn-view" lang={language === "zh" ? "zh-CN" : "en"}>
    <div className="learn-toolbar" role="group" aria-label={copy.switchLabel}>
      <button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")} aria-pressed={language === "en"}>English</button>
      <button className={language === "zh" ? "active" : ""} onClick={() => setLanguage("zh")} aria-pressed={language === "zh"}>简体中文</button>
    </div>

    <section className="learn-hero">
      <p className="eyebrow">{copy.eyebrow}</p>
      <h1>{copy.title}</h1>
      <p className="lede">{copy.intro}</p>
      <button className="primary-button compact" onClick={onExample}>{copy.start}<span aria-hidden="true">→</span></button>
    </section>

    <section className="learn-section" aria-labelledby="learn-boundaries">
      <h2 id="learn-boundaries">{copy.boundaryTitle}</h2>
      <div className="learn-boundaries">{copy.boundaries.map(([title, text]) => <article key={title}><h3>{title}</h3><p>{text}</p></article>)}</div>
    </section>

    <section className="learn-section" aria-labelledby="learn-pipeline">
      <h2 id="learn-pipeline">{copy.pipelineTitle}</h2><p className="learn-intro">{copy.pipelineIntro}</p>
      <ol className="learn-pipeline">{copy.pipeline.map(([number, title, text]) => <li key={number}><span>{number}</span><div><h3>{title}</h3><p>{text}</p></div></li>)}</ol>
    </section>

    <section className="learn-section" aria-labelledby="learn-tracks">
      <p className="eyebrow">{copy.tracksEyebrow}</p><h2 id="learn-tracks">{copy.tracksTitle}</h2>
      <div className="learn-track-grid">{copy.tracks.map(([title, meaning, caution], index) => <article key={title} className={`learn-track track-border-${index}`}><h3>{title}</h3><b>{copy.means}</b><p>{meaning}</p><b>{copy.notMeans}</b><p>{caution}</p></article>)}</div>
      <p className="notice learn-precedence">{copy.precedence}</p>
    </section>

    <section className="learn-section" aria-labelledby="learn-reading">
      <p className="eyebrow">{copy.readEyebrow}</p><h2 id="learn-reading">{copy.readTitle}</h2>
      <ol className="learn-reading">{copy.readSteps.map(([title, text], index) => <li key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><h3>{title}</h3><p>{text}</p></div></li>)}</ol>
    </section>

    <section className="learn-section learn-example" aria-labelledby="learn-example">
      <div><p className="eyebrow">{copy.exampleEyebrow}</p><h2 id="learn-example">{copy.exampleTitle}</h2><p>{copy.exampleIntro}</p><button className="secondary-button" onClick={onExample}>{copy.start}<span aria-hidden="true">→</span></button></div>
      <ol>{copy.questions.map((question) => <li key={question}>{question}</li>)}</ol>
    </section>

    <section className="learn-section" aria-labelledby="learn-ai">
      <p className="eyebrow">{copy.aiEyebrow}</p><h2 id="learn-ai">{copy.aiTitle}</h2>
      <div className="learn-ai-flow">{copy.aiFlow.map((step, index) => <div key={step}><span>{index + 1}</span><b>{step}</b></div>)}</div>
      <p className="learn-intro">{copy.aiText}</p>
    </section>

    <section className="learn-section glossary learn-glossary" aria-labelledby="learn-glossary">
      <p className="eyebrow">{copy.glossaryEyebrow}</p><h2 id="learn-glossary">{copy.glossaryTitle}</h2>
      <div>{copy.glossary.map(([term, definition]) => <details key={term}><summary>{term}<span>+</span></summary><p>{definition}</p></details>)}</div>
    </section>

    <section className="learn-section" aria-labelledby="learn-check">
      <p className="eyebrow">{copy.checkEyebrow}</p><h2 id="learn-check">{copy.checkTitle}</h2>
      <div className="learn-checks">{copy.checks.map(([question, answer], index) => <article key={question}><span>{String(index + 1).padStart(2, "0")}</span><h3>{question}</h3><details><summary>{copy.reveal}</summary><p>{answer}</p></details></article>)}</div>
    </section>

    <p className="learn-final-note">{copy.finalNote}</p>
    <p className="persistent-disclaimer">{language === "zh" ? "仅用于假设生成和教育，不用于临床决策。" : disclaimer}</p>
  </main>;
}
