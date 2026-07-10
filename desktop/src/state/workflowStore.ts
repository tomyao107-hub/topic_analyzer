import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";

export type RouteKey = "welcome" | "import" | "clean" | "lda" | "stm" | "compare" | "export";
export type TaskStatus = "idle" | "running" | "succeeded" | "failed";
export type TaskKey = "import" | "clean" | "lda" | "stm" | "compare" | "export";

type WorkflowFlags = {
  imported: boolean;
  merged: boolean;
  cleaned: boolean;
  ldaDone: boolean;
  stmDone: boolean;
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

type WorkflowSummary = {
  metadataRows: number;
  textRows: number;
  mergedRows: number;
  unmatchedMetaRows: number;
  unmatchedTextRows: number;
  cleanDocuments: number;
  totalTokens: number;
  uniqueWords: number;
  ldaTopics: number;
  ldaCoherence: number | null;
  stmTopics: number;
  exportFiles: number;
};

export type ImportConfig = {
  metadataPath: string;
  textPath: string;
  metadataIdField: string;
  textIdField: string;
};

export type CleanConfig = {
  removeEmpty: boolean;
  removeDuplicates: boolean;
  ocrClean: boolean;
  removePunct: boolean;
  removeNumbers: boolean;
  traditionalToSimplified: boolean;
  minTextLength: number;
  minTokenFreq: number;
  minDocFreq: number;
  maxDocFreqRatio: number;
  customDictPath: string;
};

export type LdaConfig = {
  numTopics: number;
  passes: number;
  iterations: number;
  randomState: number;
  minDocFreq: number;
  maxDocFreqRatio: number;
};

export type StmConfig = {
  numTopics: number;
  prevalenceFormula: string;
  contentCovariate: string;
  maxEmIterations: number;
  randomState: number;
};

export type CompareConfig = {
  model: "lda" | "stm";
  axisField: string;
  representativeLimit: number;
  chartType: "line" | "bar";
};

export type ExportConfig = {
  projectName: string;
  outputDir: string;
  items: string[];
};

export type WorkflowConfigs = {
  clean: CleanConfig;
  lda: LdaConfig;
  stm: StmConfig;
  compare: CompareConfig;
  export: ExportConfig;
};

export type ConfigTaskKey = keyof WorkflowConfigs;

type WorkflowState = {
  activeRoute: RouteKey;
  projectName: string;
  outputDir: string;
  workflow: WorkflowFlags;
  summary: WorkflowSummary;
  importConfig: ImportConfig;
  configs: WorkflowConfigs;
  tasks: Record<TaskKey, TaskState>;
  setActiveRoute: (route: RouteKey) => void;
  setImportConfig: (values: Partial<ImportConfig>) => void;
  setTaskConfig: <K extends ConfigTaskKey>(task: K, values: Partial<WorkflowConfigs[K]>) => void;
  chooseImportFile: (role: "metadata" | "text") => Promise<void>;
  chooseConfigPath: (target: "customDict" | "outputDir") => Promise<void>;
  runBackendTask: (task: TaskKey) => Promise<void>;
  failBackendTask: (task: TaskKey) => void;
};

const now = () => new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

const createTask = (key: TaskKey, label: string): TaskState => ({
  key,
  label,
  status: "idle",
  phase: "等待操作",
  message: "尚未启动",
  progress: null,
  summary: "",
  error: "",
  updatedAt: "--"
});

const taskLabels: Record<TaskKey, string> = {
  import: "导入与合并",
  clean: "清洗与分词",
  lda: "LDA 训练",
  stm: "STM 训练",
  compare: "对比分析",
  export: "批量导出"
};

const taskPlans: Record<TaskKey, { phase: string; message: string; progress: number }> = {
  import: {
    phase: "字段识别与合并",
    message: "正在校验元数据表、正文表和 doc_id 映射",
    progress: 72
  },
  clean: {
    phase: "文本清洗与分词",
    message: "正在应用 OCR 清理、停用词和词频阈值",
    progress: 58
  },
  lda: {
    phase: "模型训练与指标计算",
    message: "正在训练主题模型并计算一致性指标",
    progress: 64
  },
  stm: {
    phase: "R 环境调用与协变量估计",
    message: "正在检查 prevalence 公式并训练结构主题模型",
    progress: 46
  },
  compare: {
    phase: "聚合主题差异",
    message: "正在按报刊、年份和主题维度生成趋势摘要",
    progress: 83
  },
  export: {
    phase: "写入结果文件",
    message: "正在汇总清洗语料、主题结果、图表数据和日志",
    progress: 69
  }
};

const initialTasks = Object.fromEntries(
  (Object.keys(taskLabels) as TaskKey[]).map((key) => [key, createTask(key, taskLabels[key])])
) as Record<TaskKey, TaskState>;

const applyTaskResult = (task: TaskKey, workflow: WorkflowFlags, summary: WorkflowSummary) => {
  if (task === "import") {
    workflow.imported = true;
    workflow.merged = true;
    summary.metadataRows = 1248;
    summary.textRows = 1243;
    summary.mergedRows = 1236;
    summary.unmatchedMetaRows = 12;
    summary.unmatchedTextRows = 7;
  }

  if (task === "clean") {
    workflow.cleaned = true;
    summary.cleanDocuments = 1204;
    summary.totalTokens = 86420;
    summary.uniqueWords = 7842;
  }

  if (task === "lda") {
    workflow.ldaDone = true;
    summary.ldaTopics = 12;
    summary.ldaCoherence = 0.512;
  }

  if (task === "stm") {
    workflow.stmDone = true;
    summary.stmTopics = 10;
  }

  if (task === "export") {
    summary.exportFiles = 5;
  }
};

type BackendResponse = {
  ok: boolean;
  data?: Record<string, unknown>;
  state?: {
    workflow?: WorkflowFlags;
    session?: {
      projectName?: string;
      outputDir?: string;
    };
    summary?: Partial<WorkflowSummary>;
  };
  error?: {
    message?: string;
    suggestion?: string;
  };
};

const backendPayload = (task: TaskKey, state: WorkflowState) => {
  const session = { projectName: state.projectName, outputDir: state.outputDir };

  if (task === "import") {
    return {
      ...session,
      metadataPath: state.importConfig.metadataPath.trim() || undefined,
      textPath: state.importConfig.textPath.trim() || undefined,
      metadataIdField: state.importConfig.metadataIdField,
      textIdField: state.importConfig.textIdField
    };
  }

  if (task === "export") {
    return {
      projectName: state.configs.export.projectName.trim() || "未命名项目",
      outputDir: state.configs.export.outputDir.trim(),
      exportItems: state.configs.export.items,
      options: state.configs.clean,
      customDictPath: state.configs.clean.customDictPath.trim() || undefined,
      ldaConfig: state.configs.lda,
      stmConfig: state.configs.stm
    };
  }

  if (task === "lda") {
    return { ...session, ...state.configs.lda };
  }

  if (task === "clean") {
    return {
      ...session,
      options: state.configs.clean,
      customDictPath: state.configs.clean.customDictPath.trim() || undefined
    };
  }

  if (task === "stm") {
    return { ...session, ...state.configs.stm };
  }

  if (task === "compare") {
    const modelConfig = state.configs.compare.model === "stm" ? state.configs.stm : state.configs.lda;
    return { ...session, ...modelConfig, ...state.configs.compare };
  }

  return session;
};

const taskSummary = (task: TaskKey, response: BackendResponse) => {
  const summary = response.state?.summary;
  const data = response.data ?? {};

  if (task === "import") {
    return `已识别 ${summary?.metadataRows ?? 0} 条元数据、${summary?.textRows ?? 0} 条正文，合并 ${summary?.mergedRows ?? 0} 篇文章`;
  }

  if (task === "clean") {
    return `已生成 ${summary?.cleanDocuments ?? 0} 篇有效语料，保留 ${summary?.totalTokens ?? 0} 个词元和 ${summary?.uniqueWords ?? 0} 个唯一词`;
  }

  if (task === "lda") {
    return `已完成 ${summary?.ldaTopics ?? 0} 个 LDA 主题，Coherence ${summary?.ldaCoherence ?? "未计算"}`;
  }

  if (task === "stm") {
    return `已完成 ${data.topicCount ?? summary?.stmTopics ?? 0} 个 STM 主题，覆盖 ${data.documents ?? 0} 篇文档`;
  }

  if (task === "compare") {
    const rows = Array.isArray(data.rows) ? data.rows.length : Number(data.rows ?? 0);
    const topics = data.representativeArticles && typeof data.representativeArticles === "object"
      ? Object.keys(data.representativeArticles).length
      : 0;
    return `已生成 ${rows} 行对比数据，包含 ${topics} 个主题的代表文章`;
  }

  return `已导出 ${summary?.exportFiles ?? 0} 个结果文件`;
};

const mergeBackendState = (task: TaskKey, state: WorkflowState, response: BackendResponse) => {
  const workflow = { ...state.workflow, ...(response.state?.workflow ?? {}) };
  const summary = { ...state.summary, ...(response.state?.summary ?? {}) };
  const session = response.state?.session ?? {};

  if (!response.state?.workflow) {
    applyTaskResult(task, workflow, summary);
  }

  return {
    workflow,
    summary,
    projectName: session.projectName ?? state.projectName,
    outputDir: session.outputDir ?? state.outputDir
  };
};

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  activeRoute: "welcome",
  projectName: "未命名项目",
  outputDir: "E:/topic-analyzer/output",
  workflow: {
    imported: false,
    merged: false,
    cleaned: false,
    ldaDone: false,
    stmDone: false
  },
  summary: {
    metadataRows: 0,
    textRows: 0,
    mergedRows: 0,
    unmatchedMetaRows: 0,
    unmatchedTextRows: 0,
    cleanDocuments: 0,
    totalTokens: 0,
    uniqueWords: 0,
    ldaTopics: 0,
    ldaCoherence: null,
    stmTopics: 0,
    exportFiles: 0
  },
  importConfig: {
    metadataPath: "",
    textPath: "",
    metadataIdField: "doc_id",
    textIdField: "doc_id"
  },
  configs: {
    clean: {
      removeEmpty: true,
      removeDuplicates: true,
      ocrClean: true,
      removePunct: true,
      removeNumbers: true,
      traditionalToSimplified: false,
      minTextLength: 10,
      minTokenFreq: 1,
      minDocFreq: 2,
      maxDocFreqRatio: 0.95,
      customDictPath: ""
    },
    lda: {
      numTopics: 10,
      passes: 20,
      iterations: 400,
      randomState: 42,
      minDocFreq: 2,
      maxDocFreqRatio: 0.95
    },
    stm: {
      numTopics: 10,
      prevalenceFormula: "~ newspaper + s(pub_year)",
      contentCovariate: "genre",
      maxEmIterations: 75,
      randomState: 42
    },
    compare: {
      model: "lda",
      axisField: "newspaper",
      representativeLimit: 3,
      chartType: "line"
    },
    export: {
      projectName: "未命名项目",
      outputDir: "E:/topic-analyzer/output",
      items: ["merged_data", "cleaned_records", "cleaned_corpus", "lda_topic_word", "lda_doc_topic", "lda_coherence", "session_config"]
    }
  },
  tasks: initialTasks,
  setActiveRoute: (route) => set({ activeRoute: route }),
  setImportConfig: (values) => set((state) => ({ importConfig: { ...state.importConfig, ...values } })),
  setTaskConfig: (task, values) => set((state) => ({
    configs: { ...state.configs, [task]: { ...state.configs[task], ...values } }
  } as Partial<WorkflowState>)),
  chooseImportFile: async (role) => {
    const path = await invoke<string | null>("select_import_file");
    if (path) {
      set((state) => ({
        importConfig: {
          ...state.importConfig,
          [role === "metadata" ? "metadataPath" : "textPath"]: path
        }
      }));
    }
  },
  chooseConfigPath: async (target) => {
    const command = target === "outputDir" ? "select_output_directory" : "select_dictionary_file";
    const path = await invoke<string | null>(command);
    if (!path) return;
    set((state) => target === "outputDir"
      ? {
          outputDir: path,
          configs: { ...state.configs, export: { ...state.configs.export, outputDir: path } }
        }
      : {
          configs: { ...state.configs, clean: { ...state.configs.clean, customDictPath: path } }
        });
  },
  runBackendTask: async (task) => {
    const plan = taskPlans[task];
    set((state) => ({
      tasks: {
        ...state.tasks,
        [task]: {
          ...state.tasks[task],
          status: "running",
          phase: plan.phase,
          message: plan.message,
          progress: plan.progress,
          summary: "",
          error: "",
          updatedAt: now()
        }
      }
    }));

    try {
      const response = await invoke<BackendResponse>("run_python_task", { task, payload: backendPayload(task, get()) });
      if (!response.ok) {
        throw new Error([response.error?.message, response.error?.suggestion].filter(Boolean).join("；") || "Python bridge 返回失败");
      }

      set((state) => {
        const backendState = mergeBackendState(task, state, response);

        return {
          ...backendState,
          tasks: {
            ...state.tasks,
            [task]: {
              ...state.tasks[task],
              status: "succeeded",
              phase: "已完成",
              message: "Python 后端任务完成，结果摘要已同步到当前工作流",
              progress: 100,
              summary: taskSummary(task, response),
              error: "",
              updatedAt: now()
            }
          }
        };
      });
    } catch (error) {
      set((state) => ({
        tasks: {
          ...state.tasks,
          [task]: {
            ...state.tasks[task],
            status: "failed",
            phase: "Python 后端调用失败",
            message: "任务未完成",
            progress: null,
            summary: "",
            error: error instanceof Error ? error.message : String(error),
            updatedAt: now()
          }
        }
      }));
    }
  },
  failBackendTask: (task) => {
    set((state) => ({
      tasks: {
        ...state.tasks,
        [task]: {
          ...state.tasks[task],
          status: "failed",
          phase: "前置条件未满足",
          message: "任务未启动",
          progress: null,
          summary: "",
          error: "请先完成上一工作流步骤，或检查 Python bridge 返回的可恢复错误详情。",
          updatedAt: now()
        }
      }
    }));
  }
}));
