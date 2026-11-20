# 在不同客户端中使用 Gaia XP 吸积拟合

[English](agent-clients.md) · 简体中文

在 agent 中打开研究目录。各客户端读取同一份 `gaia-xp-fit` 说明，共用一个 Python 环境运行 `gaia-xp`。执行分析时，客户端需要能运行本地命令并读取观测文件。

## 在 Mac 上安装

可以直接把[中文首页](../README.zh-CN.md)的安装请求发给 agent。若手动安装，请从研究目录运行以下命令。已有仓库副本时，把 `./gaia-xp-workbench` 替换为其路径，跳过第一条命令即可。

```sh
git clone https://github.com/cetizhao/gaia-xp-workbench.git
python3.12 -m venv .venv-gaia-xp
.venv-gaia-xp/bin/python -m pip install "./gaia-xp-workbench[gaia,spectroscopy]"
.venv-gaia-xp/bin/python ./gaia-xp-workbench/scripts/install_skill.py --project . --agent all
.venv-gaia-xp/bin/gaia-xp --version
```

也可以指定客户端。例如，`--agent claude-code cursor` 只为 Claude Code 和 Cursor 安装。脚本从仓库复制完整的 skill 及其参考文件，可离线运行。目标已有相同副本时直接复用，遇到不同版本会显示路径，供你核对后再替换或移走。在 Windows 上，使用虚拟环境中的 `Scripts/python.exe` 和 `Scripts/gaia-xp.exe`。

| 安装到研究目录下的位置 | `--agent` 可选名称 | 客户端官方说明 |
|---|---|---|
| `.agents/skills/` | `codex`、`cursor`、`gemini-cli`、`opencode` | [Codex](https://developers.openai.com/codex/skills/) · [Cursor](https://cursor.com/docs/skills) · [Gemini CLI](https://geminicli.com/docs/cli/skills/) · [OpenCode](https://opencode.ai/docs/skills) |
| `.agents/skills/` | `deepseek`、`pi`、`openclaw`、`antigravity` | [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) · [Pi](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md) · [OpenClaw](https://docs.openclaw.ai/tools/skills) · [Google Antigravity](https://antigravity.google/docs/ide/skills) |
| `.claude/skills/` | `claude-code`、`cline` | [Claude Code](https://code.claude.com/docs/en/skills) · [Cline](https://docs.cline.bot/customization/skills) |
| `.github/skills/` | `github-copilot`（CLI 或 VS Code 的 agent 模式） | [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) · [VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) |
| `.windsurf/skills/` | `windsurf`（Devin Desktop 也识别这个目录） | [Windsurf / Devin Desktop](https://docs.devin.ai/desktop/devin-local/customizations) |

## 在自己的客户端验证

在研究目录新开对话。还没有观测数据或模型模板时，可以先验证安装。

> 请使用 Gaia XP 吸积拟合 skill，列出你实际读取的本地说明文件，运行拟合程序的版本命令，告诉我你用的是哪个 Python 环境。

如果有完整的单源拟合结果，可以接着说：

> 请读取 `runs/target` 中保存的拟合，在新目录生成英文 HTML 和总览图，并解释蓝端残差说明了什么。使用已有后验。

报告应显示预期的 Gaia 源编号，`report_manifest.json` 中应有 `fit_executed: false`。新拟合需要你提供 Fang 光球模板，吸积模型网格和两张校准表随程序安装。使用远程或容器客户端时，程序和所需资料必须能在客户端执行命令的环境中访问。

能够读取文件并运行命令的其他客户端也可[直接阅读 skill 说明](../skills/gaia-xp-fit/SKILL.zh-CN.md)。若它无法自动找到 skill，把说明文件和项目中 `gaia-xp` 的路径发给它即可。
