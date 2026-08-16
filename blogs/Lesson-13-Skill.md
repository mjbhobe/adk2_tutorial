# Lesson 13: Skills — Packaging and Reusing Agent Capabilities

The ADK provides several ways to reuse agent behavior:

1. `SequentialAgent`, `ParallelAgent`, and `LoopAgent` reuse a fixed shape of orchestration. 
2. An `AgentTool` reuses a whole agent, its own model, its own instruction, its own tools, as one callable unit.
3. And this lesson covers `Skills`, the 3rd kind of reuse: skills  package knowledge and procedure, not agents, so any agent can pick it up on demand, _without that knowledge being hardcoded into its instruction ahead of time_.

## Why Skills exist: the gap a shared tools.py doesn't close

Across lessons `11a`, `11b`, and `12`, PAN validation, the credit bureau mock, and the EMI formula got written fresh into each lesson's own `tools.py`. The obvious fix is a shared module, one `validate_pan_format` function, imported into every agent that needs it. That solves code duplication, but it doesn't solve two other things:

1. **Every agent still needs its own instruction text** explaining when and how to use that tool. The function is shared but the guidance around it isn't.
2. **A plain function tool has no "only when relevant" mode.** Once `validate_pan_format` is in an agent's `tools=[]` list, it's sent to the model as one of its available functions on *every single turn*, whether that conversation ever mentions a PAN or not. 

    There's no way to say "this agent knows PAN validation exists, but only pull in the real detail once a PAN actually shows up"! A plain function tool is either in the list or it isn't.

A Skill closes both gaps. The instructions live in one place, a `SKILL.md` (markdown format) file, not copied into every agent's own instruction. And they're discovered and loaded on demand, an agent with several skills available doesn't carry the full weight of all of them on every turn, only the ones it actually decides to use.

## What a Skill actually is

A Skill is a folder with a specific layout:

```
pan-validation/
├── SKILL.md
├── references/   (optional)
├── assets/       (optional)
└── scripts/      (optional)
```

`SKILL.md` has two parts: YAML front-matter, then a markdown body. The front-matter needs exactly two required fields, `name` and `description`. Everything else, such as `license`, `compatibility`, `allowed-tools`, `metadata`, is optional. 

Here's the example with every field included:

```markdown
---
name: pan-validation
description: |
  Validates Indian PAN (Permanent Account Number) format. Use this
  whenever an agent needs to check whether a PAN is well-formed.
license: Apache-2.0
compatibility: Requires no external services; pure Python validation.
allowed-tools: validate_pan_format
metadata:
  author: your-team-name
  version: "1.0"
  adk_additional_tools:
    - validate_pan_format
  adk_inject_state: false
---

# PAN Validation

A valid PAN is 10 characters: 5 uppercase letters, 4 digits, 1 uppercase
letter, e.g. ABCDE1234F...
```

- **`name`** (required): kebab-case or snake_case, must match the directory name exactly.
- **`description`** (required): what the skill does and when to use it. This is the L1 text an agent sees before deciding whether to load anything further.
- **`license`** (optional): a license identifier, useful if you're sharing the skill outside your own project.
- **`compatibility`** (optional): free text noting anything the skill depends on, or doesn't.
- **`allowed-tools`** (optional, experimental): a space-delimited list of tools pre-approved to run when this skill is active, part of the open `agentskills.io` spec this format follows.
- **`metadata`** (optional): a free-form dict for anything client-specific. Two keys mean something to ADK specifically: `adk_additional_tools`, a list of tool names that should become available once this skill is loaded, drawn from whatever `SkillToolset` was given via its own `additional_tools` parameter; and `adk_inject_state`, which, set to `true`, lets the instructions body use `{var}` interpolation from session state, the same `{key}` / `{key?}` syntax you've used in agent instructions since Lesson 6a.

The directory name (holding the `SKILL.md` file) _has to match_ `name` in the frontmatter exactly, `pan-validation/` for a skill named `pan-validation`. That's not a style convention, ADK's own loader raises an error if they don't match.

## Why is it split into layers?

The frontmatter and the body aren't loaded at the same time, and that's the actual point of a Skill, not an implementation detail.

- **L1**: just the frontmatter, `name` and `description`. Cheap enough that an agent can be shown dozens of these at once, just to figure out which ones might be relevant.
- **L2**: the full markdown body, `SKILL.md`'s instructions. Only loaded once a specific skill actually looks relevant.
- **L3**: anything in `references/`, `assets/`, or `scripts/`. Loaded later still, only if the instructions in L2 actually point at one of them.

An agent that has ten skills available never pays the cost of all ten's full instructions on every turn, it sees ten short descriptions, decides which one or two or three are relevant to the request in front of it, and only pulls in the full detail for those.

> 📌 **NOTE:** If you've used Claude, Claude Code, or Cowork's Skills feature, this format will look familiar, same idea of a `SKILL.md` file with layered detail. That's not a coincidence, but it's also not the same feature under a different name! 
>
> ADK's Skills system is its own independent implementation, built around a shared open format (`agentskills.io`), not something wired into Anthropic's product surface. They converge on a similar shape because it's a good shape for this problem, not because one is built on top of the other.

## How ADK wires this up

```python
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.skills import load_skill_from_dir

pan_skill = load_skill_from_dir("skills/pan-validation")

root_agent = Agent(
    name="orchestrator",
    model=get_model("primary"),
    tools=[SkillToolset(skills=[pan_skill])],
)
```

`SkillToolset` doesn't hand the agent the skill's instructions directly. It hands the agent four tools of its own:

- **List skills**: see what's available, frontmatter only, L1.
- **Load a skill**: pull in one specific skill's full instructions, L2.
- **Load a skill resource**: pull in something from `references/` or `assets/`, L3.
- **Run a skill script**: execute something from `scripts/`, L3, and only if `SkillToolset` was given a `code_executor`.

The model decides when to call each of these, the same way it decides when to call any other tool. Nothing about a skill is force-fed into the conversation.

## Where skills live in your project

ADK has no opinion on this, no CLI flag scans a folder for skills, no shipped registry reads them off local disk, the one concrete `SkillRegistry` ADK ships, `GcpSkillRegistry`, is a *remote* registry, not a local filesystem convention. Wherever you point `load_skill_from_dir`, that's where a skill lives, ADK never goes looking on its own. Google's own shipped BigQuery skills follow this too, they sit inside the BigQuery tool's own package, next to the code that uses them, not in some project-wide skills directory.

That leaves the actual placement decision to you, and two shapes make sense depending on scope:

1. A skill specific to one agent belongs under that agent's own folder, alongside that agent's own code. Place it in a sub-folder of the folder holding the `agent.py` file.
2. A skill genuinely reused across multiple agents belongs somewhere shared, `agents/common/skills/`, alongside this project's other shared code like `model_config.py` would make sense.

Neither is enforced, both are just what makes sense for how widely a given skill actually gets used.

## The two flavors of Skills

**Instructions-only** is what `pan-validation` above looks like: `SKILL.md`, nothing in `scripts/`. The model loads the instructions, then does the actual work itself, reasoning through the steps, possibly calling its own separate function tools, following the guidance it just read.

**Scripted** adds a `scripts/` folder with actual executable code. Instead of reasoning through a task by following written-out steps, the model can call `RunSkillScriptTool` and have the skill's own script do the work directly.

In practice, this is the less common of the two, and worth being upfront about that rather than implying it's an equal, everyday choice. Plain function tools, whether gated behind a skill's `adk_additional_tools` (see metadata in `Skills.md` file) or sitting bare in `tools=[]`, are the default reach for most logic, no subprocess, no `code_executor` to configure, nothing to sandbox, easier to test and maintain. 

A scripted skill earns its place in a narrower set of situations:

* The skill is meant to be shared or distributed outside your own codebase, to a team, a different project, possibly people not using ADK or Python at all!
* The logic genuinely isn't Python, maybe a shell script or a compiled binary, or a task that needs real process isolation, something that could hang or crash without taking your agent's own process down with it. It also needs some sort of code executor to execute the script. 

### A real constraint worth understanding before you build the scripted example

Running a script needs somewhere to actually execute it, that's the `code_executor` parameter on `SkillToolset`. ADK ships several of these:

- **`UnsafeLocalCodeExecutor`**: runs whatever code the model generates directly in your own Python process. Zero setup, no Docker, no cloud account, works the moment you install ADK.
- **`ContainerCodeExecutor`**: runs code inside a Docker container, real isolation, needs Docker installed and configured.
- **`VertexAiCodeExecutor`**, **`AgentEngineSandboxCodeExecutor`**, **`GkeCodeExecutor`**: run code in a managed cloud sandbox, need actual GCP resources.

The name `UnsafeLocalCodeExecutor` isn't a scare tactic, it's accurate. It executes arbitrary, model-generated code in your own process, with no sandbox at all. For a script you wrote yourself, in a skill you control, running on your own machine while you're learning, that's a reasonable trade against the setup cost of Docker or a cloud sandbox. It is not something you'd point at untrusted input, or run anywhere near production, without real isolation underneath it. Lesson 13a uses `UnsafeLocalCodeExecutor` for exactly that reason, it's the only option that doesn't require you to set up infrastructure just to see a scripted skill work, and it says so again right where it's used.

## Skills, `AgentTool`, and a shared `tools.py`, side by side

Three different things get called "reuse" in this series, and they're not interchangeable.

| | Reuses | Always present? | Own model? |
|---|---|---|---|
| Shared `tools.py` | Code (one function) | Yes, if it's in the `tools` list | No, runs inside the calling agent |
| `AgentTool` (11d) | A whole agent | Only when the model chooses to call it | Yes, its own model, own config, own isolation |
| Skill | Knowledge and procedure, optionally with bundled tools/scripts | Only the L1 description; full detail loaded on demand | No, it's not an agent at all |

A shared `tools.py` function is the right call when the logic is small, stable, and every agent that needs it should just always have it, no discovery step required, that's most of what 11a through 12 actually did. `AgentTool` is the right call when the reused thing needs its own model or configuration, or when a model has to decide, at runtime, whether to delegate to a genuinely separate agent. A Skill is the right call when what you're packaging is guidance, a procedure, domain knowledge, something an agent should be able to find and pull in only when it's relevant, without carrying it, or its instruction-bloat, on every single turn regardless.

## Can you combine all three on one agent?

Yes, freely, with no special handling. A plain function tool, an `AgentTool`, and a `SkillToolset` can all sit in the same `tools=[]` list at once:

```python
root_agent = Agent(
    name="orchestrator",
    model=get_model("primary"),
    instruction="...",
    tools=[
        calculate_something,               # plain function tool
        AgentTool(agent=some_specialist),  # a whole agent as a tool
        SkillToolset(skills=[some_skill]), # skills, discoverable on demand
    ],
)
```

This isn't three competing mechanisms you have to pick one of, it's three tools an agent's own list can hold at the same time, resolved the same way regardless of which kind each one is. `13a`'s demo agent already does part of this, a `SkillToolset` sitting in a `tools=[]` list on its own, nothing else in the way.

## In this lesson

You learned what a Skill is: a `SKILL.md` file with required `name` and `description` frontmatter, an instructions body, and optional `references/`, `assets/`, and `scripts/` folders, loaded in layers so an agent only pays for what it actually uses. You saw the two flavors, instructions-only and scripted, and what a scripted skill actually needs underneath, a `code_executor`, with `UnsafeLocalCodeExecutor` being the only zero-setup option and exactly why that name is a real warning, not a formality. You also saw where a Skill sits next to the two other reuse mechanisms this series has already covered, reusing code, reusing a whole agent, or reusing knowledge, each solving a genuinely different problem.

## In the next lesson

Lesson 13a builds both flavors for real: an instructions-only skill packaging PAN validation and the credit bureau mock, and a scripted skill running the EMI calculation as an actual executed script, both loaded into one small demo agent through `SkillToolset`.
