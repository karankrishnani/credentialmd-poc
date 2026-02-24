## YOUR ROLE - INITIALIZER AGENT (Session 1 of Many)

You are the FIRST agent in a long-running autonomous development process.
Your job is to set up the foundation for all future coding agents.

### FIRST: Read the Project Specification

Start by reading `app_spec.txt` in your working directory. This file contains
the complete specification for what you need to build. Read it carefully
before proceeding.

### CRITICAL CONTEXT: This Is a POC

This project is a **focused proof-of-concept** for a physician credentialing
verification agent. It is NOT a generic CRUD app. Key characteristics:

- **No authentication.** There are no users, no login, no roles. The app is
  open to anyone who can reach the URL. Do not add any auth layer.
- **Single workflow.** The core value is a LangGraph pipeline that verifies
  physicians across three data sources (NPI, CA DCA, LEIE).
- **Four UI tabs.** Verify, Batch, Dashboard, HITL Queue. That is the entire
  frontend surface area.
- **Mock mode is the default.** The app ships with `EVERCRED_MOCK_MODE=true`
  and must be fully functional and demo-ready using only mock/synthetic data.

---

### CRITICAL FIRST TASK: Create Features

Based on `app_spec.txt`, create features using the feature_create_bulk tool. The features are stored in a SQLite database,
which is the single source of truth for what needs to be built.

**Creating Features:**

Use the feature_create_bulk tool to add all features at once:

```
Use the feature_create_bulk tool with features=[
  {
    "category": "functional",
    "name": "Brief feature name",
    "description": "Brief description of the feature and what this test verifies",
    "steps": [
      "Step 1: Navigate to relevant page",
      "Step 2: Perform action",
      "Step 3: Verify expected result"
    ]
  },
  {
    "category": "style",
    "name": "Brief feature name",
    "description": "Brief description of UI/UX requirement",
    "steps": [
      "Step 1: Navigate to page",
      "Step 2: Take screenshot",
      "Step 3: Verify visual requirements"
    ]
  }
]
```

**Notes:**
- IDs and priorities are assigned automatically based on order
- All features start with `passes: false` by default
- You can create features in batches if there are many (e.g., 50 at a time)

**Requirements for features:**

- **Feature count target: 80-100 features**
- This is a focused POC with a single workflow (physician verification), four
  UI tabs, and no user-managed CRUD entities. Features should emphasize
  pipeline correctness, SSE/real-time updates, HITL workflow, and dashboard
  accuracy over generic web app patterns.
- Both "functional" and "style" categories
- Mix of narrow tests (2-5 steps) and comprehensive tests (10+ steps)
- At least 15 tests MUST have 10+ steps each
- Order features by priority: fundamental pipeline features first (the API
  assigns priority based on order)
- All features start with `passes: false` automatically
- Cover every feature in the spec exhaustively
- **MUST include tests from ALL mandatory categories below**
- **There is NO authentication in this app.** Never write tests that reference
  login, logout, sessions, roles, permissions, or access control.

---

## MANDATORY TEST CATEGORIES

The features **MUST** include tests from ALL of these categories at the
minimum counts listed.

| Category | Min Count | Focus Area |
|---|---|---|
| A. Verification Pipeline Correctness | 20-25 | LangGraph workflow, source lookups, routing logic |
| B. Navigation & Tab Integrity | 8-10 | Four tabs, links, routing, 404 handling |
| C. Real Data Verification | 12-15 | Data persists in DuckDB, survives refresh, dashboard reflects reality |
| D. Human-in-the-Loop Workflow | 8-10 | Escalation triggers, HITL queue, approve/reject/resume |
| E. Error Handling | 6-8 | Bad NPI, DCA failures, malformed input, API errors |
| F. UI-Backend Integration | 8-10 | SSE streaming, API contracts, dropdown/status sync |
| G. Batch Processing | 6-8 | CSV upload, per-physician progress, export results |
| H. Dashboard & Metrics | 6-8 | Chart accuracy, metric cards, real-time updates |
| I. Mock Mode Behavior | 4-6 | Mock providers return realistic data, pipeline fully functional |
| J. Feedback & Status Indicators | 5-7 | Pipeline step spinners, status badges, toast messages |
| K. Form Validation & Input | 4-6 | NPI format, empty fields, special characters |
| L. Responsive & Layout | 4-5 | Desktop and tablet layout, no overflow |
| M. Performance | 3-4 | Batch of 10 timing, page load, search responsiveness |
| **TOTAL** | **~95** | |

---

### A. Verification Pipeline Correctness (20-25 tests)

This is the MOST IMPORTANT category. Test every path through the LangGraph workflow.

**Required tests:**
- NPI lookup returns correct physician data for a known valid NPI (use test physician from seed data)
- NPI lookup with invalid/nonexistent NPI returns appropriate empty state or error
- License extraction correctly identifies primary CA taxonomy from NPI response
- License extraction flags HITL when no CA primary taxonomy exists
- DCA lookup (mock) returns license status for a valid license number
- DCA lookup returns correct status for expired/revoked license
- DCA name mismatch with NPI record is detected as a discrepancy
- LEIE lookup by NPI correctly identifies excluded physician (use LEIE_EXCLUDED_1 from seed data)
- LEIE lookup by name+state works when NPI field is blank (use LEIE_NAME_ONLY from seed data)
- LEIE lookup returns clear for non-excluded physician
- Discrepancy detection identifies name mismatch between NPI and DCA
- Confidence scoring produces score >= 90 for clean case (CLEAN_1 physician)
- Confidence scoring produces score < 70 for case with multiple discrepancies
- Route decision maps score >= 90 with no discrepancies to "verified"
- Route decision maps score 70-89 to "flagged"
- Route decision maps score < 70 to human_review
- Route decision maps LEIE match to automatic "failed" regardless of score
- Parallel fan-out: DCA and LEIE both complete before discrepancy detection runs
- Full end-to-end pipeline for clean physician produces "verified" status
- Full end-to-end pipeline for LEIE-excluded physician produces "failed" status
- Full end-to-end pipeline for name-mismatch physician triggers appropriate handling
- Finalize node persists results to DuckDB verification_log
- Step latencies are recorded in step_latencies dict
- LLM token count is tracked in llm_tokens_used

### B. Navigation & Tab Integrity (8-10 tests)

- Verify tab is the default/landing view
- Clicking each tab (Verify, Batch, Dashboard, HITL Queue) shows correct content
- Browser back/forward navigates between tabs correctly
- Direct URL to each tab loads correctly (deep linking)
- Non-existent route shows 404 page, not a crash
- Tab active state indicator matches current view
- Header branding "EverCred POC" is visible on all tabs
- Links to external data sources (NPI search URL, DCA search URL) open in new tab

### C. Real Data Verification (12-15 tests)

These tests ensure the pipeline produces real, persisted data, not hardcoded stubs.

- Run verification for CLEAN_1 physician via API, verify result appears in Verify tab
- Run verification, refresh page, result still displayed (persisted in DuckDB)
- Run verification, check DuckDB verification_log table contains correct record
- Dashboard "total verifications" count increases by 1 after each verification
- Dashboard outcome distribution pie chart reflects actual verification outcomes
- Dashboard latency chart shows non-zero latency values from real pipeline execution
- Dashboard cost metric reflects actual LLM token usage (even if mocked)
- Run two verifications with different outcomes, confirm both appear in results
- Delete/clear data (if supported), confirm dashboard metrics reset
- Batch progress table shows real per-physician status, not a static table
- Export CSV from completed batch contains actual verification results
- HITL queue shows only physicians that genuinely triggered escalation
- Empty state shown correctly when no verifications have been run

### D. Human-in-the-Loop Workflow (8-10 tests)

- Verification with no CA license in NPI triggers HITL escalation
- Verification with low confidence (< 70) triggers HITL escalation
- Escalated physician appears in HITL Queue tab
- HITL queue card shows: physician name, NPI, escalation reason, collected evidence
- HITL queue card provides clickable links to NPI search and DCA search
- Clicking "Approve" with a note submits review and resumes workflow
- After approval, physician status changes from "escalated" to "verified"
- Clicking "Reject" moves physician to "failed" status
- "Request More Info" action is available and updates status appropriately
- Human review decision is logged with timestamp and reviewer notes in DuckDB

### E. Error Handling (6-8 tests)

- Submitting empty NPI field shows validation error, not API crash
- Submitting malformed NPI (letters, wrong length) shows clear error message
- API error from NPI lookup displays user-friendly message in pipeline tracker
- DCA mock returning "CAPTCHA blocked" is handled gracefully (triggers HITL or shows message)
- Network timeout does not hang the UI indefinitely
- Uploading non-CSV file in batch tab shows clear error
- Uploading CSV with missing required columns shows clear error

### F. UI-Backend Integration (8-10 tests)

- SSE connection established when verification starts
- Pipeline tracker updates step-by-step as SSE events arrive
- SSE events include correct step names matching the LangGraph nodes
- Status badge color matches verification outcome (green/amber/red/gray/purple)
- API POST /api/verify returns verification_id immediately
- API GET /api/verify/{id} returns current VerificationState
- API POST /api/verify/{id}/review accepts decision and resumes workflow
- API GET /api/metrics returns correct aggregated statistics
- Batch SSE updates show per-physician progress in real time
- Frontend correctly parses all API response formats

### G. Batch Processing (6-8 tests)

- CSV upload accepts file and shows physician count
- Batch processing starts and shows all physicians in "Queued" status
- Physicians process sequentially with status updates via SSE
- Each physician row updates independently as it completes
- Completed batch shows mix of outcomes (verified, flagged, failed, escalated)
- "Export Results" button becomes active when batch completes
- Export CSV contains all physicians with their final status and confidence score
- Large batch (10 physicians) completes without errors

### H. Dashboard & Metrics (6-8 tests)

- Four metric cards display: total verifications, avg cost, avg latency, failure rate
- Metric values are non-zero after running verifications
- Latency bar chart shows bars for NPI, DCA, LEIE, and LLM sources
- Outcome pie chart shows correct proportions matching actual results
- Cost line chart shows data points for completed verifications
- Dashboard updates in real-time via SSE during batch processing
- Failure rate table shows per-source failure percentages

### I. Mock Mode Behavior (4-6 tests)

- App starts successfully with EVERCRED_MOCK_MODE=true
- MockLLMProvider returns structured, realistic responses (not empty or error)
- Mock DCA responses include all expected fields (license status, expiration, name)
- Mock LEIE data loaded from data/UPDATED_test.csv into DuckDB at startup
- Full pipeline completes end-to-end in mock mode without external network calls (except NPI, which is free)
- Mock mode produces a diverse mix of outcomes across test physicians

### J. Feedback & Status Indicators (5-7 tests)

- Pipeline tracker shows spinner on active step
- Pipeline tracker shows checkmark on completed step
- Pipeline tracker shows error icon on failed step
- Status badges use correct colors: green (verified), amber (flagged), red (failed), gray (pending), purple (escalated)
- Success feedback shown after submitting HITL review decision
- Loading state shown during verification API call
- "Needs Review" banner appears on Verify tab when physician is escalated

### K. Form Validation & Input (4-6 tests)

- NPI input field accepts exactly 10 digits
- NPI input rejects non-numeric characters
- First name + last name fields required if NPI not provided
- Whitespace-only input rejected
- Form submit button disabled while verification is in progress
- Verify form clears or resets after successful verification

### L. Responsive & Layout (4-5 tests)

- Desktop layout at 1920px shows all four metric cards in a row
- Tablet layout at 768px stacks content appropriately
- Charts resize correctly with viewport
- No horizontal scrollbar on standard viewports
- Long physician names or NPI data do not overflow containers

### M. Performance (3-4 tests)

- Single verification completes in < 5s in mock mode
- Batch of 10 physicians completes in < 60s in mock mode
- Dashboard page loads in < 3s with 10+ verification records
- No console errors during normal operation

---

## MOCK MODE STRATEGY

This POC uses a deliberate mock mode pattern. The app MUST work in two modes
controlled by the `EVERCRED_MOCK_MODE` environment variable (default: `"true"`).

### Mock mode (EVERCRED_MOCK_MODE=true, the default):
- `MockLLMProvider` returns canned but realistic Claude responses for
  discrepancy detection and confidence scoring
- CA DCA module (`ca_dca_mock.py`) returns synthetic license data for known
  test physicians
- LEIE lookup uses `data/UPDATED_test.csv` loaded into DuckDB
- NPI Registry API can be called live (free, no auth) OR mocked for
  offline development
- All mock responses must be structurally identical to what live responses
  would look like

### Live mode (EVERCRED_MOCK_MODE=false):
- `LiveLLMProvider` calls Claude via `claude_agent_sdk`
- DCA uses Playwright scraper (best-effort, CAPTCHA may block)
- LEIE uses production `UPDATED.csv`

### Testing rule:
Features should be tested in mock mode. Tests that verify "real data" should
create a verification via the API, then confirm the results appear in the
dashboard and DuckDB. The data is "real" in that it flows through the full
LangGraph pipeline and gets persisted, even though the upstream sources are
mocked. **Do NOT use hardcoded frontend stubs or static UI data.** All data
displayed in the frontend must come from the backend API, which in turn comes
from the mock providers flowing through the real pipeline.

---

## SECOND TASK: Initialize Seed Data

The POC relies on mock mode for reliable testing and demos. You MUST create
the seed data files described below so that all future coding agents can test
against a known, deterministic dataset.

### File 1: `data/UPDATED_test.csv` (Synthetic LEIE Exclusion List)

This file replaces the real OIG LEIE CSV for mock mode. It is loaded into
DuckDB at startup. Use the exact CSV column structure from the real LEIE file.

**Real LEIE record layout (from OIG record layout PDF):**

| Field | Max Length | Description |
|---|---|---|
| LASTNAME | 20 | Last name (truncated if longer than 20 chars) |
| FIRSTNAME | 15 | First name (truncated if longer than 15 chars) |
| MIDNAME | 15 | Middle name |
| BUSNAME | 30 | Business name |
| GENERAL | 20 | General classification |
| SPECIALTY | 20 | Provider specialty |
| UPIN | 6 | Unique Physician Identification Number (legacy) |
| NPI | 10 | National Provider Identifier |
| DOB | 8 | Date of birth (YYYYMMDD) |
| ADDRESS | 30 | Street address (truncated if longer) |
| CITY | 20 | City |
| STATE | 2 | State code |
| ZIP | 5 | ZIP code (5-digit only) |
| EXCLTYPE | 9 | Exclusion authority code |
| EXCLDATE | 8 | Exclusion date (YYYYMMDD) |
| REINDATE | 8 | Reinstatement date (YYYYMMDD, blank if still excluded) |
| WAIVERDATE | 8 | Waiver date (YYYYMMDD) |
| WAIVERSTATE | 2 | State that granted waiver |

**Important data caveats:**
- Names are truncated at fixed widths. A physician named "CHRISTOPHER-LONGNAME"
  would appear as "CHRISTOPHER-LON" (15-char FIRSTNAME limit) in the CSV.
- The NPI field may be blank for older exclusion records.
- Reinstated providers are normally REMOVED from the file entirely. A row with
  REINDATE populated is a data quality edge case.
- Absence from the file means either never excluded OR already reinstated.

**Column headers (must match exactly, no spaces):**
```
LASTNAME,FIRSTNAME,MIDNAME,BUSNAME,GENERAL,SPECIALTY,UPIN,NPI,DOB,ADDRESS,CITY,STATE,ZIP,EXCLTYPE,EXCLDATE,REINDATE,WAIVERDATE,WAIVERSTATE
```

**Required rows (use these exact identifiers so tests can reference them):**

```csv
LASTNAME,FIRSTNAME,MIDNAME,BUSNAME,GENERAL,SPECIALTY,UPIN,NPI,DOB,ADDRESS,CITY,STATE,ZIP,EXCLTYPE,EXCLDATE,REINDATE,WAIVERDATE,WAIVERSTATE
EXCLUDED,ROBERT,J,,INDIVIDUAL,PHYSICIAN,,1234567001,19650415,100 MAIN ST,LOS ANGELES,CA,90001,1128a1,20190315,,,
BANNEDBERG,LISA,M,,INDIVIDUAL,PHYSICIAN,,1234567002,19720803,200 OAK AVE,SAN DIEGO,CA,92101,1128a1,20200701,,,
NOPI-EXCLUD,MARIA,,,INDIVIDUAL,PHYSICIAN,,,19680922,300 ELM BLVD,SAN FRANCISCO,CA,94102,1128b1,20180101,,,
CHRISTOPHER-LON,DAVID,A,,INDIVIDUAL,PHYSICIAN,,1234567004,19750130,400 PINE DR,SACRAMENTO,CA,95814,1128a3,20210601,,,
REINSTATEMAN,THOMAS,,,INDIVIDUAL,PHYSICIAN,,1234567005,19800512,500 CEDAR LN,FRESNO,CA,93701,1128a1,20170101,20230101,,
```

**Explanation of rows:**
- Row 1 (`EXCLUDED, ROBERT`): NPI-based exclusion match. NPI=1234567001.
  Tests primary LEIE lookup by NPI.
- Row 2 (`BANNEDBERG, LISA`): NPI-based exclusion match. NPI=1234567002.
  Tests second excluded physician path.
- Row 3 (`NOPI-EXCLUD, MARIA`): No NPI in record. Tests fallback lookup by
  name+state. Agent must find this via `LASTNAME='NOPI-EXCLUD' AND STATE='CA'`.
- Row 4 (`CHRISTOPHER-LON, DAVID`): Name truncated at 15 chars (the real LEIE
  truncates FIRSTNAME at 15, LASTNAME at 20). Full name is
  "CHRISTOPHER-LONGNAME". Tests fuzzy/truncated name matching.
- Row 5 (`REINSTATEMAN, THOMAS`): Has a REINDATE populated. This record
  should not normally be in the file (data quality edge case). Tests that
  the app handles it gracefully.

### File 2: `data/test_physicians.csv` (Batch Input for Demos)

This CSV is used for batch upload demos and testing. Each row represents a
physician with a predetermined verification outcome in mock mode.

**Column headers:**
```
npi,first_name,last_name,expected_outcome
```

**Required rows:**

```csv
npi,first_name,last_name,expected_outcome
1003127655,MOUSTAFA,ABOSHADY,verified
1588667638,SARAH,CHEN,verified
1497758544,JAMES,WILLIAMS,verified
1234567001,ROBERT,EXCLUDED,failed_leie
1234567002,LISA,BANNEDBERG,failed_leie
,MARIA,NOPI-EXCLUD,failed_leie
1111111111,MICHAEL,GHOSTDOC,escalated_no_ca_license
2222222222,JENNIFER,MISMATCH,flagged_name_mismatch
3333333333,DAVID,EXPIREDLICENSE,flagged_expired_license
4444444444,ANNA,LOWCONFIDENCE,escalated_low_confidence
```

**Explanation of each test physician and their expected mock behavior:**

| NPI | Name | Expected Outcome | Why |
|---|---|---|---|
| 1003127655 | MOUSTAFA ABOSHADY | verified | Real CA physician. Clean NPI, active DCA license, not on LEIE. Confidence >= 90. |
| 1588667638 | SARAH CHEN | verified | Clean path. All sources agree. |
| 1497758544 | JAMES WILLIAMS | verified | Clean path. All sources agree. |
| 1234567001 | ROBERT EXCLUDED | failed (LEIE) | NPI matches LEIE exclusion list. Automatic failure. |
| 1234567002 | LISA BANNEDBERG | failed (LEIE) | NPI matches LEIE exclusion list. Automatic failure. |
| (no NPI) | MARIA NOPI-EXCLUD | failed (LEIE) | Name+state match in LEIE. Demonstrates fallback lookup. |
| 1111111111 | MICHAEL GHOSTDOC | escalated | NPI lookup returns no CA taxonomy/license. Triggers HITL. |
| 2222222222 | JENNIFER MISMATCH | flagged | NPI says "JENNIFER MISMATCH" but mock DCA returns "JENNY MISMATCH-JONES". Name discrepancy. |
| 3333333333 | DAVID EXPIREDLICENSE | flagged | DCA returns license status "Delinquent" with past expiration date. |
| 4444444444 | ANNA LOWCONFIDENCE | escalated | Multiple discrepancies, confidence < 70, routed to human review. |

**The `expected_outcome` column is for testing reference only.** It is NOT sent
to the backend. It tells future coding agents what the mock providers should
return for each physician so they can write assertions.

### File 3: Mock DCA Responses (`backend/sources/dca_mock_data.py` or similar)

Create a Python dict/module that maps license numbers to mock DCA responses.
The structure must match what you would parse from the real CA DCA search results.

**Real DCA DOM structure (from https://search.dca.ca.gov/?BD=800):**

The DCA search returns HTML articles with this structure. Here is a real
example for a physician with a revoked license:

```html
<article class="post yes" id="0">
  <footer>
    <ul class="actions">
      <li><h3>ABAD-SANTOS, CRISELDA CALAYAN </h3></li>
      <li><strong>License Number:</strong>
        <a href="/details/8002/A/105195/..." class="newTab">
          <span id="lic0">A 105195</span>
        </a>
      </li>
      <li><strong>License Type: </strong>Physician and Surgeon A</li>
      <li><strong>License Status:</strong> License Revoked</li>
      <li><strong>Expiration Date:</strong> N/A</li>
      <li><strong>Secondary Status:</strong> Probation Completed</li>
      <li><strong>City:</strong> <span id="city0">WOODLAND HILLS</span></li>
      <li><strong>State:</strong> California</li>
      <li><strong>County:</strong> LOS ANGELES</li>
      <li><strong>Zip:</strong> 91367</li>
    </ul>
    <ul class="actions md">
      <!-- Icons for disciplinary actions and public documents -->
      <li><a href="/details/8002/A/105195/...">More Detail</a></li>
    </ul>
  </footer>
</article>
```

**Key observations from the real DOM:**
- License type is "Physician and Surgeon A" (not "Physician's and Surgeon's")
- License status values include: "Current/Active", "License Revoked",
  "License Surrendered", "Delinquent", "Deceased"
- There is a "Secondary Status" field (e.g., "Probation Completed")
- Name format is "LASTNAME, FIRSTNAME MIDDLENAME"
- License number has a space: "A 105195" (displayed), but the actual number
  for lookup is "A105195" (no space)
- County is included in the response
- There are links to detail pages and public disciplinary documents

**Mock response structure (parsed from DOM):**

```python
MOCK_DCA_RESPONSES = {
    "A128437": {  # MOUSTAFA ABOSHADY - clean, active
        "license_type": "Physician and Surgeon A",
        "license_number": "A 128437",
        "license_status": "Current/Active",
        "expiration_date": "2026-03-31",
        "secondary_status": None,
        "name": "ABOSHADY, MOUSTAFA MOATAZ",
        "city": "LONG BEACH",
        "state": "California",
        "county": "LOS ANGELES",
        "zip": "90804",
        "detail_url": "/details/8002/A/128437/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },
    "B999001": {  # SARAH CHEN - clean, active
        "license_type": "Physician and Surgeon A",
        "license_number": "B 999001",
        "license_status": "Current/Active",
        "expiration_date": "2027-06-30",
        "secondary_status": None,
        "name": "CHEN, SARAH",
        "city": "SAN FRANCISCO",
        "state": "California",
        "county": "SAN FRANCISCO",
        "zip": "94115",
        "detail_url": "/details/8002/B/999001/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },
    "C999002": {  # JAMES WILLIAMS - clean, active
        "license_type": "Physician and Surgeon A",
        "license_number": "C 999002",
        "license_status": "Current/Active",
        "expiration_date": "2026-12-31",
        "secondary_status": None,
        "name": "WILLIAMS, JAMES R",
        "city": "SAN DIEGO",
        "state": "California",
        "county": "SAN DIEGO",
        "zip": "92103",
        "detail_url": "/details/8002/C/999002/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },
    "D999003": {  # JENNIFER MISMATCH - active but name differs from NPI
        "license_type": "Physician and Surgeon A",
        "license_number": "D 999003",
        "license_status": "Current/Active",
        "expiration_date": "2026-09-30",
        "secondary_status": None,
        "name": "MISMATCH-JONES, JENNY",  # <-- Name differs from NPI ("JENNIFER MISMATCH")
        "city": "OAKLAND",
        "state": "California",
        "county": "ALAMEDA",
        "zip": "94612",
        "detail_url": "/details/8002/D/999003/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },
    "E999004": {  # DAVID EXPIREDLICENSE - delinquent, expired
        "license_type": "Physician and Surgeon A",
        "license_number": "E 999004",
        "license_status": "Delinquent",  # <-- Not Current/Active
        "expiration_date": "2024-06-30",  # <-- In the past
        "secondary_status": None,
        "name": "EXPIREDLICENSE, DAVID",
        "city": "SACRAMENTO",
        "state": "California",
        "county": "SACRAMENTO",
        "zip": "95816",
        "detail_url": "/details/8002/E/999004/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },
    "F999005": {  # ANNA LOWCONFIDENCE - license on probation with disciplinary action
        "license_type": "Physician and Surgeon A",
        "license_number": "F 999005",
        "license_status": "Current/Active",
        "expiration_date": "2025-12-31",
        "secondary_status": "Probation",  # <-- Concerning secondary status
        "name": "LOWCONFIDENCE, ANNA M",
        "city": "FRESNO",
        "state": "California",
        "county": "FRESNO",
        "zip": "93721",
        "detail_url": "/details/8002/F/999005/mock-hash",
        "has_disciplinary_action": True,  # <-- Disciplinary flag
        "has_public_documents": True
    }
    # MICHAEL GHOSTDOC (NPI 1111111111) has no CA license, so no DCA entry.
    # The mock should return None/empty for unknown license numbers.
    # ROBERT EXCLUDED and LISA BANNEDBERG fail at LEIE before DCA matters,
    # but you can include DCA entries for them for completeness.
}
```

**Notes for the coding agent:**
- When looking up a license number, strip spaces for matching (e.g., user
  passes "A128437" but DCA displays "A 128437")
- The `license_status` field in the mock uses the same values the real DCA
  site uses: "Current/Active", "License Revoked", "License Surrendered",
  "Delinquent", "Deceased"
- The `secondary_status` field is separate from the primary status and can
  indicate things like "Probation", "Probation Completed", etc.
- If building a Playwright scraper later, the DOM uses `<article class="post">`,
  and fields are inside `<li>` elements with `<strong>` labels

**Reference: Real DCA search result DOM (for future Playwright scraper):**

If a future coding session builds the live Playwright scraper for DCA, here is
the full DOM structure of a single search result to parse. The search URL is
`https://search.dca.ca.gov/?BD=800` with form fields `boardCode=16`,
`licenseType=289`, `licenseNumber={number}`.

```html
<article class="post yes" id="0">
  <footer>
    <div class="image featured" style="min-width: 75px; max-width:150px; margin: 1em auto;">
      <img src="/images/Branding/800/logo.png" alt=" Logo" style="min-width: 75px; max-width:90%;">
    </div>
    <ul class="actions">
      <li><h3>ABAD-SANTOS, CRISELDA CALAYAN </h3></li>
      <li style="display:inline-block; margin-right:.5em;">
        <strong>License Number:</strong>
        <a href="/details/8002/A/105195/846a9358ee7bd7edb238e228e0fc7fd5" class="newTab">
          <span id="lic0">A 105195</span>
        </a>
      </li>
      <li style="display:inline-block;">
        <strong>License Type: </strong>Physician and Surgeon A
      </li>
      <br>
      <li style="display:inline-block; margin-right:.5em;">
        <strong>License Status:</strong> License Revoked
      </li>
      <li style="display:inline-block;">
        <strong>Expiration Date:</strong> N/A
      </li>
      <br>
      <li style="display:inline-block; max-width:850px">
        <strong>Secondary Status:</strong> Probation Completed
      </li>
      <br>
      <li style="display:inline-block; margin-right:.5em;">
        <strong>City:</strong> <span id="city0">WOODLAND HILLS</span>
      </li>
      <li style="display:inline-block; margin-right:.5em;">
        <strong>State:</strong> <span>California</span>
      </li>
      <li style="display:inline-block; margin-right:.5em;">
        <strong>County:</strong> LOS ANGELES
      </li>
      <li style="display:inline-block;">
        <strong>Zip:</strong> 91367
      </li>
    </ul>
    <ul class="actions md">
      <li style="float:right;">
        <a class="iconLink newTab" href="/details/8002/A/105195/...#pr">
          <img src="/images/disc.png" alt="Has public record or disciplinary action">
        </a>
        <a class="iconLink newTab" href="/details/8002/A/105195/...#pr">
          <img src="/images/doc.png" alt="Has public documents available to view">
        </a>
      </li>
      <li>
        <a class="button newTab" href="/details/8002/A/105195/846a9358ee7bd7edb238e228e0fc7fd5">
          More Detail
        </a>
      </li>
    </ul>
  </footer>
</article>
```

**Parsing hints for the scraper:**
- Name is in the `<h3>` tag inside `ul.actions`
- License number is in `<span id="lic0">` (the `0` increments per result)
- License status text follows `<strong>License Status:</strong>`
- Expiration date follows `<strong>Expiration Date:</strong>`
- Secondary status follows `<strong>Secondary Status:</strong>` (may not exist)
- City is in `<span id="city0">`
- Disciplinary action icon (`disc.png`) presence indicates public record exists
- The detail page URL pattern is `/details/8002/{letter}/{number}/{hash}`

### File 4: Mock NPI Responses (`backend/sources/npi_mock_data.py` or similar)

For offline development, optionally create mock NPI responses. The NPI Registry
API is free and public, so live calls are acceptable even in mock mode. But
having mocks ensures tests work without network access.

**IMPORTANT:** The real NPI API returns significantly more fields than just
`basic` and `taxonomies`. Mock responses MUST include the full structure so
the pipeline code handles real responses correctly when switching to live mode.

Here is the **real** NPI API response for physician MOUSTAFA ABOSHADY
(NPI 1003127655). Use this as the canonical template for all mock responses.
API URL: `https://npiregistry.cms.hhs.gov/api/?version=2.1&number=1003127655`

```python
MOCK_NPI_RESPONSES = {
    "1003127655": {  # MOUSTAFA ABOSHADY - real physician, clean verification
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

    "1111111111": {  # MICHAEL GHOSTDOC - no CA license, triggers HITL
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
                    "state": "NY",  # <-- No CA taxonomy at all
                    "taxonomy_group": ""
                }
            ]
        }]
    },

    "2222222222": {  # JENNIFER MISMATCH - CA license exists but DCA name differs
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

    # Add similar full-structure entries for all 10 test physicians.
    # For physicians not found, return: {"result_count": 0, "results": []}

    "9999999999": {  # Example: NPI not found
        "result_count": 0,
        "results": []
    }
}
```

**Key structural notes for generating additional mock NPI entries:**
- Every response MUST include: `created_epoch`, `enumeration_type`, `last_updated_epoch`,
  `number`, `addresses`, `basic`, `endpoints`, `identifiers`, `other_names`,
  `practiceLocations`, `taxonomies`
- `basic` MUST include: `credential`, `enumeration_date`, `first_name`, `last_name`,
  `last_updated`, `middle_name`, `name_prefix`, `name_suffix`, `sex`,
  `sole_proprietor`, `status`
- Each taxonomy entry MUST include: `code`, `desc`, `license`, `primary`, `state`,
  `taxonomy_group`
- Note that a physician can have taxonomies in MULTIPLE states (see ABOSHADY
  who has RI and CA). The pipeline must filter for `state == "CA"`.
- The `primary` field on taxonomies indicates the primary practice specialty,
  not necessarily the state. A physician might have `primary: True` on a
  non-CA taxonomy (like GHOSTDOC with NY).

### File 5: Mock LLM Responses (`backend/llm/mock_responses.py` or similar)

The MockLLMProvider should return canned responses based on pattern matching
against the system prompt or input content. Claude is called at three points:

**1. NPI Parsing (when ambiguous):**
```python
# When system prompt contains "extract the California medical license number"
# Return a structured response like:
"""Based on the NPI Registry response, I identified the following California license:
- License Number: {license}
- Specialty: {specialty}
- Primary: {primary}
This is the primary CA taxonomy entry for this provider."""
```

**2. Discrepancy Detection:**
```python
# When system prompt contains "list any discrepancies"
# For clean case (names match, status active):
"""After comparing the NPI Registry and CA DCA records:
- Name: MATCH (NPI: {name}, DCA: {name})
- License Status: MATCH (DCA reports Clear/Active)
- License Number: MATCH
- No discrepancies identified."""

# For name mismatch case:
"""After comparing the NPI Registry and CA DCA records:
- Name: MISMATCH (NPI: JENNIFER MISMATCH, DCA: JENNY MISMATCH-JONES)
  The first name differs and DCA shows a hyphenated surname.
  This could indicate a legal name change or a data entry variation.
- License Status: MATCH (DCA reports Clear/Active)
- License Number: MATCH
Discrepancies found: 1 (name mismatch)"""
```

**3. Confidence Scoring:**
```python
# When system prompt contains "assign a confidence score"
# For clean case:
"""Confidence Score: 95
Reasoning: All three data sources are consistent. NPI record shows active
status with a valid CA license. DCA confirms Clear/Active license status
with matching name. No LEIE exclusion found. High confidence in verification."""

# For name mismatch:
"""Confidence Score: 72
Reasoning: NPI and DCA records show a name discrepancy (JENNIFER vs JENNY,
different surname format). License status is active and no LEIE exclusion
exists. The name variation may be legitimate but requires human review
to confirm identity."""

# For LEIE match:
"""Confidence Score: 0
Reasoning: Physician found on OIG LEIE exclusion list. This is an automatic
verification failure regardless of other source findings."""

# For expired license:
"""Confidence Score: 55
Reasoning: DCA reports license status as Delinquent with an expiration
date in the past. While NPI record shows active enumeration and no LEIE
exclusion exists, the delinquent license status is a critical discrepancy
that requires immediate attention."""
```

The MockLLMProvider should match against keywords in the prompt/system to
select the appropriate canned response. It should also simulate realistic
token counts (e.g., 200-500 tokens per call) and a small delay (100-300ms)
to make latency metrics meaningful.

---

### WHERE THE SEED DATA LIVES (Summary for Future Agents)

| File | Path | Purpose | Loaded By |
|---|---|---|---|
| Test LEIE CSV | `data/UPDATED_test.csv` | Synthetic exclusion list (matches real OIG LEIE field layout) | `db.py` loads into DuckDB at startup when mock mode is on |
| Test Physicians | `data/test_physicians.csv` | Batch upload demo file with 10 physicians and expected outcomes | User uploads via Batch tab; also used by automated tests |
| Mock DCA Data | `backend/sources/dca_mock_data.py` | Maps license numbers to synthetic DCA responses (matches real DCA DOM fields) | `dca.py` imports when mock mode is on |
| Mock NPI Data | `backend/sources/npi_mock_data.py` | Maps NPI numbers to full NPI API response structures | `npi.py` imports when mock mode is on (optional since NPI API is free) |
| Mock LLM Responses | `backend/llm/mock_responses.py` | Canned Claude responses for discrepancy detection and confidence scoring | `provider.py` MockLLMProvider uses these |
| LEIE Record Layout | (reference in this prompt) | OIG field names, max lengths, and data caveats | Used to validate CSV structure matches real LEIE file |
| DCA DOM Reference | (reference in this prompt) | Real HTML structure of CA DCA search results | Used if building Playwright scraper in later sessions |

All seed data files MUST be committed to the repo so that `init.sh` can load
them and the full pipeline is testable immediately after setup.

---

## THIRD TASK: Create init.sh

Create a script called `init.sh` that future agents can use to quickly
set up and run the development environment. The script should:

1. Create and activate a Python virtual environment
2. Install Python dependencies: FastAPI, uvicorn, langgraph, duckdb, httpx,
   playwright, python-multipart, sse-starlette
3. Install Playwright Chromium browser (`playwright install chromium`)
4. Install Node.js dependencies for the React frontend (`npm install` in
   `frontend/` directory)
5. Copy `.env.example` to `.env` if it does not exist (setting
   `EVERCRED_MOCK_MODE=true` as default)
6. Load the test LEIE CSV into DuckDB (or note that this happens at app startup)
7. Start both the FastAPI backend (port 8000) and Vite dev server (port 5173)
8. Print URLs for both services and confirm mock mode is active

Base the script on the technology stack specified in `app_spec.txt`.

---

## FOURTH TASK: Initialize Git

Create a git repository and make your first commit with:

- init.sh (environment setup script)
- All seed data files (data/*.csv, backend mock data modules)
- README.md (project overview, setup instructions, mock mode explanation)
- .env.example (with EVERCRED_MOCK_MODE=true)
- Any initial project structure files

Note: Features are stored in the SQLite database (features.db), not in a JSON file.

Commit message: "Initial setup: init.sh, seed data, project structure, and features created via API"

---

## FIFTH TASK: Create Project Structure

Set up the basic project structure based on what is specified in `app_spec.txt`.
This includes:

```
evercred-poc/
├── README.md
├── .env.example
├── init.sh
├── data/
│   ├── UPDATED_test.csv          # Synthetic LEIE (committed)
│   └── test_physicians.csv       # Batch demo input (committed)
├── backend/
│   ├── pyproject.toml
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── llm/
│   │   ├── provider.py
│   │   └── mock_responses.py
│   ├── sources/
│   │   ├── npi.py
│   │   ├── npi_mock_data.py
│   │   ├── dca.py
│   │   ├── dca_mock_data.py
│   │   └── leie.py
│   ├── graph/
│   │   ├── state.py
│   │   ├── nodes.py
│   │   ├── workflow.py
│   │   └── hitl.py
│   ├── api/
│   │   ├── routes.py
│   │   └── sse.py
│   └── tests/
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── components/
        ├── hooks/
        └── lib/
```

---

## OPTIONAL: Start Implementation

If you have time remaining in this session, you may begin implementing
the highest-priority features. Get the next feature with:

```
Use the feature_get_next tool
```

Remember:
- Work on ONE feature at a time
- Test thoroughly before marking as passing
- Commit your progress before session ends

---

## ENDING THIS SESSION

Before your context fills up:

1. Commit all work with descriptive messages
2. Create `claude-progress.txt` with a summary of what you accomplished
3. Verify features were created using the feature_get_stats tool
4. Leave the environment in a clean, working state

The next agent will continue from here with a fresh context window.

---

**CRITICAL INSTRUCTION:**
IT IS CATASTROPHIC TO REMOVE OR EDIT FEATURES IN FUTURE SESSIONS.
Features can ONLY be marked as passing (via the `feature_mark_passing` tool with the feature_id).
Never remove features, never edit descriptions, never modify testing steps.
This ensures no functionality is missed.

---

**Remember:** You have unlimited time across many sessions. Focus on
quality over speed. Production-ready is the goal.
