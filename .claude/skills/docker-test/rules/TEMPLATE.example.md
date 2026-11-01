# acme-api - testing rules

Template for one service. `/docker-test` reads `rules/<repo-name>.local.md`, where
`<repo-name>` is the last part of `git remote get-url origin`, without `.git`.

To add a service, copy this file to `rules/<repo-name>.local.md` and replace every value.
Files ending in `.local.md` are gitignored - keep hosts, IDs, and test data there, never in `skill.md`.

## Setup
1. In a worktree, copy `.env` from the main checkout, or `.env-example` if there is none.
2. Required for the image build: `GH_ACCESS_TOKEN` (set in your shell).
3. Start the port forwards for the endpoints under test (see "Connect to the dev environment").
4. `docker compose up -d`.

## Endpoints
- API base URL: `http://localhost:8080`
- Auth gateway: `http://localhost:8081/graphql`

## Connect to the dev environment
Without an address in `.env`, each dependency uses a local fake. To test against the real
dependency, forward its port from the dev cluster and point `.env` at it.

1. Check that kubectl uses the dev cluster: `kubectl config current-context` must print `<dev-context>`.
   NEVER port-forward from a production context.
2. Get cluster access first if your org requires it (for example a just-in-time access request).
3. Start only the forwards the endpoints under test need, each as a background process:

   ```bash
   kubectl port-forward \
     $(kubectl get pods -l app.kubernetes.io/name=<pod-label> -o jsonpath='{.items[0].metadata.name}' -n <namespace>) \
     -n <namespace> <local-port>:<pod-port>
   ```

4. Set the address in `.env`. The container reaches the host through `host.docker.internal`:

   ```
   <DEPENDENCY>_GRPC_ADDRESS=host.docker.internal:<local-port>
   ```

5. Restart the service container, so it reads the new `.env`.

| Dependency | Namespace | Pod label | Ports | `.env` variable |
|------------|-----------|-----------|-------|-----------------|
| Orders | `orders` | `orders-grpc` | `50052:50051` | `ORDERS_GRPC_ADDRESS` |
| Inventory | `inventory` | `inventory-api` | `50053:50051` | `INVENTORY_GRPC_ADDRESS` |

## Test on sandbox
The sandbox serves fixed, fictional data, so a test there checks the API shape, not real
business logic. Use it when a change adds or renames a public field.

- **Local sandbox mode:** start the service with `APP_ENV=sandbox`. It needs no database and
  no dependencies - it reads the fixture files in `<fixtures-dir>/`. Change a fixture file, then
  restart the container to load it.
- **Hosted sandbox:** `https://sandbox.acme.example/api/v1`. Any non-empty bearer token works:

  ```bash
  curl https://sandbox.acme.example/api/v1/orders -H "Authorization: Bearer sandbox"
  ```

- A new public field needs fixture data in the same change: fill it on some rows and leave
  it empty on others, so both cases show.

## Test access
How to get a token, as a command that sets a shell variable:

```bash
API_TOKEN=$(<command that prints a token>)
```

Headers every request needs:
- `Authorization: Bearer $API_TOKEN`
- `X-Forwarded-For: 127.0.0.1` - the token only allows this IP

## Test data
| What | ID | Notes |
|------|----|-------|
| Test account | `acct_123` | Has statements |

## Mandatory tests
`/docker-test` runs these on every run, after its generic tests M1-M6. Use concrete requests.

| # | Test | Request | Expect |
|---|------|---------|--------|
| S1 | Health | `GET http://localhost:8080/health` | `200` |
| S2 | Wrong client IP | Any endpoint without `X-Forwarded-For` | `403` |
| S3 | Missing scope | Token without the endpoint's scope | `403` |

## Rules
- <anything that makes a test pass or fail for reasons other than the code under test>
