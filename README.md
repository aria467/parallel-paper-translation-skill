# 论文正文并行翻译 Skill

这个 Skill 用 Codex 协调多个智能体，将学术论文 PDF 的正文翻译为简体中文 Markdown，并在合并后由主智能体校订图片、图注与数学公式。它适合需要保留章节层级、引用编号和图表位置的长篇论文翻译。

> **适用范围：目前只适用于 Codex，暂时不适用于其它 harness。** 当前版本仍是未完工的草稿；流程依赖 Codex 的子智能体调度能力及 `pdf:pdf` 能力，不能仅凭仓库中的 Python 脚本独立完成翻译。

## 工作流程

1. **确认模型与环境。** 主智能体列出当前子智能体工具实际提供的模型 ID，请用户选择全部翻译智能体使用的模型。随后核对本次实际需要且缺失的依赖，与用户确认安装方式；总结流程并等待用户明确同意开始。`Auditor` 使用主智能体的默认模型。
2. **按标题切分正文。** 从第一个编号正文标题开始，以 `References` 为终点，按相邻标题建立片段。片段包含起始标题，不包含终止标题；摘要和参考文献条目不在翻译范围内。主智能体只确定标题边界，不预先解析片段正文。
3. **准备独立 PDF 副本。** 每个 `Translater n` 获得一份独立的 PDF 副本；辅助脚本用 SHA-256 核对副本，并生成片段清单与统一的文件名。
4. **并行翻译与形式审核。** 先启动一个 `Auditor`，再分批启动翻译智能体；同时最多运行两个 `Translater n` 和一个 `Auditor`。每名翻译智能体只读取自己的 PDF 副本，提取并翻译被分配的片段。`Auditor` 只判断提交是否为正常、对应片段的 Markdown 译文，不评判翻译准确性，也不改写内容。所有子智能体均不得安装包或修改工作环境。
5. **核对交接并合并。** 翻译智能体的最终回复是基准文本。主智能体比较该回复与 `Auditor` 保存文件的 SHA-256 摘要；不一致的片段不能合并。所有片段通过后，按标题顺序合并为初版 Markdown，并确认 `Auditor` 已返回报告、所有子智能体均已停止。
6. **独立校订最终副本。** 主智能体单独从 PDF 提取正文图片，按位置插入初版文档的副本并规范图注；随后先检查块级公式，再检查行内公式，最后检查章节结构、内容顺序、图片链接与遗漏或重复。此阶段不调用子智能体，也不覆盖初版合并文档或片段文件。

详细规则见 [SKILL.md](SKILL.md) 和 [工作流程说明](references/workflow.md)。仓库另含 [翻译智能体提示词](references/translater-prompt.md)、[审核智能体提示词](references/auditor-prompt.md) 与 [文件辅助脚本](scripts/translation_files.py)。辅助脚本使用 Python 标准库；其它依赖按具体论文和运行环境确认，不默认安装 PyYAML。

## 安装到 Codex

需要已安装的 Codex、Git，以及本流程使用的子智能体和 `pdf:pdf` 能力。以下命令会把仓库克隆到 Codex 可发现的用户级 Skill 目录；**阅读 README 或克隆仓库不会启动翻译**。

```sh
mkdir -p "$HOME/.agents/skills"
git clone https://github.com/aria467/parallel-paper-translation-skill.git \
  "$HOME/.agents/skills/parallel-paper-translation"
```

Codex 通常会自动发现新增或更新的 Skill；若没有出现，重启 Codex。若目标目录已存在，应先检查其中内容，再决定是否更新，避免覆盖本地改动。

> 依据：[OpenAI 官方 Skill 文档：本地发现位置、安装与调用](https://learn.chatgpt.com/docs/build-skills)。

## 使用方法

在 Codex 中提供论文 PDF 的绝对路径，并显式提及 Skill，例如：

```text
$parallel-paper-translation
请将 /absolute/path/to/paper.pdf 的正文翻译为简体中文 Markdown，并按此 Skill 的流程交付初版与校订版。
```

主智能体会先询问翻译子智能体的模型，随后讨论必要依赖的安装方式，再汇总计划并等待你**单独确认开始**。选择模型或同意依赖安装方式本身不会启动翻译。运行完成后，应保留各片段、初版合并文档，以及带有 `assets/` 图片目录的校订版文档。

## 许可证

本仓库的 Skill 文档、提示词和辅助脚本采用 [MIT License](LICENSE)，版权署名为 `2026 aria467`。这一许可不会自动授予原论文 PDF、第三方素材或使用本 Skill 生成的译文的权利。

> 依据：[Open Source Initiative 的 MIT 许可证原文](https://opensource.org/license/mit)。

## 参考资料

> [OpenAI 官方 Skill 文档：结构、发现位置和显式调用](https://learn.chatgpt.com/docs/build-skills)。
>
> [本仓库的工作流程说明](references/workflow.md)。
>
> [Open Source Initiative：MIT License](https://opensource.org/license/mit)。
