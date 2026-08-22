"""Frozen version-one contracts for leadership/source observation documents.

The contracts are deliberately narrow.  Optional scientific content is
represented by an explicit JSON ``null`` under an exact key rather than by
silently changing a record's shape.
"""

from __future__ import annotations

import re


OBSERVATION_SCHEMA_VERSION = "edge.leadership_observation_batch.v1"
IMPORT_MANIFEST_SCHEMA_VERSION = "edge.leadership_import_manifest.v1"
VALIDATION_REPORT_SCHEMA_VERSION = "edge.lobs.validation_report.v1"

AWAITING_PROVENANCE = "AWAITING_RAW_SOURCES_AND_PROVENANCE"
READY_FOR_IMPORT = "READY_FOR_IMPORT"
VALIDATION_STATUSES = frozenset({AWAITING_PROVENANCE, READY_FOR_IMPORT})

CAPTURE_MODES = frozenset({"PROSPECTIVE", "RETROSPECTIVE"})
ALLOWED_SOURCE_DERIVATIONS = frozenset({"SOURCE_DERIVED", "USER_DERIVED"})
FORBIDDEN_SOURCE_DERIVATIONS = frozenset(
    {"MODEL_DERIVED", "MDM_DERIVED", "RESEARCH_DERIVED"}
)
HUMAN_OBSERVATION_SUBTYPE = "CONTEMPORANEOUS_HUMAN_OBSERVATION"

OBSERVATION_BATCH_ID_RE = re.compile(
    r"^EDGE-LOBS-(?P<date>[0-9]{8})-[A-Z0-9][A-Z0-9_-]*$"
)
OBSERVATION_ID_RE = re.compile(r"^EDGE-LOBS-OBS-[A-Z0-9][A-Z0-9_-]*$")
GENERIC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,15}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

OBSERVATION_DOCUMENT_KEYS = frozenset(
    {
        "schema_version",
        "observation_batch_id",
        "observation_date",
        "information_cutoff_timestamp",
        "information_cutoff_timezone",
        "capture_mode",
        "recorded_at",
        "source_ids",
        "extractor",
        "validation_status",
        "supersedes_batch_id",
        "market",
        "instruments",
        "groups",
        "stocks",
        "futures_snapshot",
        "macro_context",
        "notes",
    }
)

EXTRACTOR_KEYS = frozenset({"actor_type", "actor_id", "method", "version"})
EXTRACTOR_ACTOR_TYPES = frozenset({"USER", "MODEL", "PARSER", "SYSTEM"})

OBSERVATION_ARRAY_NAMES = (
    "market",
    "instruments",
    "groups",
    "stocks",
    "futures_snapshot",
    "macro_context",
)

COMMON_RECORD_KEYS = frozenset(
    {
        "observation_id",
        "timestamp",
        "timezone",
        "derivation_type",
        "observation_subtype",
        "source_text",
        "source_id",
        "source_location",
        "confidence_of_extraction",
        "capture_mode",
        "notes",
    }
)

RECORD_KEYS = {
    "market": COMMON_RECORD_KEYS | frozenset({"field", "metric", "state"}),
    "instruments": COMMON_RECORD_KEYS
    | frozenset(
        {
            "instrument",
            "instrument_kind",
            "security_id",
            "identity_resolution_status",
            "observation_type",
            "state",
        }
    ),
    "groups": COMMON_RECORD_KEYS
    | frozenset(
        {
            "group_id",
            "group_name",
            "group_type",
            "taxonomy_origin",
            "source_classification",
            "classification_basis",
        }
    ),
    "stocks": COMMON_RECORD_KEYS
    | frozenset(
        {
            "ticker",
            "security_id",
            "identity_resolution_status",
            "company_name",
            "group_id",
            "source_role",
            "setup_family",
            "setup_state",
            "relative_strength_description",
            "moving_average_description",
            "price_action_description",
            "volume_description",
        }
    ),
    "futures_snapshot": COMMON_RECORD_KEYS
    | frozenset(
        {
            "instrument",
            "value",
            "change_absolute",
            "change_percent",
            "observation_timestamp",
            "timestamp_precision",
            "source_type",
        }
    ),
    "macro_context": COMMON_RECORD_KEYS
    | frozenset({"context_type", "title", "description"}),
}

EXTRACTION_CONFIDENCES = frozenset({"HIGH", "MEDIUM", "LOW", "UNKNOWN"})
TIMESTAMP_PRECISIONS = frozenset(
    {
        "EXACT_SECOND",
        "EXACT_MINUTE",
        "APPROXIMATE_MINUTE",
        "APPROXIMATE_TIME",
        "DATE_ONLY",
        "UNKNOWN",
    }
)

MARKET_FIELDS = frozenset(
    {
        "MARKET_TREND_STATUS",
        "MOVING_AVERAGE_STATE",
        "MARKET_DESCRIPTION",
        "SHORT_TERM_STATE",
        "INTERMEDIATE_TERM_STATE",
        "LONG_TERM_STATE",
        "RISK_BIAS",
        "BREADTH_DESCRIPTION",
        "LEADERSHIP_DESCRIPTION",
        "WEAKNESS_DESCRIPTION",
        "EVENT_RISK_DESCRIPTION",
        "CURRENT_VIEW",
        "ADDITIONAL_THOUGHT",
        "OTHER",
    }
)
MARKET_STATES = frozenset(
    {
        "FOUR_OF_FOUR_UP",
        "UP",
        "DOWN",
        "BUILDING",
        "BUILDING_UP_RIGHT_SIDE",
        "RANGE_BUILDING",
        "CONSOLIDATION",
        "UPTREND",
        "DOWNTREND",
        "MIXED",
        "UNKNOWN",
        "OTHER",
    }
)

INSTRUMENT_KINDS = frozenset(
    {
        "INDEX",
        "ETF",
        "CRYPTO_ETF",
        "SECTOR_ETF",
        "INDUSTRY_ETF",
        "THEME_ETF",
        "FUTURE",
        "VOLATILITY_INDEX",
        "OTHER",
    }
)
INSTRUMENT_OBSERVATION_TYPES = frozenset(
    {"PRICE_ACTION", "SETUP_STATE", "TREND_STATE", "COMMENTARY", "OTHER"}
)
INSTRUMENT_STATES = frozenset(
    {
        "BREAKOUT",
        "RECONFIRMATION",
        "BUILDING",
        "COILING",
        "RANGE_BUILDING",
        "HANDLE",
        "PULLBACK",
        "WEAKENING",
        "DOWNTREND",
        "UPTREND",
        "FAILED_BREAKOUT",
        "DOWN_OFF_LEVEL",
        "OTHER",
    }
)

GROUP_TYPES = frozenset(
    {"SECTOR", "INDUSTRY", "SUBINDUSTRY", "THEME", "CUSTOM_GROUP"}
)
TAXONOMY_ORIGINS = frozenset({"SOURCE_TAXONOMY", "USER_TAXONOMY"})
GROUP_CLASSIFICATIONS = frozenset(
    {
        "STRONG",
        "LEADING",
        "IMPROVING",
        "EMERGING",
        "PERKING_UP",
        "NEUTRAL",
        "MIXED",
        "WEAK",
        "DETERIORATING",
        "UNKNOWN",
        "OTHER",
    }
)

IDENTITY_RESOLUTION_STATUSES = frozenset(
    {"UNRESOLVED", "RESOLVED_POINT_IN_TIME"}
)
STOCK_SOURCE_ROLES = frozenset(
    {
        "LEADERSHIP",
        "WATCHLIST",
        "FOCUS_LIST",
        "KEY_MOVE",
        "WEAKNESS",
        "COMMENTARY",
        "OTHER",
    }
)
STOCK_SETUP_STATES = frozenset(
    {
        "RANGE_BREAKOUT_WATCH",
        "RANGE_RE_BREAKOUT_WATCH",
        "RE_BREAKOUT_WATCH",
        "FLAG_BREAKOUT_WATCH",
        "BREAKOUT",
        "RECONFIRMATION",
        "INSIDE_DAY",
        "DOUBLE_INSIDE",
        "PULLBACK",
        "PIVOT_TEST",
        "FOLLOW_THROUGH",
        "REVERSAL",
        "FAILED_BREAKOUT",
        "OTHER",
    }
)

MACRO_CONTEXT_TYPES = frozenset(
    {"ARTICLE_METADATA", "MACRO_EVENT", "SOURCE_CONTEXT", "OTHER"}
)

IMPORT_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "observation_batch_id",
        "observation_path",
        "capture_mode",
        "validation_status",
        "sources",
        "notes",
    }
)
SOURCE_ENTRY_KEYS = frozenset(
    {
        "source_id",
        "source_type",
        "source_name",
        "source_title",
        "source_original_filename",
        "source_identity",
        "path",
        "source_capture_timestamp",
        "source_publication_timestamp",
        "source_publication_date",
        "timestamp_precision",
        "timezone",
        "capture_mode",
        "historical_reconstruction",
        "contemporaneous_capture_attested",
        "expected_sha256",
        "parser_version",
        "notes",
    }
)
SOURCE_TYPES = frozenset(
    {
        "PDF",
        "SCREENSHOT",
        "IMAGE",
        "TEXT",
        "WEB_CAPTURE",
        "WEB_METADATA",
        "ANALYST_NOTE",
        "STRUCTURED_MANUAL_OBSERVATION",
        "OTHER",
    }
)
USER_DERIVED_SOURCE_TYPES = frozenset(
    {"ANALYST_NOTE", "STRUCTURED_MANUAL_OBSERVATION"}
)

# Field-name matching is intentionally independent of source-text values.  A
# contemporaneous phrase such as "failed breakout" remains valid source text.
FORBIDDEN_OUTCOME_KEYS = frozenset(
    {
        "forward_return",
        "forward_returns",
        "excess_return",
        "excess_returns",
        "mfe",
        "mae",
        "maximum_favourable_excursion",
        "maximum_favorable_excursion",
        "maximum_adverse_excursion",
        "maximum_close",
        "minimum_close",
        "time_to_threshold",
        "outcome",
        "outcomes",
        "outcome_label",
        "target",
        "target_label",
        "future_value",
        "subsequent_success",
        "subsequent_return",
        "current_constituent_membership",
        "current_membership",
    }
)
