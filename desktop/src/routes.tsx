import { Boxes, Cloud, Download, FileInput, Heart, Home, Layers3, Scissors, SplitSquareHorizontal, Users } from "lucide-react";
import type { RouteKey } from "./state/workflowStore";

export type AppRoute = {
  key: RouteKey;
  label: string;
  description: string;
  Icon: typeof Home;
};

export const routes: AppRoute[] = [
  { key: "welcome", label: "总览", description: "项目状态与下一步", Icon: Home },
  { key: "import", label: "导入", description: "单表字段识别与严格校验", Icon: FileInput },
  { key: "clean", label: "清洗", description: "中英文清洗、分词与停用词", Icon: Scissors },
  { key: "frequency", label: "词频", description: "高频词、文档频率与词云", Icon: Cloud },
  { key: "sentiment", label: "情感", description: "词典规则情感评分与聚合", Icon: Heart },
  { key: "ner", label: "实体", description: "人名地名机构官职时间抽取", Icon: Users },
  { key: "lda", label: "LDA", description: "主题建模与一致性", Icon: Layers3 },
  { key: "stm", label: "STM", description: "协变量建模与 R 环境", Icon: Boxes },
  { key: "compare", label: "对比", description: "动态历史元数据维度", Icon: SplitSquareHorizontal },
  { key: "export", label: "导出", description: "结果文件与处理日志", Icon: Download }
];

export const routeLabels = routes.reduce<Record<RouteKey, string>>((labels, route) => {
  labels[route.key] = route.label;
  return labels;
}, {} as Record<RouteKey, string>);
