import { BarChart3, Boxes, Download, FileInput, Home, Layers3, Scissors, SplitSquareHorizontal } from "lucide-react";
import type { RouteKey } from "./state/workflowStore";

export type AppRoute = {
  key: RouteKey;
  label: string;
  description: string;
  Icon: typeof Home;
};

export const routes: AppRoute[] = [
  { key: "welcome", label: "总览", description: "项目状态与下一步", Icon: Home },
  { key: "import", label: "导入", description: "元数据、正文与字段识别", Icon: FileInput },
  { key: "clean", label: "清洗", description: "OCR 清理、分词与停用词", Icon: Scissors },
  { key: "lda", label: "LDA", description: "主题建模与一致性", Icon: Layers3 },
  { key: "stm", label: "STM", description: "协变量建模与 R 环境", Icon: Boxes },
  { key: "compare", label: "对比", description: "报刊、年份、文类与主题差异", Icon: SplitSquareHorizontal },
  { key: "export", label: "导出", description: "结果文件与处理日志", Icon: Download }
];

export const routeLabels = routes.reduce<Record<RouteKey, string>>((labels, route) => {
  labels[route.key] = route.label;
  return labels;
}, {} as Record<RouteKey, string>);
