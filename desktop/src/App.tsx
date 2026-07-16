import {
  Activity, AlertTriangle, BarChart3, CheckCircle2, Circle, CircleCheck, Cloud, Database, Download,
  FileInput, FolderOpen, Heart, ImageDown, Layers3, Play, RefreshCw, Scissors, SplitSquareHorizontal, Table2
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { invoke } from "@tauri-apps/api/core";
import { routes } from "./routes";
import {
  useWorkflowStore, type LanguageCode, type RouteKey, type TaskKey, type TaskResult,
  type WorkflowSummary, type FrequencyParams, type SentimentParams, type LdaParams, type StmParams
} from "./state/workflowStore";

const languageLabels: Record<LanguageCode, string> = { zh: "中文", en: "英文" };

const pageCopy: Record<RouteKey, { title: string; eyebrow: string; description: string }> = {
  welcome: { title: "历史文献主题分析工作台", eyebrow: "数字人文研究", description: "用一张文献表完成中英文历史文本的清洗、分语言建模、比较和导出。" },
  import: { title: "导入文献表", eyebrow: "v2 单表数据模型", description: "一行一篇文献；doc_id、text、language 为必填字段。" },
  clean: { title: "清洗与分词", eyebrow: "语言感知预处理", description: "中文使用 jieba，英文使用轻量规范化与拉丁词分词，原文始终保留。" },
  frequency: { title: "词频分析与词云", eyebrow: "v2.1 双语宏观观察", description: "基于清洗后的 tokens 分别统计总词频和文档频率，并生成可复核词云。" },
  sentiment: { title: "情感分析", eyebrow: "v2.2 词典与规则", description: "基于清洗后的 tokens 用透明的情感词典与否定、程度规则计算文献情感倾向。" },
  lda: { title: "LDA 主题建模", eyebrow: "按语言独立训练", description: "中文和英文使用独立词表与模型，结果不会相互覆盖。" },
  stm: { title: "STM 结构主题模型", eyebrow: "历史元数据协变量", description: "从来源、年份、文类及自定义字段中选择协变量。" },
  compare: { title: "对比分析", eyebrow: "动态历史维度", description: "只在同一语言模型内按来源、年份或自定义元数据聚合主题。" },
  export: { title: "导出结果", eyebrow: "zh/en 分目录", description: "公共文献表位于根目录，两种语言的语料和模型结果分别写入子目录。" }
};

export function App() {
  const state = useWorkflowStore();
  const page = pageCopy[state.activeRoute];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark" aria-label="历史文献主题分析工具 logo"><BarChart3 size={24} /></div>
          <div><div className="brand-title">主题分析</div><div className="brand-subtitle">历史文献工作台 v2.2</div></div>
        </div>
        <nav className="nav-list" aria-label="主导航">
          {routes.map(({ key, label, description, Icon }) => (
            <button key={key} className={key === state.activeRoute ? "nav-item active" : "nav-item"} onClick={() => state.setActiveRoute(key)} type="button">
              <Icon size={19} /><span><strong>{label}</strong><small>{description}</small></span>
            </button>
          ))}
        </nav>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div><span className="eyebrow">{page.eyebrow}</span><h1>{page.title}</h1></div>
          <div className="session-strip"><span><Database size={16} />{state.projectName}</span><span><FolderOpen size={16} />{state.outputDir || "未设置输出目录"}</span></div>
        </header>
        <section className="hero-band"><div><p>{page.description}</p><span>中英文分别建模，不进行自动语言识别或跨语言主题对齐。</span></div><div className="task-pill"><Activity size={17} />schema v2</div></section>
        <section className="status-grid" aria-label="流程状态">
          <StatusItem label="导入" active={state.workflow.imported} />
          <StatusItem label="清洗" active={state.workflow.cleaned} />
          <StatusItem label="词频" active={state.workflow.frequencyDone} />
          <StatusItem label="情感" active={state.workflow.sentimentDone} />
          <StatusItem label="LDA" active={state.workflow.ldaDone} />
          <StatusItem label="STM" active={state.workflow.stmDone} />
        </section>
        {state.activeRoute === "welcome" ? <WelcomePage /> : <WorkflowPage route={state.activeRoute} />}
      </main>
    </div>
  );
}

function WelcomePage() {
  const { summary, tasks, setActiveRoute } = useWorkflowStore();
  return (
    <div className="page-stack">
      <section className="metric-grid">
        <Metric label="文献总数" value={summary.documentRows || "待导入"} />
        <Metric label="中文 / 英文" value={`${summary.languageRows.zh} / ${summary.languageRows.en}`} />
        <Metric label="有效语料" value={summary.cleanDocuments || "待清洗"} />
        <Metric label="导出文件" value={summary.exportFiles || "待导出"} />
      </section>
      <section className="workflow-board">
        {routes.filter(({ key }) => key !== "welcome").map(({ key, label, description, Icon }) => (
          <button className="workflow-step" key={key} type="button" onClick={() => setActiveRoute(key)}>
            <Icon size={20} /><span><strong>{label}</strong><small>{description}</small></span><TaskBadge task={tasks[key as TaskKey]} />
          </button>
        ))}
      </section>
    </div>
  );
}

function WorkflowPage({ route }: { route: Exclude<RouteKey, "welcome"> }) {
  const state = useWorkflowStore();
  const task = state.tasks[route];
  const blocked = !canRun(route, state.workflow);
  return (
    <div className="page-stack">
      {route === "import" && <ImportPage />}
      {route === "clean" && <CleanPage />}
      {route === "frequency" && <FrequencyPage />}
      {route === "sentiment" && <SentimentPage />}
      {route === "lda" && <LdaPage />}
      {route === "stm" && <StmPage />}
      {route === "compare" && <ComparePage />}
      {route === "export" && <ExportPage />}
      {blocked && <p className="hint-text"><AlertTriangle size={15} />请先完成前置步骤。</p>}
      <TaskStatus task={task} />
    </div>
  );
}

function ImportPage() {
  const { importConfig, setImportConfig, chooseImportFile, runBackendTask, tasks, results, summary } = useWorkflowStore();
  const result = results.import;
  const preview = toPreview(result?.preview);
  const mapping = toRecord(result?.mapping);
  return (
    <>
      <section className="control-panel import-panel">
        <div className="panel-title"><FileInput size={18} />单一文献表</div>
        <div className="table-source-card">
          <span className="source-heading"><Table2 size={20} /><strong>CSV / Excel</strong></span>
          <span className="source-fields">一行一篇文献；必须包含唯一编号、正文和语言</span>
          <div className="path-input-row"><input value={importConfig.dataPath} placeholder="E:/data/historical_documents.xlsx" onChange={(event) => setImportConfig({ dataPath: event.target.value })} /><button className="browse-button" type="button" onClick={chooseImportFile}><FolderOpen size={16} />选择文件</button></div>
        </div>
        <div className="field-selector-grid">
          {(["doc_id", "text", "language"] as const).map((field) => (
            <label key={field}><span>{field} 对应列名</span><input value={importConfig.fieldMapping[field]} onChange={(event) => setImportConfig({ fieldMapping: { ...importConfig.fieldMapping, [field]: event.target.value } })} /></label>
          ))}
        </div>
        <p className="field-note">language 接受 zh、en、中文、英文、Chinese、English 等常见写法；系统不会猜测缺失语言。</p>
        <button className="primary-button" type="button" disabled={!importConfig.dataPath.trim() || tasks.import.status === "running"} onClick={() => runBackendTask("import")}><Play size={17} />校验并导入</button>
      </section>
      <section className="metric-grid">
        <Metric label="文献总数" value={summary.documentRows || "待导入"} />
        <Metric label="中文" value={summary.languageRows.zh} />
        <Metric label="英文" value={summary.languageRows.en} />
        <Metric label="自定义字段" value={toStringArray(result?.unrecognizedColumns).length} />
      </section>
      <section className="result-section">
        <div className="result-heading"><Table2 size={19} /><span>字段映射与预览</span></div>
        {Object.keys(mapping).length > 0 && <div className="mapping-list">{Object.entries(mapping).map(([standard, original]) => <span key={standard}><strong>{standard}</strong> ← {String(original)}</span>)}</div>}
        <ResultTable columns={preview.columns ?? []} rows={preview.rows ?? []} emptyText="成功导入后显示前 10 行。" />
      </section>
    </>
  );
}

function CleanPage() {
  const store = useWorkflowStore();
  const config = store.configs.clean;
  const result = store.results.clean;
  const preview = toPreview(result?.preview);
  const [previewLanguage, setPreviewLanguage] = useState<LanguageCode>("zh");
  const rows = (preview.rows ?? []).filter((row) => row.language === previewLanguage);
  const languageStats = toRecord(result?.languages);
  const updateCommon = (values: Partial<typeof config>) => store.setTaskConfig("clean", values);
  return (
    <>
      <section className="control-panel">
        <div className="panel-title"><Scissors size={18} />通用清洗</div>
        <div className="parameter-form parameter-grid">
          <Toggle label="OCR 噪声符号清理" checked={config.ocrClean} onChange={(ocrClean) => updateCommon({ ocrClean })} />
          <Toggle label="移除标点" checked={config.removePunct} onChange={(removePunct) => updateCommon({ removePunct })} />
          <Toggle label="移除数字" checked={config.removeNumbers} onChange={(removeNumbers) => updateCommon({ removeNumbers })} />
          <Toggle label="移除空语料" checked={config.removeEmpty} onChange={(removeEmpty) => updateCommon({ removeEmpty })} />
          <Toggle label="同语言正文去重" checked={config.removeDuplicates} onChange={(removeDuplicates) => updateCommon({ removeDuplicates })} />
          <NumberField label="最短正文长度" value={config.minTextLength} min={1} max={10000} onChange={(minTextLength) => updateCommon({ minTextLength })} />
          <NumberField label="最小词频" value={config.minTokenFreq} min={1} max={100} onChange={(minTokenFreq) => updateCommon({ minTokenFreq })} />
        </div>
        <div className="language-clean-grid">
          <LanguageCleanPanel language="zh" />
          <LanguageCleanPanel language="en" />
        </div>
        <button className="primary-button" type="button" disabled={!store.workflow.imported || store.tasks.clean.status === "running"} onClick={() => store.runBackendTask("clean")}><Play size={17} />清洗全部文献</button>
      </section>
      <section className="metric-grid">
        {(["zh", "en"] as LanguageCode[]).map((language) => {
          const stats = toRecord(languageStats[language]);
          return <Metric key={language} label={`${languageLabels[language]}词元`} value={Number(stats.totalTokens ?? 0)} />;
        })}
        <Metric label="去重文献" value={toStringArray(toRecord(result?.report).removedDuplicateDocIds).length} />
        <Metric label="空语料文献" value={toStringArray(toRecord(result?.report).removedEmptyDocIds).length} />
      </section>
      <section className="result-section">
        <div className="result-heading"><Scissors size={19} /><span>清洗预览</span><LanguageSelect value={previewLanguage} onChange={setPreviewLanguage} /></div>
        <CleanPreview rows={rows} />
      </section>
    </>
  );
}

function LanguageCleanPanel({ language }: { language: LanguageCode }) {
  const store = useWorkflowStore();
  const config = store.configs.clean[language];
  const update = (values: Partial<typeof config>) => store.setLanguageCleanConfig(language, values);
  return (
    <fieldset className="parameter-fieldset">
      <legend>{languageLabels[language]}设置</legend>
      <Toggle label="使用内置停用词" checked={config.useDefaultStopwords} onChange={(useDefaultStopwords) => update({ useDefaultStopwords })} />
      <NumberField label="最短 token 长度" value={config.minTokenLength} min={1} max={20} onChange={(minTokenLength) => update({ minTokenLength })} />
      {language === "zh" ? <>
        <Toggle label="繁体转简体（仅清洗文本）" checked={config.traditionalToSimplified === true} onChange={(traditionalToSimplified) => update({ traditionalToSimplified })} />
        <PathRow value={config.customDictPath ?? ""} placeholder="中文自定义词典（可选）" onChange={(customDictPath) => update({ customDictPath })} onBrowse={() => store.chooseConfigPath("customDict", "zh")} />
      </> : <>
        <Toggle label="小写化" checked={config.lowercase !== false} onChange={(lowercase) => update({ lowercase })} />
        <Toggle label="修复跨行连字符" checked={config.repairHyphenation !== false} onChange={(repairHyphenation) => update({ repairHyphenation })} />
      </>}
      <textarea value={config.stopwordsText} placeholder="自定义停用词，每行一个" onChange={(event) => update({ stopwordsText: event.target.value })} />
      <button className="browse-button" type="button" onClick={() => store.chooseConfigPath("stopwords", language)}><FileInput size={15} />加载停用词</button>
    </fieldset>
  );
}

function FrequencyPage() {
  const store = useWorkflowStore();
  const language = store.configs.frequencyLanguage;
  const config = store.configs.frequency[language];
  const result = store.results.frequency[language];
  const rows = toRows(result?.rows);
  const imageData = typeof result?.wordCloudPngBase64 === "string" ? result.wordCloudPngBase64 : "";
  const update = (values: Partial<FrequencyParams>) => store.setModelConfig("frequency", language, values);
  const saveCloud = async () => {
    if (!imageData) return;
    const path = await invoke<string | null>("select_chart_png_path", { defaultName: `${language}_word_cloud.png` });
    if (path) await invoke("save_chart_png", { path, base64Data: imageData });
  };
  const maxValue = Math.max(1, ...rows.map((row) => Number(row[config.sortBy] ?? 0)));
  return <>
    <section className="control-panel">
      <div className="panel-title"><Cloud size={18} />词频参数</div>
      <LanguageSelect value={language} onChange={(value) => store.setModelLanguage("frequency", value)} />
      <div className="parameter-form parameter-grid">
        <SelectField label="排序指标" value={config.sortBy} options={[["term_frequency", "总词频"], ["document_frequency", "文档频率"]]} onChange={(sortBy) => update({ sortBy: sortBy as FrequencyParams["sortBy"] })} />
        <NumberField label="Top N" value={config.topN} min={1} max={500} onChange={(topN) => update({ topN })} />
        <NumberField label="最低总词频" value={config.minTermFrequency} min={1} max={1000000} onChange={(minTermFrequency) => update({ minTermFrequency })} />
        <NumberField label="最低文档频率" value={config.minDocumentFrequency} min={1} max={1000000} onChange={(minDocumentFrequency) => update({ minDocumentFrequency })} />
      </div>
      <p className="field-note">词云始终按总词频设置大小；相同语料和参数使用固定随机种子生成稳定结果。</p>
      <button className="primary-button" type="button" disabled={!store.workflow.cleaned || store.tasks.frequency.status === "running" || store.summary.totalTokens[language] === 0} onClick={() => store.runBackendTask("frequency")}><Play size={17} />分析{languageLabels[language]}词频</button>
    </section>
    <section className="metric-grid">
      <Metric label="分析文献" value={Number(result?.documents ?? 0) || "待分析"} />
      <Metric label="词元总数" value={Number(result?.totalTokens ?? 0)} />
      <Metric label="唯一词数" value={Number(result?.uniqueWords ?? 0)} />
      <Metric label="阈值后词数" value={Number(result?.filteredWords ?? 0)} />
    </section>
    <section className="result-section">
      <div className="result-heading"><BarChart3 size={19} /><span>高频词柱状图</span></div>
      {!rows.length ? <Empty text="完成分析后显示高频词。" /> : <div className="frequency-bars">{rows.slice(0, 30).map((row) => {
        const value = Number(row[config.sortBy] ?? 0);
        return <div className="frequency-bar" key={String(row.word)}><span>{String(row.word)}</span><div><i style={{ width: `${Math.max(2, value / maxValue * 100)}%` }} /></div><strong>{value}</strong></div>;
      })}</div>}
      <ResultTable columns={["rank", "word", "term_frequency", "document_frequency", "document_frequency_ratio", "token_share"]} rows={rows} />
    </section>
    <section className="result-section">
      <div className="result-heading"><Cloud size={19} /><span>词云</span>{imageData && <button className="ghost-button" type="button" onClick={saveCloud}><ImageDown size={15} />保存 PNG</button>}</div>
      {imageData ? <img className="word-cloud-image" src={`data:image/png;base64,${imageData}`} alt={`${languageLabels[language]}词云`} /> : <Empty text="完成分析后显示词云。" />}
    </section>
  </>;
}

function SentimentPage() {
  const store = useWorkflowStore();
  const language = store.configs.sentimentLanguage;
  const config = store.configs.sentiment[language];
  const result = store.results.sentiment[language];
  const summary = toRecord(result?.summary);
  const distribution = toRecord(summary.distribution);
  const rows = toRows(result?.rows);
  const aggregation = toRows(result?.aggregation);
  const fields = toMetadataFields(store.results.import?.metadataFields);
  const update = (values: Partial<SentimentParams>) => store.setModelConfig("sentiment", language, values);
  const counts = {
    positive: Number(distribution.positive ?? 0),
    neutral: Number(distribution.neutral ?? 0),
    negative: Number(distribution.negative ?? 0)
  };
  const totalDocs = Math.max(1, counts.positive + counts.neutral + counts.negative);
  const bars: Array<[string, number, string]> = [
    ["正面", counts.positive, "positive"], ["中性", counts.neutral, "neutral"], ["负面", counts.negative, "negative"]
  ];
  return <>
    <section className="control-panel">
      <div className="panel-title"><Heart size={18} />情感参数</div>
      <LanguageSelect value={language} onChange={(value) => store.setModelLanguage("sentiment", value)} />
      <div className="parameter-form parameter-grid">
        <NumberField label="正面阈值" value={config.positiveThreshold} min={0} max={1} step={0.01} onChange={(positiveThreshold) => update({ positiveThreshold })} />
        <NumberField label="负面阈值" value={config.negativeThreshold} min={-1} max={0} step={0.01} onChange={(negativeThreshold) => update({ negativeThreshold })} />
        <NumberField label="证据词上限" value={config.topEvidence} min={1} max={30} onChange={(topEvidence) => update({ topEvidence })} />
        <SelectField label="聚合维度（可选）" value={config.groupBy} options={[["", "不聚合"], ...fields.map(({ field }) => [field, field] as const)]} onChange={(groupBy) => update({ groupBy })} />
      </div>
      <div className="parameter-form parameter-grid">
        <Toggle label="启用否定词翻转" checked={config.useNegation} onChange={(useNegation) => update({ useNegation })} />
        <Toggle label="启用程度副词缩放" checked={config.useDegree} onChange={(useDegree) => update({ useDegree })} />
      </div>
      <div className="language-clean-grid">
        <fieldset className="parameter-fieldset"><legend>自定义正面词（每行一个）</legend><textarea value={config.positiveText} placeholder="覆盖或补充内置正面词典" onChange={(event) => update({ positiveText: event.target.value })} /></fieldset>
        <fieldset className="parameter-fieldset"><legend>自定义负面词（每行一个）</legend><textarea value={config.negativeText} placeholder="覆盖或补充内置负面词典" onChange={(event) => update({ negativeText: event.target.value })} /></fieldset>
      </div>
      <p className="field-note">情感分类是算法测量结果，请结合文本证据与历史语境解释；相同语料和词典配置产生稳定结果。</p>
      <button className="primary-button" type="button" disabled={!store.workflow.cleaned || store.tasks.sentiment.status === "running" || store.summary.totalTokens[language] === 0} onClick={() => store.runBackendTask("sentiment")}><Play size={17} />分析{languageLabels[language]}情感</button>
    </section>
    <section className="metric-grid">
      <Metric label="分析文献" value={Number(summary.documents ?? 0) || "待分析"} />
      <Metric label="平均情感分" value={typeof summary.averageScore === "number" ? summary.averageScore.toFixed(3) : "0.000"} />
      <Metric label="命中情感词" value={Number(summary.matchedWords ?? 0)} />
      <Metric label="词典规模" value={Number(summary.lexiconSize ?? 0)} />
    </section>
    <section className="result-section">
      <div className="result-heading"><BarChart3 size={19} /><span>情感分布</span></div>
      {!rows.length ? <Empty text="完成分析后显示情感分布。" /> : <div className="frequency-bars">{bars.map(([label, value, tone]) => (
        <div className={`frequency-bar sentiment-${tone}`} key={label}><span>{label}</span><div><i style={{ width: `${Math.max(2, value / totalDocs * 100)}%` }} /></div><strong>{value}</strong></div>
      ))}</div>}
      {aggregation.length > 0 && <ResultTable columns={["group", "documents", "positive", "neutral", "negative", "average_score"]} rows={aggregation} />}
    </section>
    <section className="result-section">
      <div className="result-heading"><Heart size={19} /><span>文献情感明细</span></div>
      <ResultTable columns={["doc_id", "sentiment_label", "score", "positive_hits", "negative_hits", "positive_terms", "negative_terms"]} rows={rows} emptyText="完成分析后显示逐篇情感得分与证据词。" />
    </section>
  </>;
}

function LdaPage() {
  const store = useWorkflowStore();
  const language = store.configs.ldaLanguage;
  const config = store.configs.lda[language];
  const result = store.results.lda[language];
  return (
    <>
      <ModelControls title="LDA 参数" language={language} onLanguage={(value) => store.setModelLanguage("lda", value)}>
        <LdaFields config={config} onChange={(values) => store.setModelConfig("lda", language, values)} />
      </ModelControls>
      <button className="primary-button" type="button" disabled={!store.workflow.cleaned || store.tasks.lda.status === "running" || store.summary.languageRows[language] === 0} onClick={() => store.runBackendTask("lda")}><Play size={17} />训练{languageLabels[language]} LDA</button>
      <ModelResult title={`${languageLabels[language]} LDA 结果`} result={result} language={language} />
    </>
  );
}

function StmPage() {
  const store = useWorkflowStore();
  const language = store.configs.stmLanguage;
  const config = store.configs.stm[language];
  const covariates = toCovariates(store.results.import?.covariates);
  return (
    <>
      <ModelControls title="STM 参数" language={language} onLanguage={(value) => store.setModelLanguage("stm", value)}>
        <StmFields config={config} onChange={(values) => store.setModelConfig("stm", language, values)} covariates={covariates} />
        <div className={`environment-banner ${store.stmEnvironment.available === true ? "available" : store.stmEnvironment.available === false ? "unavailable" : ""}`}><strong>{store.stmEnvironment.available === true ? "R 环境可用" : "R 环境待检查"}</strong><span>{store.stmEnvironment.message}</span><button className="ghost-button" type="button" onClick={store.checkStmEnvironment}><Activity size={15} />检查环境</button></div>
      </ModelControls>
      <button className="primary-button" type="button" disabled={!store.workflow.cleaned || store.tasks.stm.status === "running" || store.summary.languageRows[language] === 0} onClick={() => store.runBackendTask("stm")}><Play size={17} />训练{languageLabels[language]} STM</button>
      <ModelResult title={`${languageLabels[language]} STM 结果`} result={store.results.stm[language]} language={language} showPrevalence />
    </>
  );
}

function ComparePage() {
  const store = useWorkflowStore();
  const config = store.configs.compare;
  const fields = toMetadataFields(store.results.import?.metadataFields);
  const axisField = fields.some((field) => field.field === config.axisField) ? config.axisField : fields[0]?.field ?? "";
  const topics = toTopics(store.results[config.model][config.language]?.topics);
  const result = store.results.compare[config.language];
  const filterEntry = Object.entries(config.filters)[0] ?? ["", "__all__"];
  const filterField = filterEntry[0];
  const filterValues = fields.find((field) => field.field === filterField)?.values ?? [];
  const update = (values: Partial<typeof config>) => store.setTaskConfig("compare", values);
  return (
    <>
      <section className="control-panel">
        <div className="panel-title"><SplitSquareHorizontal size={18} />同语言主题对比</div>
        <div className="parameter-form parameter-grid">
          <LanguageSelect value={config.language} onChange={(language) => update({ language })} />
          <SelectField label="主题模型" value={config.model} options={[["lda", "LDA"], ["stm", "STM"]]} onChange={(model) => update({ model: model as "lda" | "stm" })} />
          <SelectField label="聚合维度" value={axisField} options={fields.map(({ field }) => [field, field] as const)} onChange={(value) => update({ axisField: value })} />
          <SelectField label="主题指标" value={config.metricField} options={[["__all__", "全部主题"], ...topics.map((topic) => [`topic_${topic.topic_id}`, topic.label ?? `主题 ${topic.topic_id + 1}`] as const)]} onChange={(metricField) => update({ metricField })} />
          <SelectField label="筛选字段（可选）" value={filterField} options={[["", "不筛选"], ...fields.filter(({ values }) => values.length > 0).map(({ field }) => [field, field] as const)]} onChange={(field) => update({ filters: field ? { [field]: "__all__" } : {} })} />
          {filterField && <SelectField label="筛选值" value={filterEntry[1]} options={[["__all__", "全部"], ...filterValues.map((value) => [value, value] as const)]} onChange={(value) => update({ filters: { [filterField]: value } })} />}
          <NumberField label="每主题代表文献数" value={config.representativeLimit} min={1} max={20} onChange={(representativeLimit) => update({ representativeLimit })} />
        </div>
        <p className="field-note">不同语言使用不同词表与主题编号，系统不会把中英文 topic_0 当作同一主题。</p>
        <button className="primary-button" type="button" disabled={!axisField || !(config.model === "lda" ? store.languageWorkflow[config.language].ldaDone : store.languageWorkflow[config.language].stmDone)} onClick={() => { if (axisField !== config.axisField) update({ axisField }); store.runBackendTask("compare"); }}><Play size={17} />生成对比</button>
      </section>
      <CompareResult result={result} />
    </>
  );
}

function ExportPage() {
  const store = useWorkflowStore();
  const config = store.configs.export;
  const update = (values: Partial<typeof config>) => store.setTaskConfig("export", values);
  const items = [
    ["documents", "标准化文献表"], ["cleaned_documents", "清洗后文献"], ["tokens_corpus", "分语言语料"],
    ["word_frequency", "词频明细"], ["word_cloud", "词云 PNG"],
    ["sentiment_documents", "情感文献明细"], ["sentiment_summary", "情感聚合摘要"],
    ["lda_topic_word", "LDA 主题词"], ["lda_doc_topic", "LDA 文献主题"], ["lda_coherence", "LDA 一致性"],
    ["stm_topic_word", "STM 主题词"], ["stm_doc_topic", "STM 文献主题"], ["stm_prevalence", "STM prevalence"],
    ["session_config", "v2 会话配置"]
  ];
  return (
    <>
      <section className="control-panel">
        <div className="panel-title"><Download size={18} />导出配置</div>
        <TextField label="项目名称" value={config.projectName} onChange={(projectName) => update({ projectName })} />
        <PathRow value={config.outputDir} placeholder="选择输出目录" onChange={(outputDir) => update({ outputDir })} onBrowse={() => store.chooseConfigPath("outputDir")} />
        <fieldset className="parameter-fieldset"><legend>导出语言</legend>{(["zh", "en"] as LanguageCode[]).map((language) => <Toggle key={language} label={languageLabels[language]} checked={config.languages.includes(language)} onChange={(checked) => update({ languages: checked ? [...new Set([...config.languages, language])] : config.languages.filter((item) => item !== language) })} />)}</fieldset>
        <div className="export-item-grid">{items.map(([key, label]) => <Toggle key={key} label={label} checked={config.items.includes(key)} onChange={(checked) => update({ items: checked ? [...new Set([...config.items, key])] : config.items.filter((item) => item !== key) })} />)}</div>
        <p className="field-note">导出会按保存的配置和固定随机种子重建所选模型；STM 未配置时会单独报告失败，不影响其他文件。</p>
        <button className="primary-button" type="button" disabled={!store.workflow.imported || !config.outputDir.trim() || !config.items.length || !config.languages.length} onClick={() => store.runBackendTask("export")}><Download size={17} />导出 v2 结果</button>
      </section>
      <ExportResult result={store.results.export} logs={store.logs} onClear={store.clearLogs} />
    </>
  );
}

function ModelControls({ title, language, onLanguage, children }: { title: string; language: LanguageCode; onLanguage: (language: LanguageCode) => void; children: ReactNode }) {
  return <section className="control-panel"><div className="panel-title"><Layers3 size={18} />{title}</div><LanguageSelect value={language} onChange={onLanguage} />{children}</section>;
}

function LdaFields({ config, onChange }: { config: LdaParams; onChange: (values: Partial<LdaParams>) => void }) {
  return <div className="parameter-form parameter-grid">
    <NumberField label="主题数" value={config.numTopics} min={2} max={100} onChange={(numTopics) => onChange({ numTopics })} />
    <NumberField label="训练轮数" value={config.passes} min={1} max={500} onChange={(passes) => onChange({ passes })} />
    <NumberField label="单轮迭代" value={config.iterations} min={10} max={2000} onChange={(iterations) => onChange({ iterations })} />
    <NumberField label="随机种子" value={config.randomState} min={0} max={99999} onChange={(randomState) => onChange({ randomState })} />
    <NumberField label="最小文档频率" value={config.minDocFreq} min={1} max={100} onChange={(minDocFreq) => onChange({ minDocFreq })} />
    <NumberField label="最大文档频率比例" value={config.maxDocFreqRatio} min={0.01} max={1} step={0.05} onChange={(maxDocFreqRatio) => onChange({ maxDocFreqRatio })} />
  </div>;
}

function StmFields({ config, onChange, covariates }: { config: StmParams; onChange: (values: Partial<StmParams>) => void; covariates: Array<{ field: string; available: boolean; reason?: string }> }) {
  return <div className="parameter-form parameter-grid">
    <NumberField label="主题数" value={config.numTopics} min={2} max={100} onChange={(numTopics) => onChange({ numTopics })} />
    <NumberField label="最大 EM 迭代" value={config.maxEmIterations} min={10} max={500} onChange={(maxEmIterations) => onChange({ maxEmIterations })} />
    <NumberField label="随机种子" value={config.randomState} min={0} max={99999} onChange={(randomState) => onChange({ randomState })} />
    <TextField label="prevalence 公式" value={config.prevalenceFormula} placeholder="~ 1" onChange={(prevalenceFormula) => onChange({ prevalenceFormula })} />
    <SelectField label="content 协变量" value={config.contentCovariate} options={[["", "不使用"], ...covariates.filter((item) => item.available).map((item) => [item.field, item.field] as const)]} onChange={(contentCovariate) => onChange({ contentCovariate })} />
  </div>;
}

function ModelResult({ title, result, language, showPrevalence = false }: { title: string; result: TaskResult; language: LanguageCode; showPrevalence?: boolean }) {
  const topics = toTopics(result?.topics);
  const preview = toPreview(result?.documentTopics);
  const [message, setMessage] = useState("");
  const openVis = async () => {
    setMessage("正在生成…");
    try {
      const response = await invoke<{ ok: boolean; data?: Record<string, unknown>; error?: { message?: string } }>("run_python_task", { task: "lda-vis", payload: { language } });
      if (!response.ok) throw new Error(response.error?.message || "生成失败");
      setMessage(String(response.data?.message ?? "已打开"));
    } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); }
  };
  return <section className="result-section">
    <div className="result-heading"><Layers3 size={19} /><span>{title}</span>{typeof result?.coherence === "number" && <strong>Coherence：{result.coherence.toFixed(4)}</strong>}</div>
    {!topics.length ? <Empty text="训练完成后显示该语言的主题与文献主题分布。" /> : <>
      <div className="topic-card-grid">{topics.map((topic) => <article className="topic-card" key={topic.topic_id}><strong>主题 {topic.topic_id + 1}</strong><div className="topic-words">{topic.words.slice(0, 10).map(([word, weight]) => <span key={word}>{word}{weight > 0 ? `（${weight.toFixed(3)}）` : ""}</span>)}</div></article>)}</div>
      {!showPrevalence && <div className="button-row"><button className="ghost-button" type="button" onClick={openVis}><Activity size={15} />打开 pyLDAvis</button><span className="field-note">{message}</span></div>}
      {showPrevalence && <ResultTable columns={toStringArray(result?.prevalenceColumns)} rows={toRows(result?.prevalence)} emptyText="当前没有 prevalence 表。" />}
      <ResultTable columns={preview.columns ?? []} rows={preview.rows ?? []} />
    </>}
  </section>;
}

function CompareResult({ result }: { result: TaskResult }) {
  const rows = toRows(result?.rows);
  const axis = typeof result?.axisField === "string" ? result.axisField : "source_name";
  const topics = toStringArray(result?.topicColumns);
  const groups = toRecord(result?.representativeArticles);
  const articles: Array<Record<string, unknown> & { _topic: string }> = Object.entries(groups).flatMap(([topic, value]) => toRows(value).map((row) => ({ ...row, _topic: topic })));
  return <section className="result-section"><div className="result-heading"><SplitSquareHorizontal size={19} /><span>主题分布对比</span></div>{!rows.length ? <Empty text="生成后显示聚合表和代表文献。" /> : <><ResultTable columns={[axis, ...topics]} rows={rows} /><div className="article-list">{articles.map((article, index) => <article className="article-item" key={`${article._topic}-${article.doc_id ?? index}`}><strong>{String(article._topic).replace("topic_", "主题 ")}</strong><span>{String(article.title ?? article.doc_id ?? "（无题名）")}</span><small>{String(article.source_name ?? "")} · {String(article.creator ?? "")}</small></article>)}</div></>}</section>;
}

function ExportResult({ result, logs, onClear }: { result: TaskResult; logs: string[]; onClear: () => void }) {
  const exported = toStringArray(result?.exported);
  const errors = toRows(result?.errors);
  return <section className="result-section"><div className="result-heading"><Download size={19} /><span>导出结果</span></div><div className="export-result-layout"><div>{exported.length ? <ul className="file-result-list">{exported.map((file) => <li key={file}><CheckCircle2 size={15} />{file}</li>)}</ul> : <Empty text="尚未导出。" />}{errors.length > 0 && <ul className="error-result-list">{errors.map((error, index) => <li key={index}><AlertTriangle size={15} />{String(error.language ?? "公共")} / {String(error.key)}：{String(error.error)}</li>)}</ul>}</div><div className="log-panel"><div className="log-header"><h3>处理日志</h3><button className="ghost-button" type="button" onClick={onClear}>清空</button></div><pre>{logs.join("\n") || "暂无日志"}</pre></div></div></section>;
}

function CleanPreview({ rows }: { rows: Array<Record<string, unknown>> }) {
  const [index, setIndex] = useState(0);
  const safe = rows.length ? Math.min(index, rows.length - 1) : 0;
  const row = rows[safe];
  if (!row) return <Empty text="完成清洗后显示逐篇预览。" />;
  return <><label className="parameter-field article-selector"><span>选择文献</span><select value={safe} onChange={(event) => setIndex(Number(event.target.value))}>{rows.map((item, rowIndex) => <option key={String(item.doc_id ?? rowIndex)} value={rowIndex}>{String(item.title ?? item.doc_id)}</option>)}</select></label><div className="text-preview-grid"><TextPreview title="原文" text={String(row.text ?? "")} /><TextPreview title="清洗后文本" text={String(row.cleaned_text ?? "")} /><TextPreview title={`tokens（${row.token_count ?? 0}）`} text={String(row.tokens ?? "").split(" ").join(" / ")} /></div></>;
}

function TaskStatus({ task }: { task: ReturnType<typeof useWorkflowStore.getState>["tasks"][TaskKey] }) {
  return <section className={`task-status-panel ${task.status}`}><div><TaskBadge task={task} /><strong>{task.phase}</strong></div><p>{task.message}</p>{task.error && <div className="error-callout"><AlertTriangle size={16} />{task.error}</div>}</section>;
}
function TaskBadge({ task }: { task: ReturnType<typeof useWorkflowStore.getState>["tasks"][TaskKey] }) {
  if (task.status === "running") return <span className="task-badge running"><RefreshCw size={14} />运行中</span>;
  if (task.status === "succeeded") return <span className="task-badge succeeded"><CircleCheck size={14} />已完成</span>;
  if (task.status === "failed") return <span className="task-badge failed"><AlertTriangle size={14} />失败</span>;
  return <span className="task-badge"><Circle size={14} />待运行</span>;
}
function StatusItem({ label, active }: { label: string; active: boolean }) { return <div className={active ? "status-item active" : "status-item"}>{active ? <CircleCheck size={17} /> : <Circle size={17} />}<span>{label}</span></div>; }
function Metric({ label, value }: { label: string; value: ReactNode }) { return <article className="metric-card"><span>{label}</span><strong>{value}</strong></article>; }
function Empty({ text }: { text: string }) { return <p className="empty-result">{text}</p>; }
function TextPreview({ title, text }: { title: string; text: string }) { return <article className="text-preview"><strong>{title}</strong><div>{text || "（空）"}</div></article>; }

function LanguageSelect({ value, onChange }: { value: LanguageCode; onChange: (value: LanguageCode) => void }) { return <SelectField label="语料语言" value={value} options={[["zh", "中文"], ["en", "英文"]]} onChange={(language) => onChange(language as LanguageCode)} />; }
function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) { return <label className="toggle-field"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /><span>{label}</span></label>; }
function NumberField({ label, value, min, max, step = 1, onChange }: { label: string; value: number; min: number; max: number; step?: number; onChange: (value: number) => void }) { return <label className="parameter-field"><span>{label}</span><input type="number" value={value} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))} /></label>; }
function TextField({ label, value, placeholder = "", onChange }: { label: string; value: string; placeholder?: string; onChange: (value: string) => void }) { return <label className="parameter-field"><span>{label}</span><input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} /></label>; }
function SelectField({ label, value, options, onChange }: { label: string; value: string; options: Array<readonly [string, string]>; onChange: (value: string) => void }) { return <label className="parameter-field"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.length ? options.map(([key, text]) => <option key={key} value={key}>{text}</option>) : <option value="">暂无可用字段</option>}</select></label>; }
function PathRow({ value, placeholder, onChange, onBrowse }: { value: string; placeholder: string; onChange: (value: string) => void; onBrowse: () => void }) { return <div className="path-input-row"><input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} /><button className="browse-button" type="button" onClick={onBrowse}><FolderOpen size={15} />选择</button></div>; }

function ResultTable({ columns, rows, emptyText = "暂无数据" }: { columns: string[]; rows: Array<Record<string, unknown>>; emptyText?: string }) {
  const visible = columns.slice(0, 18);
  if (!visible.length || !rows.length) return <Empty text={emptyText} />;
  return <div className="table-scroll"><table className="result-table"><thead><tr>{visible.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.slice(0, 200).map((row, index) => <tr key={String(row.doc_id ?? index)}>{visible.map((column) => <td key={column}>{formatCell(row[column])}</td>)}</tr>)}</tbody></table></div>;
}

function canRun(route: Exclude<RouteKey, "welcome">, workflow: { imported: boolean; cleaned: boolean; frequencyDone: boolean; sentimentDone: boolean; ldaDone: boolean; stmDone: boolean }) {
  if (route === "import") return true;
  if (route === "clean") return workflow.imported;
  if (route === "frequency" || route === "sentiment" || route === "lda" || route === "stm") return workflow.cleaned;
  if (route === "compare") return workflow.ldaDone || workflow.stmDone;
  return workflow.imported;
}
function toRecord(value: unknown): Record<string, unknown> { return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
function toRows(value: unknown): Array<Record<string, unknown>> { return Array.isArray(value) ? value.filter((item) => item && typeof item === "object") as Array<Record<string, unknown>> : []; }
function toStringArray(value: unknown): string[] { return Array.isArray(value) ? value.map(String) : []; }
function toPreview(value: unknown): { columns?: string[]; rows?: Array<Record<string, unknown>>; total?: number } { const record = toRecord(value); return { columns: toStringArray(record.columns), rows: toRows(record.rows), total: Number(record.total ?? 0) }; }
function toTopics(value: unknown): Array<{ topic_id: number; label?: string; words: Array<[string, number]> }> { return toRows(value).map((topic) => ({ topic_id: Number(topic.topic_id), label: typeof topic.label === "string" ? topic.label : undefined, words: Array.isArray(topic.words) ? topic.words.map((pair) => [String((pair as unknown[])[0]), Number((pair as unknown[])[1] ?? 0)]) : [] })); }
function toCovariates(value: unknown): Array<{ field: string; available: boolean; reason?: string }> { return toRows(value).map((item) => ({ field: String(item.field ?? ""), available: item.available === true, reason: typeof item.reason === "string" ? item.reason : undefined })).filter((item) => item.field); }
function toMetadataFields(value: unknown): Array<{ field: string; values: string[] }> { return toRows(value).map((item) => ({ field: String(item.field ?? ""), values: toStringArray(item.values) })).filter((item) => item.field); }
function formatCell(value: unknown): string { if (value == null) return ""; if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(4); if (typeof value === "object") return JSON.stringify(value); return String(value); }
