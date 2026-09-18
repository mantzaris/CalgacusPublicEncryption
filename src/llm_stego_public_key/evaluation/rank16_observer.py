"""Public frame observer: no key, private records or tag authentication input."""
import hashlib
from ..errors import CapacityError, FramingError, TransportError


def observe_rank16(codec, transmitted_utf8, public_profile, cover_context):
    try:
        envelope = codec.extract(transmitted_utf8, public_profile, cover_context)
        return {'format_valid': True, 'authenticated': False, 'envelope_bytes': len(envelope),
                'envelope_sha256': hashlib.sha256(envelope).hexdigest()}
    except (CapacityError, FramingError, TransportError) as exc:
        return {'format_valid': False, 'authenticated': False,
                'failure_category': exc.category, 'error': str(exc)}
