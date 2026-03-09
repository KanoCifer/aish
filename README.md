# aish (AI Shell)

Convert natural language into safe shell commands. `aish` uses an LLM to translate your intent into bash, validates it for safety, and executes it.

## Requirements

Python 3.10 or higher.

## Installation

```bash
git clone <repo>
cd aish
pip install -e .
```

## Configuration

Set up your LLM provider by running `aish init`.

**Interactive mode:**
```bash
aish init
```

**Flag mode:**
```bash
aish init --base-url "https://api.openai.com/v1" --api-key "sk-..." --model "gpt-4o"
```

## Usage

Pass your prompt directly to `aish run`. No quotes needed.

```bash
aish run list all python files
aish run show disk usage --dry-run
```

### Options

| Option      | Short | Description                        |
|-------------|-------|------------------------------------|
| `--yes`     | `-y`  | Skip confirmation for safe commands |
| `--dry-run` | `-d`  | Show the command without executing |

## Safety

Built-in validation checks every command before execution:
*   **ALLOW**: Low risk. Runs immediately if you use `--yes`.
*   **WARN**: Medium risk. Always asks for confirmation, even with `--yes`.
*   **DENY**: High risk (like disk wipes or fork bombs). Blocked completely.

## History

Your last 1000 commands are saved to `~/.aish/history` in JSON Lines format. Old commands are automatically trimmed to save space.