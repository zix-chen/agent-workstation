# Agent Workstation

[English](README.md) · [安全边界](SECURITY.md) · [架构](docs/architecture.md) · [客户端接入](docs/clients.md)

**让 MCP 客户端复用真实开发工作流。后端任务优先 API/CLI，不把模拟鼠标点击作为主路径。**

这是基于 [Coding Tools MCP](https://github.com/xyTom/coding-tools-mcp) 的轻量适配层，
不是新模型、完整 Agent 框架或另一套代码执行引擎。文件、Git、Patch、命令生命周期与 MCP 协议复用上游。
新增的是显式主机信任模式、多仓上下文发现、按需 Skills/Recipe 入口，以及有界输出策略。

## 安装

需要 Python 3.11+ 和 Git。服务端本身不需要 Codex，也不需要模型 API Key；模型由你选择的 MCP 客户端提供。
首版从 GitHub 安装，未发布 PyPI。同一套源码可以放入独立虚拟环境，不替换你已有的开发工具。

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install "git+https://github.com/zix-chen/agent-workstation.git@v0.1.1"
agent-workstation --workspace /你的工作区 --doctor
agent-workstation --workspace /你的工作区 --stdio
```

在支持 stdio MCP 的客户端配置 `.venv/bin/agent-workstation` 的绝对路径；完整 JSON 见英文首页。
ChatGPT 网页不能直接运行这条本地命令，需要额外的安全远程接入层；首版不自动安装隧道或 OAuth。

## 两种模式，边界说清楚

| 模式 | 行为 |
| --- | --- |
| `workspace`（默认） | 保留上游 safe 命令门禁、隔离 HOME、结构化文件路径校验；**不是完整操作系统沙箱** |
| `trusted-workstation` | 命令使用真实 HOME/CLI 身份，可访问工作区外文件、网络与开发凭据；必须信任 Agent 与代码 |

```bash
agent-workstation --workspace "$HOME/work" --mode trusted-workstation --stdio
```

主机模式不是“凭据对模型不可见”，也不能阻止任意 Shell 或提示注入窃取秘密。
不可信代码应在隔离账号、容器或虚拟机中运行。服务不伪装工具只读标记。

## 实际增量

`workspace_guide(path="目标仓库")` 返回适用 AGENTS/CLAUDE 路径、Skill 名称/描述/摘要，以及显式加载的 Recipe。
完整 Skill 由 Agent 按需读取，而不是全部塞入上下文；这不是服务端保证模型自动遵守的调度器。
启动阶段避免遍历整个多仓目录，跳过生成目录与 worktree；选定目标后仍逐级检查深层规则。

命令默认返回 8 KiB 首尾预览，为短 stderr 保留预算，截断后保留续读入口；文件默认 32 KiB、diff 64 KiB。
上游缓冲区仍有容量与过期限制，`output_ref` 不是永久完整日志。

MySQL、Redis、Kubernetes 等通过你已有的 CLI 和 Skill 组合使用，本项目不捆绑公司配置、账号或生产操作。
GUI、浏览器和 Secret-to-Sink 暂不发布，避免扩大首版安全与维护负担。

## 自己验证

克隆仓库并执行 `python -m pip install -e '.[dev]'` 后：

```bash
python -m unittest discover -s tests -v
python scripts/demo.py
python scripts/benchmark_output.py
python scripts/check_release.py
```

Demo 只在临时目录的假后端上操作，通过真实 MCP 与本地 HTTP 演示“发现规则 → 读配置/日志 → 验证异常 → 验证修正”。
它不调用大模型，不代表模型端到端成功率；Benchmark 只统计字节，不声称订阅额度节省比例。
实际验证范围见 [validation](docs/validation.md)。

## 开源边界

上游依赖固定到 `bedb632e1afd2e9ec9b268a50fe0b04695c22c64`，私有接口接触点集中在 `compat/`。
不承诺随任意上游版本自动兼容。Apache-2.0；上游贡献归属见 [NOTICE](NOTICE)。
面试时可展示真实设计、测试与取舍，但不要将上游执行引擎或未发布 GUI 能力说成个人独立实现。
