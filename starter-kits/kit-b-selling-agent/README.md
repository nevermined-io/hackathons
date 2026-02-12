# Kit B: Selling Agent

An agent that sells data or services with x402 payment protection. This starter kit provides a complete selling agent with tiered pricing (1, 5, 10 credits), two deployment modes (local FastAPI and AWS AgentCore), and built-in usage analytics.

**Track:** 1 - Data Marketplace | **Protocol:** x402 | **Languages:** TypeScript, Python

## Quick Start (Python)

```bash
cd ../../agents/seller-simple-agent
poetry install
cp .env.example .env
# Edit .env with your credentials
poetry run agent
```

Full documentation, architecture diagram, API reference, and customization ideas are in the [seller-simple-agent README](../../agents/seller-simple-agent/).

## Quick Start (TypeScript)

```bash
cd typescript
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent
```

## Related

- [Kit A: Buyer Agent](../kit-a-buyer-agent/) - Build the buyer side
- [Kit C: Switching Agent](../kit-c-switching-agent/) - Multi-provider switching
- [Track 1 Overview](../../docs/tracks/track-1-data-marketplace.md)
