## Overview
- Add a red "Alarm Bar" at the top of the main window that appears when an alarm is triggered and shows a horizontally scrolling (marquee) message explaining the cause.
- Use a lightweight global signal bus so existing alarm logic can notify the UI without tight coupling.

## Current Alarm Logic (where triggers happen)
- Pressure gauge: `CircularPressureGauge.check_and_write_alarm` writes coil and records history in `ui-displayer.py:4813–4888` (coil write `4855–4859`, history `4875–4883`).
- Temperature gauge: `CircularTemperatureGauge.check_and_write_alarm` writes coil and records history in `ui-displayer.py:5403–5474` (coil write `5444–5448`, history `5463–5471`).
- Cylinder Head bars: coil write in `CylinderHeadTab.check_and_write_alarm` `ui-displayer.py:3302–3375`.
- Main Bearing bars: coil write in `MainBearingTab.check_and_write_alarm` `ui-displayer.py:4228–4301`.
- Alarm history helpers: `add_alarm_to_history` and `clear_alarm_from_history` in `ui-displayer.py:357–393` and `ui-displayer.py:395–426`.
- History tab displays alarm records: `HistoryTab` `ui-displayer.py:11534–11892`.

## Design
- Create `AlarmBus(QObject)` with signals `alarm_triggered(dict)` and `alarm_cleared(dict)`.
- Emit `alarm_triggered` and `alarm_cleared` inside the history helper functions so all existing alarm sources automatically notify the UI.
- Implement `AlarmBar(QWidget)` with:
  - Red gradient background, compact height.
  - A `QLabel` whose text scrolls left-to-right using a `QTimer` for marquee effect.
  - A small queue to rotate through multiple alarm messages; auto-hide if idle.
- Integrate `AlarmBar` at the top of `HMIWindow` layout, initially hidden. Show and start marquee on trigger; optionally hide after N seconds or when cleared.

## Implementation Steps
1. Add `AlarmBus` near the history helpers:
   - Define `class AlarmBus(QObject)` with `alarm_triggered = pyqtSignal(dict)` and `alarm_cleared = pyqtSignal(dict)`.
   - Instantiate a singleton `ALARM_BUS` accessible across the module.
2. Update history helpers to emit:
   - In `add_alarm_to_history(...)` (`ui-displayer.py:357–393`), after saving, emit `ALARM_BUS.alarm_triggered.emit(alarm_record)`.
   - In `clear_alarm_from_history(...)` (`ui-displayer.py:395–426`), after saving, emit `ALARM_BUS.alarm_cleared.emit({ 'gauge_name': gauge_name, 'alarm_type': alarm_type })`.
3. Implement `AlarmBar(QWidget)`:
   - Props: `queue` (list of dicts), `timer` for marquee, `label` for text.
   - Methods: `push_alarm(record)`, `start_marquee()`, `step_marquee()`, `show_next()`, `hide_if_idle()`.
   - Format message: `🚨 <gauge_type> - <gauge_name>: <alarm_type> — value=<value><unit>, limit=<limit><unit>`.
4. Wire `AlarmBar` into `HMIWindow`:
   - Create `self.alarm_bar = AlarmBar()` in `HMIWindow.__init__` (`ui-displayer.py:15472+`).
   - Insert it at the very top: `self.main_layout.insertWidget(0, self.alarm_bar, 0)` with fixed height and `setVisible(False)`.
   - Connect signals: `ALARM_BUS.alarm_triggered.connect(self.alarm_bar.push_alarm)` and `ALARM_BUS.alarm_cleared.connect(self.alarm_bar.hide_if_idle)` (or decrement active counter).
5. Optional: Add a dismiss button on the bar for manual hide; style consistent with existing CSS.

## Integration Points
- HMI layout: add the widget just before `control_bar_container` addition (`ui-displayer.py:15770–15773`).
- Keep existing logic untouched for coil writes; all emissions happen via the history helpers already invoked by gauges.

## Message Format
- Example: `🚨 Pressure - Fuel Oil Pressure Inlet: HIGH — value=12.3bar, limit=10.0bar`.
- Use data from `alarm_record` in `add_alarm_to_history` (`timestamp`, `gauge_name`, `gauge_type`, `alarm_type`, `value`, `limit`, `unit`).

## Verification
- Use built-in Test Mode in `HMIWindow` to generate values (`ui-displayer.py:15787–15893` for pressures; `15795–15817` for cylinder/bearing temps; `15819–15829` for engine temps) so alarms occur naturally.
- Confirm:
  - Coil writes continue to succeed (existing printouts).
  - History tab shows triggered records (unchanged).
  - Alarm Bar appears when alarms trigger, scrolls text, and hides when queue is empty or after timeout.

## Notes
- Framework is PyQt5 (`ui-displayer.py:3–11`); follow existing styling constants (e.g., `TOPBAR_STYLE`, `CONTENT_STACK_STYLE`).
- All updates are bounded within `ui-displayer.py`; no external dependencies added.
- Performance impact is minimal: marquee uses a short interval `QTimer` and small strings; signals are in-process.