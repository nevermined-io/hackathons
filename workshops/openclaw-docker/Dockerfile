FROM node:22-slim

# Install system dependencies required by OpenClaw installer
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install OpenClaw CLI (skip onboarding wizard and interactive prompts)
ENV OPENCLAW_NO_PROMPT=1
ENV OPENCLAW_NO_ONBOARD=1
RUN curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard --no-prompt

# Add openclaw to PATH (installed globally via npm)
ENV PATH="/root/.local/bin:/root/.openclaw/bin:${PATH}"

# Update to latest version
RUN openclaw update --yes 2>/dev/null || true

# Install Nevermined plugin from npm registry and its dependencies
RUN openclaw plugins install @nevermined-io/openclaw-plugin && \
    cd /root/.openclaw/extensions/openclaw-plugin && npm install

# Create config directory
RUN mkdir -p /root/.openclaw

# Copy config, workspace files, and entrypoints
COPY openclaw.json openclaw-buyer.json /opt/openclaw/
COPY TOOLS.md /opt/openclaw/TOOLS.md
COPY patch-handler.js /opt/openclaw/patch-handler.js
COPY entrypoint.sh entrypoint-buyer.sh /opt/openclaw/
RUN chmod +x /opt/openclaw/entrypoint.sh /opt/openclaw/entrypoint-buyer.sh

WORKDIR /root

EXPOSE 18789

ENTRYPOINT ["/opt/openclaw/entrypoint.sh"]
