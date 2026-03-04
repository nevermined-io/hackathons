#!/usr/bin/env bash
# Test deployed AgentCore agents (buyer + seller).
#
# Usage:
#   ./scripts/test-agentcore.sh
#
# Optional env vars:
#   BUYER_AGENT_ARN    Buyer agent ARN (auto-detected from config if not set)
#   SELLER_AGENT_ARN   Seller agent ARN (auto-detected from config if not set)
#   AWS_REGION         AWS region (default: us-west-2)
#   PROMPT             Test prompt (default: "Search for AI market trends")

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SELLER_DIR="$REPO_ROOT/agents/seller-simple-agent"
BUYER_DIR="$REPO_ROOT/agents/buyer-simple-agent"

AWS_REGION="${AWS_REGION:-us-west-2}"
PROMPT="${PROMPT:-Search for AI market trends}"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# --- Extract ARN from yaml config ---
get_arn_from_config() {
    local agent_dir="$1"
    local yaml_file="$agent_dir/.bedrock_agentcore.yaml"

    if [[ ! -f "$yaml_file" ]]; then
        return 1
    fi

    local arn
    arn="$(grep 'agent_arn:' "$yaml_file" 2>/dev/null | head -1 | awk '{print $2}' | tr -d "'" | tr -d '"')"

    if [[ -n "$arn" && "$arn" != "null" ]]; then
        echo "$arn"
    else
        return 1
    fi
}

# --- Resolve ARNs ---
resolve_arns() {
    if [[ -z "${SELLER_AGENT_ARN:-}" ]]; then
        info "Detecting seller ARN from config..."
        SELLER_AGENT_ARN="$(get_arn_from_config "$SELLER_DIR" 2>/dev/null || true)"
        if [[ -z "$SELLER_AGENT_ARN" ]]; then
            err "Could not detect seller ARN. Set SELLER_AGENT_ARN or deploy first."
            exit 1
        fi
    fi

    if [[ -z "${BUYER_AGENT_ARN:-}" ]]; then
        info "Detecting buyer ARN from config..."
        BUYER_AGENT_ARN="$(get_arn_from_config "$BUYER_DIR" 2>/dev/null || true)"
        if [[ -z "$BUYER_AGENT_ARN" ]]; then
            err "Could not detect buyer ARN. Set BUYER_AGENT_ARN or deploy first."
            exit 1
        fi
    fi

    ok "Seller: $SELLER_AGENT_ARN"
    ok "Buyer:  $BUYER_AGENT_ARN"
}

# --- Check agent status ---
check_status() {
    local name="$1"
    local dir="$2"

    info "Checking $name status..."
    cd "$dir"
    agentcore status "$name" 2>&1 | head -20 || warn "Could not get status for $name"
    cd "$REPO_ROOT"
    echo ""
}

# --- Invoke agent ---
invoke_buyer() {
    info "Invoking buyer agent with prompt: \"$PROMPT\""
    echo ""

    local output_file
    output_file="$(mktemp /tmp/agentcore-test-XXXXXX.json)"

    aws bedrock-agentcore invoke-agent-runtime \
        --agent-runtime-arn "$BUYER_AGENT_ARN" \
        --qualifier DEFAULT \
        --payload "{\"prompt\": \"$PROMPT\"}" \
        --region "$AWS_REGION" \
        "$output_file"

    echo ""
    ok "Response saved to $output_file"
    echo ""
    echo "--- Response ---"
    cat "$output_file"
    echo ""
    echo "--- End ---"
    echo ""
}

# --- Tail logs ---
tail_logs() {
    local agent_name="$1"
    local agent_dir="$2"

    info "Tailing $agent_name logs (Ctrl+C to stop)..."
    cd "$agent_dir"
    agentcore logs "$agent_name" --follow || warn "Could not tail logs for $agent_name"
    cd "$REPO_ROOT"
}

# ===========================================================================
# Main
# ===========================================================================

echo ""
echo "======================================"
echo "  AgentCore Test — Nevermined"
echo "======================================"
echo ""

resolve_arns
echo ""

# Check status of both agents
check_status "seller_agent" "$SELLER_DIR"
check_status "buyer_agent" "$BUYER_DIR"

# Invoke the buyer
invoke_buyer

# Ask about logs
echo "View logs with:"
echo "  agentcore logs seller_agent --follow"
echo "  agentcore logs buyer_agent --follow"
echo ""
