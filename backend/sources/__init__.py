"""Data source modules for NPI, DCA, and LEIE lookups."""

from sources.npi import (
    lookup_npi,
    NPILookupResult,
    NPILookupError,
    NPINotFoundError,
    NPIInactiveError,
    NoStateLicenseError,
    MultipleLicensesError,
    SourceUnavailableError as NPISourceUnavailableError,
)

from sources.dca import (
    lookup_dca_license,
    DCALookupResult,
    SourceUnavailableError as DCASourceUnavailableError,
)

from sources.leie import (
    lookup_leie,
    LEIELookupResult,
    is_excluded,
    format_exclusion_reason,
)

__all__ = [
    # NPI
    "lookup_npi",
    "NPILookupResult",
    "NPILookupError",
    "NPINotFoundError",
    "NPIInactiveError",
    "NoStateLicenseError",
    "MultipleLicensesError",
    "NPISourceUnavailableError",
    # DCA
    "lookup_dca_license",
    "DCALookupResult",
    "DCASourceUnavailableError",
    # LEIE
    "lookup_leie",
    "LEIELookupResult",
    "is_excluded",
    "format_exclusion_reason",
]
