# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- IntelliScada is a desktop HMI built with PyQt5. The main application is in ui-displayer.py; styling constants live in styles.py. Communication with external devices is via Modbus RTU (pymodbus) over serial ports (pyserial). Application/config state is stored in an encrypted file modbus_config.dat (cryptography.Fernet).

Common commands (Windows PowerShell)
- Create and activate a virtual environment
  - py -3 -m venv .venv
  - .\.venv\Scripts\Activate.ps1
- Install dependencies
  - pip install -r requirements.txt
- Run the app
  - python ui-displayer.py
- Linting
  - No lint tooling/config is checked in.
- Tests
  - No tests or test runner config is present.

High-level architecture
- UI layer (PyQt5)
  - Entry point and main window are in ui-displayer.py. UI uses QStackedWidget/tabs and multiple configuration dialogs:
    - CylinderHeadConfigDialog and MainBearingConfigDialog manage temperature alarm limits and relay outputs.
    - PressureGaugeConfigDialog and TemperatureGaugeConfigDialog manage per-gauge labels, limits, device IDs, coil addresses, and delays.
  - CustomSplashScreen and LoadingWorker provide a startup splash with staged progress updates before showing the main UI.
  - All widget styles are consolidated in styles.py as string constants (e.g., MAIN_WINDOW_STYLE, button and label styles).
- Device I/O
  - Serial port enumeration via serial.tools.list_ports; Modbus communication via pymodbus.client.ModbusSerialClient (RTU). Modbus device IDs, coil addresses, and gauge addresses are user-configurable via the dialogs above.
- Configuration and persistence
  - Encrypted config file: modbus_config.dat at the repo root. Helpers: get_encryption_key(), encrypt_config_data(), decrypt_config_data(), load_encrypted_config(), save_encrypted_config().
  - Alarm history is appended into the encrypted config (AlarmHistory) via add_alarm_to_history() and clear_alarm_from_history().
  - Industry profiles (marine, power_generation, industrial, custom) define default visibility for pressure/temperature gauges: get_industry_default_configurations(), get_current_industry_profile(), set_industry_profile().
  - Import/export of gauge visibility settings to JSON: export_gauge_visibility_config() and import_gauge_visibility_config(). Some dialogs also read/write a plain JSON file modbus_config.json if present for gauge-specific settings.
- Assets
  - SPLASH.png is used by the splash screen; additional assets under imgs/.

Repository notes for agents
- There is no build/packaging setup (e.g., PyInstaller) or CI config in the repo; run the app directly with Python after installing requirements.
- If modbus_config.dat is missing on first run, the UI code can generate a default config structure and may prompt to store initial admin parameters; subsequent runs read/write the encrypted file.
