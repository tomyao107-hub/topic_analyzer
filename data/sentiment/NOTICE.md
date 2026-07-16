# 情感分析词典来源与许可

本目录内的情感词典来自公开发布的第三方研究资源，随本工具一同分发，仅做了编码统一（UTF-8）、
换行统一（LF）、去重和长度过滤等无损清理，未改变词语的情感极性判断。使用这些结果进行研究时，
建议在成果中引用下列原始来源。

## 英文：`en/vader_lexicon.txt`

- 名称：VADER（Valence Aware Dictionary and sEntiment Reasoner）情感词典
- 作者：C.J. Hutto
- 许可：MIT License，允许再分发与商用
- 来源：https://github.com/cjhutto/vaderSentiment
- 引用：Hutto, C.J. & Gilbert, E.E. (2014). VADER: A Parsimonious Rule-based Model for
  Sentiment Analysis of Social Media Text. Eighth International Conference on Weblogs and
  Social Media (ICWSM-14).
- 文件格式：`词\t均值效价\t标准差\t人工标注数组`，本工具仅使用第 1、2 列（词与均值效价）。

## 中文：`zh/positive.txt`、`zh/negative.txt`

- 名称：台湾大学 NTUSD 简体中文情感词典（正面词表 / 负面词表）
- 说明：由台湾大学整理发布的中文正负情感词表，长期在公开研究项目中转载使用。
- 本工具做的处理：转换为 UTF-8/LF，剔除包含空白、标点、数字的多词条目，剔除长度大于 6 的
  超长复合词，去除同时出现在正、负词表中的词，并保持原始顺序去重。
- 情感极性说明：这两个词表只提供正面 / 负面的二元归类，不含强度分值；本工具对命中词赋予
  单位权重，再叠加否定与程度规则。

## 中文：`zh/negation.txt`

- 名称：中文否定词表
- 说明：常见的中文情感分析否定词集合（如“不”“没有”“毫无”等），用于翻转其后情感词的极性。
- 处理：转换为 UTF-8/LF 并去重。

## 说明

- 本工具刻意未内置“大连理工大学情感词汇本体库”，因其发布说明限定“仅供学术研究”，与本工具
  作为通用桌面软件随包分发的场景不完全兼容。
- 程度副词（增强 / 减弱词）与其分级权重由本工具在 `services/sentiment_service.py` 中以
  精选内置表的形式维护，未直接分发第三方的程度副词文件。
- 情感分类为算法测量结果，需结合文本证据与历史语境解释，不能作为客观事实。
