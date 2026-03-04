# Paceon

Control your terminal from Telegram. Send keystrokes, read terminal output — all from your phone.

![screenrecording](https://github.com/user-attachments/assets/64602166-6016-4909-bf17-fcabe03002ad)

Works on **macOS** and **Linux**.

> **One bot per machine.** Each machine needs its own Telegram bot token. Create a separate bot for each machine you want to control (e.g. `@my_macbook_bot`, `@my_server_bot`). Only one paceon instance can use a given bot token at a time.
>

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/warlockee/paceon/main/setup.sh | bash
```

The setup script handles everything: clones the repo, installs dependencies, builds the project, walks you through creating a Telegram bot, and starts paceon. Works on both macOS and Linux.

Or clone manually:

```bash
git clone https://github.com/warlockee/paceon.git
cd paceon
./setup.sh
```

## How It Works

On **macOS**, paceon reads terminal window text via the Accessibility API (`AXUIElement`), injects keystrokes via `CGEvent`, and focuses windows using `AXUIElement`. It works with any terminal app — no Screen Recording permission needed.

On **Linux**, paceon uses tmux: `tmux list-panes` to discover sessions, `tmux capture-pane` to read content, and `tmux send-keys` to inject keystrokes. All sessions you want to control must run inside tmux.

In both cases, terminal output is sent as monospace text to Telegram with a refresh button to update on demand.

## Manual Setup

### Prerequisites

### Create a Telegram Bot

Each machine needs its own bot. To create one:

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Name it something you'll recognize (e.g. "My Server Terminal")
4. Copy the API token

### Run

```bash
# The setup script saves the token to apikey.txt and creates run.sh
./run.sh

# Or run directly
./paceon

# Or pass the token directly
./paceon --apikey YOUR_BOT_TOKEN
```

### Options

| Flag | Description |
|------|-------------|
| `--apikey <token>` | Telegram bot API token |
| `--use-weak-security` | Disable Authenticator (owner-only lock still applies) |
| `--dbfile <path>` | Custom database path (default: `./mybot.sqlite`) |
| `--dangerously-attach-to-any-window` | Show all windows, not just terminals (macOS only) |
| `--mgr <path>` | Path to the manager agent script (e.g. `mgr/main.py`) |

## Usage

Message your bot on Telegram:

| Command | Action |
|---------|--------|
| `.list` | List available terminal sessions |
| `.1` `.2` ... | Connect to a session by number |
| `.help` | Show help |
| `.mgr` | Toggle AI manager mode (requires `--mgr`) |
| `.exit` | Leave manager mode |
| `.health` | Manager health report (uptime, memory, stats) |
| `.otptimeout <seconds>` | Set TOTP session timeout |
| Any other text | Sent as keystrokes to the connected terminal (or to the manager in manager mode) |

### Linux: tmux requirement

On Linux, paceon controls tmux sessions. Make sure your work is running inside tmux:

```bash
# Start a named session
tmux new -s dev

# Or start detached sessions
tmux new -s server1 -d
tmux new -s server2 -d
```

Then run paceon separately (outside tmux or in its own tmux window) and use `.list` to see your sessions.

### Keystroke Modifiers

Prefix your message with an emoji to add a modifier key:

| Emoji | Modifier | Example |
|-------|----------|---------|
| `❤️` | Ctrl | `❤️c` = Ctrl+C |
| `💙` | Alt | `💙x` = Alt+X |
| `💚` | Cmd | macOS only |
| `💛` | ESC | `💛` = send Escape |
| `🧡` | Enter | `🧡` = send Enter |
| `💜` | Suppress auto-newline | `ls -la💜` = no Enter appended |

### Escape Sequences

`\n` for Enter, `\t` for Tab, `\\` for literal backslash.

## AI Manager Agent

The manager is an LLM-powered agent (Claude) that can autonomously monitor and control your terminals. Start paceon with `--mgr` to enable it:

```bash
ANTHROPIC_API_KEY=sk-... ./paceon --apikey YOUR_BOT_TOKEN --mgr mgr/main.py
```

Then send `.mgr` in Telegram to enter manager mode. In manager mode, your messages go to the AI agent instead of being sent as keystrokes. Dot commands (`.list`, `.1`, etc.) still work normally.

The manager can:
- List, read, and send commands to any terminal
- Execute commands asynchronously and notify you when they finish
- Queue commands to the same terminal so they don't overlap
- Run repeating background tasks ("watch this terminal until X happens")
- Remember things across restarts (persistent memory)

Send `.exit` to leave manager mode, or `.health` for a status report.

### paceon-ctl

`paceon-ctl` is a standalone CLI tool used by the manager agent. You can also use it directly:

```bash
paceon-ctl list                    # List terminals as JSON
paceon-ctl capture <terminal_id>   # Capture visible text from a terminal
paceon-ctl send <terminal_id> <keys>  # Send keystrokes to a terminal
paceon-ctl status <terminal_id>    # Check if a terminal is alive
```

Terminal IDs come from the `list` output (e.g. `12399` on macOS, `%0` on tmux).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PACEON_VISIBLE_LINES` | `40` | Number of terminal lines to include in output |
| `PACEON_SPLIT_MESSAGES` | off | Set to `1` to split long output across multiple messages |
| `PACEON_CTL` | `./paceon-ctl` | Path to the paceon-ctl binary (used by manager) |
| `PACEON_MGR_MODEL` | `claude-sonnet-4-20250514` | Claude model for the manager agent |
| `ANTHROPIC_API_KEY` | (none) | Anthropic API key for the manager agent |

Terminal output is sent as a single message by default. Each new command or refresh **deletes the previous output messages** and sends fresh ones, creating a clean "live terminal" view rather than spamming the chat.

If your terminal produces very long output (e.g. build logs) and you want to see all of it, enable splitting:

```bash
PACEON_SPLIT_MESSAGES=1 ./paceon
```

## Security

- **Owner lock**: The first Telegram user to message the bot becomes the owner. All other users are ignored.
- **TOTP**: By default, paceon requires Google Authenticator verification. A QR code is shown on first launch. Use `--use-weak-security` to disable.
- **One bot = one machine**: Don't share a bot token across machines. Each machine should have its own bot.
- **Reset**: Delete `mybot.sqlite` to reset ownership and TOTP.

## Permissions

**macOS:** Requires Accessibility permission. macOS will prompt on first use, or grant it in System Settings > Privacy & Security > Accessibility.

**Linux:** No special permissions needed. Just ensure the user running paceon can access the tmux socket.

## Supported Terminals

**macOS:** Terminal.app, iTerm2, Ghostty, kitty, Alacritty, Hyper, Warp, WezTerm, Tabby.

**Linux:** Any terminal running inside tmux.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical documentation: component design, thread model, data flow, IPC protocol, backend interface, global state, and known limitations.

## License

MIT -- see [LICENSE](LICENSE).

Based on [tgterm](https://github.com/antirez/tgterm) by Salvatore Sanfilippo (antirez).
