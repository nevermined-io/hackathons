"""Check NVM plan balance - queries the Nevermined API for credit balance."""

from payments_py import Payments

from ..log import get_logger, log


_logger = get_logger("buyer.balance")


def check_balance_impl(payments: Payments, plan_id: str) -> dict:
    """Check the credit balance for a given plan.

    Args:
        payments: Initialized Payments SDK instance.
        plan_id: The seller's plan ID to check balance for.

    Returns:
        dict with status, content (for Strands), balance, and isSubscriber.
    """
    log(_logger, "BALANCE", "CHECK", f"plan={plan_id[:12]}")
    try:
        result = payments.plans.get_plan_balance(plan_id)

        balance = result.balance
        is_subscriber = result.is_subscriber
        log(_logger, "BALANCE", "RESULT",
            f"balance={balance} subscriber={is_subscriber}")

        lines = [
            f"Plan ID: {plan_id}",
            f"Balance: {balance} credits",
            f"Subscriber: {'Yes' if is_subscriber else 'No'}",
        ]

        if not is_subscriber:
            lines.append(
                "\nYou are not yet subscribed to this plan. "
                "The x402 payment flow will handle subscription "
                "automatically when you make a purchase."
            )

        return {
            "status": "success",
            "content": [{"text": "\n".join(lines)}],
            "balance": balance,
            "isSubscriber": is_subscriber,
        }

    except Exception as e:
        log(_logger, "BALANCE", "ERROR", f"failed: {e}")
        return {
            "status": "error",
            "content": [{"text": f"Failed to check balance: {e}"}],
            "balance": 0,
            "isSubscriber": False,
        }
