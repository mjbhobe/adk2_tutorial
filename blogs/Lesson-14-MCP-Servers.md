# Lesson 14: MCP Servers

Skills package knowledge, `AgentTool` wraps another agent, both stay inside your own Python process. MCP (Model Context Protocol) is what you reach for when the thing you need to connect to isn't yours at all, a separate service, built by a different team, possibly in a different language, that you connect to over a standardized protocol rather than importing.

## What MCP actually is

MCP is an open protocol for connecting an LLM application to external tools and data. Though invented by Anthropic, it's not specific to Anthropic or Google or OpenAI. 

It defines a _client-server_ relationship: 

* An **MCP server** exposes capabilities over the protocol.
* An MCP **client** connects to it and can discover and call those capabilities the same way it would call a local tool. 

ADK's client `McpToolset`, is one implementation of the client side. The server it connects to doesn't have to be written in Python, nor use ADK, or even exist yet when you write your agent's code! As long as it speaks MCP, it can be plugged in.


A server exposes two different kinds of _things_ worth telling apart:

- **Tools**: callable functions, the same idea as any function tool you've written throughout this series, just living on the other side of the protocol instead of in your own `tools.py`.
- **Resources**: named data the server can supply. These can be documents, records, files, for a client to read, not something you call so much as something you fetch.

`McpToolset` handles tools by default; reading resources needs `use_mcp_resources=True` set explicitly. Here's the difference in code:

```python
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

root_agent = Agent(
    name="research_agent",
    model=get_model("primary"),
    instruction="...",
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(url="https://mcp.example.com/mcp"),
        ),
    ],
)
```

That's all it takes for tools: every tool the server exposes becomes callable, discovered the first time the agent resolves its tools, same as anything else in this series. Resources work differently, they don't each become their own callable tool. Set `use_mcp_resources=True`, and the agent gets exactly one extra tool, `load_mcp_resource`, which the model calls with a list of resource names to fetch their content:

```python
McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="https://mcp.example.com/mcp"),
    use_mcp_resources=True,
)
```

One tool handles every resource the server has; the server's own tools are still resolved and called individually, same as before.

## Two separate roles, two separate packages

**Consuming** an MCP server (client side) is part of core ADK, `McpToolset`, once the right dependency is installed.

**Building** an MCP server (server side) has nothing to do with `google-adk`! It's the standalone `mcp` SDK's own server-building tools, a completely separate concern from anything ADK provides.

> 📌 **NOTE:** To build MCP clients with the ADK, install `google-adk[mcp]`. You don't need `mcp` (i.e. `uv add mcp` IS NOT REQUIRED!). The `mcp` package is required when you want to write an MCP server - nothing to do with the ADK.

```bash
uv add "google-adk[mcp]"
```

## Transport types: what actually carries the connection

`McpToolset` accepts a `connection_params` argument, and it can take 3 values:

- **`StdioConnectionParams`**: the client launches the server as a local subprocess and talks to it over standard input and output. No network involved at all. This is the value you'd use if your MCP server runs on the same machine as the one client using it. It is the simplest of the 3 options & a good way to _test_ your MCP server with an ADK client.
- **`StreamableHTTPConnectionParams`**: the current standard for anything remote or reachable by more than one client, a single HTTP endpoint handling both directions. This is what the official MCP specification recommends for remote connections, and this is what you'll use in most cases when you access remote MCP servers.
- **`SseConnectionParams`**: an older remote transport, two separate endpoints instead of one, _officially deprecated_. It still exists, ADK still supports it, and plenty of servers built before the spec changed still only offer it, but it's not what you'd choose for anything new.

> 📌 **NOTE:** If you see "SSE" mentioned in an MCP server's documentation, that's a signal about its age, not a style choice. For newer MCPs use `StdioConnectionParams` for local servers, `StreamableHTTPConnectionParams` for remote (which is the default you'll use in most cases).

## Why the transport choice actually matters for where your agent runs

This isn't just a spec detail, it maps directly onto where your agent and its MCP server actually live. `StdioConnectionParams` only works when your agent's own process can spawn and manage a child process on the same machine, that's normal for local development, and for deployments where the server runs as a sidecar right next to your agent, same container, same host. It's not a fit for a typical stateless cloud function, or for any setup where the agent and the server are genuinely separate services.

`StreamableHTTPConnectionParams` is what a scalable, possibly multi-instance agent deployment actually needs, and `McpToolset` is built with that in mind: its session manager pools sessions by authentication context, so repeated calls under the same auth headers reuse an already-established MCP session rather than reconnecting every time. That's the shape you want when your agent is running as a real service talking to a remote server, not a one-off script.

## What else `McpToolset` actually supports

Beyond the transport, its constructor takes `auth_scheme` and `auth_credential` for servers that require authentication, `tool_filter` to expose only some of a server's tools, and `header_provider` for anything else a request needs to carry.

## MCP, `AgentTool`, and Skills, one more comparison

Three lessons now have covered three ways to reach outside an agent's own instruction. 

1. `Skills` package knowledge and procedure, loaded on demand, still entirely inside your process. 
2. `AgentTool` wraps a whole other agent, still your own code, still the same process, just a different model or configuration.
3. `MCP` is the one that genuinely leaves your process, a separate service, potentially a different vendor, a different language, a different team entirely, standardized specifically so that boundary doesn't matter to the agent calling across it.

## Skills and MCP, working together

These two aren't just similar, they combine directly. `SkillToolset`'s `additional_tools` parameter accepts a `BaseToolset`, not just individual tools, and `McpToolset` is one. Pass an `McpToolset` in, and a skill's `adk_additional_tools` metadata can name specific tools from that server to activate only once that skill loads, the same on-demand pattern from `13a`, just with the underlying tool backed by a remote server instead of a local Python function.

```python
mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="https://mcp.alphavantage.co/mcp?apikey=..."),
)

skill_toolset = SkillToolset(
    skills=[stock_lookup_skill],
    additional_tools=[mcp_toolset],
)
```

If `stock_lookup_skill`'s frontmatter lists only `get_stock_quote` in `adk_additional_tools`, that's the only tool from Alpha Vantage's entire server the agent ever sees, and only once that specific skill is loaded. Whatever else the server exposes stays invisible unless another skill names it too.

This matters more as an MCP server's surface grows. A remote server with twenty tools, added directly to `tools=[]`, hands the model twenty choices on every single turn. Wrapped behind a skill instead, the model sees one short description, and only pulls in the specific tool it actually decides it needs, the same context-discipline argument Lesson 13 made for local knowledge, holding up just as well for a tool that happens to live on someone else's server.

> 📌 **NOTE:** This isn't the only way to combine them. A `SkillToolset` and a separate `McpToolset` can also just sit side by side in `tools=[]`, both always available, with a skill's instructions simply mentioning the MCP tool by name rather than gating access to it. That's the right call when a server's whole surface is small enough that gating wouldn't buy you much. `14a` builds both versions, so you can see the difference directly.

## Where to find other MCP servers

Thousands of these already exist, most maintained independently by whoever built the thing they connect to. Worth knowing where to look:

- **[`github.com/modelcontextprotocol/servers`](github.com/modelcontextprotocol/servers)**, the official reference server repository, maintained under the same GitHub organization as the protocol itself.
- **`pulsemcp.com`** and **`mcpservers.org`**, community directories that index and let you search across servers by category.

In the next lesson, we connect to one specific, officially maintained server: **Alpha Vantage's** server, at `https://mcp.alphavantage.co/mcp?apikey=YOUR_API_KEY` (`github.com/alphavantage/alpha_vantage_mcp`), maintained by Alpha Vantage themselves, not a community reimplementation, giving you real stock quotes and financial statements through a genuinely external service.

## In this lesson

You learned what MCP actually is, a client-server protocol for reaching tools and resources outside your own process, and the real difference between consuming a server (`McpToolset`, part of core ADK) and building one (the standalone `mcp` SDK, unrelated to ADK). You saw the actual install trap that catches this, `pip install mcp` alone can pull the wrong package, and the correct fix, `google-adk[mcp]`. You also got the current, accurate picture of MCP's transports, `stdio` for local, `Streamable HTTP` for remote, and `SSE` as the deprecated transport still around for backward compatibility, not something to build new work on.

## In the upcoming lessons

In the next lesson, `14a`, we'll code an agent that uses an MCP server, connecting to Alpha Vantage's real, official server over `StreamableHTTPConnectionParams` to pull live stock data and financial statements through a genuinely external service for the first time in this series, then extend it to show a skill gating one of Alpha Vantage's tools on demand, the pairing just covered above, working alongside the plain, always-available version. Thereafter, in `14b`, we'll develop an MCP server of our own, a mutual fund NAV lookup built with the standalone `mcp` SDK, offered over both `StdioConnectionParams` and `StreamableHTTPConnectionParams`, then consumed back through `McpToolset` to prove the round trip actually works.
