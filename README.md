# aish (AI Shell 智能命令行)

将自然语言转换为安全可执行的 Shell 命令。`aish` 基于大语言模型将你的需求翻译成 bash 命令，自动进行安全校验后再执行，让命令行使用更简单高效。

## 环境要求

Python 3.10 或更高版本。

## 安装

```bash
pip install aish-cli
# 或使用uv
uv pip install --system aish-cli
```

安装完成后，你就可以在任意位置使用 `aish` 命令了。

## 配置

使用 `aish init` 命令配置你的大模型服务商信息，支持交互式和参数两种配置模式。

### 交互式配置（推荐）

直接运行 `aish init`，按照提示输入相关信息即可：

```bash
aish init
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

配置文件会自动保存到 `~/.aish/config` 目录下。

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

## 安全机制

`aish` 内置安全校验机制，所有命令在执行前都会进行风险检测，分为三个风险等级：

- **ALLOW（低风险）**：普通文件操作、查看类命令等，使用 `-y` 参数时会自动执行
- **WARN（中风险）**：修改系统配置、删除文件等操作，即使使用 `-y` 也会要求用户确认后再执行
- **DENY（高风险）**：磁盘格式化、删根、fork 炸弹等危险命令，会直接被禁止执行

所有命令在执行前都会明确显示风险等级和提示信息，确保操作安全。

## 执行历史

最近 1000 条执行的命令会自动保存在 `~/.aish/history` 文件中（JSON Lines 格式），超过上限的历史记录会自动清理，节省存储空间。

## 常见问题

### Q: 如何修改配置？

A: 重新运行 `aish init` 即可覆盖原有配置，或者直接编辑 `~/.aish/config` 文件。

### Q: 支持哪些大模型服务商？

A: 所有兼容 OpenAI API 格式的大模型服务商都支持，包括但不限于 OpenAI、Anthropic、豆包、DeepSeek、通义千问、文心一言等。

### Q: 生成的命令不符合预期怎么办？

A: 你可以使用 `--dry-run` 参数先查看生成的命令，或者更精确地描述你的需求。

### Q: 历史记录可以手动清理吗？

A: 可以直接删除 `~/.aish/history` 文件，或者执行 `aish run 清空aish历史记录` 命令。
