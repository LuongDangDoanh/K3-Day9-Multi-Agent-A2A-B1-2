"""Stable workflow configuration.

The model name intentionally lives in source code, not in ``.env``, as required
by the assignment. Business decisions remain deterministic and are always
verified against CSV data. The OpenAI model is only used when ``--llm-audit``
is explicitly enabled.
"""

from decimal import Decimal

MODEL_PROVIDER = "openai"
MODEL_NAME = "gpt-4o-mini"
MODEL_PARAMETER_SIZE = "undisclosed_by_provider"
MODEL_PARAMETER_LIMIT_B = 10
MODEL_PARAMETER_COMPLIANCE = "not_verifiable"
POLICY_VERSION = "EC_POLICY_V1"
PROTOCOL_VERSION = "1.0"
CONTRACT_VERSION = "1.0"
MONEY_QUANTUM = Decimal("0.01")
PAYMENT_TOLERANCE = Decimal("0.10")
CONFIDENCE = Decimal("1.00")
MAX_LLM_AUDIT_TOKENS = 180
