# Call patterns for each protocol

Use the host, the path, and the headers from the service file. `$RUN` is the run folder. Read each token from its file, never from the conversation.

## REST

```bash
curl -sS -w '\n%{http_code}\n' -X POST "<dev-host>/<path>" \
  -H "Authorization: Bearer $(cat $RUN/.token-<name>)" \
  -H 'Content-Type: application/json' \
  -d '{"field": "value"}' | tee "$RUN/<test #>.json"
```

The last line of the output is the HTTP status.

## GraphQL

```bash
curl -sS "<dev-host>/graphql" \
  -H "Authorization: Bearer $(cat $RUN/.token-<name>)" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'EOF' | tee "$RUN/<test #>.json"
{"query": "query ($id: ID!) { thing(id: $id) { id status } }", "variables": {"id": "<id>"}}
EOF
```

GraphQL returns `200` for most errors. A test passes only if `errors` is absent, unless the test expects the error. Check with `jq '.errors'`.

## gRPC

```bash
grpcurl -H "authorization: Bearer $(cat $RUN/.token-<name>)" \
  -d '{"id": "<id>"}' <host:port> <package.Service>/<Method> | tee "$RUN/<test #>.json"
```

- If the server has no reflection, add `-import-path <dir> -proto <file>.proto`. The service file gives the proto source.
- Add `-plaintext` only for a port forward to `localhost`.
- List the methods first: `grpcurl <host:port> list <package.Service>`.
- The expected result of an error test is the gRPC status name, for example `NOT_FOUND`.

## MCP (Streamable HTTP)

1. Initialize, and keep the session ID:

   ```bash
   curl -sS -D "$RUN/mcp-headers" "<mcp-url>" \
     -H "Authorization: Bearer $(cat $RUN/.token-<name>)" \
     -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test-on-dev","version":"1"}}}'
   SID=$(awk -F': ' 'tolower($1)=="mcp-session-id"{print $2}' "$RUN/mcp-headers" | tr -d '\r')
   ```

2. Send `notifications/initialized`, then call `tools/list` or `tools/call` with the header `Mcp-Session-Id: $SID`:

   ```bash
   curl -sS "<mcp-url>" -H "Mcp-Session-Id: $SID" \
     -H "Authorization: Bearer $(cat $RUN/.token-<name>)" \
     -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
     -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"<tool>","arguments":{}}}' \
     | tee "$RUN/<test #>.json"
   ```

- If the response is `text/event-stream`, read the JSON in the `data:` lines.
- A tool error is `result.isError: true`, not a JSON-RPC `error`. Check both.
- If the server is connected to this Claude session as an MCP server, call its tool directly instead. Check first that it points to dev.
