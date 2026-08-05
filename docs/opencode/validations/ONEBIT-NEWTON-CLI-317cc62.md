# ONEBIT-NEWTON-CLI-317cc62

**Дата:** 2026-08-01

## CLI Discovery

| Поле | Значение |
|---|---|
| CLI path | `C:\Users\egore\AppData\Local\NewtonCLI\newton.cmd` |
| Version | **2026.07.13** |
| Transport | **native** (Windows .cmd) |
| WSL | not installed |
| Git Bash | not used |

## Available Commands

`newton {transcribe,fetch,summarize,tts,voices,status,result,health,version}`

## Summarize Command

```
newton summarize <text_file|-> [--model {llama,gpt4}] [--system-prompt ...] [--user-prompt ...] [--output ...]
```

## Health Check

All 7 services healthy:
- LLM Summarize: https://bit-summarize.1bitai.ru — **healthy**

## Provider Implementation

`OneBitNewtonCLIProvider`:
- Auth: `NEWTON_TOKEN` env var
- Models: `llama` (default), `gpt4` — NOT `gpt-4o`
- `subprocess.run`, `shell=False`, stdin, temp output file
- Token in env, NOT in command line args
- JSON code fence extraction from output file
