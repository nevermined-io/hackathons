#!/bin/bash
set -e

mkdir -p /root/.openclaw/workspace
cp /opt/openclaw/TOOLS.md /root/.openclaw/workspace/TOOLS.md

# Auto-select model based on available API key (must run before config injection)
if [ -n "$OPENAI_API_KEY" ]; then
  openclaw models set openai/gpt-4o-mini 2>/dev/null || true
  echo "Model: openai/gpt-4o-mini"
elif [ -n "$ANTHROPIC_API_KEY" ]; then
  openclaw models set anthropic/claude-sonnet-4-6 2>/dev/null || true
  echo "Model: anthropic/claude-sonnet-4-6"
fi

# Inject Nevermined config AFTER models set (which rewrites the config)
node -e "
const fs = require('fs');
const p = '/root/.openclaw/openclaw.json';
const c = JSON.parse(fs.readFileSync(p, 'utf8'));
const key = Object.keys(c.plugins?.entries || {}).find(k => k === 'nevermined' || k === 'openclaw-plugin') || 'nevermined';
c.plugins = c.plugins || {};
c.plugins.entries = c.plugins.entries || {};
c.plugins.entries[key] = c.plugins.entries[key] || { enabled: true };
c.plugins.entries[key].config = Object.assign(c.plugins.entries[key].config || {}, {
  environment: 'sandbox',
  enablePaidEndpoint: true,
  agentEndpointPath: '/nevermined/agent',
  creditsPerRequest: 1,
  ...(process.env.NVM_SELLER_API_KEY ? { nvmApiKey: process.env.NVM_SELLER_API_KEY } : {}),
  ...(process.env.NVM_PLAN_ID ? { planId: process.env.NVM_PLAN_ID } : {}),
});
c.plugins.allow = ['openclaw-plugin'];
c.gateway = c.gateway || {};
c.gateway.mode = 'local';
c.gateway.auth = { mode: 'token', token: 'demo' };
c.gateway.trustedProxies = ['0.0.0.0/0'];
c.gateway.controlUi = { allowedOrigins: ['http://localhost:18789', 'http://localhost:18790'], allowInsecureAuth: true };
c.gateway.http = c.gateway.http || {};
c.gateway.http.endpoints = c.gateway.http.endpoints || {};
c.gateway.http.endpoints.chatCompletions = { enabled: true };
fs.writeFileSync(p, JSON.stringify(c, null, 2));
"

# Patch plugin: route auth + replace mock handler with local agent forwarding
node /opt/openclaw/patch-handler.js

echo "=== OpenClaw + Nevermined Demo (Seller) ==="
echo "Starting OpenClaw gateway on port 18789..."
exec openclaw gateway --bind lan
