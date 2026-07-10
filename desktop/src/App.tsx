import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Circle,
  CircleCheck,
  Clock3,
  Database,
  Download,
  FileSpreadsheet,
  FileInput,
  FolderOpen,
  Layers3,
  Play,
  RefreshCw,
  Scissors,
  Settings2,
  SplitSquareHorizontal,
  Table2,
  TextSelect
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { invoke } from "@tauri-apps/api/core";
import { routes, routeLabels } from "./routes";
import {
  useWorkflowStore,
  type ConfigTaskKey,
  type ImportConfig,
  type RouteKey,
  type TaskKey,
  type TaskState,
  type WorkflowConfigs
} from "./state/workflowStore";

type PageCopy = {
  title: string;
  eyebrow: string;
  primary: string;
  secondary: string;
  task: TaskKey | null;
};

const pageCopy: Record<RouteKey, PageCopy> = {
  welcome: {
    title: "历史报刊主题分析工作台",
    eyebrow: "桌面数据分析",
    primary: "以导入、清洗、建模、对比和导出为主线组织新版桌面工作流。",
    secondary: "导入、清洗、主题建模和导出任务已连接本地 Python 计算能力。",
    task: null
  },
  import: {
    title: "导入数据",
    eyebrow: "元数据与正文表",
    primary: "选择 CSV、XLSX 或 XLS 文件，完成字段识别、缺失字段提示和文档合并。",
    secondary: "页面结构对应 data_service 的读取、字段检测、标准化和 merge_tables 能力。",
    task: "import"
  },
  clean: {
    title: "清洗与分词",
    eyebrow: "文本预处理",
    primary: "配置 OCR 清理、标点数字过滤、繁简转换、停用词和词频阈值。",
    secondary: "清洗任务使用统一长任务状态展示阶段、忙碌、完成摘要和错误。",
    task: "clean"
  },
  lda: {
    title: "LDA 主题建模",
    eyebrow: "gensim 分析",
    primary: "设置主题数、迭代参数和文类筛选，查看主题词、文档主题和一致性指标。",
    secondary: "模型对象保留在 Python 层，前端只承载可序列化结果摘要和入口。",
    task: "lda"
  },
  stm: {
    title: "STM 结构主题模型",
    eyebrow: "R stm 集成",
    primary: "检查 R 环境，配置 prevalence 公式、content 协变量和训练参数。",
    secondary: "协变量可用性、R 环境检查、主题结果和 prevalence 已连接 stm_service 与 Python bridge。",
    task: "stm"
  },
  compare: {
    title: "对比分析",
    eyebrow: "主题差异浏览",
    primary: "按报刊、年份、文类和主题维度生成聚合视图与代表文章列表。",
    secondary: "Python 负责筛选与聚合，前端展示图表、聚合表和可浏览的主题代表文章。",
    task: "compare"
  },
  export: {
    title: "导出结果",
    eyebrow: "文件与日志",
    primary: "选择输出目录和导出项目，查看成功文件、部分失败和处理日志。",
    secondary: "导出文件名、格式和结果语义保持与历史报刊主题分析流程一致。",
    task: "export"
  }
};

export function App() {
  const activeRoute = useWorkflowStore((state) => state.activeRoute);
  const projectName = useWorkflowStore((state) => state.projectName);
  const outputDir = useWorkflowStore((state) => state.outputDir);
  const workflow = useWorkflowStore((state) => state.workflow);
  const summary = useWorkflowStore((state) => state.summary);
  const tasks = useWorkflowStore((state) => state.tasks);
  const importConfig = useWorkflowStore((state) => state.importConfig);
  const setActiveRoute = useWorkflowStore((state) => state.setActiveRoute);
  const setImportConfig = useWorkflowStore((state) => state.setImportConfig);
  const runBackendTask = useWorkflowStore((state) => state.runBackendTask);
  const page = pageCopy[activeRoute];
  const task = page.task ? tasks[page.task] : null;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark" aria-label="历史报刊主题分析工具 logo">
            <BarChart3 size={24} />
          </div>
          <div>
            <div className="brand-title">主题分析</div>
            <div className="brand-subtitle">历史报刊工作台</div>
          </div>
        </div>
        <nav className="nav-list" aria-label="主导航">
          {routes.map(({ key, label, description, Icon }) => {
            const active = key === activeRoute;
            return (
              <button key={key} className={active ? "nav-item active" : "nav-item"} onClick={() => setActiveRoute(key)} type="button">
                <Icon size={19} />
                <span>
                  <strong>{label}</strong>
                  <small>{description}</small>
                </span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">{page.eyebrow}</span>
            <h1>{page.title}</h1>
          </div>
          <div className="session-strip" aria-label="会话信息">
            <span><Database size={16} />{projectName}</span>
            <span><FolderOpen size={16} />{outputDir || "未设置输出目录"}</span>
          </div>
        </header>

        <section className="hero-band">
          <div>
            <p>{page.primary}</p>
            <span>{page.secondary}</span>
          </div>
          <div className="task-pill"><Activity size={17} />当前页面：{routeLabels[activeRoute]}</div>
        </section>

        <section className="status-grid" aria-label="流程状态">
          <StatusItem label="导入" active={workflow.imported} />
          <StatusItem label="合并" active={workflow.merged} />
          <StatusItem label="清洗" active={workflow.cleaned} />
          <StatusItem label="LDA" active={workflow.ldaDone} />
          <StatusItem label="STM" active={workflow.stmDone} />
        </section>

        {activeRoute === "welcome" ? (
          <WelcomePage summary={summary} tasks={tasks} onNavigate={setActiveRoute} />
        ) : (
          <WorkflowPage
            route={activeRoute}
            task={task as TaskState}
            summary={summary}
            workflow={workflow}
            importConfig={importConfig}
            onImportConfigChange={setImportConfig}
            onRun={runBackendTask}
          />
        )}
      </main>
    </div>
  );
}

function WelcomePage({ summary, tasks, onNavigate }: { summary: ReturnType<typeof useWorkflowStore.getState>["summary"]; tasks: Record<TaskKey, TaskState>; onNavigate: (route: RouteKey) => void }) {
  return (
    <div className="page-stack">
      <section className="metric-grid" aria-label="项目摘要">
        <Metric label="合并文章" value={summary.mergedRows || "待导入"} />
        <Metric label="有效语料" value={summary.cleanDocuments || "待清洗"} />
        <Metric label="LDA 主题" value={summary.ldaTopics || "待训练"} />
        <Metric label="导出文件" value={summary.exportFiles || "待导出"} />
      </section>

      <section className="workflow-board" aria-label="核心工作流">
        {routes.filter((route) => route.key !== "welcome").map(({ key, label, description, Icon }) => {
          const task = tasks[key as TaskKey];
          return (
            <button className="workflow-step" key={key} type="button" onClick={() => onNavigate(key)}>
              <Icon size={20} />
              <span>
                <strong>{label}</strong>
                <small>{description}</small>
              </span>
              <TaskBadge task={task} />
            </button>
          );
        })}
      </section>
    </div>
  );
}

type WorkflowRouteKey = Exclude<RouteKey, "welcome">;

type WorkflowSummary = ReturnType<typeof useWorkflowStore.getState>["summary"];
type TaskResult = Record<string, unknown> | null;
type PreviewResult = { columns?: string[]; rows?: Array<Record<string, unknown>>; total?: number };
type TopicResult = { topic_id: number; label?: string; words: Array<[string, number]> };

type PageDefinition = {
  task: TaskKey;
  primaryAction: string;
  cards: Array<{ title: string; icon: ReactNode; body: (summary: WorkflowSummary) => string }>;
};

function WorkflowPage({ route, task, summary, workflow, importConfig, onImportConfigChange, onRun }: { route: WorkflowRouteKey; task: TaskState; summary: WorkflowSummary; workflow: ReturnType<typeof useWorkflowStore.getState>["workflow"]; importConfig: ImportConfig; onImportConfigChange: (values: Partial<ImportConfig>) => void; onRun: (task: TaskKey) => void }) {
  const config = pageDefinitions[route];
  const configs = useWorkflowStore((state) => state.configs);
  const setTaskConfig = useWorkflowStore((state) => state.setTaskConfig);
  const chooseConfigPath = useWorkflowStore((state) => state.chooseConfigPath);
  const results = useWorkflowStore((state) => state.results);
  const stmEnvironment = useWorkflowStore((state) => state.stmEnvironment);
  const checkStmEnvironment = useWorkflowStore((state) => state.checkStmEnvironment);
  const logs = useWorkflowStore((state) => state.logs);
  const clearLogs = useWorkflowStore((state) => state.clearLogs);
  const parameterBlocked = route === "stm" && stmEnvironment.available !== true;
  const exportBlocked = route === "export" && (!configs.export.outputDir.trim() || configs.export.items.length === 0);
  const disabled = !canRun(route, workflow) || parameterBlocked || exportBlocked || task.status === "running";

  if (route === "import") {
    return <ImportWorkflowPage task={task} summary={summary} result={results.import} importConfig={importConfig} onImportConfigChange={onImportConfigChange} onRun={onRun} />;
  }

  return (
    <div className="page-stack">
      <section className="action-layout">
        <article className="control-panel">
          <div className="panel-title"><Settings2 size={18} />主操作</div>
          <ParameterEditor route={route as ConfigTaskKey} configs={configs} results={results} stmEnvironment={stmEnvironment} onChange={setTaskConfig} onChoosePath={chooseConfigPath} />
          <div className="button-row">
            {route === "stm" && (
              <button className="ghost-button" type="button" disabled={stmEnvironment.checking} onClick={checkStmEnvironment}>
                <Activity size={17} />{stmEnvironment.checking ? "正在检查..." : "检查 R 环境"}
              </button>
            )}
            <button className="primary-button" type="button" disabled={disabled} onClick={() => onRun(config.task)}>
              {task.status === "running" ? <RefreshCw size={17} /> : <Play size={17} />}
              {config.primaryAction}
            </button>
          </div>
          {!canRun(route, workflow) && <p className="hint-text">需要先完成前置步骤后才能启动该任务。</p>}
          {route === "stm" && stmEnvironment.available !== true && <p className="hint-text">请先完成 R 环境检查，环境可用后才能训练 STM。</p>}
          {route === "export" && !configs.export.outputDir.trim() && <p className="hint-text">请选择输出目录。</p>}
        </article>

        <TaskStatusPanel task={task} />
      </section>

      <section className="content-grid" aria-label="页面内容">
        {config.cards.map((card) => (
          <article className="module-card" key={card.title}>
            <div className="module-heading">{card.icon}<span>{card.title}</span></div>
            <p>{card.body(summary)}</p>
          </article>
        ))}
      </section>

      <WorkflowResultPanel route={route} result={results[route]} summary={summary} logs={logs} onClearLogs={clearLogs} />
    </div>
  );
}

function ImportWorkflowPage({ task, summary, result, importConfig, onImportConfigChange, onRun }: { task: TaskState; summary: WorkflowSummary; result: TaskResult; importConfig: ImportConfig; onImportConfigChange: (values: Partial<ImportConfig>) => void; onRun: (task: TaskKey) => void }) {
  const missingFiles = !importConfig.metadataPath.trim() || !importConfig.textPath.trim();
  const disabled = task.status === "running" || missingFiles;
  const chooseImportFile = useWorkflowStore((state) => state.chooseImportFile);
  const metadataColumns = toStringArray(result?.metadataColumns);
  const textColumns = toStringArray(result?.textColumns);
  const metadataOptions = fieldOptions(metadataColumns, importConfig.metadataIdField);
  const textOptions = fieldOptions(textColumns, importConfig.textIdField);

  return (
    <div className="page-stack">
      <section className="import-layout">
        <article className="control-panel import-panel">
          <div className="panel-title"><FileInput size={18} />导入配置</div>
          <div className="table-source-grid">
            <TableSourceCard
              title="元数据表"
              icon={<FileSpreadsheet size={20} />}
              value={importConfig.metadataPath}
              placeholder="E:/data/metadata.xlsx"
              fields="文档编号、报刊名、出版日期、标题、文类"
              onChange={(metadataPath) => onImportConfigChange({ metadataPath })}
              onBrowse={() => chooseImportFile("metadata")}
            />
            <TableSourceCard
              title="正文表"
              icon={<TextSelect size={20} />}
              value={importConfig.textPath}
              placeholder="E:/data/full_text.csv"
              fields="文档编号、正文文本"
              onChange={(textPath) => onImportConfigChange({ textPath })}
              onBrowse={() => chooseImportFile("text")}
            />
          </div>
          <div className="field-selector-grid" aria-label="关联字段选择">
            <label>
              <span>元数据关联字段</span>
              <select value={importConfig.metadataIdField} onChange={(event) => onImportConfigChange({ metadataIdField: event.target.value })}>
                {metadataOptions.map((column) => <option key={column} value={column}>{column}</option>)}
              </select>
            </label>
            <label>
              <span>正文关联字段</span>
              <select value={importConfig.textIdField} onChange={(event) => onImportConfigChange({ textIdField: event.target.value })}>
                {textOptions.map((column) => <option key={column} value={column}>{column}</option>)}
              </select>
            </label>
          </div>
          {missingFiles && <p className="hint-text">请分别选择元数据表和正文表；正式导入不会自动混用示例数据。</p>}
          <div className="button-row">
            <button className="primary-button" type="button" disabled={disabled} onClick={() => onRun("import")}>
              {task.status === "running" ? <RefreshCw size={17} /> : <Play size={17} />}
              识别字段并合并
            </button>
          </div>
        </article>

        <TaskStatusPanel task={task} />
      </section>

      <section className="import-result-grid" aria-label="导入结果">
        <ImportMappingPanel result={result} />
        <ImportPreviewPanel summary={summary} result={result} />
      </section>
    </div>
  );
}

function TableSourceCard({ title, icon, value, placeholder, fields, onChange, onBrowse }: { title: string; icon: ReactNode; value: string; placeholder: string; fields: string; onChange: (value: string) => void; onBrowse: () => void }) {
  return (
    <div className="table-source-card">
      <span className="source-heading">{icon}<strong>{title}</strong></span>
      <span className="source-fields">{fields}</span>
      <div className="path-input-row">
        <input aria-label={`${title}文件路径`} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
        <button className="browse-button" type="button" onClick={onBrowse}><FolderOpen size={16} />选择文件</button>
      </div>
    </div>
  );
}

function ImportMappingPanel({ result }: { result: TaskResult }) {
  const metadataMapping = toRecord(result?.metadataMapping);
  const textMapping = toRecord(result?.textMapping);
  const mappings = [
    ...Object.entries(metadataMapping).map(([standard, original]) => ["元数据表", standard, String(original)]),
    ...Object.entries(textMapping).map(([standard, original]) => ["正文表", standard, String(original)])
  ];

  return (
    <article className="module-card import-table-card">
      <div className="module-heading"><Table2 size={18} /><span>字段识别结果</span></div>
      <table className="data-table">
        <thead>
          <tr><th>数据表</th><th>标准字段</th><th>原始字段</th></tr>
        </thead>
        <tbody>
          {mappings.length ? mappings.map(([source, field, original]) => <tr key={`${source}-${field}`}><td>{source}</td><td>{field}</td><td>{original}</td></tr>) : <tr><td colSpan={3}>完成导入后显示实际字段识别结果</td></tr>}
        </tbody>
      </table>
    </article>
  );
}

function ImportPreviewPanel({ summary, result }: { summary: WorkflowSummary; result: TaskResult }) {
  const preview = toPreview(result?.preview);
  return (
    <article className="module-card import-table-card">
      <div className="module-heading"><Database size={18} /><span>合并与预览</span></div>
      <div className="import-summary-strip">
        <Metric label="元数据行" value={summary.metadataRows || "待导入"} />
        <Metric label="正文行" value={summary.textRows || "待导入"} />
        <Metric label="合并文章" value={summary.mergedRows || "待合并"} />
      </div>
      <ResultTable columns={preview.columns ?? []} rows={preview.rows ?? []} emptyText="完成合并后显示前 10 行真实数据" />
      <p className="import-match-note">元数据未匹配 {summary.unmatchedMetaRows} 条，正文未匹配 {summary.unmatchedTextRows} 条。</p>
    </article>
  );
}

function fieldOptions(columns: string[], current: string) {
  const aliases = ["doc_id", "文档编号", "docid", "id", "编号", "文章编号", "document_id"];
  return [...new Set([current, ...columns, ...aliases].filter(Boolean))];
}

type ParameterEditorProps = {
  route: ConfigTaskKey;
  configs: WorkflowConfigs;
  results: Record<TaskKey, TaskResult>;
  stmEnvironment: ReturnType<typeof useWorkflowStore.getState>["stmEnvironment"];
  onChange: <K extends ConfigTaskKey>(task: K, values: Partial<WorkflowConfigs[K]>) => void;
  onChoosePath: (target: "customDict" | "stopwords" | "outputDir") => Promise<void>;
};

const exportOptions = [
  ["merged_data", "合并后的主数据集"],
  ["cleaned_records", "清洗后的记录"],
  ["cleaned_corpus", "分词结果语料"],
  ["lda_topic_word", "LDA 主题词"],
  ["lda_doc_topic", "LDA 文档主题分布"],
  ["lda_coherence", "LDA 一致性指标"],
  ["stm_topic_word", "STM 主题词"],
  ["stm_doc_topic", "STM 文档主题分布"],
  ["stm_prevalence", "STM prevalence"],
  ["session_config", "会话配置"]
] as const;

function ParameterEditor({ route, configs, results, stmEnvironment, onChange, onChoosePath }: ParameterEditorProps) {
  const importResult = results.import;
  const genres = toStringArray(importResult?.genres);
  if (route === "clean") {
    const values = configs.clean;
    const stopwordCount = values.stopwordsText.split(/\r?\n/).filter((word) => word.trim()).length;
    return (
      <div className="parameter-form">
        <div className="toggle-grid">
          <ToggleField label="去除空文本" checked={values.removeEmpty} onChange={(removeEmpty) => onChange("clean", { removeEmpty })} />
          <ToggleField label="去除重复文章" checked={values.removeDuplicates} onChange={(removeDuplicates) => onChange("clean", { removeDuplicates })} />
          <ToggleField label="OCR 噪声清理" checked={values.ocrClean} onChange={(ocrClean) => onChange("clean", { ocrClean })} />
          <ToggleField label="去除标点" checked={values.removePunct} onChange={(removePunct) => onChange("clean", { removePunct })} />
          <ToggleField label="去除数字" checked={values.removeNumbers} onChange={(removeNumbers) => onChange("clean", { removeNumbers })} />
          <ToggleField label="繁体转简体" checked={values.traditionalToSimplified} onChange={(traditionalToSimplified) => onChange("clean", { traditionalToSimplified })} />
        </div>
        <div className="parameter-grid">
          <NumberField label="最短文本长度" value={values.minTextLength} min={1} max={500} onChange={(minTextLength) => onChange("clean", { minTextLength })} />
          <NumberField label="最小文档频率" value={values.minDocFreq} min={1} max={100} onChange={(minDocFreq) => onChange("clean", { minDocFreq })} />
          <NumberField label="最大文档频率比例" value={values.maxDocFreqRatio} min={0.01} max={1} step={0.05} onChange={(maxDocFreqRatio) => onChange("clean", { maxDocFreqRatio })} />
        </div>
        <fieldset className="export-options">
          <legend>停用词与词典</legend>
          <ToggleField label="使用内置中文停用词" checked={values.useDefaultStopwords} onChange={(useDefaultStopwords) => onChange("clean", { useDefaultStopwords })} />
          <div className="parameter-field stopword-editor">
            <span>可编辑停用词（每行一词，当前 {stopwordCount} 个）</span>
            <textarea value={values.stopwordsText} placeholder="可直接添加、删除停用词；每行一个。" onChange={(event) => onChange("clean", { stopwordsText: event.target.value })} />
          </div>
          <div className="button-row compact-buttons">
            <button className="browse-button" type="button" onClick={() => onChoosePath("stopwords")}><FileInput size={16} />加载停用词表</button>
            <button className="ghost-button" type="button" onClick={() => onChange("clean", { stopwordsText: "", stopwordsPath: "" })}>清空编辑</button>
          </div>
          {values.stopwordsPath && <p className="field-note">外部文件：{values.stopwordsPath}</p>}
        </fieldset>
        <PathField label="自定义词典（可选）" value={values.customDictPath} placeholder="选择 .txt 词典文件" onChange={(customDictPath) => onChange("clean", { customDictPath })} onBrowse={() => onChoosePath("customDict")} buttonLabel="选择词典" />
      </div>
    );
  }

  if (route === "lda") {
    const values = configs.lda;
    return (
      <div className="parameter-form parameter-grid">
        <NumberField label="主题数" value={values.numTopics} min={2} max={100} onChange={(numTopics) => onChange("lda", { numTopics })} />
        <NumberField label="训练轮数 (passes)" value={values.passes} min={1} max={500} onChange={(passes) => onChange("lda", { passes })} />
        <NumberField label="单轮迭代数" value={values.iterations} min={50} max={2000} onChange={(iterations) => onChange("lda", { iterations })} />
        <NumberField label="随机种子" value={values.randomState} min={0} max={9999} onChange={(randomState) => onChange("lda", { randomState })} />
        <NumberField label="最小文档频率" value={values.minDocFreq} min={1} max={50} onChange={(minDocFreq) => onChange("lda", { minDocFreq })} />
        <NumberField label="最大文档频率比例" value={values.maxDocFreqRatio} min={0.01} max={1} step={0.05} onChange={(maxDocFreqRatio) => onChange("lda", { maxDocFreqRatio })} />
        <SelectField label="文类筛选" value={values.genre} options={[["全部文类", "全部文类"], ...genres.map((genre) => [genre, genre] as const)]} onChange={(genre) => onChange("lda", { genre })} />
      </div>
    );
  }

  if (route === "stm") {
    const values = configs.stm;
    return (
      <div className="parameter-form parameter-grid">
        <NumberField label="主题数" value={values.numTopics} min={2} max={100} onChange={(numTopics) => onChange("stm", { numTopics })} />
        <NumberField label="最大 EM 迭代" value={values.maxEmIterations} min={10} max={500} onChange={(maxEmIterations) => onChange("stm", { maxEmIterations })} />
        <NumberField label="随机种子" value={values.randomState} min={0} max={9999} onChange={(randomState) => onChange("stm", { randomState })} />
        <SelectField label="文类筛选" value={values.genre} options={[["全部文类", "全部文类"], ...genres.map((genre) => [genre, genre] as const)]} onChange={(genre) => onChange("stm", { genre })} />
        <TextField label="prevalence 公式" value={values.prevalenceFormula} placeholder="~ newspaper" onChange={(prevalenceFormula) => onChange("stm", { prevalenceFormula })} />
        <TextField label="content 协变量（可选）" value={values.contentCovariate} placeholder="genre" onChange={(contentCovariate) => onChange("stm", { contentCovariate })} />
        <div className={`environment-banner ${stmEnvironment.available === true ? "available" : stmEnvironment.available === false ? "unavailable" : ""}`}>
          <strong>{stmEnvironment.available === true ? "R 环境可用" : stmEnvironment.available === false ? "R 环境不可用" : "R 环境待检查"}</strong>
          <span>{stmEnvironment.message}</span>
        </div>
        <CovariateList items={toCovariates(importResult?.covariates)} />
      </div>
    );
  }

  if (route === "compare") {
    const values = configs.compare;
    const selectedTopics = values.model === "stm"
      ? toTopics(results.stm?.topics)
      : values.model === "lda"
        ? toTopics(results.lda?.topics)
        : toTopics(results.lda?.topics).length ? toTopics(results.lda?.topics) : toTopics(results.stm?.topics);
    const topicOptions: Array<readonly [string, string]> = [["__all__", "全部主题"], ...selectedTopics.map((topic) => [`topic_${topic.topic_id}`, topic.label || `主题 ${topic.topic_id + 1}`] as const)];
    const newspapers = toStringArray(importResult?.newspapers);
    const years = toStringArray(importResult?.years);
    return (
      <div className="parameter-form parameter-grid">
        <SelectField label="主题模型" value={values.model} options={[["auto", "自动（优先 LDA）"], ["lda", "LDA"], ["stm", "STM"]]} onChange={(model) => onChange("compare", { model: model as "auto" | "lda" | "stm" })} />
        <SelectField label="聚合维度" value={values.axisField} options={[["newspaper", "报刊"], ["pub_year", "年份"], ["time_index", "时间序号"], ["genre", "文类"], ["dominant_topic", "主导主题"]]} onChange={(axisField) => onChange("compare", { axisField })} />
        <SelectField label="纵轴指标" value={values.metricField} options={topicOptions} onChange={(metricField) => onChange("compare", { metricField })} />
        <SelectField label="代表文章主题" value={values.topicField} options={topicOptions} onChange={(topicField) => onChange("compare", { topicField })} />
        <SelectField label="报刊筛选" value={values.newspaper} options={[["__all__", "全部"], ...newspapers.map((item) => [item, item] as const)]} onChange={(newspaper) => onChange("compare", { newspaper })} />
        <SelectField label="年份筛选" value={values.year} options={[["__all__", "全部"], ...years.map((item) => [item, item] as const)]} onChange={(year) => onChange("compare", { year })} />
        <SelectField label="文类筛选" value={values.genre} options={[["__all__", "全部"], ...genres.map((item) => [item, item] as const)]} onChange={(genre) => onChange("compare", { genre })} />
        <SelectField label="图表类型" value={values.chartType} options={[["bar", "柱状图"], ["line", "折线图"]]} onChange={(chartType) => onChange("compare", { chartType: chartType as "line" | "bar" })} />
        <NumberField label="每主题代表文章数" value={values.representativeLimit} min={1} max={20} onChange={(representativeLimit) => onChange("compare", { representativeLimit })} />
      </div>
    );
  }

  const values = configs.export;
  const toggleItem = (key: string, checked: boolean) => {
    const items = checked ? [...new Set([...values.items, key])] : values.items.filter((item) => item !== key);
    onChange("export", { items });
  };
  return (
    <div className="parameter-form">
      <div className="parameter-grid">
        <TextField label="项目名称" value={values.projectName} placeholder="报刊主题分析项目" onChange={(projectName) => onChange("export", { projectName })} />
        <PathField label="输出目录" value={values.outputDir} placeholder="选择导出目录" onChange={(outputDir) => onChange("export", { outputDir })} onBrowse={() => onChoosePath("outputDir")} buttonLabel="选择目录" />
      </div>
      <fieldset className="export-options">
        <legend>导出项目</legend>
        <div className="button-row compact-buttons">
          <button className="ghost-button" type="button" onClick={() => onChange("export", { items: exportOptions.map(([key]) => key) })}>全选</button>
          <button className="ghost-button" type="button" onClick={() => onChange("export", { items: [] })}>全不选</button>
        </div>
        <div className="toggle-grid">
          {exportOptions.map(([key, label]) => <ToggleField key={key} label={label} checked={values.items.includes(key)} onChange={(checked) => toggleItem(key, checked)} />)}
        </div>
      </fieldset>
    </div>
  );
}

function NumberField({ label, value, min, max, step = 1, onChange }: { label: string; value: number; min: number; max: number; step?: number; onChange: (value: number) => void }) {
  return (
    <label className="parameter-field">
      <span>{label}</span>
      <input type="number" value={value} min={min} max={max} step={step} onChange={(event) => {
        const next = Number(event.target.value);
        if (Number.isFinite(next)) onChange(Math.min(max, Math.max(min, next)));
      }} />
    </label>
  );
}

function TextField({ label, value, placeholder, onChange }: { label: string; value: string; placeholder: string; onChange: (value: string) => void }) {
  return (
    <label className="parameter-field">
      <span>{label}</span>
      <input type="text" value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: ReadonlyArray<readonly [string, string]>; onChange: (value: string) => void }) {
  return (
    <label className="parameter-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([key, text]) => <option key={key} value={key}>{text}</option>)}
      </select>
    </label>
  );
}

function ToggleField({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="toggle-field">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

function PathField({ label, value, placeholder, buttonLabel, onChange, onBrowse }: { label: string; value: string; placeholder: string; buttonLabel: string; onChange: (value: string) => void; onBrowse: () => void }) {
  return (
    <div className="parameter-field path-field">
      <span>{label}</span>
      <span className="path-input-row">
        <input aria-label={label} type="text" value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
        <button className="browse-button" type="button" onClick={onBrowse}><FolderOpen size={16} />{buttonLabel}</button>
      </span>
    </div>
  );
}

function WorkflowResultPanel({ route, result, summary, logs, onClearLogs }: { route: WorkflowRouteKey; result: TaskResult; summary: WorkflowSummary; logs: string[]; onClearLogs: () => void }) {
  if (route === "clean") return <CleanResultPanel result={result} />;
  if (route === "lda") return <ModelResultPanel title="LDA 训练结果" result={result} coherence={summary.ldaCoherence} />;
  if (route === "stm") return <ModelResultPanel title="STM 训练结果" result={result} showPrevalence />;
  if (route === "compare") return <CompareResultPanel result={result} />;
  if (route === "export") return <ExportResultPanel result={result} logs={logs} onClearLogs={onClearLogs} />;
  return null;
}

function CleanResultPanel({ result }: { result: TaskResult }) {
  const preview = toPreview(result?.preview);
  const rows = preview.rows ?? [];
  const [selectedIndex, setSelectedIndex] = useState(0);
  const safeIndex = rows.length ? Math.min(selectedIndex, rows.length - 1) : 0;
  const row = rows[safeIndex] ?? {};
  return (
    <section className="result-section">
      <div className="result-heading"><Scissors size={19} /><span>清洗对比预览</span></div>
      {!rows.length ? <EmptyResult text="完成清洗后，可逐篇比较原文、清洗文本和分词结果。" /> : (
        <>
          <label className="parameter-field article-selector">
            <span>预览文章</span>
            <select value={safeIndex} onChange={(event) => setSelectedIndex(Number(event.target.value))}>
              {rows.map((item, index) => <option key={String(item.doc_id ?? index)} value={index}>{index + 1}. {String(item.article_title ?? item.doc_id ?? `文章 ${index + 1}`)}</option>)}
            </select>
          </label>
          <div className="text-preview-grid">
            <TextPreview title="原文" text={String(row.text ?? "")} />
            <TextPreview title="清洗后文本" text={String(row.cleaned_text ?? "")} />
            <TextPreview title={`分词结果（${Number(row.token_count ?? 0)} 词）`} text={String(row.tokens ?? "").split(" ").filter(Boolean).slice(0, 200).join(" / ")} />
          </div>
        </>
      )}
    </section>
  );
}

function ModelResultPanel({ title, result, coherence, showPrevalence = false }: { title: string; result: TaskResult; coherence?: number | null; showPrevalence?: boolean }) {
  const topics = toTopics(result?.topics);
  const preview = toPreview(result?.documentTopics);
  const prevalenceRows = toRows(result?.prevalence);
  const prevalenceColumns = toStringArray(result?.prevalenceColumns);
  const [visualizationMessage, setVisualizationMessage] = useState("");
  const openLdaVisualization = async () => {
    setVisualizationMessage("正在生成 pyLDAvis...");
    try {
      const response = await invoke<{ ok: boolean; data?: Record<string, unknown>; error?: { message?: string } }>("run_python_task", { task: "lda-vis", payload: {} });
      if (!response.ok) throw new Error(response.error?.message || "pyLDAvis 生成失败");
      setVisualizationMessage(String(response.data?.message || response.data?.path || "pyLDAvis 已打开"));
    } catch (error) {
      setVisualizationMessage(error instanceof Error ? error.message : String(error));
    }
  };
  return (
    <section className="result-section">
      <div className="result-heading"><Layers3 size={19} /><span>{title}</span>{coherence != null && <strong>Coherence (c_v)：{coherence.toFixed(4)}</strong>}</div>
      {!topics.length ? <EmptyResult text="训练完成后显示主题关键词、文档主题分布和模型指标。" /> : (
        <>
          <div className="topic-card-grid">
            {topics.map((topic) => (
              <article className="topic-card" key={topic.topic_id}>
                <strong>主题 {topic.topic_id + 1}</strong>
                <div className="topic-words">{topic.words.slice(0, 10).map(([word, weight]) => <span key={word}>{word}{weight > 0 ? `（${weight.toFixed(3)}）` : ""}</span>)}</div>
              </article>
            ))}
          </div>
          {!showPrevalence && <div className="button-row"><button className="ghost-button" type="button" onClick={openLdaVisualization}><Activity size={16} />在浏览器中打开 pyLDAvis</button>{visualizationMessage && <span className="field-note">{visualizationMessage}</span>}</div>}
          {showPrevalence && prevalenceRows.length > 0 && (
            <div className="result-block">
              <h3>协变量效应（Prevalence）</h3>
              <ResultTable columns={prevalenceColumns} rows={prevalenceRows} />
            </div>
          )}
          <div className="result-block">
            <h3>文档主题分布（前 200 行）</h3>
            <ResultTable columns={preview.columns ?? []} rows={preview.rows ?? []} />
          </div>
        </>
      )}
    </section>
  );
}

function CompareResultPanel({ result }: { result: TaskResult }) {
  const rows = toRows(result?.rows);
  const topicColumns = toStringArray(result?.topicColumns);
  const axisField = typeof result?.axisField === "string" ? result.axisField : "newspaper";
  const chartType = result?.chartType === "line" ? "line" : "bar";
  const articleGroups = toRecord(result?.representativeArticles);
  const articles: Array<Record<string, unknown> & { _topic: string }> = Object.entries(articleGroups).flatMap(([topic, value]) => toRows(value).map((article) => ({ ...article, _topic: topic })));
  const [selectedDocId, setSelectedDocId] = useState("");
  const selectedArticle = articles.find((article) => String(article.doc_id ?? "") === selectedDocId) ?? articles[0];
  return (
    <section className="result-section">
      <div className="result-heading"><SplitSquareHorizontal size={19} /><span>主题分布对比</span></div>
      {!rows.length ? <EmptyResult text="生成对比视图后显示图表、聚合表和代表文章。" /> : (
        <>
          <CompareChart rows={rows} axisField={axisField} topicColumns={topicColumns} chartType={chartType} />
          <div className="result-block">
            <h3>聚合数据</h3>
            <ResultTable columns={[axisField, ...topicColumns]} rows={rows} />
          </div>
          <div className="article-browser">
            <div className="result-block">
              <h3>主题代表文章</h3>
              <div className="article-list">
                {articles.map((article, index) => {
                  const docId = String(article.doc_id ?? index);
                  return <button className={selectedArticle === article ? "article-item active" : "article-item"} type="button" key={`${article._topic}-${docId}`} onClick={() => setSelectedDocId(docId)}><strong>{String(article._topic).replace("topic_", "主题 ")}</strong><span>{String(article.article_title || "（无标题）")}</span><small>{String(article.newspaper ?? "")} · 权重 {formatCell(article[article._topic])}</small></button>;
                })}
              </div>
            </div>
            <div className="article-text-panel">
              <h3>{String(selectedArticle?.article_title ?? "请选择代表文章")}</h3>
              <p>{[selectedArticle?.newspaper, selectedArticle?.pub_date, selectedArticle?.author, selectedArticle?.genre].filter(Boolean).map(String).join("  |  ")}</p>
              <div>{String(selectedArticle?.text ?? "暂无原文")}</div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function CompareChart({ rows, axisField, topicColumns, chartType }: { rows: Array<Record<string, unknown>>; axisField: string; topicColumns: string[]; chartType: "line" | "bar" }) {
  const visibleTopics = topicColumns.slice(0, 8);
  const maxValue = Math.max(0.0001, ...rows.flatMap((row) => visibleTopics.map((topic) => Number(row[topic] ?? 0))));
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [exportMessage, setExportMessage] = useState("");

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const width = canvas.width;
    const height = canvas.height;
    const left = 90;
    const right = 30;
    const top = 42;
    const bottom = 90;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    context.fillStyle = "#f8fafc";
    context.fillRect(0, 0, width, height);
    context.strokeStyle = "#cfd8e3";
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(left, top);
    context.lineTo(left, top + plotHeight);
    context.lineTo(left + plotWidth, top + plotHeight);
    context.stroke();
    context.font = "22px Microsoft YaHei, sans-serif";
    context.fillStyle = "#172033";
    context.fillText("主题分布对比", left, 28);

    const stepX = plotWidth / Math.max(rows.length, 1);
    visibleTopics.forEach((topic, topicIndex) => {
      const color = `hsl(${topicIndex * 47} 65% 45%)`;
      context.strokeStyle = color;
      context.fillStyle = color;
      context.lineWidth = 4;
      if (chartType === "line") context.beginPath();
      rows.forEach((row, rowIndex) => {
        const value = Number(row[topic] ?? 0);
        const x = left + stepX * rowIndex + stepX / 2;
        const y = top + plotHeight - value / maxValue * plotHeight;
        if (chartType === "line") {
          if (rowIndex === 0) context.moveTo(x, y); else context.lineTo(x, y);
        } else {
          const barWidth = Math.max(4, stepX * 0.75 / Math.max(visibleTopics.length, 1));
          const barX = left + stepX * rowIndex + stepX * 0.125 + topicIndex * barWidth;
          context.fillRect(barX, y, barWidth * 0.85, top + plotHeight - y);
        }
      });
      if (chartType === "line") context.stroke();
    });
    context.font = "17px Microsoft YaHei, sans-serif";
    context.fillStyle = "#596779";
    rows.forEach((row, index) => {
      const label = String(row[axisField] ?? "").slice(0, 12);
      const x = left + stepX * index + stepX / 2;
      context.save();
      context.translate(x, top + plotHeight + 16);
      context.rotate(-Math.PI / 7);
      context.fillText(label, 0, 0);
      context.restore();
    });
  }, [axisField, chartType, maxValue, rows, visibleTopics.join("|")]);

  const exportChart = async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const path = await invoke<string | null>("select_chart_png_path");
    if (!path) return;
    const base64Data = canvas.toDataURL("image/png").split(",")[1];
    await invoke("save_chart_png", { path, base64Data });
    setExportMessage(`图表已保存：${path}`);
  };

  return (
    <div className="compare-chart" role="img" aria-label={chartType === "line" ? "主题趋势折线图" : "主题分布柱状图"}>
      <canvas ref={canvasRef} width={1600} height={600} />
      <div className="button-row compact-buttons"><button className="ghost-button" type="button" onClick={exportChart}><Download size={16} />导出当前图表 PNG</button>{exportMessage && <span className="field-note">{exportMessage}</span>}</div>
    </div>
  );
}

function ExportResultPanel({ result, logs, onClearLogs }: { result: TaskResult; logs: string[]; onClearLogs: () => void }) {
  const exported = toStringArray(result?.exported);
  const errors = toRows(result?.errors);
  return (
    <section className="result-section">
      <div className="result-heading"><Download size={19} /><span>导出结果与处理日志</span></div>
      <div className="export-result-layout">
        <div>
          <h3>成功文件</h3>
          {exported.length ? <ul className="file-result-list">{exported.map((filename) => <li key={filename}><CheckCircle2 size={15} />{filename}</li>)}</ul> : <EmptyResult text="尚未导出文件" />}
          {errors.length > 0 && <><h3>未导出项目</h3><ul className="error-result-list">{errors.map((item, index) => <li key={`${item.key}-${index}`}><AlertTriangle size={15} />{String(item.label ?? item.key)}：{String(item.error ?? "未知错误")}</li>)}</ul></>}
        </div>
        <div className="log-panel">
          <div className="log-header"><h3>处理日志</h3><button className="ghost-button" type="button" onClick={onClearLogs}>清除日志</button></div>
          <pre>{logs.length ? logs.join("\n") : "暂无处理日志"}</pre>
        </div>
      </div>
    </section>
  );
}

function CovariateList({ items }: { items: Array<{ field: string; available: boolean; reason?: string }> }) {
  if (!items.length) return <p className="field-note">完成导入后显示可用协变量。</p>;
  return <div className="covariate-list">{items.map((item) => <span className={item.available ? "available" : "unavailable"} key={item.field} title={item.reason || "可用于 STM 协变量"}>{item.field}{item.available ? "" : `（${item.reason || "不可用"}）`}</span>)}</div>;
}

function TextPreview({ title, text }: { title: string; text: string }) {
  return <article className="text-preview"><strong>{title}</strong><div>{text || "（空）"}</div></article>;
}

function EmptyResult({ text }: { text: string }) {
  return <p className="empty-result">{text}</p>;
}

function ResultTable({ columns, rows, emptyText = "暂无数据" }: { columns: string[]; rows: Array<Record<string, unknown>>; emptyText?: string }) {
  const visibleColumns = columns.slice(0, 18);
  if (!visibleColumns.length || !rows.length) return <p className="empty-result">{emptyText}</p>;
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead><tr>{visibleColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
        <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{visibleColumns.map((column) => <td key={column}>{formatCell(row[column])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function toRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function toRows(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item) => item && typeof item === "object" && !Array.isArray(item)) as Array<Record<string, unknown>> : [];
}

function toStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

function toPreview(value: unknown): PreviewResult {
  const preview = toRecord(value);
  return { columns: toStringArray(preview.columns), rows: toRows(preview.rows), total: Number(preview.total ?? 0) };
}

function toTopics(value: unknown): TopicResult[] {
  return toRows(value).map((topic) => ({
    topic_id: Number(topic.topic_id ?? 0),
    label: typeof topic.label === "string" ? topic.label : undefined,
    words: Array.isArray(topic.words) ? topic.words.filter(Array.isArray).map((pair) => [String(pair[0]), Number(pair[1] ?? 0)] as [string, number]) : []
  }));
}

function toCovariates(value: unknown) {
  return toRows(value).map((item) => ({ field: String(item.field ?? ""), available: item.available === true, reason: typeof item.reason === "string" ? item.reason : undefined })).filter((item) => item.field);
}

function formatCell(value: unknown) {
  if (typeof value === "number") return Number.isFinite(value) ? value.toFixed(4) : "";
  const text = value == null ? "" : String(value);
  return text.length > 120 ? `${text.slice(0, 120)}…` : text;
}

const pageDefinitions: Record<WorkflowRouteKey, PageDefinition> = {
  import: {
    task: "import",
    primaryAction: "识别字段并合并",
    cards: [
      { title: "文件摘要", icon: <FileInput size={18} />, body: (summary) => `元数据 ${summary.metadataRows} 行，正文 ${summary.textRows} 行。` },
      { title: "字段映射", icon: <Table2 size={18} />, body: () => "doc_id、article_title、newspaper、pub_year、genre 与 text 字段进入标准映射预览。" },
      { title: "合并结果", icon: <Database size={18} />, body: (summary) => `已合并 ${summary.mergedRows} 篇，元数据未匹配 ${summary.unmatchedMetaRows} 条，正文未匹配 ${summary.unmatchedTextRows} 条。` }
    ]
  },
  clean: {
    task: "clean",
    primaryAction: "启动清洗任务",
    cards: [
      { title: "清洗参数", icon: <Scissors size={18} />, body: () => "OCR、标点、数字、繁简、停用词和词频参数会直接传入清洗任务。" },
      { title: "逐篇预览", icon: <Table2 size={18} />, body: () => "清洗完成后可逐篇比较原文、清洗后文本和分词结果。" },
      { title: "语料统计", icon: <Database size={18} />, body: (summary) => `有效文档 ${summary.cleanDocuments} 篇，词元 ${summary.totalTokens} 个，唯一词 ${summary.uniqueWords} 个。` }
    ]
  },
  lda: {
    task: "lda",
    primaryAction: "训练 LDA",
    cards: [
      { title: "主题关键词", icon: <Layers3 size={18} />, body: (summary) => `当前 ${summary.ldaTopics} 个主题，展示每个主题前 10 个关键词。` },
      { title: "一致性指标", icon: <BarChart3 size={18} />, body: (summary) => `Coherence：${summary.ldaCoherence ?? "待训练"}。` },
      { title: "可视化入口", icon: <Activity size={18} />, body: () => "训练完成后可生成 pyLDAvis 并在系统浏览器中打开。" }
    ]
  },
  stm: {
    task: "stm",
    primaryAction: "训练 STM",
    cards: [
      { title: "环境检查", icon: <Activity size={18} />, body: () => "展示 R、rpy2 与 stm 包可用性，并提供失败详情。" },
      { title: "协变量", icon: <Table2 size={18} />, body: () => "字段可用性、缺失值和低基数原因会集中展示。" },
      { title: "prevalence 摘要", icon: <BarChart3 size={18} />, body: (summary) => `当前 ${summary.stmTopics} 个 STM 主题，训练后展示协变量效应。` }
    ]
  },
  compare: {
    task: "compare",
    primaryAction: "生成对比视图",
    cards: [
      { title: "趋势图", icon: <BarChart3 size={18} />, body: () => "展示主题占比随报刊和年份变化的序列。" },
      { title: "聚合表", icon: <Table2 size={18} />, body: () => "保留模型、主题、维度、文章数和平均权重列。" },
      { title: "代表文章", icon: <SplitSquareHorizontal size={18} />, body: () => "按主题权重列出 top 文档，并提供原文查看入口。" }
    ]
  },
  export: {
    task: "export",
    primaryAction: "导出选中项目",
    cards: [
      { title: "可导出项目", icon: <Download size={18} />, body: () => "支持十类结果全选、全不选与逐项导出，缺失结果会单独报告。" },
      { title: "结果摘要", icon: <CheckCircle2 size={18} />, body: (summary) => `已导出 ${summary.exportFiles} 个文件，部分失败会保留明细。` },
      { title: "处理日志", icon: <Table2 size={18} />, body: () => "展示最近日志行，并保留清空和复制入口。" }
    ]
  }
};

function canRun(route: RouteKey, workflow: ReturnType<typeof useWorkflowStore.getState>["workflow"]) {
  if (route === "clean") return workflow.merged;
  if (route === "lda" || route === "stm") return workflow.cleaned;
  if (route === "compare") return workflow.ldaDone || workflow.stmDone;
  if (route === "export") return workflow.merged || workflow.cleaned || workflow.ldaDone || workflow.stmDone;
  return true;
}

function StatusItem({ label, active }: { label: string; active: boolean }) {
  return (
    <div className={active ? "status-item done" : "status-item"}>
      {active ? <CircleCheck size={18} /> : <Circle size={18} />}
      <span>{label}</span>
    </div>
  );
}

function TaskStatusPanel({ task }: { task: TaskState }) {
  return (
    <article className={`task-status ${task.status}`}>
      <div className="panel-title"><Clock3 size={18} />长任务状态</div>
      <div className="task-status-header">
        <TaskBadge task={task} />
        <span>{task.updatedAt}</span>
      </div>
      <h2>{task.phase}</h2>
      <p>{task.error || task.summary || task.message}</p>
      <div className="progress-track" aria-label="任务进度">
        <span style={{ width: `${task.progress ?? 0}%` }} />
      </div>
    </article>
  );
}

function TaskBadge({ task }: { task: TaskState }) {
  const label = task.status === "running" ? "运行中" : task.status === "succeeded" ? "已完成" : task.status === "failed" ? "失败" : "待启动";
  return <span className={`task-badge ${task.status}`}>{label}</span>;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
