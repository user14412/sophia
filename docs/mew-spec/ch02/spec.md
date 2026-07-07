# Agent Podcast Frontend Spec

## 背景

项目已经完成第一阶段整理：CLI 支持 `demo`、`stage`、`full` 三种模式，运行产物按 session 写入 `resources/outputs/<session>/`，并有 `manifest.json`、阶段 artifact、脚本、配音摘要、画面摘要和视频摘要。

当前缺口是没有前端。课程演示时，用户仍需要在命令行里输入参数、查看 JSON 文件、手动理解阶段状态。这不利于展示 agent 工作流的结构，也不利于说明“可复现、可调试、可验收”的工程整理成果。

本阶段目标是做一个本地 Web 前端，把现有 CLI/runtime 底座变成可视化、可点击、可解释的演示控制台。

## 推荐方案

推荐方案：本地 Web 控制台 + 轻量后端 API。

页面负责展示 session、运行配置、阶段状态和产物；轻量后端负责调用现有 runtime 或 CLI，读取 `resources/outputs` 中的 manifest 和产物。这个方案和当前底座贴合，开发速度快，也方便后续扩展成真正产品。

备选方案 1：纯静态页面直接读取 fixture。

优点是最快；缺点是不能触发运行，也不能体现“调试不用从头跑”的工程价值。

备选方案 2：直接做完整产品级前端。

优点是展示效果强；缺点是范围过大，会引入账户、任务队列、长连接、真实媒体预览等复杂度，不适合当前作业收口阶段。

## 目标

- 提供一个本地可启动的 Web UI，用于课程演示和日常调试。
- 让用户无需记 CLI 命令即可运行 demo、查看运行健康检查和重跑单阶段。
- 可视化展示 v3 主线阶段：Topic、Director、Agent Speechers、Voice、Image、Editor。
- 让用户能在页面中阅读关键产物：topic 规划、director 规划、脚本文本、voice/image/video 摘要。
- 保持 demo/mock 优先，不默认触发真实 LLM、TTS、生图或 FFmpeg。

## 功能需求

- F1: 前端应提供一个首页仪表盘，展示项目名称、当前推荐主线、运行模式说明和最近 session 列表。
- F2: 用户应能在页面上创建或选择 session，并以 demo 模式运行完整流程。
- F3: 用户应能查看 runtime health 结果，区分 required 和 optional 依赖。
- F4: 用户应能查看某个 session 的阶段状态，包括 pending、done、failed、skipped 等状态。
- F5: 用户应能在同一个 session 下触发单阶段重跑，至少支持 voice、image、editor 的 mock 调试。
- F6: 用户应能浏览核心产物，包括 topic、director、script、voice、images、video 和 manifest。
- F7: 用户应能看到清晰的错误反馈，例如缺少前置产物、缺少参考章节、full 模式缺少 required 环境变量。
- F8: 前端应提供一个面向报告展示的“工程视图”，解释 v3 agent 管线、fixture/mock、manifest、stage runner 的作用。
- F9: 前端启动方式应简单，README/runbook 中应提供明确命令。

## 非功能需求

- N1: 默认演示路径必须离线可运行，不依赖真实 API key、TTS 服务、生图服务或 FFmpeg 渲染。
- N2: UI 应适合工程演示场景，信息密度适中，强调阶段、状态、产物和操作，不做营销式落地页。
- N3: 前端和轻量后端不能破坏现有 CLI；命令行路径仍应可独立使用。
- N4: 页面应在常见桌面宽度下布局稳定，并在移动宽度下可基本阅读。
- N5: 运行产生的 session 产物仍写入既有 `resources/outputs`，不引入新的未忽略大文件目录。
- N6: 测试和默认启动不应触发真实网络模型调用或媒体生成。
- N7: 错误信息应面向用户可读，不暴露长 traceback 作为主要反馈。

## 不做的事

- 不做用户登录、权限、多用户隔离或远程部署。
- 不做真实长时间任务队列、后台 worker、WebSocket 实时流式日志。
- 不做在线编辑 prompt、编辑 agent 角色或重新设计 v3 生成逻辑。
- 不做完整视频播放器能力；如果当前产物是 mock 摘要，则只展示摘要。
- 不在本阶段实现 full 模式的完整真实媒体生成 UI；full 只做健康检查和说明。
- 不修复所有历史 v1/v2.1 管线和历史 prompt 乱码问题。

## 验收标准

- AC1: 运行前端启动命令后，浏览器能打开本地页面并看到仪表盘。
- AC2: 页面能触发 demo 运行，并生成或刷新一个 session 的 manifest。
- AC3: 页面能列出至少一个 session，并展示该 session 的阶段状态。
- AC4: 页面能展示 topic、director、script、voice、images、video 中至少五类产物内容。
- AC5: 页面能触发 voice、image、editor 三个 mock 单阶段重跑，并展示成功结果或明确错误。
- AC6: 页面能展示健康检查结果，并区分 required/optional。
- AC7: 在缺少前置产物的 session 上重跑 voice 时，页面应显示“缺少 script_items.json”一类可读错误。
- AC8: 默认测试和演示不需要真实 API key，不触发真实 LLM/TTS/生图/FFmpeg。
- AC9: 现有 `python src/cli.py --mode demo ...` 和 pytest 仍然通过。
- AC10: README 或 runbook 中包含前端启动、demo 演示和常见错误说明。
