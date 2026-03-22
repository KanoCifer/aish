# aish (AI Shell 智能命令行)

将自然语言转换为安全可执行的 Shell 命令。`aish` 基于大语言模型将你的需求翻译成 bash 命令，自动进行安全校验后再执行，让命令行使用更简单高效。
[![License](https://img.shields.io/pypi/l/aish-cli?color=green)](https://github.com/KanoCifer/aish/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-v3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/aish-cli?color=blue&logo=pypi)](https://pypi.org/project/aish-cli/#description)

## 技术栈

- **CLI 框架**: [Typer](https://typer.tiangolo.com/) — 现代 Python CLI 框架，支持类型提示
- **终端输出**: [Rich](https://github.com/Textualize/rich) — 富文本终端输出
- **配置验证**: [Pydantic](https://docs.pydantic.dev/) — 数据验证与配置管理
- **LLM 客户端**: [OpenAI Python SDK](https://github.com/openai/openai-python) — 兼容所有 OpenAI API 格式的服务商

## 环境要求

Python 3.10+。

## 安装

```bash
pip install aish-cli
# 或使用uv
uv pip install --system aish-cli

aish -v
```

安装完成后，你就可以在任意位置使用 `aish` 命令了。

## 配置

使用 `aish init` 命令配置你的大模型服务商信息，支持交互式和参数两种配置模式。

### 交互式配置（推荐）

直接运行 `aish init`，按照提示输入相关信息即可：

```bash
aish init

aish -M # 列出所有已配置的模型
```

### 参数模式配置

你也可以通过参数一次性完成配置：

```bash
# OpenAI 官方接口示例
aish init --base-url "https://api.openai.com/v1" --api-key "sk-..." --model "gpt-4o"

# 国内服务商示例（豆包）
aish init --base-url "https://ark.cn-beijing.volces.com/api/v3" --api-key "331fda..." --model "doubao-1.5-pro-250315"

# 国内服务商示例（DeepSeek）
aish init --base-url "https://api.deepseek.com/v1" --api-key "sk-..." --model "deepseek-chat"

# 国内服务商示例（通义千问）
aish init --base-url "https://dashscope.aliyuncs.com/compatible-mode/v1" --api-key "sk-..." --model "qwen-max"
```

### 推荐配置

推荐使用阿里百灵大模型，每日有50WToken的免费额度，且性能稳定，适合长期使用：
[阿里百灵](https://ling.tbox.cn/)

```bash
# 阿里百灵大模型示例
aish init --base-url "https://api.tbox.cn/api/llm/v1" --api-key "sk-..." --model "Ling-2.5-1T/Ling-1T"
```

配置文件会自动保存到 `~/.aish/config.json` 目录下。

## 多模型管理

`aish` 支持同时配置多个大模型服务商，可随时切换使用：

| 命令                                       | 说明                   |
| ------------------------------------------ | ---------------------- |
| `aish model`                               | 显示当前使用的模型     |
| `aish model -l` / `--list`                 | 列出所有已配置的模型   |
| `aish model -s <模型名/别名>` / `--switch` | 切换到指定模型         |
| `aish model -a` / `--add`                  | 交互式添加新的模型配置 |

### 多模型使用示例

```bash
# 查看当前模型
aish model
Current model: Ling-2.5-1T

# 列出所有配置
aish model -l
Available Configurations:
  Ling-2.5-1T (alias: tbox)
✓ Ling-1T (alias: ling)

# 切换模型
aish model -s gpt-4o
✓ Switched active configuration to gpt-4o.

# 添加新配置
aish model -a
Base URL: https://api.deepseek.com/v1
API key: ************************
Model: deepseek-chat
Alias (optional): deepseek
✓ Configuration updated successfully.
```

## 使用方法

直接在 `aish run` 后面输入你的需求即可，**不需要加引号**：

```bash
# 列出当前目录下所有 Python 文件
aish run 列出所有python文件

# 显示磁盘使用情况
aish run 显示磁盘使用情况

# 查找当前目录下大于100MB的文件
aish run 查找大于100MB的文件

# 查看最近10条命令历史
aish run 查看最近10条历史命令
```

### 可用选项

| 选项        | 简写 | 说明                             |
| ----------- | ---- | -------------------------------- |
| `--yes`     | `-y` | 低风险命令自动执行，跳过确认步骤 |
| `--dry-run` | `-d` | 仅显示生成的命令，不实际执行     |

使用示例：

```bash
# 自动执行低风险命令
aish run 更新系统包 -y

# 仅查看生成的命令，不执行
aish run 删除所有日志文件 --dry-run
```

## history 命令

```bash
# 显示最近10条历史记录
aish history
aish -H

aish history -l 20 # 显示最近20条历史记录

aish history -c # 清空历史记录
```

## 安全机制

`aish` 内置多层安全保障机制：

### 1. 命令风险检测

所有命令在执行前都会进行风险评估，分为三个等级：

- **ALLOW（低风险）**：普通文件操作、查看类命令等，使用 `-y` 参数时会自动执行
- **WARN（中风险）**：修改系统配置、删除文件等操作，即使使用 `-y` 也会要求用户确认后再执行
- **DENY（高风险）**：磁盘格式化、删根、fork 炸弹等危险命令，会直接被禁止执行

### 2. 敏感信息保护

- API密钥使用 Pydantic `SecretStr` 类型存储，内存中不会明文暴露，避免意外泄露
- 配置文件默认权限为用户只读（`-rw-------`），仅当前用户可读取

所有操作都会明确显示风险等级和提示信息，确保使用安全。

## 执行历史

最近 1000 条执行的命令会自动保存在 `~/.aish/history` 文件中（JSON Lines 格式），超过上限的历史记录会自动清理，节省存储空间。

## 常见问题

### Q: 如何添加/修改配置？

A:

- 添加新配置：运行 `aish model -a` 交互式添加
- 切换模型：运行 `aish model -s <模型名/别名>`
- 查看所有配置：运行 `aish model -l`
- 也可以直接编辑 `~/.aish/config.json` 文件手动修改

### Q: 最多可以配置多少个模型？

A: 没有数量限制，可以添加任意多个兼容OpenAI API格式的模型服务商。

### Q: 支持哪些大模型服务商？

A: 所有兼容 OpenAI API 格式的大模型服务商都支持，包括但不限于 OpenAI、Anthropic、豆包、DeepSeek、通义千问、文心一言等。

### Q: 生成的命令不符合预期怎么办？

A: 你可以使用 `--dry-run` 参数先查看生成的命令，或者更精确地描述你的需求。

### Q: 历史记录可以手动清理吗？

A: 可以直接删除 `~/.aish/history` 文件，或者执行 `aish run 清空aish历史记录` 命令。
