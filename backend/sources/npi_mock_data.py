"""
Mock NPI Registry API Responses

This module contains synthetic NPI API responses for testing.
The structure exactly matches the real NPI Registry API response format.

API Documentation: https://npiregistry.cms.hhs.gov/api-page
API Endpoint: https://npiregistry.cms.hhs.gov/api/?version=2.1&number={npi}
"""

from typing import Dict, Any


MOCK_NPI_RESPONSES: Dict[str, Dict[str, Any]] = {
    # MOUSTAFA ABOSHADY - real physician, clean verification
    # Has CA primary taxonomy with license A128437
    "1003127655": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1277836466000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1521292439000",
            "number": "1003127655",
            "addresses": [
                {
                    "address_1": "5150 E PACIFIC COAST HWY",
                    "address_2": "SUITE 500",
                    "address_purpose": "MAILING",
                    "address_type": "DOM",
                    "city": "LONG BEACH",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "90804",
                    "state": "CA"
                },
                {
                    "address_1": "3751 KATELLA AVE",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "LOS ALAMITOS",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "907203113",
                    "state": "CA",
                    "telephone_number": "928-854-9603"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2010-06-29",
                "first_name": "MOUSTAFA",
                "last_name": "ABOSHADY",
                "last_updated": "2018-03-17",
                "middle_name": "MOATAZ",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "M",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [
                {
                    "address_1": "5580 NOTTINGHAM CT",
                    "address_2": "APT 104",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "DEARBORN",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "481264281",
                    "state": "MI",
                    "telephone_number": "508-494-6333"
                }
            ],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "LP02034",
                    "primary": False,
                    "state": "RI",
                    "taxonomy_group": ""
                },
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "A128437",
                    "primary": False,
                    "state": "CA",
                    "taxonomy_group": ""
                },
                {
                    "code": "208M00000X",
                    "desc": "Hospitalist",
                    "license": "A128437",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # SARAH CHEN - clean verification
    "1588667638": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1325376000000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1672531200000",
            "number": "1588667638",
            "addresses": [
                {
                    "address_1": "100 VAN NESS AVE",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "SAN FRANCISCO",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "94115",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2012-01-01",
                "first_name": "SARAH",
                "last_name": "CHEN",
                "last_updated": "2023-01-01",
                "middle_name": "",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "F",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "B999001",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # JAMES WILLIAMS - clean verification
    "1497758544": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1356998400000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1688169600000",
            "number": "1497758544",
            "addresses": [
                {
                    "address_1": "4000 FIFTH AVE",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "SAN DIEGO",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "92103",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2013-01-01",
                "first_name": "JAMES",
                "last_name": "WILLIAMS",
                "last_updated": "2023-07-01",
                "middle_name": "R",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "M",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207Q00000X",
                    "desc": "Family Medicine",
                    "license": "C999002",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # MICHAEL GHOSTDOC - no CA license, triggers HITL
    # Has only NY taxonomy, no CA at all
    "1111111111": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1104537600000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1590969600000",
            "number": "1111111111",
            "addresses": [
                {
                    "address_1": "100 BROADWAY",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "NEW YORK",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "10001",
                    "state": "NY"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2005-01-15",
                "first_name": "MICHAEL",
                "last_name": "GHOSTDOC",
                "last_updated": "2020-06-01",
                "middle_name": "",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "M",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "NY123456",
                    "primary": True,
                    "state": "NY",  # No CA taxonomy
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # JENNIFER MISMATCH - CA license but DCA name differs
    "2222222222": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1393632000000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1642204800000",
            "number": "2222222222",
            "addresses": [
                {
                    "address_1": "500 GRAND AVE",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "OAKLAND",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "94612",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2014-03-01",
                "first_name": "JENNIFER",
                "last_name": "MISMATCH",
                "last_updated": "2022-01-15",
                "middle_name": "",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "F",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "D999003",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # DAVID EXPIREDLICENSE - CA license is delinquent
    "3333333333": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1420070400000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1651363200000",
            "number": "3333333333",
            "addresses": [
                {
                    "address_1": "700 CAPITOL MALL",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "SACRAMENTO",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "95816",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2015-01-01",
                "first_name": "DAVID",
                "last_name": "EXPIREDLICENSE",
                "last_updated": "2022-05-01",
                "middle_name": "",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "M",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "E999004",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # ANNA LOWCONFIDENCE - multiple issues, triggers low confidence
    "4444444444": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1451606400000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1672531200000",
            "number": "4444444444",
            "addresses": [
                {
                    "address_1": "2000 FRESNO ST",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "FRESNO",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "93721",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2016-01-01",
                "first_name": "ANNA",
                "last_name": "LOWCONFIDENCE",
                "last_updated": "2023-01-01",
                "middle_name": "M",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "F",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "F999005",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # ROBERT EXCLUDED - will fail LEIE check
    "1234567001": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1262304000000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1577836800000",
            "number": "1234567001",
            "addresses": [
                {
                    "address_1": "100 MAIN ST",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "LOS ANGELES",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "90001",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2010-01-01",
                "first_name": "ROBERT",
                "last_name": "EXCLUDED",
                "last_updated": "2020-01-01",
                "middle_name": "J",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "M",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "G999006",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # LISA BANNEDBERG - will fail LEIE check
    "1234567002": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1293840000000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1609459200000",
            "number": "1234567002",
            "addresses": [
                {
                    "address_1": "200 OAK AVE",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "SAN DIEGO",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "92101",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2011-01-01",
                "first_name": "LISA",
                "last_name": "BANNEDBERG",
                "last_updated": "2021-01-01",
                "middle_name": "M",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "F",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "H999007",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # NPI NOT FOUND case
    "8888888888": {
        "result_count": 0,
        "results": []
    },

    # CLEAN VERIFICATION - second test case
    "1234567890": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1388534400000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1704067200000",
            "number": "1234567890",
            "addresses": [
                {
                    "address_1": "1000 WILSHIRE BLVD",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "LOS ANGELES",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "90017",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2014-01-01",
                "first_name": "JOHN",
                "last_name": "CLEANDOC",
                "last_updated": "2024-01-01",
                "middle_name": "P",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "M",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207Q00000X",
                    "desc": "Family Medicine",
                    "license": "G999999",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # LEIE EXCLUDED - has valid CA license but NPI is in LEIE database
    "5555555555": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1262304000000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1577836800000",
            "number": "5555555555",
            "addresses": [
                {
                    "address_1": "123 MAIN ST",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "LOS ANGELES",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "90001",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2010-01-01",
                "first_name": "DOCTOR",
                "last_name": "EXCLUDED",
                "last_updated": "2020-01-01",
                "middle_name": "E",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "M",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "D555555",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # LICENSE REVOKED - CA license maps to DCA revoked status
    "6666666666": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1325376000000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1609459200000",
            "number": "6666666666",
            "addresses": [
                {
                    "address_1": "500 REVOKED BLVD",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "SAN FRANCISCO",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "94102",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2012-01-01",
                "first_name": "CRISELDA",
                "last_name": "ABAD-SANTOS",
                "last_updated": "2021-01-01",
                "middle_name": "CALAYAN",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "F",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "A666666",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # DCA SOURCE UNAVAILABLE - license triggers SourceUnavailableError from DCA mock
    "7777777777": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1388534400000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1672531200000",
            "number": "7777777777",
            "addresses": [
                {
                    "address_1": "777 UNAVAILABLE ST",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "OAKLAND",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "94612",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2014-01-01",
                "first_name": "UNAVAILABLE",
                "last_name": "DCADOC",
                "last_updated": "2023-01-01",
                "middle_name": "",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "M",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "B777777",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # MARIA NOPI-EXCLUD - LEIE excluded but has NO NPI in LEIE record
    # This tests the name+state fallback lookup in LEIE
    # LEIE record: NOPI-EXCLUD,MARIA,,,INDIVIDUAL,PHYSICIAN,,,19680922,...,CA,...
    # The NPI field in LEIE is blank, so lookup by NPI won't match,
    # but lookup by name+state should match
    "1234560001": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1325376000000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1672531200000",
            "number": "1234560001",
            "addresses": [
                {
                    "address_1": "300 ELM BLVD",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "SAN FRANCISCO",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "94102",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2012-01-01",
                "first_name": "MARIA",
                "last_name": "NOPI-EXCLUD",
                "last_updated": "2023-01-01",
                "middle_name": "",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "F",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "license": "M123456",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    # LICENSE DELINQUENT - CA license maps to DCA delinquent status
    "9999999999": {
        "result_count": 1,
        "results": [{
            "created_epoch": "1420070400000",
            "enumeration_type": "NPI-1",
            "last_updated_epoch": "1704067200000",
            "number": "9999999999",
            "addresses": [
                {
                    "address_1": "999 DELINQUENT DR",
                    "address_purpose": "LOCATION",
                    "address_type": "DOM",
                    "city": "SACRAMENTO",
                    "country_code": "US",
                    "country_name": "United States",
                    "postal_code": "95814",
                    "state": "CA"
                }
            ],
            "basic": {
                "credential": "M.D.",
                "enumeration_date": "2015-01-01",
                "first_name": "ALICE",
                "last_name": "JONES",
                "last_updated": "2024-01-01",
                "middle_name": "MARIE",
                "name_prefix": "--",
                "name_suffix": "--",
                "sex": "F",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "endpoints": [],
            "identifiers": [],
            "other_names": [],
            "practiceLocations": [],
            "taxonomies": [
                {
                    "code": "207Q00000X",
                    "desc": "Family Medicine",
                    "license": "C999999",
                    "primary": True,
                    "state": "CA",
                    "taxonomy_group": ""
                }
            ]
        }]
    },
}


def get_mock_npi_response(npi: str) -> Dict[str, Any]:
    """
    Get mock NPI API response for an NPI number.

    Args:
        npi: The 10-digit NPI number

    Returns:
        Dict matching NPI Registry API response format
    """
    # Return empty result if not in mock data
    if npi not in MOCK_NPI_RESPONSES:
        return {
            "result_count": 0,
            "results": []
        }
    return MOCK_NPI_RESPONSES[npi]
