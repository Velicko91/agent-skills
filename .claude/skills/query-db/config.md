# query-db configuration

`~/.claude/skills/query-db/data.json` lists the databases. Its shape is in `data.example.json`. NEVER write a password in it.

## Fields of an entry in `databases`

| Field | Required | Meaning |
|-------|----------|---------|
| `engine` | Yes | `postgres`. The script refuses other engines. |
| `host`, `port` | Yes | The address that `psql` connects to. With a port forward, `127.0.0.1` and the local port. |
| `database`, `user` | Yes | The database name and the database user |
| `sslmode` | No | The `psql` SSL mode. Default: `prefer`. |
| `keywords` | No | Words that select this database from the question |
| `tables` | No | Important tables and what one row means. Use them before schema discovery. |
| `notes` | No | Facts that a query needs, for example "amounts are in cents" |
| `keychainAccount` | No | The Keychain account. Default: the alias. |
| `passwordless` | No | `true` if the forwarder authenticates, for example `cloud-sql-proxy --auto-iam-authn`. The script then does not read the Keychain. |
| `statementTimeout` | No | The server-side timeout. Default: `defaults.statementTimeout`. |
| `portForward` | No | For kubectl: `context`, `namespace`, `target` (for example `svc/<name>`), `remotePort`. For another forwarder: `command`, as a list of arguments. The local port is `port`. |

Write `portForward.command` as the full command, not as a shell alias, because the script starts no interactive shell and cannot load aliases.

## Store a password

The user stores each password once. Tell the user to run this command, because it asks for the password, and the value must not pass through the conversation:

```
! security add-generic-password -U -s query-db -a <alias> -w
```
