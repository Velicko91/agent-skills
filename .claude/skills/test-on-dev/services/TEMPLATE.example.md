# acme-ledger - dev testing

Template for one service. `/test-on-dev` reads `services/<service>.local.md`.

To add a service, copy this file to `services/<service>.local.md` and replace every value.
Files ending in `.local.md` are gitignored - keep hosts, IDs, and test data there, never in `skill.md`.

## Dev hosts
`/test-on-dev` calls only these hosts and kubectl contexts. Anything else stops the run.

- REST and GraphQL: `https://ledger.dev.acme.example`
- MCP: `https://ledger.dev.acme.example/mcp`
- gRPC: `localhost:50051`, through the port forward below
- kubectl context: `acme-dev`

Port forward for gRPC:

```bash
kubectl --context acme-dev -n ledger port-forward svc/ledger-grpc 50051:50051
```

## Protocols and endpoints
| Protocol | Endpoint | Notes |
|---|---|---|
| REST | `/api/v1/...` | OpenAPI: `<repo>/openapi.yaml` |
| GraphQL | `/graphql` | Through the gateway; needs the gateway token |
| gRPC | `acme.ledger.v1.Ledger` | No reflection; protos in `<repo>/proto` |
| MCP | `/mcp` | Tools: `get_balance`, `list_entries` |

## Test access
One command for each token. It prints the token on stdout.

| Token | For | Command |
|---|---|---|
| `api` | REST, GraphQL, MCP | `<command that prints a token>` |
| `grpc` | gRPC | `gcloud auth print-identity-token --audiences=<audience>` |

If a token has no command, `/test-on-dev` asks for it.

## Test data
| What | ID | Notes |
|---|---|---|
| Test account | `acct_123` | Has a positive balance |
| Empty account | `acct_456` | No entries |

## Logs
`/get-gcloud-logs` alias: `ledger`

## Mandatory tests
Run on every test run.

| # | Test | Call | Expect |
|---|---|---|---|
| M1 | Health | `GET /health` | `200` |
| M2 | No token | Any endpoint without `Authorization` | `401` |

## Main flows
`--random` tests these when there is no branch diff.

1. Create an entry, then read the balance - the balance changes by the amount.
2. List the entries of the empty account - an empty list, not an error.

## Known problems
- <a problem on dev that makes a test fail for reasons other than the code under test, and how to see it>
