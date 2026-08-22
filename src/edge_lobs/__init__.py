"""Project EDGE Leadership Observation Ledger.

This sibling package records immutable source observations and exposes
fail-closed MDM/outcome boundaries. It does not generate signals or perform
leadership research.
"""

from .errors import LobsError
from .ledger import (
    LedgerPaths,
    SealedBatch,
    import_observation_batch,
    rebuild_index,
    verify_ledger,
)
from .mdm import (
    derive_last_completed_session,
    read_mdm_status,
    validate_test_only_enrichment,
    validate_test_only_feature_inputs,
)
from .outcomes import (
    ALLOWED_HORIZONS,
    derive_first_permissible_outcome_session,
    derive_outcome_window,
    materialise_test_only_outcomes,
    validate_test_only_outcomes,
)
from .validation import (
    ValidationReport,
    validate_import_manifest_document,
    validate_observation_document,
)

__all__ = [
    "ALLOWED_HORIZONS",
    "LedgerPaths",
    "LobsError",
    "SealedBatch",
    "ValidationReport",
    "derive_first_permissible_outcome_session",
    "derive_last_completed_session",
    "derive_outcome_window",
    "import_observation_batch",
    "materialise_test_only_outcomes",
    "read_mdm_status",
    "rebuild_index",
    "validate_import_manifest_document",
    "validate_observation_document",
    "validate_test_only_enrichment",
    "validate_test_only_feature_inputs",
    "validate_test_only_outcomes",
    "verify_ledger",
]

