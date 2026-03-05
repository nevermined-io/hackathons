# OpenClaw Docker Demo

## Clearing Chat History

The OpenClaw UI does not have a built-in way to clear visible chat messages. `/reset` and `/new` only clear the AI context, not the displayed messages. The main session (`agent:main:main`) cannot be deleted from the Sessions page.

To get a clean slate without losing pairing (Nevermined login, agent registration, plan setup):

1. Find the session transcript file inside the container:
   ```bash
   docker exec nvm-seller find /root/.openclaw/agents/main/sessions -name "*.jsonl"
   ```

2. Truncate it:
   ```bash
   docker exec nvm-seller truncate -s 0 /root/.openclaw/agents/main/sessions/<session-id>.jsonl
   ```

3. Hard-refresh the browser (`Cmd+Shift+R`).

Same applies to the buyer container — replace `nvm-seller` with `nvm-buyer`.

## Device Pairing

Every time volumes are wiped (`docker compose down -v`) or containers are rebuilt from scratch, the browser loses its pairing with the gateway. The UI will show "Pairing required" and refuse to load.

To fix, approve all pending device pairing requests:

```bash
# List pending requests
docker exec nvm-seller openclaw devices list
docker exec nvm-buyer openclaw devices list

# Approve each pending request ID
docker exec nvm-seller openclaw devices approve <request-id>
docker exec nvm-buyer openclaw devices approve <request-id>
```

Then hard-refresh the browser (`Cmd+Shift+R`).

There are usually 2 pending requests per container (one per browser tab/window that tried to connect). Approve all of them.

## Rebuilding Containers

**MANDATORY: Always delete old images when rebuilding.** Disk space runs out fast and Docker Desktop will crash. Before every `docker compose up --build`, run:

```bash
docker compose down -v
docker rmi openclaw-docker-seller openclaw-docker-buyer 2>/dev/null
docker image ls  # Check for any other stale images and remove them
docker image prune -f
docker compose up --build -d
```

This is a hard rule — never skip it.

## Container Names

- `nvm-seller` — Seller UI at http://localhost:18789
- `nvm-buyer` — Buyer UI at http://localhost:18790

## Session Storage

- Session config: `/root/.openclaw/agents/main/sessions/sessions.json`
- Chat transcript: `/root/.openclaw/agents/main/sessions/<uuid>.jsonl`
- Plugin/pairing state is stored separately and survives transcript clearing.
