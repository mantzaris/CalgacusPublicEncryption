class Stage1Error(Exception):
    category = "implementation_failure"


class FramingError(Stage1Error):
    category = "framing_failure"


class AuthenticationError(Stage1Error):
    category = "cryptographic_authentication_failure"


class ReplayError(Stage1Error):
    category = "replay_rejection"


class TransportError(Stage1Error):
    category = "tokenization_serialization_drift"


class RankError(Stage1Error):
    category = "rank_numerical_divergence"


class CapacityError(Stage1Error):
    category = "capacity_exhaustion"


class BudgetError(Stage1Error):
    category = "timeout_resource_failure"
