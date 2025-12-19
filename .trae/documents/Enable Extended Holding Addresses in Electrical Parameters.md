## Goal
Enable reading electrical parameters from extended holding-register addresses (e.g., `450001`) without changing protocol (keep existing `pymodbus` with serial/RTU). Automatically compute offsets for both 5-digit (`40001`) and 6-digit (`450001`) inputs.

## Current Code Overview
- Modbus client: `pymodbus.client.ModbusSerialClient` (`ui-displayer.py:25`).
- Electrical tab: `class ElectricalParameterTab` (`ui-displayer.py:10754`).
- Reads (holding/input/coils/discretes): `read_modbus_value(self, param)` (`ui-displayer.py:11223`).
- Electrical-tab read path: `read_electrical_param(self, param, modbus_client)` (`ui-displayer.py:12322`).
- Bar widgets read: `read_individual_bar_data` (`ui-displayer.py:3393`).
- UI config forms for electrical groups (address widgets, register type): voltage/current/power dialogs around (`ui-displayer.py:9027–9110`, `10250–10255`, `10424–10429`, `10693–10699`).

## Logic Change
- Holding registers only:
  - If `addr >= 400001`, use `offset = addr - 400001`.
  - Else if `addr >= 40001`, use `offset = addr - 40001`.
  - Else reject (must start with 4).
  - Validate `offset <= 65535`; otherwise error.
- Keep existing logic for other function codes (input/coils/discretes).

## Implementation Steps
1. Create helper for holding offset
   - Add `calc_holding_offset(addr: int) -> int` in a utilities section near existing read helpers.
   - Behavior: compute dual-scheme offset; raise a user-facing error if invalid or `> 65535`.

2. Update electrical-tab read path
   - In `read_electrical_param(self, param, modbus_client)` (`ui-displayer.py:12322–12358`):
     - When `param['reg_type'] == 'holding'`, replace `addr - 40001` with `calc_holding_offset(addr)`.
     - Use consistent unit argument with `pymodbus` (keep the project’s existing choice, e.g., `slave=dev_id`).
     - Preserve scaling for input-register values; do not change non-holding logic.

3. Update general read path used by electrical tab
   - In `read_modbus_value(self, param)` (`ui-displayer.py:11223–11275`):
     - For holding registers, use `calc_holding_offset(addr)` instead of `addr - 40001`.
     - Ensure error handling aligns with the electrical-tab UX (show message or safe fallback).

4. Update bar widget read (if used by electrical parameters)
   - In `read_individual_bar_data` (`ui-displayer.py:3393–3401`):
     - When `reg_type == 'holding'`, compute offset with `calc_holding_offset(addr)`.

5. UI configuration updates (electrical parameter dialogs)
   - Address input for holding-register items:
     - Allow 6-digit entries by increasing maximum to `465536` (i.e., `400001 + 65535`).
     - Keep default min at `40001`.
     - If the widget is `QSpinBox`, set conditional max based on register type selection; otherwise switch to `QLineEdit` with numeric validator and range check.
   - Do not change input-register ranges unless requested; leave as is.
   - Update any range checks that currently restrict holding addresses to `< 50000` to accept extended values.

6. Validation and UX
   - On read: if `offset > 65535`, display a clear error (standard Modbus limit) and skip the request.
   - Ensure consistent device/unit ID argument usage across all calls (`slave` vs `device_id`) to match the client in use.
   - Tooltips/labels: mention that electrical parameters support extended holding addresses up to `465536`.

## Constraints
- Standard Modbus offset is 16-bit (`0–65535`). Max extended holding address is `465536`.
- Leave protocol and timing unchanged (serial/RTU, current client config).
- No changes to input registers, coils, or discretes beyond existing behavior.

## Verification Plan
- Manual tests in Electrical Parameters tab:
  - Enter `40001` (holding) → offset `0` → read succeeds.
  - Enter `450001` (holding) → offset `50000` → read succeeds.
  - Enter `470001` → offset `70000` → error due to limit.
- Confirm reads and displayed values update correctly for Voltage/Current/Power groups.
- Validate configuration persistence for 6-digit addresses (save/load cycle).

## Acceptance Criteria
- Electrical parameters can be configured and read from 5-digit and 6-digit holding addresses.
- UI accepts `40001…465536` for holding-register items and enforces Modbus limits.
- All reads in the electrical tab use the smart offset logic without breaking existing non-holding behavior.
