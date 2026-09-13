# Client setup and remote-access boundaries

## Local stdio clients

Use the executable's absolute path and an existing workspace. Generic JSON is in README.
The model/client owns the conversation loop, tool approvals and inference costs. The server
does not require Codex or launch a second model. Start with `--doctor` to inspect the mode.
Paths in example config must be replaced for your installation; do not put credentials there.

## HTTP-capable MCP clients

Use `--transport http --port 8765`; supply `AGENT_WORKSTATION_HTTP_TOKEN` from your own
secret manager or process environment, with 32+ random non-whitespace ASCII characters.
Send `Authorization: Bearer <token>` to `http://127.0.0.1:8765/mcp`. The listener refuses an
absent token and does not support non-loopback bind addresses. Transport, parser and bearer
verification are inherited from the pinned Coding Tools MCP revision.
A raw local endpoint is not publicly reachable. Only use an authenticated HTTPS proxy/tunnel.

## ChatGPT web / remote chat clients

A web client cannot launch a local stdio command. It requires a supported remote connection,
which may also require OAuth rather than a manually configured bearer header.
This V1 does not implement OAuth registration, a hosted proxy, or tunnel installation.
A separately provisioned authenticated stdio-to-remote bridge may launch this executable,
or an appropriate authenticated gateway may proxy the loopback endpoint. Gateway access
controls must not be disabled just to make a client accept the server.

Consult current vendor documentation; client capabilities and account availability change:
- OpenAI remote MCP guidance: https://platform.openai.com/docs/guides/tools-remote-mcp
- Upstream remote deployment: https://github.com/xyTom/coding-tools-mcp/blob/main/docs/remote-mcp.md

This release tests protocol behavior locally. It does not claim end-to-end certification for
every ChatGPT/Claude/Cursor version, plan, gateway or authentication method. Your existing
personal MCP connection is not copied into the public package or changed by installing it.
