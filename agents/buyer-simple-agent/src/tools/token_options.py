"""Build x402 token options with card-delegation support for fiat plans."""

from payments_py import Payments
from payments_py.x402.resolve_scheme import resolve_scheme
from payments_py.x402.types import CardDelegationConfig, X402TokenOptions

from ..log import get_logger, log

_logger = get_logger("buyer.token")

# Defaults for card-delegation
_SPENDING_LIMIT_CENTS = 10_000  # $100
_DURATION_SECS = 604_800  # 7 days


def build_token_options(payments: Payments, plan_id: str) -> X402TokenOptions:
    """Resolve scheme and build X402TokenOptions, including delegation config for fiat plans."""
    scheme = resolve_scheme(payments, plan_id)
    log(_logger, "TOKEN", "SCHEME", f"plan={plan_id[:12]} scheme={scheme}")

    if scheme != "nvm:card-delegation":
        return X402TokenOptions(scheme=scheme)

    # Fiat plan — fetch enrolled payment methods and build delegation config
    methods = payments.delegation.list_payment_methods()
    if not methods:
        log(_logger, "TOKEN", "ERROR", "no payment methods enrolled")
        raise ValueError(
            "Fiat plan requires a payment method but none are enrolled. "
            "Add a card at https://nevermined.app first."
        )

    pm = methods[0]
    log(_logger, "TOKEN", "CARD", f"using {pm.brand} *{pm.last4}")

    return X402TokenOptions(
        scheme=scheme,
        delegation_config=CardDelegationConfig(
            provider_payment_method_id=pm.id,
            spending_limit_cents=_SPENDING_LIMIT_CENTS,
            duration_secs=_DURATION_SECS,
            currency="usd",
        ),
    )
