from ..errors import FramingError
from ..cryptography.hpke import deserialize


def public_format_test(extracted: str) -> dict:
    """Pure public syntax/length check; no keys and no tag authentication."""
    try:
        data = deserialize(extracted)
    except FramingError:
        return {"format_valid": False, "authenticated": False}
    return {"format_valid": True, "envelope_bytes": len(data), "authenticated": False}
