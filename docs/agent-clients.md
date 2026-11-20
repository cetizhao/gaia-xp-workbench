# Use Gaia XP Accretion Fitter with your agent

English · [简体中文](agent-clients.zh-CN.md)

Open the folder where you keep your research in the agent. The agent reads the same `gaia-xp-fit` instructions in each client and runs the same Python program. One Python environment can serve all the clients you use in that folder. A terminal and access to the observation files are needed to carry out an analysis.

## Set up a research folder on a Mac

You can ask the agent to do this using the setup prompt in the [English](../README.md) or [中文](../README.zh-CN.md) README. For a terminal installation, start in your research folder. If you already have a checkout, substitute its path for `./gaia-xp-workbench` and skip the clone.

```sh
git clone https://github.com/cetizhao/gaia-xp-workbench.git
python3.12 -m venv .venv-gaia-xp
.venv-gaia-xp/bin/python -m pip install "./gaia-xp-workbench[gaia,spectroscopy]"
.venv-gaia-xp/bin/python ./gaia-xp-workbench/scripts/install_skill.py --project . --agent all
.venv-gaia-xp/bin/gaia-xp --version
```

Use `--agent claude-code cursor`, for example, to install just for those clients. The installer copies the skill and its reference files into the selected project directories. An identical copy is already installed. If a copy differs, it reports the path so you can review it before replacing or moving it. The Python installer works offline from a checkout. On Windows, use the virtual environment's `Scripts/python.exe` and `Scripts/gaia-xp.exe`.

| Project directory used by the installer | Client names accepted by `--agent` | Client documentation |
|---|---|---|
| `.agents/skills/` | `codex`, `cursor`, `gemini-cli`, `opencode` | [Codex](https://developers.openai.com/codex/skills/) · [Cursor](https://cursor.com/docs/skills) · [Gemini CLI](https://geminicli.com/docs/cli/skills/) · [OpenCode](https://opencode.ai/docs/skills) |
| `.agents/skills/` | `deepseek`, `pi`, `openclaw`, `antigravity` | [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) · [Pi](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md) · [OpenClaw](https://docs.openclaw.ai/tools/skills) · [Google Antigravity](https://antigravity.google/docs/ide/skills) |
| `.claude/skills/` | `claude-code`, `cline` | [Claude Code](https://code.claude.com/docs/en/skills) · [Cline](https://docs.cline.bot/customization/skills) |
| `.github/skills/` | `github-copilot` (CLI or VS Code agent mode) | [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) · [VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) |
| `.windsurf/skills/` | `windsurf` (also recognized by Devin Desktop) | [Windsurf / Devin Desktop](https://docs.devin.ai/desktop/devin-local/customizations) |

## Check your own client

Start a new chat in the research folder. You can check the installation before supplying observations or model templates.

> Use the Gaia XP accretion skill. Show me the local file you loaded, run the fitter's version command, and tell me which Python environment you used.

When you have a complete saved fit, try this request.

> Read the saved fit in `runs/target` and make an English HTML report and overview in a new directory. Explain what the blue residuals tell us. Use the saved posterior.

Check that the report shows the expected Gaia source ID and that `report_manifest.json` records `fit_executed: false`. For a new fit, provide the Fang photospheric template. The installed package includes the slab grid and both calibration tables. A remote or containerized client needs access to the program and files inside its own execution environment.

A client with file-reading and shell tools can also use the [skill directly](../skills/gaia-xp-fit/SKILL.md). Give it the path to that file and the project's `gaia-xp` executable if its skill picker does not list it.
