import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";

export type LanguageCode = "zh" | "en";
export type RouteKey = "welcome" | "import" | "clean" | "frequency" | "sentiment" | "ner" | "lda" | "stm" | "compare" | "export";
export type TaskKey = Exclude<RouteKey, "welcome">;
export type TaskStatus = "idle" | "running" | "succeeded" | "failed";
export type TaskResult = Record<string, unknown> | null;

export type WorkflowFlags = {
  imported: boolean;
  cleaned: boolean;
  frequencyDone: boolean;
  sentimentDone: boolean;
  nerDone: boolean;
  ldaDone: boolean;
  stmDone: boolean;
};

export type LanguageWorkflow = Record<LanguageCode, { cleaned: boolean; frequencyDone: boolean; sentimentDone: boolean; nerDone: boolean; ldaDone: boolean; stmDone: boolean }>;

export type WorkflowSummary = {
  documentRows: number;
  languageRows: Record<LanguageCode, number>;
  cleanDocuments: number;
  totalTokens: Record<LanguageCode, number>;
  uniqueWords: Record<LanguageCode, number>;
  frequencyWords: Record<LanguageCode, number>;
  sentimentDocuments: Record<LanguageCode, number>;
  nerEntities: Record<LanguageCode, number>;
  ldaTopics: Record<LanguageCode, number>;
  ldaCoherence: Record<LanguageCode, number | null>;
  stmTopics: Record<LanguageCode, number>;
  exportFiles: number;
};

export type TaskState = {
  key: TaskKey;
  label: string;
  status: TaskStatus;
  phase: string;
  message: string;
  progress: number | null;
  summary: string;
  error: string;
  updatedAt: string;
};

export type ImportConfig = {
  dataPath: string;
  fieldMapping: { doc_id: string; text: string; language: string };
};

export type LanguageCleanConfig = {
  useDefaultStopwords: boolean;
  stopwordsText: string;
  stopwordsPath: string;
  minTokenLength: number;
  customDictPath?: string;
  traditionalToSimplified?: boolean;
  lowercase?: boolean;
  repairHyphenation?: boolean;
};

export type CleanConfig = {
  removeEmpty: boolean;
  removeDuplicates: boolean;
  ocrClean: boolean;
  removePunct: boolean;
  removeNumbers: boolean;
  minTextLength: number;
  minTokenFreq: number;
  minDocFreq: number;
  maxDocFreqRatio: number;
  zh: LanguageCleanConfig;
  en: LanguageCleanConfig;
};

export type LdaParams = {
  numTopics: number;
  passes: number;
  iterations: number;
  randomState: number;
  minDocFreq: number;
  maxDocFreqRatio: number;
  genre: string;
};

export type FrequencyParams = {
  sortBy: "term_frequency" | "document_frequency";
  topN: number;
  minTermFrequency: number;
  minDocumentFrequency: number;
  randomState: number;
};

export type SentimentParams = {
  positiveThreshold: number;
  negativeThreshold: number;
  useNegation: boolean;
  useDegree: boolean;
  topEvidence: number;
  groupBy: string;
  positiveText: string;
  negativeText: string;
};

export type EntityType = "person" | "location" | "organization" | "office" | "time";

export type NerParams = {
  entityTypes: EntityType[];
  minMentionCount: number;
  contextWindow: number;
  useModel: boolean;
  personText: string;
  locationText: string;
  organizationText: string;
  officeText: string;
  timeText: string;
};

export type StmParams = {
  numTopics: number;
  prevalenceFormula: string;
  contentCovariate: string;
  maxEmIterations: number;
  randomState: number;
  genre: string;
};

export type CompareConfig = {
  language: LanguageCode;
  model: "lda" | "stm";
  axisField: string;
  metricField: string;
  filters: Record<string, string>;
  representativeLimit: number;
  chartType: "line" | "bar";
};

export type ExportConfig = {
  projectName: string;
  outputDir: string;
  items: string[];
  languages: LanguageCode[];
};

export type WorkflowConfigs = {
  clean: CleanConfig;
  frequencyLanguage: LanguageCode;
  frequency: Record<LanguageCode, FrequencyParams>;
  sentimentLanguage: LanguageCode;
  sentiment: Record<LanguageCode, SentimentParams>;
  nerLanguage: LanguageCode;
  ner: Record<LanguageCode, NerParams>;
  ldaLanguage: LanguageCode;
  lda: Record<LanguageCode, LdaParams>;
  stmLanguage: LanguageCode;
  stm: Record<LanguageCode, StmParams>;
  compare: CompareConfig;
  export: ExportConfig;
};

export type ConfigTaskKey = "clean" | "compare" | "export";
type LanguageResults = Record<LanguageCode, TaskResult>;
export type WorkflowResults = {
  import: TaskResult;
  clean: TaskResult;
  frequency: LanguageResults;
  sentiment: LanguageResults;
  ner: LanguageResults;
  lda: LanguageResults;
  stm: LanguageResults;
  compare: LanguageResults;
  export: TaskResult;
};

export type StmEnvironmentState = {
  checking: boolean;
  available: boolean | null;
  message: string;
  checkedAt: string;
};

type SelectedTextFile = { path: string; content: string };
type BackendResponse = {
  ok: boolean;
  data?: Record<string, unknown>;
  logs?: string[];
  state?: {
    workflow?: Partial<WorkflowFlags>;
    languageWorkflow?: Partial<LanguageWorkflow>;
    session?: { projectName?: string; outputDir?: string };
    summary?: Partial<WorkflowSummary>;
  };
  error?: { message?: string; suggestion?: string; issues?: Array<{ message?: string }> };
};

type WorkflowState = {
  activeRoute: RouteKey;
  projectName: string;
  outputDir: string;
  workflow: WorkflowFlags;
  languageWorkflow: LanguageWorkflow;
  summary: WorkflowSummary;
  importConfig: ImportConfig;
  configs: WorkflowConfigs;
  tasks: Record<TaskKey, TaskState>;
  results: WorkflowResults;
  stmEnvironment: StmEnvironmentState;
  logs: string[];
  setActiveRoute: (route: RouteKey) => void;
  setImportConfig: (values: Partial<ImportConfig>) => void;
  setTaskConfig: <K extends ConfigTaskKey>(task: K, values: Partial<WorkflowConfigs[K]>) => void;
  setModelLanguage: (model: "frequency" | "sentiment" | "ner" | "lda" | "stm", language: LanguageCode) => void;
  setModelConfig: (model: "frequency" | "sentiment" | "ner" | "lda" | "stm", language: LanguageCode, values: Partial<FrequencyParams & SentimentParams & NerParams & LdaParams & StmParams>) => void;
  setLanguageCleanConfig: (language: LanguageCode, values: Partial<LanguageCleanConfig>) => void;
  chooseImportFile: () => Promise<void>;
  chooseConfigPath: (target: "customDict" | "stopwords" | "outputDir", language?: LanguageCode) => Promise<void>;
  runBackendTask: (task: TaskKey) => Promise<void>;
  checkStmEnvironment: () => Promise<void>;
  clearLogs: () => void;
};

const now = () => new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const languages: LanguageCode[] = ["zh", "en"];
const labels: Record<TaskKey, string> = {
  import: "导入文献", clean: "双语清洗", frequency: "词频与词云", sentiment: "情感分析", ner: "实体识别", lda: "LDA 训练", stm: "STM 训练", compare: "对比分析", export: "导出结果"
};
const phases: Record<TaskKey, string> = {
  import: "字段识别与严格校验", clean: "语言感知清洗与分词", lda: "分语言 LDA 训练",
  frequency: "分语言词频统计与词云", sentiment: "分语言情感评分与聚合", ner: "分语言实体抽取与聚合", stm: "分语言 STM 训练", compare: "历史元数据聚合", export: "按语言重建并写入结果"
};

const createTask = (key: TaskKey): TaskState => ({
  key, label: labels[key], status: "idle", phase: "等待操作", message: "尚未启动",
  progress: null, summary: "", error: "", updatedAt: "--"
});
const createTasks = () => Object.fromEntries((Object.keys(labels) as TaskKey[]).map((key) => [key, createTask(key)])) as Record<TaskKey, TaskState>;
const emptyLanguageResults = (): LanguageResults => ({ zh: null, en: null });
const createResults = (): WorkflowResults => ({ import: null, clean: null, frequency: emptyLanguageResults(), sentiment: emptyLanguageResults(), ner: emptyLanguageResults(), lda: emptyLanguageResults(), stm: emptyLanguageResults(), compare: emptyLanguageResults(), export: null });
const emptyLanguageWorkflow = (): LanguageWorkflow => ({
  zh: { cleaned: false, frequencyDone: false, sentimentDone: false, nerDone: false, ldaDone: false, stmDone: false },
  en: { cleaned: false, frequencyDone: false, sentimentDone: false, nerDone: false, ldaDone: false, stmDone: false }
});
const emptySummary = (): WorkflowSummary => ({
  documentRows: 0, languageRows: { zh: 0, en: 0 }, cleanDocuments: 0,
  totalTokens: { zh: 0, en: 0 }, uniqueWords: { zh: 0, en: 0 },
  frequencyWords: { zh: 0, en: 0 }, sentimentDocuments: { zh: 0, en: 0 },
  nerEntities: { zh: 0, en: 0 },
  ldaTopics: { zh: 0, en: 0 }, ldaCoherence: { zh: null, en: null },
  stmTopics: { zh: 0, en: 0 }, exportFiles: 0
});

const defaultLda = (): LdaParams => ({ numTopics: 10, passes: 20, iterations: 400, randomState: 42, minDocFreq: 2, maxDocFreqRatio: 0.95, genre: "__all__" });
const defaultFrequency = (): FrequencyParams => ({ sortBy: "term_frequency", topN: 50, minTermFrequency: 1, minDocumentFrequency: 1, randomState: 42 });
const defaultSentiment = (): SentimentParams => ({ positiveThreshold: 0.05, negativeThreshold: -0.05, useNegation: true, useDegree: true, topEvidence: 8, groupBy: "", positiveText: "", negativeText: "" });
const defaultNer = (): NerParams => ({ entityTypes: ["person", "location", "organization", "office", "time"], minMentionCount: 1, contextWindow: 20, useModel: true, personText: "", locationText: "", organizationText: "", officeText: "", timeText: "" });
const defaultStm = (): StmParams => ({ numTopics: 10, prevalenceFormula: "~ 1", contentCovariate: "", maxEmIterations: 75, randomState: 42, genre: "__all__" });
const parseStopwords = (text: string) => [...new Set(text.split(/\r?\n/).map((word) => word.trim()).filter(Boolean))];

const sentimentPayload = (config: Record<LanguageCode, SentimentParams>) => {
  const build = (params: SentimentParams) => ({
    positiveThreshold: params.positiveThreshold,
    negativeThreshold: params.negativeThreshold,
    useNegation: params.useNegation,
    useDegree: params.useDegree,
    topEvidence: params.topEvidence,
    groupBy: params.groupBy,
    positiveWords: parseStopwords(params.positiveText),
    negativeWords: parseStopwords(params.negativeText)
  });
  return { zh: build(config.zh), en: build(config.en) };
};

const nerPayload = (config: Record<LanguageCode, NerParams>) => {
  const build = (params: NerParams) => ({
    entityTypes: params.entityTypes,
    minMentionCount: params.minMentionCount,
    contextWindow: params.contextWindow,
    useModel: params.useModel,
    personWords: parseStopwords(params.personText),
    locationWords: parseStopwords(params.locationText),
    organizationWords: parseStopwords(params.organizationText),
    officeWords: parseStopwords(params.officeText),
    timeWords: parseStopwords(params.timeText)
  });
  return { zh: build(config.zh), en: build(config.en) };
};

const cleanPayload = (config: CleanConfig) => ({
  cleanConfig: {
    removeEmpty: config.removeEmpty,
    removeDuplicates: config.removeDuplicates,
    ocrClean: config.ocrClean,
    removePunct: config.removePunct,
    removeNumbers: config.removeNumbers,
    minTextLength: config.minTextLength,
    minTokenFreq: config.minTokenFreq,
    minDocFreq: config.minDocFreq,
    maxDocFreqRatio: config.maxDocFreqRatio,
    zh: { ...config.zh, stopwords: parseStopwords(config.zh.stopwordsText) },
    en: { ...config.en, stopwords: parseStopwords(config.en.stopwordsText) }
  }
});

const backendPayload = (task: TaskKey, state: WorkflowState) => {
  const session = { projectName: state.projectName, outputDir: state.outputDir };
  if (task === "import") return {
    ...session,
    dataPath: state.importConfig.dataPath.trim() || undefined,
    fieldMapping: state.importConfig.fieldMapping
  };
  const common = {
    ...session,
    ...cleanPayload(state.configs.clean),
    frequencyConfigs: state.configs.frequency,
    sentimentConfigs: sentimentPayload(state.configs.sentiment),
    nerConfigs: nerPayload(state.configs.ner),
    ldaConfigs: state.configs.lda,
    stmConfigs: state.configs.stm
  };
  if (task === "clean") return common;
  if (task === "frequency") return { ...common, language: state.configs.frequencyLanguage };
  if (task === "sentiment") return { ...common, language: state.configs.sentimentLanguage };
  if (task === "ner") return { ...common, language: state.configs.nerLanguage };
  if (task === "lda") return { ...common, language: state.configs.ldaLanguage };
  if (task === "stm") return { ...common, language: state.configs.stmLanguage };
  if (task === "compare") return { ...common, ...state.configs.compare };
  return {
    ...common,
    projectName: state.configs.export.projectName.trim() || "未命名项目",
    outputDir: state.configs.export.outputDir.trim(),
    exportItems: state.configs.export.items,
    exportLanguages: state.configs.export.languages
  };
};

const appendLogs = (existing: string[], incoming: string[] = []) => [...existing, ...incoming].slice(-600);

const taskSummary = (task: TaskKey, state: WorkflowState, data: Record<string, unknown>) => {
  if (task === "import") return `已导入 ${state.summary.documentRows} 篇文献（中文 ${state.summary.languageRows.zh}，英文 ${state.summary.languageRows.en}）`;
  if (task === "clean") return `已生成 ${state.summary.cleanDocuments} 篇有效语料`;
  if (task === "frequency") return `${data.language === "en" ? "英文" : "中文"}词频分析完成，共显示 ${Array.isArray(data.rows) ? data.rows.length : 0} / ${String(data.filteredWords ?? 0)} 个词`;
  if (task === "sentiment") {
    const summary = (data.summary ?? {}) as { distribution?: Record<string, number> };
    const dist = summary.distribution ?? {};
    return `${data.language === "en" ? "英文" : "中文"}情感分析完成：正面 ${dist.positive ?? 0} / 中性 ${dist.neutral ?? 0} / 负面 ${dist.negative ?? 0}`;
  }
  if (task === "ner") {
    const summary = (data.summary ?? {}) as { entities?: number; mentions?: number };
    return `${data.language === "en" ? "英文" : "中文"}实体识别完成：${summary.entities ?? 0} 个实体 / ${summary.mentions ?? 0} 次出现`;
  }
  if (task === "export") return `已写入 ${String(data.count ?? state.summary.exportFiles)} 个文件`;
  const fallbackLanguage = task === "lda" ? state.configs.ldaLanguage : task === "stm" ? state.configs.stmLanguage : state.configs.compare.language;
  const language = String(data.language ?? fallbackLanguage);
  return `${language === "en" ? "英文" : "中文"}${labels[task]}完成`;
};

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  activeRoute: "welcome",
  projectName: "未命名项目",
  outputDir: "",
  workflow: { imported: false, cleaned: false, frequencyDone: false, sentimentDone: false, nerDone: false, ldaDone: false, stmDone: false },
  languageWorkflow: emptyLanguageWorkflow(),
  summary: emptySummary(),
  importConfig: { dataPath: "", fieldMapping: { doc_id: "doc_id", text: "text", language: "language" } },
  configs: {
    clean: {
      removeEmpty: true, removeDuplicates: true, ocrClean: true, removePunct: true,
      removeNumbers: true, minTextLength: 10, minTokenFreq: 1, minDocFreq: 2, maxDocFreqRatio: 0.95,
      zh: { useDefaultStopwords: true, stopwordsText: "", stopwordsPath: "", minTokenLength: 1, customDictPath: "", traditionalToSimplified: false },
      en: { useDefaultStopwords: true, stopwordsText: "", stopwordsPath: "", minTokenLength: 2, lowercase: true, repairHyphenation: true }
    },
    frequencyLanguage: "zh", frequency: { zh: defaultFrequency(), en: defaultFrequency() },
    sentimentLanguage: "zh", sentiment: { zh: defaultSentiment(), en: defaultSentiment() },
    nerLanguage: "zh", ner: { zh: defaultNer(), en: defaultNer() },
    ldaLanguage: "zh", lda: { zh: defaultLda(), en: defaultLda() },
    stmLanguage: "zh", stm: { zh: defaultStm(), en: defaultStm() },
    compare: { language: "zh", model: "lda", axisField: "source_name", metricField: "__all__", filters: {}, representativeLimit: 3, chartType: "bar" },
    export: {
      projectName: "未命名项目", outputDir: "", languages: ["zh", "en"],
      items: ["documents", "cleaned_documents", "tokens_corpus", "word_frequency", "word_cloud", "sentiment_documents", "sentiment_summary", "entities", "entity_mentions", "lda_topic_word", "lda_doc_topic", "lda_coherence", "stm_topic_word", "stm_doc_topic", "stm_prevalence", "session_config"]
    }
  },
  tasks: createTasks(),
  results: createResults(),
  stmEnvironment: { checking: false, available: null, message: "尚未检查 R 环境", checkedAt: "--" },
  logs: [],
  setActiveRoute: (activeRoute) => set({ activeRoute }),
  setImportConfig: (values) => set((state) => ({ importConfig: { ...state.importConfig, ...values } })),
  setTaskConfig: (task, values) => set((state) => ({ configs: { ...state.configs, [task]: { ...state.configs[task], ...values } } as WorkflowConfigs })),
  setModelLanguage: (model, language) => set((state) => ({ configs: { ...state.configs, [`${model}Language`]: language } } as Partial<WorkflowState>)),
  setModelConfig: (model, language, values) => set((state) => ({
    configs: { ...state.configs, [model]: { ...state.configs[model], [language]: { ...state.configs[model][language], ...values } } } as WorkflowConfigs
  })),
  setLanguageCleanConfig: (language, values) => set((state) => ({
    configs: { ...state.configs, clean: { ...state.configs.clean, [language]: { ...state.configs.clean[language], ...values } } }
  })),
  chooseImportFile: async () => {
    const dataPath = await invoke<string | null>("select_import_file");
    if (dataPath) set((state) => ({ importConfig: { ...state.importConfig, dataPath } }));
  },
  chooseConfigPath: async (target, language = "zh") => {
    if (target === "stopwords") {
      const selected = await invoke<SelectedTextFile | null>("select_stopwords_file");
      if (selected) get().setLanguageCleanConfig(language, { stopwordsPath: selected.path, stopwordsText: selected.content });
      return;
    }
    if (target === "outputDir") {
      const outputDir = await invoke<string | null>("select_output_directory");
      if (outputDir) set((state) => ({ outputDir, configs: { ...state.configs, export: { ...state.configs.export, outputDir } } }));
      return;
    }
    const path = await invoke<string | null>("select_dictionary_file");
    if (path) get().setLanguageCleanConfig("zh", { customDictPath: path });
  },
  runBackendTask: async (task) => {
    set((state) => ({
      logs: appendLogs(state.logs, [`[${now()}] ${labels[task]}：开始`]),
      tasks: { ...state.tasks, [task]: { ...state.tasks[task], status: "running", phase: phases[task], message: "处理中…", progress: null, error: "", updatedAt: now() } },
      ...(task === "import" ? { results: createResults(), workflow: { imported: false, cleaned: false, frequencyDone: false, sentimentDone: false, nerDone: false, ldaDone: false, stmDone: false }, languageWorkflow: emptyLanguageWorkflow(), summary: emptySummary() } : {}),
      ...(task === "clean" ? {
        results: { ...state.results, clean: null, frequency: emptyLanguageResults(), sentiment: emptyLanguageResults(), ner: emptyLanguageResults(), lda: emptyLanguageResults(), stm: emptyLanguageResults(), compare: emptyLanguageResults(), export: null },
        workflow: { ...state.workflow, cleaned: false, frequencyDone: false, sentimentDone: false, nerDone: false, ldaDone: false, stmDone: false },
        languageWorkflow: emptyLanguageWorkflow(),
        summary: { ...state.summary, cleanDocuments: 0, totalTokens: { zh: 0, en: 0 }, uniqueWords: { zh: 0, en: 0 }, frequencyWords: { zh: 0, en: 0 }, sentimentDocuments: { zh: 0, en: 0 }, nerEntities: { zh: 0, en: 0 }, ldaTopics: { zh: 0, en: 0 }, ldaCoherence: { zh: null, en: null }, stmTopics: { zh: 0, en: 0 }, exportFiles: 0 }
      } : {})
    }));
    try {
      const state = get();
      const response = await invoke<BackendResponse>("run_python_task", { task, payload: backendPayload(task, state) });
      if (!response.ok) {
        const detail = response.error?.issues?.map((item) => item.message).filter(Boolean).join("；");
        throw new Error(detail || response.error?.message || response.error?.suggestion || "任务失败");
      }
      const data = response.data ?? {};
      set((current) => {
        const incomingSummary = response.state?.summary;
        const incomingFrequencyWords: Partial<Record<LanguageCode, number>> = incomingSummary?.frequencyWords ?? {};
        const incomingSentimentDocuments: Partial<Record<LanguageCode, number>> = incomingSummary?.sentimentDocuments ?? {};
        const incomingNerEntities: Partial<Record<LanguageCode, number>> = incomingSummary?.nerEntities ?? {};
        const incomingLdaTopics: Partial<Record<LanguageCode, number>> = incomingSummary?.ldaTopics ?? {};
        const incomingLdaCoherence: Partial<Record<LanguageCode, number | null>> = incomingSummary?.ldaCoherence ?? {};
        const incomingStmTopics: Partial<Record<LanguageCode, number>> = incomingSummary?.stmTopics ?? {};
        const summary: WorkflowSummary = {
          ...current.summary,
          ...incomingSummary,
          languageRows: { ...current.summary.languageRows, ...(incomingSummary?.languageRows ?? {}) },
          totalTokens: { ...current.summary.totalTokens, ...(incomingSummary?.totalTokens ?? {}) },
          uniqueWords: { ...current.summary.uniqueWords, ...(incomingSummary?.uniqueWords ?? {}) },
          frequencyWords: {
            zh: Number(incomingFrequencyWords.zh ?? 0) > 0 ? Number(incomingFrequencyWords.zh) : current.summary.frequencyWords.zh,
            en: Number(incomingFrequencyWords.en ?? 0) > 0 ? Number(incomingFrequencyWords.en) : current.summary.frequencyWords.en
          },
          sentimentDocuments: {
            zh: Number(incomingSentimentDocuments.zh ?? 0) > 0 ? Number(incomingSentimentDocuments.zh) : current.summary.sentimentDocuments.zh,
            en: Number(incomingSentimentDocuments.en ?? 0) > 0 ? Number(incomingSentimentDocuments.en) : current.summary.sentimentDocuments.en
          },
          nerEntities: {
            zh: Number(incomingNerEntities.zh ?? 0) > 0 ? Number(incomingNerEntities.zh) : current.summary.nerEntities.zh,
            en: Number(incomingNerEntities.en ?? 0) > 0 ? Number(incomingNerEntities.en) : current.summary.nerEntities.en
          },
          ldaTopics: {
            zh: Number(incomingLdaTopics.zh ?? 0) > 0 ? Number(incomingLdaTopics.zh) : current.summary.ldaTopics.zh,
            en: Number(incomingLdaTopics.en ?? 0) > 0 ? Number(incomingLdaTopics.en) : current.summary.ldaTopics.en
          },
          ldaCoherence: {
            zh: incomingLdaCoherence.zh != null ? incomingLdaCoherence.zh : current.summary.ldaCoherence.zh,
            en: incomingLdaCoherence.en != null ? incomingLdaCoherence.en : current.summary.ldaCoherence.en
          },
          stmTopics: {
            zh: Number(incomingStmTopics.zh ?? 0) > 0 ? Number(incomingStmTopics.zh) : current.summary.stmTopics.zh,
            en: Number(incomingStmTopics.en ?? 0) > 0 ? Number(incomingStmTopics.en) : current.summary.stmTopics.en
          }
        };
        const languageWorkflow = { ...current.languageWorkflow };
        languages.forEach((language) => {
          const incoming = response.state?.languageWorkflow?.[language];
          languageWorkflow[language] = {
            cleaned: languageWorkflow[language].cleaned || incoming?.cleaned === true,
            frequencyDone: languageWorkflow[language].frequencyDone || incoming?.frequencyDone === true,
            sentimentDone: languageWorkflow[language].sentimentDone || incoming?.sentimentDone === true,
            nerDone: languageWorkflow[language].nerDone || incoming?.nerDone === true,
            ldaDone: languageWorkflow[language].ldaDone || incoming?.ldaDone === true,
            stmDone: languageWorkflow[language].stmDone || incoming?.stmDone === true
          };
        });
        const workflow = {
          imported: current.workflow.imported || response.state?.workflow?.imported === true,
          cleaned: current.workflow.cleaned || response.state?.workflow?.cleaned === true,
          frequencyDone: current.workflow.frequencyDone || response.state?.workflow?.frequencyDone === true,
          sentimentDone: current.workflow.sentimentDone || response.state?.workflow?.sentimentDone === true,
          nerDone: current.workflow.nerDone || response.state?.workflow?.nerDone === true,
          ldaDone: current.workflow.ldaDone || response.state?.workflow?.ldaDone === true,
          stmDone: current.workflow.stmDone || response.state?.workflow?.stmDone === true
        };
        const results = { ...current.results };
        if (task === "frequency" || task === "sentiment" || task === "ner" || task === "lda" || task === "stm" || task === "compare") {
          const fallbackLanguage = task === "frequency" ? current.configs.frequencyLanguage : task === "sentiment" ? current.configs.sentimentLanguage : task === "ner" ? current.configs.nerLanguage : task === "lda" ? current.configs.ldaLanguage : task === "stm" ? current.configs.stmLanguage : current.configs.compare.language;
          const language: LanguageCode = data.language === "en" ? "en" : data.language === "zh" ? "zh" : fallbackLanguage;
          results[task] = { ...results[task], [language]: data } as never;
        } else {
          results[task] = data as never;
        }
        const next = { ...current, summary, workflow, languageWorkflow, results };
        return {
          summary, workflow, languageWorkflow, results,
          projectName: response.state?.session?.projectName ?? current.projectName,
          outputDir: response.state?.session?.outputDir ?? current.outputDir,
          logs: appendLogs(current.logs, response.logs),
          tasks: { ...current.tasks, [task]: { ...current.tasks[task], status: "succeeded", phase: "已完成", message: taskSummary(task, next, data), summary: taskSummary(task, next, data), progress: 100, updatedAt: now() } }
        };
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      set((state) => ({
        logs: appendLogs(state.logs, [`[${now()}] ${labels[task]}失败：${message}`]),
        tasks: { ...state.tasks, [task]: { ...state.tasks[task], status: "failed", phase: "执行失败", message, error: message, progress: null, updatedAt: now() } }
      }));
    }
  },
  checkStmEnvironment: async () => {
    set({ stmEnvironment: { checking: true, available: null, message: "正在检查 R、rpy2 与 stm 包…", checkedAt: now() } });
    try {
      const response = await invoke<BackendResponse>("run_python_task", { task: "stm-check", payload: {} });
      if (!response.ok) throw new Error(response.error?.message || "环境检查失败");
      set({ stmEnvironment: { checking: false, available: response.data?.available === true, message: String(response.data?.message ?? "检查完成"), checkedAt: now() } });
    } catch (error) {
      set({ stmEnvironment: { checking: false, available: false, message: error instanceof Error ? error.message : String(error), checkedAt: now() } });
    }
  },
  clearLogs: () => set({ logs: [] })
}));
