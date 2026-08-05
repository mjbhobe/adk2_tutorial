# Lesson 2: Your First Agent

In this lesson, you'll build and run your first working ADK agent: a simple assistant for a retail bank's customer support desk that explains everyday banking terms like APR, EMI, KYC, and overdraft in plain language. It won't touch real customer data or do anything BFSI-specific yet, that starts in Lesson 3, but it's enough to show you the three things every ADK agent needs, and the two ways you can run one on your machine.

You'll also see the same agent answer using two different models, Claude Haiku and Gemini Flash, by changing a single line. That's worth seeing early, since it tells you something true about ADK: your agent code generally doesn't change when you swap the model underneath it.

## Step 1: Create the agent folder

Every ADK agent lives in its own folder with a specific, small structure: an `agent.py` file that defines and exports a `root_agent`, and an `__init__.py` that imports it so ADK can find it.

Open the project root folder (`adk2_tutorial`) in a terminal and run the following command:

```bash
mkdir -p agents/lesson02_first_agent
```

You don't need a separate `.env` file inside this folder. ADK automatically looks upward from an agent's folder for a `.env` file, so the one you created at `adk2_tutorial/.env` back in Lesson 1 already covers every agent folder we'll create in this series.

## Step 2: Write the agent

Create `agents/lesson02_first_agent/agent.py`:

```python
"""Lesson 2: Your First Agent.

A minimal agent that answers general banking terminology questions for
a retail bank's customer support desk.

Everything here is hardcoded on purpose. Starting in Lesson 3, model
choice and instructions move into config/models.yaml and per-agent
config, so agents stop needing code changes to swap models.
"""

from google.adk.agents import Agent
from google.adk.models.anthropic_llm import AnthropicLlm

# Flip this to True to run the exact same agent on Gemini Flash instead
# of Claude Haiku. Both API keys are already available from the
# project's root .env.
USE_GEMINI_FLASH = False

AGENT_INSTRUCTION = (
    "You are a friendly, knowledgeable assistant for a retail bank's "
    "customer support desk. Answer questions about common banking "
    "terms and concepts, things like APR, EMI, KYC, and overdraft, "
    "in plain language a first-time customer would understand. Keep "
    "answers under 100 words. If a question requires looking at a "
    "specific customer's account or transaction data, say so clearly "
    "rather than guessing, since you don't have access to that data "
    "yet in this lesson."
)

if USE_GEMINI_FLASH:
    model = "gemini-3.5-flash-lite"
else:
    model = AnthropicLlm(model="claude-haiku-4-5-20251001")

root_agent = Agent(
    name="bfsi_support_desk_agent",
    model=model,
    instruction=AGENT_INSTRUCTION,
    description="Answers general retail banking terminology questions.",
)
```

Create `agents/lesson02_first_agent/__init__.py`:

```python
from . import agent
```

That's the whole agent. Three real pieces: a `model`, an `instruction`, and a `name`. Everything else, the conversation loop, calling the LLM API, managing the exchange, is ADK's job, not yours.

## What each parameter in `Agent(...)` actually does

Before we move on, it's worth knowing what each of these four arguments controls, since you'll use all of them in every agent you build for the rest of this series.

- **`name`** (mandatory) — a unique identifier for this agent. ADK enforces two rules on it: it must be a valid Python identifier (letters, digits, underscores, no spaces or hyphens, can't start with a digit), and it **can't be the literal string `"user"`**, since ADK reserves that for the end user's own input. Once you start building multi-agent systems, this name is also how one agent refers to another, so it's worth naming agents descriptively from the start, the way we did with `bfsi_support_desk_agent`.

- **`model`** (mandatory) — which LLM answers on this agent's behalf, either a plain string (for models ADK resolves natively, like Gemini) or a model object you construct yourself (as we just did for Claude, with `AnthropicLlm(...)`). This is the one parameter you'll see change the most across the series as we swap between Haiku, Sonnet, and Gemini Flash depending on the lesson.

- **`instruction`** (mandatory) — the system prompt: your agent's standing directions for how to behave, what tone to use, and what it should and shouldn't do. This is the single biggest lever you have over an agent's behavior, and it's worth spending real time on. Later in the series, once we cover sessions and state, you'll see this field can also contain placeholders like `{customer_name}` that get filled in from live conversation data, rather than being fixed text like it is here.

- **`description`** (optional) — a short, one-line summary of what this agent does, separate from `instruction`. It doesn't affect how the agent behaves at all. It matters once an agent has other agents working under it: the parent uses each sub-agent's `description` to decide which one to hand a task to - so when it comes to multi-agent systems, treat this as mandatory. In this lesson, with a single standalone agent, it's doing nothing functionally yet, but it's good practice to write it accurately from the start, since it becomes load-bearing the moment this agent joins a larger system in later lessons.

## A caveat worth knowing: Claude and Gemini aren't resolved the same way

Notice that Gemini gets passed in as a plain string (`"gemini-3.5-flash-lite"`), but Claude gets wrapped in an `AnthropicLlm(...)` object instead of a string like `"claude-haiku-4-5-20251001"`. This isn't a style choice, it's necessary, and it's worth understanding so it doesn't trip you up later.

When you give ADK a plain model name string, it looks the name up against a set of built-in patterns to decide which provider to use. Gemini names resolve straight to ADK's native Gemini support, no extra step needed. Claude names, if left as a plain string, resolve to a version of Claude meant to run through Google Cloud's Vertex AI, which expects a GCP project to be configured. Since we're using a direct Anthropic API key instead, a bare Claude string would fail with a configuration error. Wrapping it in `AnthropicLlm(...)` sidesteps that entirely and talks to Anthropic directly, using the `ANTHROPIC_API_KEY` you already set in `.env`. You'll use this same pattern every time you reach for Claude in this series.

## Step 3: Run it with `adk run`

`adk run` gives you a command-line chat loop, the fastest way to test an agent without opening a browser. From the project root (i.e. from `adk2_tutorial` folder) run the following command:

```bash
uv run adk run agents/lesson02_first_agent
```

> 📌 **NOTE** We pass a folder name (specifically the name of the folder containing our `agent.py` file) to the `adk run` command - not a Python module name!

If all runs correctly, you'll see a bunch of logging information printed on your console, which you can safely ignore, followed by this: 

```bash
Running agent bfsi_support_desk_agent, type exit to exit.
[user]: 
```

The `bsfi_support_desk_agent` comes from the value of the `name` parameter we gave our Agent. Type a question like:

```
What does APR mean?
```

and press Enter. Within a few seconds you should see a short, plain-language explanation come back, written the way you'd expect a bank's support desk to explain it to a new customer. For example you may see something like this (your text may vary because LLM output is not deterministic!):

```bash
[user]: What does APR mean?
[bfsi_support_desk_agent]: **APR** stands for **Annual Percentage Rate**. It's the yearly cost of borrowing money, shown as a percentage.

Think of it this way: if you borrow $100 at 10% APR, you'll pay $10 in interest over one year (though payments are usually monthly, so it works out differently).

APR helps you compare loans fairly because it includes the interest rate plus any fees the lender charges. A lower APR means you pay less to borrow money, so it's always good to look for the lowest APR when shopping for loans or credit cards.
[user]:
```

Try a couple more terms if you like: EMI, KYC, overdraft. Type `exit` or press `Ctrl+C` when you're done.

## Step 4: Run it with `adk web`

`adk web` starts a local browser-based chat UI, and it becomes genuinely useful once you have more than one agent in your project, since it lists every agent it finds in a dropdown. Run it from your project root, pointing at the whole `agents/` folder rather than this one lesson's subfolder:

```bash
uv run adk web agents
```

ADK will print a local URL, typically `http://127.0.0.1:8000`. Open it in your browser and you'll see something like this:

<div align="center">
    <image src="images/adk_web_ui.png" alt="adk web UI"/>
</div>

You'll see a dropdown with one entry, `lesson02_first_agent`, select it, and you'll get a chat window that behaves the same way as `adk run`, just with a proper UI: message history, a text box, and a cleaner read on the agent's responses. Ask it the same banking-terms questions - for example asking `What is APR` may give a response like this:

<div align="center">
    <image src="images/adk_web_ui2.png" alt="adk web UI Response"/>
</div>

Right now there's only one agent to pick from, but by the time we're a few lessons in, this dropdown will hold several, which is exactly why the project is structured this way.

## Step 5: Switch it to Gemini Flash

Open `agent.py` and change one line:

```python
USE_GEMINI_FLASH = True
```

Run either command again:

```bash
uv run adk run agents/lesson02_first_agent
```

Ask the same question you asked before. You'll get an answer from a different model, likely worded a bit differently, but coming from the exact same agent definition, same instruction, same code around it. That's the point of this step: switching providers here took one line, not a rewrite.

Set `USE_GEMINI_FLASH` back to `False` before moving on, since Claude Haiku is our default for the rest of the series.

## If you're coming from LangChain or LangGraph

What you just built maps closely to the simplest possible LangGraph app: a single node with a system prompt and no graph or edges around it yet. ADK's `Agent` and a single-node LangGraph app are solving the same narrow problem here. The real differences between the two frameworks show up once you start composing multiple agents together and need to decide how control passes between them, which is where Lesson 8 picks up.

## A word on cost

This lesson used a handful of short exchanges on Claude Haiku, and the same again if you tried the Gemini Flash swap. Both are inexpensive per token for messages this short, and Gemini Flash specifically has a free tier that easily covers this kind of testing. You shouldn't see any meaningful cost from this lesson.

## Conclusion

In this lesson, we learnt how to build and test our very first agent, which could answer general questions on Retail banking terminology. In the next lesson, our agent will start doing some real work, like calculating loan EMIs and affordability for retail lending use case. 
