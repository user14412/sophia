# Agent 课程大作业报告 Tasks

## 文件清单

| 操作 | 文件 | 职责 |
| --- | --- | --- |
| 已有 | `docs/mew-spec/report/spec.md` | 报告目标、边界、验收标准 |
| 已有 | `docs/mew-spec/report/plan.md` | 章节结构、素材映射、图表规划 |
| 新建 | `docs/mew-spec/report/pending-info.md` | 用户最后需要补充的信息 |
| 待新建 | `docs/report/agent-podcast-report.md` | 论文正文 Markdown 初稿 |
| 待新建 | `docs/report/figures/workflow.mmd` | 系统工作流图源码 |
| 待新建 | `docs/report/figures/workflow.png` | 系统工作流图图片 |
| 待新建 | `docs/report/latex/main.tex` | 软件学报风格 LaTeX 正文 |
| 待生成 | `docs/report/output/<学号+姓名>.pdf` | 最终提交 PDF |
| 新建 | `docs/mew-spec/report/reference-plan.md` | 核心参考文献与正文标注方案 |

## T1: 整理待确认信息

**文件：** `docs/mew-spec/report/pending-info.md`

**依赖：** `plan.md`

**步骤：**

1. 列出最终 PDF 前必须由用户提供的信息。
2. 只保留必要项：姓名、学号、署名单位/课程信息、最终文件名。
3. 不列环境变量、代码运行、端口等与论文提交无关的信息。

**验证：** 打开 `pending-info.md`，应能在 1 分钟内看懂需要填写什么。

## T2: 建立论文正文工作目录

**文件：** `docs/report/`

**依赖：** T1

**步骤：**

1. 创建 `docs/report/`。
2. 创建 `docs/report/figures/`。
3. 创建 `docs/report/latex/`。
4. 创建 `docs/report/output/`。

**验证：** `Get-ChildItem docs/report` 能看到正文、图表、LaTeX 和输出目录的组织位置。

## T3: 生成系统工作流图

**文件：**

- `docs/report/figures/workflow.mmd`
- `docs/report/figures/workflow.png`

**依赖：** T2

**步骤：**

1. 根据 `plan.md` 中的图 1 设计生成 Mermaid 工作流图。
2. 图中包含：参考章节、Topic、Director、Agent Speechers、Voice、Image、Editor、播客视频/摘要。
3. 优先用本地可用工具渲染成 PNG；如果本地渲染不稳定，则保留 Mermaid 源码并在 LaTeX 中用文字图或表格替代。

**验证：** 图能清楚表达端到端流程，不出现最近调试相关词汇。

## T4: 提取案例产物

**文件：** `resources/outputs/ch01-demo/*`

**依赖：** T2

**步骤：**

1. 读取 `topic.json`，提取 2 个主题名称与核心概念。
2. 读取 `director.json`，提取阶段名称和编导字段。
3. 读取 `script.txt`，选取 2-4 句短脚本作为案例。
4. 读取 `voice.json`、`video.json`，提取媒体阶段产物形态。
5. 记录为正文可用素材，不把 mock、端口、manifest 等调试词写入正文。

**验证：** 素材能够支撑第 5 节案例分析，不需要额外跑真实 API。

## T5: 撰写 Markdown 正文初稿

**文件：** `docs/report/agent-podcast-report.md`

**依赖：** T1-T4

**步骤：**

1. 按 `plan.md` 的结构写标题、摘要、关键词。
2. 写正文第 0-8 节。
3. 在第 0 节前 100 字内明确标注选题 E。
4. 在第 3 节插入系统工作流图占位。
5. 在第 5 节插入阶段职责表和案例产物。
6. 在第 7 节写 AI 使用说明。
7. 全文保持课程论文语气，不写最近 bug 和调试过程。

**验证：** Markdown 正文约 3500 字量级，结构完整，可直接迁移到 LaTeX。

## T6: 准备图表与表格

**文件：**

- `docs/report/figures/workflow.png`
- `docs/report/agent-podcast-report.md`

**依赖：** T5

**步骤：**

1. 确认图 1 能放入正文。
2. 整理表 1：阶段、输入、输出、作用。
3. 整理表 2：上下文类型、生命周期、作用、风险控制。
4. 如果篇幅紧张，优先保留图 1 和表 1。

**验证：** 至少有 2 个图表或表格，满足 spec 的 F6。

## T7: 整理参考文献

**文件：**

- `docs/mew-spec/report/reference-plan.md`
- `docs/report/agent-podcast-report.md`

**依赖：** T5

**步骤：**

1. 正式参考文献控制在 4 条左右。
2. 使用 ReAct、RAG、AutoGen、LangGraph 官方文档作为核心来源。
3. 正文采用顺序编码制标注：`[1]`、`[2]`、`[3]`、`[4]`。
4. 每条参考文献只在支撑关键论点时出现，不满篇堆引用。
5. 不写无法确认的论文、年份、作者。

**验证：** 参考文献数量精简、可核验；正文引用编号与文末条目一致。

## T8: 迁移到软件学报风格 LaTeX

**文件：** `docs/report/latex/main.tex`

**依赖：** T5-T7

**步骤：**

1. 参考 `作业相关/报告模板/latex.tex` 的结构。
2. 写入标题、作者占位、摘要、关键词。
3. 将 Markdown 正文转换为 LaTeX 分节。
4. 插入图表。
5. 保留 `姓名`、`学号` 占位，等待用户补齐。

**验证：** LaTeX 文件结构完整，能找到 `rjthesis.cls` 或复制模板依赖后编译。

## T9: 编译 PDF

**文件：** `docs/report/output/<学号+姓名>.pdf`

**依赖：** T8 和用户补齐个人信息

**步骤：**

1. 使用本地 LaTeX 工具链尝试编译。
2. 若缺少 LaTeX 工具链，使用可行的备用方式生成 PDF。
3. 确认首页包含选题编号、姓名、学号。
4. 按课程要求命名 PDF。

**验证：** 能打开 PDF，首页信息完整，正文图表正常显示。

## T10: 最终自查

**文件：**

- `docs/report/agent-podcast-report.md`
- `docs/report/latex/main.tex`
- `docs/report/output/<学号+姓名>.pdf`

**依赖：** T9

**步骤：**

1. 检查选题编号 E 是否显式出现。
2. 检查 AI 使用说明是否存在。
3. 检查正文是否没有端口、前端代理、上传失败、manifest 报错等调试细节。
4. 检查 PDF 文件名是否符合 `学号+姓名.PDF`。
5. 检查提交链接以新链接为准。

**验证：** 对照 checklist 逐项通过后交付。

## 执行顺序

```text
T1 -> T2 -> T3
         -> T4
T3 + T4 -> T5 -> T6 -> T7 -> T8 -> T9 -> T10
```

## 备注

- 图表优先由我根据工作流和中间产物生成。
- 用户只需要补最终提交必须的信息，不需要参与工程细节。
- 不运行真实 LLM、TTS 或视频生成；报告案例使用已有中间产物。
