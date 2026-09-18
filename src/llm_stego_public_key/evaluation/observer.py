from ..errors import FramingError
from ..cryptography.hpke import deserialize


def public_format_test(extracted: str) -> dict:
    """Pure public syntax/length check; no keys and no tag authentication."""
    try:
        data = deserialize(extracted)
    except FramingError:
        return {"format_valid": False, "authenticated": False}
    return {"format_valid": True, "envelope_bytes": len(data), "authenticated": False}


def observe_text(codec, transmitted_utf8: bytes, cover_context: str) -> dict:
    """O2 input boundary: public codec/text/context, never evaluator records or keys."""
    from ..errors import Stage1Error

    try:
        extracted = codec.extract(transmitted_utf8, cover_context)
        return dict(public_format_test(extracted), extracted_text=extracted)
    except Stage1Error as exc:
        return {
            "format_valid": False,
            "authenticated": False,
            "failure_category": exc.category,
            "error": str(exc),
        }
