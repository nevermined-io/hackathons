#!/usr/bin/env bash
# Deploy seller and buyer agents to AWS Bedrock AgentCore with Nevermined payments.
#
# Usage:
#   export SELLER_NVM_API_KEY=sandbox:...   # Seller's API key (builder/publisher)
#   export BUYER_NVM_API_KEY=sandbox:...    # Buyer's API key (subscriber)
#   export NVM_PLAN_ID=...                  # Seller's payment plan ID
#   export NVM_AGENT_ID=...                 # Seller's agent ID
#   export OPENAI_API_KEY=sk-...
#   ./scripts/deploy-agentcore.sh
#
# Optional env vars:
#   AWS_REGION          AWS region (default: us-west-2)
#   NVM_ENVIRONMENT     Nevermined environment (default: sandbox)
#   SKIP_SELLER         Set to 1 to skip seller deployment (reuses existing ARN)
#   SELLER_AGENT_ARN    Seller ARN (required when SKIP_SELLER=1)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SELLER_DIR="$REPO_ROOT/agents/seller-simple-agent"
BUYER_DIR="$REPO_ROOT/agents/buyer-simple-agent"

AWS_REGION="${AWS_REGION:-us-west-2}"
NVM_ENVIRONMENT="${NVM_ENVIRONMENT:-sandbox}"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# --- Prerequisites ---
check_prerequisites() {
    info "Checking prerequisites..."

    local missing=0

    # AWS CLI
    if ! command -v aws &>/dev/null; then
        err "AWS CLI not found. Install it: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
        missing=1
    fi

    # AWS identity
    if ! aws sts get-caller-identity &>/dev/null; then
        err "AWS credentials not configured. Run: aws configure"
        missing=1
    fi

    # AgentCore toolkit
    if ! command -v agentcore &>/dev/null; then
        err "AgentCore toolkit not found. Install it: pip install bedrock-agentcore"
        missing=1
    fi

    # Docker
    if ! docker info &>/dev/null 2>&1; then
        err "Docker is not running. Start Docker Desktop or the Docker daemon."
        missing=1
    fi

    if [[ $missing -ne 0 ]]; then
        err "Missing prerequisites. Fix the issues above and try again."
        exit 1
    fi

    ok "All prerequisites met"
}

# --- Environment variables ---
check_env_vars() {
    info "Checking environment variables..."

    # Try loading .env from repo root
    if [[ -f "$REPO_ROOT/.env" ]]; then
        info "Loading .env from $REPO_ROOT/.env"
        set -a
        # shellcheck disable=SC1091
        source "$REPO_ROOT/.env"
        set +a
    fi

    local missing=0

    for var in SELLER_NVM_API_KEY BUYER_NVM_API_KEY NVM_PLAN_ID NVM_AGENT_ID OPENAI_API_KEY; do
        if [[ -z "${!var:-}" ]]; then
            err "Required env var $var is not set"
            missing=1
        fi
    done

    if [[ $missing -ne 0 ]]; then
        err "Set the missing variables and try again."
        echo ""
        echo "  export SELLER_NVM_API_KEY=sandbox:...  # Seller's key (builder/publisher)"
        echo "  export BUYER_NVM_API_KEY=sandbox:...   # Buyer's key (subscriber)"
        echo "  export NVM_PLAN_ID=...                 # Seller's payment plan ID"
        echo "  export NVM_AGENT_ID=...                # Seller's agent ID"
        echo "  export OPENAI_API_KEY=sk-..."
        exit 1
    fi

    ok "Environment variables OK"
}

# --- Get AWS account ID ---
get_aws_account() {
    aws sts get-caller-identity --query Account --output text
}

# --- Setup .bedrock_agentcore.yaml from example ---
setup_yaml() {
    local agent_dir="$1"
    local agent_name="$2"
    local yaml_file="$agent_dir/.bedrock_agentcore.yaml"
    local yaml_example="$agent_dir/.bedrock_agentcore.yaml.example"

    if [[ -f "$yaml_file" ]]; then
        info "$agent_name: .bedrock_agentcore.yaml already exists, using existing config"
        return
    fi

    if [[ ! -f "$yaml_example" ]]; then
        err "$agent_name: No .bedrock_agentcore.yaml.example found. Run 'agentcore init' first."
        exit 1
    fi

    local account_id
    account_id="$(get_aws_account)"

    info "$agent_name: Creating .bedrock_agentcore.yaml from example (account=$account_id, region=$AWS_REGION)"
    sed -e "s/YOUR_AWS_ACCOUNT_ID/$account_id/g" \
        -e "s/YOUR_REGION/$AWS_REGION/g" \
        "$yaml_example" > "$yaml_file"

    ok "$agent_name: Config ready"
}

# --- Deploy an agent ---
deploy_agent() {
    local agent_dir="$1"
    local agent_name="$2"
    shift 2
    # Remaining args are --env KEY=VALUE pairs
    local env_args=("$@")

    info "$agent_name: Starting deployment..."
    cd "$agent_dir"

    agentcore deploy --auto-update-on-conflict "${env_args[@]}"

    ok "$agent_name: Deployed"
    cd "$REPO_ROOT"
}

# --- Extract agent ARN from agentcore status ---
get_agent_arn() {
    local agent_dir="$1"
    local agent_name="$2"

    cd "$agent_dir"

    # Try to get ARN from the yaml config (populated after deploy)
    local arn
    arn="$(grep 'agent_arn:' .bedrock_agentcore.yaml 2>/dev/null | head -1 | awk '{print $2}' | tr -d "'" | tr -d '"')"

    if [[ -n "$arn" && "$arn" != "null" ]]; then
        echo "$arn"
        cd "$REPO_ROOT"
        return
    fi

    # Fallback: try agentcore status
    arn="$(agentcore status "$agent_name" 2>/dev/null | grep -oE 'arn:aws:bedrock-agentcore:[^[:space:]]+' | head -1 || true)"

    cd "$REPO_ROOT"

    if [[ -n "$arn" ]]; then
        echo "$arn"
    else
        err "Could not extract ARN for $agent_name. Check 'agentcore status $agent_name'."
        exit 1
    fi
}


# ===========================================================================
# Main
# ===========================================================================

echo ""
echo "======================================"
echo "  AgentCore Deployment — Nevermined"
echo "======================================"
echo ""

check_prerequisites
check_env_vars

ACCOUNT_ID="$(get_aws_account)"
info "AWS Account: $ACCOUNT_ID | Region: $AWS_REGION"
echo ""

# --- Deploy Seller ---
SELLER_AGENT_ARN="${SELLER_AGENT_ARN:-}"

if [[ "${SKIP_SELLER:-}" == "1" ]]; then
    if [[ -z "$SELLER_AGENT_ARN" ]]; then
        err "SKIP_SELLER=1 but SELLER_AGENT_ARN is not set."
        exit 1
    fi
    info "Skipping seller deployment (using existing ARN)"
else
    info "=== Deploying Seller Agent ==="
    setup_yaml "$SELLER_DIR" "seller_agent"
    deploy_agent "$SELLER_DIR" "seller_agent" \
        --env "NVM_API_KEY=$SELLER_NVM_API_KEY" \
        --env "NVM_ENVIRONMENT=$NVM_ENVIRONMENT" \
        --env "NVM_PLAN_ID=$NVM_PLAN_ID" \
        --env "NVM_AGENT_ID=$NVM_AGENT_ID" \
        --env "OPENAI_API_KEY=$OPENAI_API_KEY"

    SELLER_AGENT_ARN="$(get_agent_arn "$SELLER_DIR" "seller_agent")"
fi

ok "Seller ARN: $SELLER_AGENT_ARN"
echo ""

# --- Deploy Buyer ---
info "=== Deploying Buyer Agent ==="
setup_yaml "$BUYER_DIR" "buyer_agent"
deploy_agent "$BUYER_DIR" "buyer_agent" \
    --env "NVM_API_KEY=$BUYER_NVM_API_KEY" \
    --env "NVM_ENVIRONMENT=$NVM_ENVIRONMENT" \
    --env "NVM_PLAN_ID=$NVM_PLAN_ID" \
    --env "NVM_AGENT_ID=$NVM_AGENT_ID" \
    --env "OPENAI_API_KEY=$OPENAI_API_KEY" \
    --env "SELLER_AGENT_ARN=$SELLER_AGENT_ARN"

BUYER_AGENT_ARN="$(get_agent_arn "$BUYER_DIR" "buyer_agent")"
ok "Buyer ARN: $BUYER_AGENT_ARN"
echo ""

# --- Summary ---
echo "======================================"
echo "  Deployment Complete"
echo "======================================"
echo ""
echo "  Seller ARN: $SELLER_AGENT_ARN"
echo "  Buyer ARN:  $BUYER_AGENT_ARN"
echo ""
echo "  View logs:"
echo "    agentcore logs seller_agent --follow"
echo "    agentcore logs buyer_agent --follow"
echo ""
echo "  Test with:"
echo "    ./scripts/test-agentcore.sh"
echo ""
echo "  Or invoke directly:"
echo "    aws bedrock-agentcore invoke-agent-runtime \\"
echo "      --agent-runtime-arn \"$BUYER_AGENT_ARN\" \\"
echo "      --qualifier DEFAULT \\"
echo "      --payload '{\"prompt\": \"Search for AI trends\"}' \\"
echo "      --region $AWS_REGION \\"
echo "      output.json"
echo ""
