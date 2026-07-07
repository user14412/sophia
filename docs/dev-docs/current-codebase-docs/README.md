# 当前代码库文档（current-codebase-docs）

> 这套文档描述的是 **当前实际运行的代码**（v3 主线：`content3/` + `view/` + `runtime/`）。
> `docs/dev-docs/` 下的 `v1.0 / v2.0 / v2.1 / v3.0 / 二周目baseline重构` 都是历史文档，与当前代码有出入，**不要参考**。
>
> 本套文档全部基于阅读源码逐行核对得出，正文中的 `文件:行号` 均可点击定位。
> 编写时间：2026-07-07。若代码有变动，以代码为准。

## 这是什么项目

一句话：**把一章哲学讲义文本，自动生成一期「双主持人对谈」播客视频**。
它是一条用 LangGraph 编排的六阶段流水线，外面套了一个本地 Web 控制台用于演示和调试。

## 阅读顺序

建议按顺序读，前三篇讲「是什么、怎么跑」，后面按分层深入：

| # | 文档 | 讲什么 | 适合谁 |
| --- | --- | --- | --- |
| 0 | [00-architecture-overview.md](00-architecture-overview.md) | 宏观架构、8 个分层、数据流全景、mock/real 双模式、legacy 边界 | 所有人先读这篇 |
| 1 | [01-runtime-and-orchestration.md](01-runtime-and-orchestration.md) | 运行时外壳（runner/config/artifacts/health）+ LangGraph 图 + CLI | 想搞清「一次运行到底发生了什么」 |
| 2 | [02-content-generation-agents.md](02-content-generation-agents.md) | topic / director / agent_speechers 三个 LLM 节点 + RAG | 想看懂「脚本是怎么写出来的」 |
| 3 | [03-media-rendering.md](03-media-rendering.md) | voice（TTS）/ image（配图）/ editor（合成） | 想看懂「视频是怎么出来的」 |
| 4 | [04-web-and-frontend.md](04-web-and-frontend.md) | FastAPI 路由与桥接 + React 前端 + Vite 代理 | 想看懂「点一个按钮之后」 |
| 5 | [05-refactoring-summary.md](05-refactoring-summary.md) | 全库重构建议汇总（按严重度排序，附文件:行号） | 想改进代码质量 |
| — | [runbook.md](runbook.md) | 面向零基础的运行手册：从装环境到出片 | 第一次上手 / 只想把它跑起来 |

## 关于重构建议

用户明确要求：本次**只写文档、不改任何源代码**。各分模块文档末尾都有「重构建议」小节，
`05-refactoring-summary.md` 把它们汇成一张总表。所有建议都标注了 `文件:行号`，是分析与方向，不是已实施的改动。

## 一张图记住全局

```
浏览器(React :5173) ──/api──▶ Vite 代理 ──▶ FastAPI(:8000)
                                              │
                                     web_api/services.py（HTTP→CLI 参数）
                                              ▼
                                  runtime/runner.py（run_pipeline / run_stage）
                                   ┌──────────┴───────────┐
                              DEMO/mock                REAL full
                          fixtures/demo/*.json    app.create_video_pipeline()
                                                   （LangGraph StateGraph）
                            topic→director→agent_speechers→voice→image→editor
                                              │
                              ArtifactStore 落盘 resources/outputs/<session>/
                                  manifest.json + 每阶段 *.json
```
