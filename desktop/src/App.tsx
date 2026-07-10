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
import type { ReactNode } from "react";
import { routes, routeLabels } from "./routes";
import { useWorkflowStore, type ImportConfig, type RouteKey, type TaskKey, type TaskState } from "./state/workflowStore";

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
    secondary: "协变量可用性与训练结果后续由 stm_service 和 Python bridge 提供。",
    task: "stm"
  },
  compare: {
    title: "对比分析",
    eyebrow: "主题差异浏览",
    primary: "按报刊、年份、文类和主题维度生成聚合视图与代表文章列表。",
    secondary: "聚合语义后续下沉到 Python 层，前端负责图表、表格和文章浏览。",
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
  const failBackendTask = useWorkflowStore((state) => state.failBackendTask);
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
            onFail={failBackendTask}
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

type PageDefinition = {
  task: TaskKey;
  primaryAction: string;
  controls: Array<{ label: string; value: string }>;
  cards: Array<{ title: string; icon: ReactNode; body: (summary: WorkflowSummary) => string }>;
};

function WorkflowPage({ route, task, summary, workflow, importConfig, onImportConfigChange, onRun, onFail }: { route: WorkflowRouteKey; task: TaskState; summary: WorkflowSummary; workflow: ReturnType<typeof useWorkflowStore.getState>["workflow"]; importConfig: ImportConfig; onImportConfigChange: (values: Partial<ImportConfig>) => void; onRun: (task: TaskKey) => void; onFail: (task: TaskKey) => void }) {
  const config = pageDefinitions[route];
  const disabled = !canRun(route, workflow) || task.status === "running";

  if (route === "import") {
    return <ImportWorkflowPage task={task} summary={summary} importConfig={importConfig} onImportConfigChange={onImportConfigChange} onRun={onRun} onFail={onFail} />;
  }

  return (
    <div className="page-stack">
      <section className="action-layout">
        <article className="control-panel">
          <div className="panel-title"><Settings2 size={18} />主操作</div>
          <div className="control-list">
            {config.controls.map((item) => <ControlRow key={item.label} label={item.label} value={item.value} />)}
          </div>
          <div className="button-row">
            <button className="primary-button" type="button" disabled={disabled} onClick={() => onRun(config.task)}>
              {task.status === "running" ? <RefreshCw size={17} /> : <Play size={17} />}
              {config.primaryAction}
            </button>
            <button className="ghost-button" type="button" onClick={() => onFail(config.task)}>
              <AlertTriangle size={17} />错误态预览
            </button>
          </div>
          {!canRun(route, workflow) && <p className="hint-text">需要先完成前置步骤后才能启动该任务。</p>}
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
    </div>
  );
}

function ImportWorkflowPage({ task, summary, importConfig, onImportConfigChange, onRun, onFail }: { task: TaskState; summary: WorkflowSummary; importConfig: ImportConfig; onImportConfigChange: (values: Partial<ImportConfig>) => void; onRun: (task: TaskKey) => void; onFail: (task: TaskKey) => void }) {
  const disabled = task.status === "running";
  const sampleMode = !importConfig.metadataPath.trim() || !importConfig.textPath.trim();

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
            />
            <TableSourceCard
              title="正文表"
              icon={<TextSelect size={20} />}
              value={importConfig.textPath}
              placeholder="E:/data/full_text.csv"
              fields="文档编号、正文文本"
              onChange={(textPath) => onImportConfigChange({ textPath })}
            />
          </div>
          <div className="field-selector-grid" aria-label="关联字段选择">
            <label>
              <span>元数据关联字段</span>
              <select value={importConfig.metadataIdField} onChange={(event) => onImportConfigChange({ metadataIdField: event.target.value })}>
                <option value="doc_id">doc_id</option>
                <option value="article_id">article_id</option>
                <option value="id">id</option>
                <option value="编号">编号</option>
              </select>
            </label>
            <label>
              <span>正文关联字段</span>
              <select value={importConfig.textIdField} onChange={(event) => onImportConfigChange({ textIdField: event.target.value })}>
                <option value="doc_id">doc_id</option>
                <option value="article_id">article_id</option>
                <option value="id">id</option>
                <option value="编号">编号</option>
              </select>
            </label>
          </div>
          {sampleMode && <p className="hint-text">未填写完整文件路径时，将使用内置样例数据完成导入验证。</p>}
          <div className="button-row">
            <button className="primary-button" type="button" disabled={disabled} onClick={() => onRun("import")}>
              {task.status === "running" ? <RefreshCw size={17} /> : <Play size={17} />}
              识别字段并合并
            </button>
            <button className="ghost-button" type="button" onClick={() => onFail("import")}>
              <AlertTriangle size={17} />错误态预览
            </button>
          </div>
        </article>

        <TaskStatusPanel task={task} />
      </section>

      <section className="import-result-grid" aria-label="导入结果">
        <ImportMappingPanel summary={summary} />
        <ImportPreviewPanel summary={summary} />
      </section>
    </div>
  );
}

function TableSourceCard({ title, icon, value, placeholder, fields, onChange }: { title: string; icon: ReactNode; value: string; placeholder: string; fields: string; onChange: (value: string) => void }) {
  return (
    <label className="table-source-card">
      <span className="source-heading">{icon}<strong>{title}</strong></span>
      <span className="source-fields">{fields}</span>
      <input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function ImportMappingPanel({ summary }: { summary: WorkflowSummary }) {
  const mappings = [
    ["doc_id", "文档编号", "必填"],
    ["article_title", "文章标题", "推荐"],
    ["newspaper", "报刊名", "推荐"],
    ["pub_date / pub_year", "出版日期 / 年份", "推荐"],
    ["genre", "文类", "可选"],
    ["text", "正文文本", "必填"]
  ];

  return (
    <article className="module-card import-table-card">
      <div className="module-heading"><Table2 size={18} /><span>字段识别结果</span></div>
      <table className="data-table">
        <thead>
          <tr><th>标准字段</th><th>含义</th><th>状态</th></tr>
        </thead>
        <tbody>
          {mappings.map(([field, label, status]) => <tr key={field}><td>{field}</td><td>{label}</td><td>{summary.mergedRows ? "已识别" : status}</td></tr>)}
        </tbody>
      </table>
    </article>
  );
}

function ImportPreviewPanel({ summary }: { summary: WorkflowSummary }) {
  return (
    <article className="module-card import-table-card">
      <div className="module-heading"><Database size={18} /><span>合并与预览</span></div>
      <div className="import-summary-strip">
        <Metric label="元数据行" value={summary.metadataRows || "待导入"} />
        <Metric label="正文行" value={summary.textRows || "待导入"} />
        <Metric label="合并文章" value={summary.mergedRows || "待合并"} />
      </div>
      <table className="data-table preview-table">
        <thead>
          <tr><th>doc_id</th><th>标题</th><th>报刊</th><th>正文</th></tr>
        </thead>
        <tbody>
          <tr><td>001</td><td>市场与工厂</td><td>申报</td><td>市场、贸易、工厂相关正文...</td></tr>
          <tr><td>002</td><td>学校新制</td><td>大公报</td><td>学校、教育、课程相关正文...</td></tr>
          <tr><td>003</td><td>城市交通</td><td>申报</td><td>城市、道路、交通相关正文...</td></tr>
        </tbody>
      </table>
      <p className="import-match-note">元数据未匹配 {summary.unmatchedMetaRows} 条，正文未匹配 {summary.unmatchedTextRows} 条。</p>
    </article>
  );
}

const pageDefinitions: Record<WorkflowRouteKey, PageDefinition> = {
  import: {
    task: "import",
    primaryAction: "识别字段并合并",
    controls: [
      { label: "元数据表", value: "metadata.xlsx" },
      { label: "正文表", value: "full_text.csv" },
      { label: "关联字段", value: "doc_id" }
    ],
    cards: [
      { title: "文件摘要", icon: <FileInput size={18} />, body: (summary) => `元数据 ${summary.metadataRows} 行，正文 ${summary.textRows} 行。` },
      { title: "字段映射", icon: <Table2 size={18} />, body: () => "doc_id、article_title、newspaper、pub_year、genre 与 text 字段进入标准映射预览。" },
      { title: "合并结果", icon: <Database size={18} />, body: (summary) => `已合并 ${summary.mergedRows} 篇，元数据未匹配 ${summary.unmatchedMetaRows} 条，正文未匹配 ${summary.unmatchedTextRows} 条。` }
    ]
  },
  clean: {
    task: "clean",
    primaryAction: "启动清洗任务",
    controls: [
      { label: "基础清理", value: "OCR、标点、数字、繁简转换" },
      { label: "文本长度", value: "最少 20 字" },
      { label: "词频阈值", value: "min_freq 2 / min_doc_freq 2" }
    ],
    cards: [
      { title: "清洗参数", icon: <Scissors size={18} />, body: () => "开关类参数与阈值分区展示，后续映射到 CleanOptionsPayload。" },
      { title: "样例预览", icon: <Table2 size={18} />, body: () => "同屏比较原文、清洗后文本和分词结果，便于调整停用词。" },
      { title: "语料统计", icon: <Database size={18} />, body: (summary) => `有效文档 ${summary.cleanDocuments} 篇，词元 ${summary.totalTokens} 个，唯一词 ${summary.uniqueWords} 个。` }
    ]
  },
  lda: {
    task: "lda",
    primaryAction: "训练 LDA",
    controls: [
      { label: "主题数", value: "12" },
      { label: "训练轮数", value: "passes 20 / iterations 400" },
      { label: "文类筛选", value: "全部文类" }
    ],
    cards: [
      { title: "主题关键词", icon: <Layers3 size={18} />, body: (summary) => `当前 ${summary.ldaTopics} 个主题，展示每个主题前 10 个关键词。` },
      { title: "一致性指标", icon: <BarChart3 size={18} />, body: (summary) => `Coherence：${summary.ldaCoherence ?? "待训练"}。` },
      { title: "可视化入口", icon: <Activity size={18} />, body: () => "保留 pyLDAvis 生成入口，作为独立长任务接入。" }
    ]
  },
  stm: {
    task: "stm",
    primaryAction: "训练 STM",
    controls: [
      { label: "R 环境", value: "待 bridge 检查" },
      { label: "prevalence", value: "~ newspaper + s(pub_year)" },
      { label: "content", value: "genre" }
    ],
    cards: [
      { title: "环境检查", icon: <Activity size={18} />, body: () => "展示 R、rpy2 与 stm 包可用性，并提供失败详情。" },
      { title: "协变量", icon: <Table2 size={18} />, body: () => "字段可用性、缺失值和低基数原因会集中展示。" },
      { title: "prevalence 摘要", icon: <BarChart3 size={18} />, body: (summary) => `当前 ${summary.stmTopics} 个 STM 主题，等待后端返回协变量效应。` }
    ]
  },
  compare: {
    task: "compare",
    primaryAction: "生成对比视图",
    controls: [
      { label: "模型", value: "自动选择 LDA / STM" },
      { label: "维度", value: "报刊 x 年份" },
      { label: "图表", value: "趋势线 + 聚合表" }
    ],
    cards: [
      { title: "趋势图", icon: <BarChart3 size={18} />, body: () => "展示主题占比随报刊和年份变化的序列。" },
      { title: "聚合表", icon: <Table2 size={18} />, body: () => "保留模型、主题、维度、文章数和平均权重列。" },
      { title: "代表文章", icon: <SplitSquareHorizontal size={18} />, body: () => "按主题权重列出 top 文档，并提供原文查看入口。" }
    ]
  },
  export: {
    task: "export",
    primaryAction: "导出选中项目",
    controls: [
      { label: "输出目录", value: "E:/topic-analyzer/output" },
      { label: "项目名", value: "未命名项目" },
      { label: "导出项目", value: "合并数据、清洗语料、LDA、STM、日志" }
    ],
    cards: [
      { title: "可导出项目", icon: <Download size={18} />, body: () => "按前置结果启用或禁用导出项，并展示缺失原因。" },
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

function ControlRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="control-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
