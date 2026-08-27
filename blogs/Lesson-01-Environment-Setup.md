# Lesson 1: Setting Up Your ADK Environment

Before you write a single agent, you need a workspace that won't fight you later. We're going to set up one shared
project for this entire series, using `uv` for environment management, Python 3.12, and a direct connection to Claude,
without pulling in LiteLLM. By the end of this lesson, you'll have a working ADK install and a verified connection to Claude Haiku, without having built an agent yet. 

## Why one shared project instead of separate ones for each example?

Each lesson gets its own subfolder under `agents/`, but they all live inside one `uv`-managed project with one `.env` file.

Two reasons for this:

- `adk web` can browse a whole directory of agent subfolders at once, so you'll have a dropdown of every agent you've built so far, and can pick anyone and test it in the application, rather than having to run `adk web` separately for each project. `adk web` is a tool provided by the ADK test your agents - we'll see how to use it later.
- You only manage one virtual environment and one set of API keys, instead of copy-pasting `.env` files fourteen times. This is very convenient when we are learning a new framework, such as the ADK.

> 📌 **NOTE:** this is not the way you'd structure your projects in production. For production use, each project should
have it's own separate folder, with it's own `.env` file holding the API keys, it's own config files etc.

## Step 1: Install uv

If you don't have `uv` yet, install it.

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify it landed correctly:

```bash
uv --version
```

You want `0.5.0` or newer. `uv` handles both your Python version and your dependencies, so you don't need a separate pyenv or conda setup.

## Step 2: Create the project

We'll create all the code under a parent `adk2_tutorial` folder. We'll call this the **root folder of our project** - a phrase you'll encounter several times across the lessons. This folder can be created _anywhere_ on disk. We'll build our projects under this folder.

Start a new terminal and `cd` to the parent folder under which you'll be creating the `adk2_tutorial` folder.

```bash
uv init adk2_tutorial --python 3.12
cd adk2_tutorial
uv venv
```

This gives you a `pyproject.toml`, a `.python-version` pinned to 3.12, and a placeholder `main.py` in the `adk2_tutorial` folder - you can delete the `main.py` file, we don't need it. The `uv venv` command creates an empty virtual environment explicitly inside a `.venv` sub-directory (i.e. `adk2_tutorial/.venv`) without installing dependencies.

Activate the local environment you just created

```bash
# on a Mac/Linux 
source .venv/bin/activate
# on Windows git-bash shell (it's Scripts not bin!)
source .venv/Scripts/activate
# on a Windows CMD shell run
.venv\Scripts\activate.bat
# on a Windows Powershell run
.venv\Scripts\Activate.ps1
```

> 📌**NOTE:** you should always activate the local environment before installing any new modules or running any code we create.

I switch between a Manjaro Linux and Windows 11 machine. I have setup my Windows 11 machine with the `git-bash` shell, that helps me run the same Linux commands on Windows. I use VS Code as my IDE and my default terminal is also the `git-bash` shell. You'll get the `git bash` shell _for free_ on Windows 11 once you install Git for Windows. I highly recommend you get `git bash` on Windows too.

Throughout this series you'll notice that I use the Linux/Mac version of the commands (such as `source .venv/bin/activate`. Replace it with the appropriate command for your shell.)

Confirm the interpreter version:

```bash
uv run python --version
```

You should see `Python 3.12.x`. ADK 2.x requires Python 3.10 or newer.

## Step 3: Add ADK and its dependencies

**Once your local environment is activated** (this is important!!), run the following commands to add the required modules.

```bash
uv add google-adk==2.5.0
uv add anthropic python-dotenv pyyaml
```

A few things worth explaining here:

* **No `[litellm]` extra.** You might see this suggested in other tutorials, e.g. `uv add "google-adk[litellm]"`. Don't use it, at lest not for this tutorial! 
* **We're skipping LiteLLM entirely, on purpose.** `LiteLLM` is the usual way to connect ADK to non-Gemini models, and you'll see it in most other tutorials you may have come across. Recent LiteLLM releases bundle a Rust-accelerated core built with `maturin`, and as of mid-2026, prebuilt Windows wheels for that Rust core aren't reliably published. That means `uv`/`pip` will fall back to compiling it from source. And compilation requires that a full Rust toolchain and Microsoft's C++ Build Tools be pre-installed on Windows, which is a big overhead!
* **We're pinning our ADK to version 2.5.0.** ADK is a fast-evolving framework. Google will no doubt keep adding capabilities and deprecating others as the framework matures. By pinning the version, we ensure the code listings in this series keep working exactly as written, so nothing breaks on your end simply because the ADK version has moved on.  It also lets us verify and confirm that every piece of code we write behaves as expected against this specific version.
* We'll be using Claude as our LLM of choice in all examples (actually in most examples - there will be a few exception where we are forced to use Gemini, which is native to the ADK). So, LiteLLM's real value (bridging to 100+ providers) doesn't buy us anything. Instead, we use ADK's native Anthropic provider, `google.adk.models.anthropic_llm`, which is built directly on Anthropic's official `anthropic` Python package. 

## Step 4: Get your API keys

You need two - one for our default Claude LLM and the other for the Gemini LLM, which we'll be _forced_ to use in a few lessons where we use built-in Google Search grounding, which only works with Gemini models.

**Anthropic (Claude):** console.anthropic.com → API Keys → Create Key.

**Google AI Studio (Gemini):** aistudio.google.com/apikey → Create API Key.

## Step 5: Externalize your configuration

Nothing in this series gets hardcoded into Python files. Two config files carry everything.

Create `.env` in the project root (i.e. in the `adk2_tutorial` folder) - this is for all your API keys.

```bash
# .env
# Anthropic (Claude) — primary provider for this series
ANTHROPIC_API_KEY=your-anthropic-key-here

# Google AI Studio (Gemini) — fallback, required only for built-in Google tools
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

`GOOGLE_GENAI_USE_VERTEXAI=FALSE` tells ADK to hit the Gemini API directly through your AI Studio key instead of expecting a Vertex AI / GCP project. We'll flip that later, in the deployment lesson, once we actually provision GCP resources.

Create `config/models.yaml`. This is the file that encodes our Haiku-first, Sonnet-if-needed, Gemini-Flash-last-resort policy, so every lesson reads from the same place instead of each agent deciding for itself:

```yaml
# config/models.yaml
# Central model policy for the series.
# Every agent should read its model from here, not hardcode a model string.
# All models are accessed natively: Claude via google.adk.models.anthropic_llm,
# Gemini via ADK's built-in Gemini support. No LiteLLM bridge is used.

models:
  primary:
    provider: anthropic
    id: "claude-haiku-4-5-20251001"
    use_when: "default choice for all agents unless a lesson says otherwise"

  escalation:
    provider: anthropic
    id: "claude-sonnet-4-5"
    use_when: "only when Haiku's output quality is measurably insufficient, e.g. complex multi-step graph routing or compliance judgment calls"

  fallback:
    provider: google
    id: "gemini-3.5-flash-latest"
    use_when: "only when a feature requires it, e.g. built-in Google Search grounding or code execution, which do not work with non-Gemini models"

# Per-lesson override example (lessons will add entries here as we go):
lesson_overrides: { }
```

Keeping this in YAML rather than Python means you can change your entire series' model policy by editing one file, and
it also gives you a single place to look if you want to change your provider.

> 📌 **NOTE:** Our aim is to minimize the cost you incur when learning a new framework like the ADK. API access of leading model providers - OpenAI (GPT-models), Anthropic (Claude models) and Google (Gemini models) - is not free. 
>
> We default to using the "cheapest" model in all our examples, unless the use-case specifically calls for using a more costly model.

## Step 6: VS Code setup

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.analysis.typeCheckingMode": "basic",
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

On Windows, `uv` places the interpreter at `.venv\Scripts\python.exe` instead. VS Code's Python extension usually detects this automatically once you open the folder, but if it doesn't, click the interpreter version in the bottom-right status bar and select "Enter interpreter path" → browse to `.venv`.

## Step 7: Verify everything works

We're not building an agent yet, that's Lesson 2, but we should confirm the CLI is installed and that your Claude key actually works.

Create `scripts/verify_setup.py`:

```python
"""Verifies the ADK environment is correctly configured.

Checks three things, in order: the ADK CLI is installed, required
environment variables are present, and the Anthropic API key can
successfully reach Claude Haiku with a minimal request.

This script calls the Anthropic SDK directly, which mirrors exactly
what ADK's native Claude provider (google.adk.models.anthropic_llm)
does under the hood, so a pass here means Lesson 2's agent will work.
It intentionally avoids importing google.adk.agents, since building
an actual Agent is the subject of Lesson 2.
"""

import os
import subprocess
import sys

from dotenv import load_dotenv


def check_adk_cli_installed() -> bool:
    """Confirms the `adk` command is available on PATH.

    Returns:
        bool: True if `adk --version` runs successfully.
    """
    try:
        result = subprocess.run(
            ["adk", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"[OK] ADK CLI installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        print(f"[FAIL] ADK CLI not found or errored: {error}")
        return False


def check_required_env_vars() -> bool:
    """Confirms the API keys needed for this series are present.

    Returns:
        bool: True if both keys are set and non-empty.
    """
    required = ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    missing = [name for name in required if not os.environ.get(name)]

    if missing:
        print(f"[FAIL] Missing environment variables: {', '.join(missing)}")
        return False

    print("[OK] Required environment variables are set")
    return True


def check_claude_connectivity() -> bool:
    """Sends one minimal request to Claude Haiku via the Anthropic SDK.

    This costs a fraction of a cent and confirms your Anthropic key
    is valid before you build anything on top of it.

    Returns:
        bool: True if Claude responds successfully.
    """
    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        reply = response.content[0].text.strip()
        print(f"[OK] Claude Haiku responded: '{reply}'")
        return True
    except Exception as error:  # noqa: BLE001 — surfacing any provider error is the point here
        print(f"[FAIL] Could not reach Claude: {error}")
        return False


def main() -> None:
    """Runs all verification checks and exits non-zero on any failure."""
    load_dotenv()

    checks = [
        check_adk_cli_installed(),
        check_required_env_vars(),
        check_claude_connectivity(),
    ]

    if all(checks):
        print("\nEnvironment is ready. Move on to Lesson 2.")
    else:
        print("\nFix the failures above before continuing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Run it:

```bash
uv run scripts/verify_setup.py
```

Expected output:

```
[OK] ADK CLI installed: google-adk 2.5.0
[OK] Required environment variables are set
[OK] Claude Haiku responded: 'OK'

Environment is ready. Move on to Lesson 2.
```

If the ADK CLI check fails, re-run `uv add google-adk==2.5.0` and make sure you're inside the `uv run` context. If the Claude check fails, double-check the key in `.env` has no stray quotes or trailing spaces.

## Your project structure should now look like this

```
# you can create adk2_tutorial anywhere on disk (hence the)
# when we refer to "project root folder" we mean the 
# complete path to this adk2_tutorial folder.
.../adk2_tutorial/
├── .env
├── .python-version
├── pyproject.toml
├── config/
│   └── models.yaml
├── scripts/
│   └── verify_setup.py
├── agents/              # empty for now, Lesson 2 adds the first one
└── .vscode/
    └── settings.json
```

Your `pyproject.toml` dependencies section should look something like this:

```toml
dependencies = [
    "google-adk==2.5.0",
    "anthropic",
    "python-dotenv",
    "pyyaml",
]
```

## A word on cost

This lesson cost you close to nothing: a single ten-token request to Haiku. That pattern holds for most of the series. The lessons that cost real money are the ones running multi-agent loops or deploying to GCP, and we'll flag ballpark costs before those specifically.

