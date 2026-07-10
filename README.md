# 历史报刊主题分析工具

> 面向数字人文研究的中文报刊 LDA + STM 主题建模桌面应用

---

## 功能概览

| 模块 | 功能 |
|------|------|
| 数据导入 | 支持 CSV / Excel，自动识别中英文字段名，拖拽上传 |
| 数据清洗 | OCR 噪声清洗、jieba 分词、停用词过滤、繁简转换 |
| LDA 建模 | gensim LDA，Coherence 评估，pyLDAvis 可视化 |
| STM 建模 | 通过 rpy2 调用 R stm 包，支持 prevalence / content 协变量 |
| 对比分析 | 报刊对比、年份趋势、文类差异，代表文章查看 |
| 导出结果 | CSV 矩阵、图表、会话配置，处理日志 |

---

## 输入数据格式

### 元数据表（metadata.csv / xlsx）

| 字段（中文） | 字段（英文） | 必须 |
|------------|------------|------|
| 文档编号 | doc_id | ✅ |
| 报刊名 | newspaper | 推荐 |
| 出版日期 | pub_date | 推荐 |
| 文章标题 | article_title | 推荐 |
| 作者 | author | 可选 |
| 期号 | issue_no | 可选 |
| 页码 | page | 可选 |
| 文类 | genre | 推荐（STM 协变量） |
| 时间序号 | time_index | 可选（系统可自动生成） |

### 关于 `time_index`

如果数据跨多个年份，单独使用 `pub_month` 会把不同年份的同一月份合并。例如 1920 年 3 月和 1921 年 3 月都会被视为 3 月。系统会自动生成 `time_index`，将月份转换为从最早年月开始的连续序号，例如 1920 年 3 月为 1，1920 年 4 月为 2，1921 年 3 月为 13。

用户也可以在元数据表中自行提供 `time_index`。如果已提供，系统会保留原值，不自动覆盖。

### 文本表（texts.csv / xlsx）

| 字段（中文） | 字段（英文） | 必须 |
|------------|------------|------|
| 文档编号 | doc_id | ✅ |
| 正文文本 | text | ✅ |

---

## 安装步骤

### 1. 环境要求

- Python 3.11+
- （STM 功能）R >= 4.0

### 2. 创建虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

开发或运行测试时安装额外依赖：

```bash
pip install -r requirements-dev.txt
```

### 4. 安装 STM 所需 R 环境（可选）

**步骤 4-1：安装 R**

访问 https://cran.r-project.org/ 下载并安装适合您系统的 R（>= 4.0）。

**步骤 4-2：在 R 控制台安装 stm 包**

```r
install.packages("stm")
install.packages("quanteda")
```

**步骤 4-3：安装 rpy2**

```bash
pip install rpy2
```

**步骤 4-4（Windows 用户）：配置 R_HOME 环境变量**

1. 找到 R 的安装路径，例如：`C:\Program Files\R\R-4.3.2`
2. 设置系统环境变量 `R_HOME = C:\Program Files\R\R-4.3.2`
3. 将 `C:\Program Files\R\R-4.3.2\bin\x64` 加入 `PATH`
4. 重启命令行和本应用

**步骤 4-5：验证配置**

在 STM 分析页点击"检查 R 环境"按钮验证是否配置成功。

### 5. 安装可选依赖

```bash
# LDA 交互可视化
pip install pyLDAvis

# 繁体转简体
pip install opencc-python-reimplemented
```

---

## 启动应用

### 推荐启动方式

**Windows：**

直接双击：

```bat
run.bat
```

它会自动：
- 创建 `.venv` 虚拟环境
- 安装 / 补齐依赖
- 用同一个 Python 环境启动程序

这样可以避免“明明安装了 PySide6，但运行时仍然提示找不到模块”的问题。

**手动启动：**

```bash
python main.py
```

---

## 开发验证

`pytest` 属于开发验证依赖，安装方式见 `requirements-dev.txt`。本机基础验证命令：

```bash
.venv\Scripts\python.exe -m py_compile backend\bridge.py main.py services\clean_service.py gui\pages\compare_page.py
.venv\Scripts\python.exe -m pytest -q
cd desktop
npm.cmd run build
cargo check --manifest-path src-tauri\Cargo.toml
```

## 使用流程

```
步骤 1  数据导入页  →  导入元数据表 + 文本表  →  合并数据
步骤 2  数据清洗页  →  配置清洗参数  →  开始清洗与分词
步骤 3  LDA 分析页  →  设置主题数  →  开始训练  →  查看结果
步骤 4  STM 分析页  →  配置协变量  →  训练 STM  →  查看 prevalence
步骤 5  对比分析页  →  刷新图表  →  查看报刊/年份/文类差异
步骤 6  导出结果页  →  勾选导出项目  →  导出
```

---

## 输出文件说明

| 文件名 | 内容 |
|-------|------|
| merged_data.csv | 合并后的主数据集 |
| tokens_corpus.txt | 每篇文章分词结果（每行一篇） |
| lda_topic_word.csv | LDA 主题-词矩阵 |
| lda_doc_topic.csv | LDA 文档-主题分布矩阵 |
| lda_coherence.json | LDA Coherence 指标 |
| stm_topic_word.csv | STM 主题-词矩阵 |
| stm_doc_topic.csv | STM 文档-主题分布矩阵 |
| stm_topic_prevalence.csv | 按协变量分组的主题 prevalence |
| session_config.json | 会话配置与导出记录 |
| lda_vis.html | pyLDAvis 交互可视化（浏览器中打开） |

---

## 项目结构

```
topic_analyzer/
├── main.py                      # 主入口
├── requirements.txt             # Python 依赖
├── README.md                    # 本文件
│
├── models/
│   ├── __init__.py
│   └── app_state.py             # 应用全局状态（单例）
│
├── services/
│   ├── __init__.py
│   ├── data_service.py          # 数据导入与合并
│   ├── clean_service.py         # 文本清洗与分词
│   ├── lda_service.py           # LDA 建模（gensim）
│   └── stm_service.py           # STM 建模（rpy2 + R stm）
│
├── utils/
│   ├── __init__.py
│   ├── field_mapper.py          # 中英文字段映射
│   └── logger.py                # 日志工具（支持 GUI 信号）
│
└── gui/
    ├── __init__.py
    ├── main_window.py           # 主窗口框架
    ├── styles.py                # 全局 QSS 样式表
    │
    ├── widgets/
    │   ├── __init__.py
    │   ├── nav_bar.py           # 左侧导航栏
    │   └── status_bar.py        # 底部状态栏
    │
    └── pages/
        ├── __init__.py
        ├── welcome_page.py      # 首页（流程说明）
        ├── import_page.py       # 数据导入页
        ├── clean_page.py        # 数据清洗页
        ├── lda_page.py          # LDA 分析页
        ├── stm_page.py          # STM 分析页
        ├── compare_page.py      # 对比分析页
        └── export_page.py       # 导出与日志页
```

---

## 常见问题

**Q：运行时报"找不到字体"**  
A：应用会自动回退到系统可用字体，中文显示不受影响。

**Q：rpy2 安装失败**  
A：确保 R 已安装且 R_HOME 环境变量已正确配置，然后重新安装 rpy2。

**Q：gensim LDA 训练很慢**  
A：减少 passes（训练轮数）或语料规模，或增加 chunksize 参数。

**Q：繁简转换不工作**  
A：安装 opencc：`pip install opencc-python-reimplemented`

**Q：pyLDAvis 无法打开**  
A：安装 pyldavis：`pip install pyldavis`，然后重启应用。

---

## 技术依赖

- **GUI**：PySide6
- **数据处理**：pandas, numpy
- **中文分词**：jieba
- **LDA 建模**：gensim
- **LDA 可视化**：pyLDAvis
- **STM 建模**：rpy2 + R stm 包
- **图表**：matplotlib
