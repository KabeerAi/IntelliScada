import sys
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QMessageBox, QStackedWidget, QGridLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout, QScrollArea,
    QTabWidget, QInputDialog, QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplashScreen, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QRect, QRectF, QPointF, QEvent, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QLinearGradient, QRadialGradient, QConicalGradient, QPixmap
import math
import random
import json
import os
import time
import string
import base64
import hashlib
import webbrowser
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pymodbus.client import ModbusSerialClient
from styles import *

def generate_admin_password():
    """Generate a random 8-character password with letters, numbers, and special characters"""
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#&"
    
    # Ensure at least one character from each category
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special_chars)
    ]
    
    # Fill remaining 4 characters with random selection from all categories
    all_chars = lowercase + uppercase + digits + special_chars
    for _ in range(4):
        password.append(random.choice(all_chars))
    
    # Shuffle the password to randomize positions
    random.shuffle(password)
    
    return ''.join(password)

# ============== Configuration Encryption/Decryption ==============
def get_encryption_key():
    """Generate encryption key from a fixed salt and application identifier"""
    # Use a fixed salt and application-specific password for key derivation
    # This ensures the same key is generated every time for this application
    password = b"MohsinElectronicsHMI2025"  # Application-specific password
    salt = b"ModbusHMISalt123"  # Fixed salt for consistency
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

def encrypt_config_data(data):
    """Encrypt configuration data (dict) and return encrypted bytes"""
    try:
        # Convert dict to JSON string
        json_str = json.dumps(data, indent=4)
        json_bytes = json_str.encode('utf-8')
        
        # Encrypt the data
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(json_bytes)
        
        return encrypted_data
    except Exception as e:
        print(f"Error encrypting config data: {e}")
        return None

def decrypt_config_data(encrypted_data):
    """Decrypt configuration data and return dict"""
    try:
        # Decrypt the data
        key = get_encryption_key()
        fernet = Fernet(key)
        decrypted_bytes = fernet.decrypt(encrypted_data)
        
        # Convert back to dict
        json_str = decrypted_bytes.decode('utf-8')
        data = json.loads(json_str)
        
        return data
    except Exception as e:
        print(f"Error decrypting config data: {e}")
        return None

def save_encrypted_config(config_data, file_path="modbus_config.dat"):
    """Save configuration data in encrypted format"""
    try:
        encrypted_data = encrypt_config_data(config_data)
        if encrypted_data:
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
            return True
    except Exception as e:
        print(f"Error saving encrypted config: {e}")
    return False

def load_encrypted_config(file_path="modbus_config.dat"):
    """Load and decrypt configuration data"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            return decrypt_config_data(encrypted_data)
    except Exception as e:
        print(f"Error loading encrypted config: {e}")
    return None


def add_alarm_to_history(gauge_name, gauge_type, alarm_type, value, limit, unit):
    """Add an alarm event to the history"""
    try:
        config = load_encrypted_config()
        if config is None:
            config = {}
        
        # Initialize AlarmHistory if it doesn't exist
        if "AlarmHistory" not in config:
            config["AlarmHistory"] = []
        
        # Create alarm record
        alarm_record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "gauge_name": gauge_name,
            "gauge_type": gauge_type,  # "Pressure", "Temperature", "Cylinder Head", "Main Bearing"
            "alarm_type": alarm_type,  # "HIGH", "LOW"
            "value": value,
            "limit": limit,
            "unit": unit,
            "status": "TRIGGERED"
        }
        
        # Add to history (newest first)
        config["AlarmHistory"].insert(0, alarm_record)
        
        # Keep only last 1000 records to prevent file from growing too large
        if len(config["AlarmHistory"]) > 1000:
            config["AlarmHistory"] = config["AlarmHistory"][:1000]
        
        # Save updated config
        save_encrypted_config(config)
        print(f"✅ Alarm recorded: {gauge_name} - {alarm_type} ({value}{unit} vs limit {limit}{unit})")
        
    except Exception as e:
        print(f"Error adding alarm to history: {e}")


def clear_alarm_from_history(gauge_name, alarm_type):
    """Mark an alarm as cleared in the history"""
    try:
        config = load_encrypted_config()
        if config is None or "AlarmHistory" not in config:
            return
        
        # Create cleared record
        alarm_record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "gauge_name": gauge_name,
            "gauge_type": "",
            "alarm_type": alarm_type,
            "value": 0,
            "limit": 0,
            "unit": "",
            "status": "CLEARED"
        }
        
        # Add to history
        config["AlarmHistory"].insert(0, alarm_record)
        
        # Keep only last 1000 records
        if len(config["AlarmHistory"]) > 1000:
            config["AlarmHistory"] = config["AlarmHistory"][:1000]
        
        # Save updated config
        save_encrypted_config(config)
        print(f"✅ Alarm cleared: {gauge_name} - {alarm_type}")
        
    except Exception as e:
        print(f"Error clearing alarm from history: {e}")


# ---------------- Custom Splash Screen ----------------
class CustomSplashScreen(QSplashScreen):
    """Custom splash screen with progress indicator and professional styling"""
    
    def __init__(self, pixmap_path):
        # Load the splash image
        pixmap = QPixmap(pixmap_path)
        if pixmap.isNull():
            # Create a default splash if image not found
            pixmap = QPixmap(800, 600)
            pixmap.fill(QColor(30, 30, 30))
        
        super().__init__(pixmap, Qt.WindowStaysOnTopHint)
        
        # Initialize progress tracking
        self.progress = 0
        self.status_message = "Initializing..."
        
        # Set up the splash screen properties
        self.setEnabled(False)  # Prevent user interaction
        
        # Center the splash screen
        self.center_on_screen()
    
    def center_on_screen(self):
        """Center the splash screen on the primary screen"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        splash_geometry = self.geometry()
        
        x = (screen_geometry.width() - splash_geometry.width()) // 2
        y = (screen_geometry.height() - splash_geometry.height()) // 2
        
        self.move(x, y)
    
    def show_message(self, message, progress=None):
        """Update the status message and optionally the progress"""
        self.status_message = message
        if progress is not None:
            self.progress = min(100, max(0, progress))
        
        # Force a repaint to show the message immediately
        self.repaint()
        QApplication.processEvents()
    
    def drawContents(self, painter):
        """Custom drawing for progress bar and status text"""
        # Set up painter
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get splash screen dimensions
        rect = self.rect()
        
        # Draw progress bar at the very bottom border (full width)
        progress_height = 8
        progress_rect = QRect(
            0,  # Start from left edge
            rect.height() - progress_height,  # At the very bottom
            rect.width(),  # Full width of splash screen
            progress_height
        )
        
        # Background of progress bar (dark semi-transparent)
        painter.fillRect(progress_rect, QColor(0, 0, 0, 120))
        
        # Progress fill
        if self.progress > 0:
            fill_width = int((progress_rect.width() * self.progress) / 100)
            fill_rect = QRect(progress_rect.x(), progress_rect.y(), fill_width, progress_height)
            gradient = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
            gradient.setColorAt(0, QColor(0, 150, 255))
            gradient.setColorAt(1, QColor(0, 200, 255))
            painter.fillRect(fill_rect, gradient)
        
        # Draw status message above the progress bar
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 11, QFont.Normal))
        
        text_margin = 40
        text_rect = QRect(
            text_margin,
            rect.height() - 35,  # Position above the progress bar
            rect.width() - (text_margin * 2),
            20
        )
        
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.status_message)
        
        # Draw progress percentage
        progress_text = f"{self.progress}%"
        painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, progress_text)


class LoadingWorker(QThread):
    """Worker thread to simulate loading process"""
    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal()
    
    def run(self):
        """Simulate application loading with realistic progress updates"""
        loading_steps = [
            (10, "Loading configuration files..."),
            (25, "Initializing Modbus communication..."),
            (40, "Setting up user interface..."),
            (60, "Loading gauge configurations..."),
            (75, "Preparing data displays..."),
            (90, "Finalizing initialization..."),
            (100, "Ready to start!")
        ]
        
        for progress, message in loading_steps:
            self.progress_updated.emit(progress, message)
            # Simulate realistic loading time
            time.sleep(0.3)
        
        self.finished.emit()


class PasswordDisplayDialog(QDialog):
    """Custom dialog to display generated password with copy functionality"""
    def __init__(self, password, parent=None):
        super().__init__(parent)
        self.password = password
        self.setWindowTitle("Admin Password Generated")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMaximumWidth(500)
        
        # Ensure dialog appears on top of splash screen
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.raise_()
        self.activateWindow()
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Icon and title
        title_layout = QHBoxLayout()
        
        # Info icon
        icon_label = QLabel("🔑")
        icon_label.setStyleSheet("font-size: 32px; background: transparent;")
        title_layout.addWidget(icon_label)
        
        # Title text
        title_label = QLabel("Admin Password Generated")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: rgb(0, 191, 255);
            margin-left: 10px;
            background: transparent;
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Message
        message_label = QLabel(
            "A new admin password has been generated for first-time setup:\n\n"
            "Please save this password securely. You will need it to access "
            "system configuration and admin functions."
        )
        message_label.setStyleSheet("""
            font-size: 13px;
            color: rgb(200, 200, 200);
            line-height: 1.4;
            background: transparent;
        """)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Password display with copy button
        password_layout = QHBoxLayout()
        
        # Password field
        self.password_field = QLineEdit(password)
        self.password_field.setReadOnly(True)
        self.password_field.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                color: rgb(255, 255, 100);
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Courier New', monospace;
                letter-spacing: 2px;
            }
        """)
        password_layout.addWidget(self.password_field)
        
        # Copy button
        copy_btn = QPushButton("📋 COPY")
        copy_btn.setMinimumWidth(100)
        copy_btn.setMinimumHeight(45)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 150, 200, 0.8);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background: rgba(0, 180, 230, 0.9);
            }
            QPushButton:pressed {
                background: rgba(0, 120, 170, 0.7);
            }
        """)
        copy_btn.clicked.connect(self.copy_password)
        password_layout.addWidget(copy_btn)
        
        layout.addLayout(password_layout)
        
        # Status label for copy feedback
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            color: rgb(0, 255, 100);
            font-size: 12px;
            font-weight: bold;
            background: transparent;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # OK button
        ok_btn = QPushButton("OK")
        ok_btn.setMinimumWidth(120)
        ok_btn.setMinimumHeight(40)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 200, 100, 0.8);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: rgba(0, 230, 120, 0.9);
            }
            QPushButton:pressed {
                background: rgba(0, 170, 80, 0.7);
            }
        """)
        ok_btn.clicked.connect(self.accept)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Set dialog style
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(25, 35, 50), stop:1 rgb(15, 25, 40));
                border: none;
                border-radius: 12px;
            }
        """)
    
    def copy_password(self):
        """Copy password to clipboard and show feedback"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.password)
        
        # Show feedback
        self.status_label.setText("✓ Password copied to clipboard!")
        
        # Clear feedback after 2 seconds
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

def create_default_modbus_config(admin_password):
    """Create complete default modbus_config.json structure with all necessary data"""
    # Create default cylinder head bars configuration (18 bars total)
    cylinder_head_bars = {}
    
    # Left section (9 bars) - addresses 0-8, device 2
    for i in range(9):
        cylinder_head_bars[str(i)] = {
            "label": f"T{i+1}",
            "address": i,
            "device_id": 2,
            "type": "input",
            "section": "left"
        }
    
    # Right section (9 bars) - addresses 9-17, device 2 for first 7, device 3 for last 2
    for i in range(9, 18):
        device_id = 2 if i < 16 else 3  # First 7 from device 2, last 2 from device 3
        address = i if i < 16 else (i - 16)  # Reset address for device 3
        cylinder_head_bars[str(i)] = {
            "label": f"T{(i-9)+1}",  # Reset numbering for right section
            "address": address,
            "device_id": device_id,
            "type": "input",
            "section": "right"
        }
    
    return {
        "admin_password": admin_password,
        "CylinderHead": {
            "low_limit": 250,
            "high_limit": 500,
            "coil_address": 0,
            "device_id": 5,
            "alarm_delay": 5,
            "enable_alarm": False
        },
        "CylinderHeadBars": cylinder_head_bars,
        "MainBearing": {
            "low_limit": 80,
            "high_limit": 150,
            "coil_address": 1,
            "device_id": 5,
            "alarm_delay": 5,
            "enable_alarm": False
        },
        "PressureGauges": {
            "0": {
                "label": "FUEL OIL PRESSURE INLET",
                "low_limit": 5.0,
                "high_limit": 6.0,
                "coil_address": 2,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "1": {
                "label": "Lube Oil Pressure Inlet",
                "low_limit": 4.0,
                "high_limit": 6.0,
                "coil_address": 3,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "2": {
                "label": "LT Water Pressure",
                "low_limit": 2.0,
                "high_limit": 8.0,
                "coil_address": 2,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "3": {
                "label": "HT Water Pressure",
                "low_limit": 2.0,
                "high_limit": 8.0,
                "coil_address": 2,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "4": {
                "label": "Charge Air Pressure",
                "low_limit": 1.0,
                "high_limit": 8.0,
                "coil_address": 2,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "5": {
                "label": "Starting Air Pressure",
                "low_limit": 15.0,
                "high_limit": 28.0,
                "coil_address": 2,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "6": {
                "label": "Lube Oil Differential Pressure",
                "low_limit": 1.0,
                "high_limit": 8.0,
                "coil_address": 2,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "7": {
                "label": "Crank Case Pressure",
                "low_limit": 1.0,
                "high_limit": 2.0,
                "coil_address": 2,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            }
        },
        "EngineTemperatures": {
            "0": {
                "label": "Charge Air Temp",
                "low_limit": 90,
                "high_limit": 110,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "1": {
                "label": "Lube Oil Inlet Temp",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "2": {
                "label": "Fuel Oil Temp",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "3": {
                "label": "HT Water Temp Inlet",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "4": {
                "label": "HT Water Temp Outlet",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "5": {
                "label": "LT Water Temp Inlet",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "6": {
                "label": "LT Water Temp Outlet",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "7": {
                "label": "Alternator bearing Temp A",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "8": {
                "label": "Alternator bearing Temp B",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "9": {
                "label": "Winding Temp U",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "10": {
                "label": "Winding Temp V",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "11": {
                "label": "Winding Temp W",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "12": {
                "label": "Engine Temp 13",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "13": {
                "label": "Engine Temp 14",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "14": {
                "label": "Engine Temp 15",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            },
            "15": {
                "label": "Engine Temp 16",
                "low_limit": 50,
                "high_limit": 220,
                "coil_address": 4,
                "device_id": 5,
                "alarm_delay": 5,
                "enable_alarm": False
            }
        },
        "ElectricalParameters": {
            "Voltage": [],
            "Current": [],
            "Power": []
        }
    }

# ---------------- Cylinder Head Configuration Dialog ----------------
class CylinderHeadConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cylinder Head Configuration")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        # Load current configuration
        self.config = self.load_config()
        
        # Setup UI
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("⚙️ CYLINDER HEAD ALARM CONFIGURATION")
        title.setStyleSheet("""
            QLabel {
                color: rgb(0, 200, 255);
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Configuration form
        form_group = QGroupBox("Temperature Limits")
        form_group.setStyleSheet("""
            QGroupBox {
                color: rgb(200, 220, 240);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: rgb(0, 200, 255);
            }
        """)
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Low Limit
        self.low_limit_spin = QSpinBox()
        self.low_limit_spin.setRange(0, 1000)
        self.low_limit_spin.setValue(self.config.get("low_limit", 250))
        self.low_limit_spin.setSuffix(" °C")
        self.low_limit_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(0, 191, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(0, 200, 255);
            }
        """)
        form_layout.addRow("Lower Limit (Too Cold):", self.low_limit_spin)
        
        # High Limit
        self.high_limit_spin = QSpinBox()
        self.high_limit_spin.setRange(0, 1000)
        self.high_limit_spin.setValue(self.config.get("high_limit", 600))
        self.high_limit_spin.setSuffix(" °C")
        self.high_limit_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 60, 100);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(255, 60, 100);
            }
        """)
        form_layout.addRow("Upper Limit (Too Hot):", self.high_limit_spin)
        
        # Coil Address
        self.coil_address_spin = QSpinBox()
        self.coil_address_spin.setRange(0, 255)
        self.coil_address_spin.setValue(self.config.get("coil_address", 0))
        self.coil_address_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 180);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(0, 255, 180);
            }
        """)
        form_layout.addRow("Coil Address:", self.coil_address_spin)
        
        # Device ID
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(self.config.get("device_id", 5))
        self.device_id_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(200, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(200, 200, 255);
            }
        """)
        form_layout.addRow("Relay Device ID:", self.device_id_spin)
        
        # Alarm Delay
        self.alarm_delay_spin = QSpinBox()
        self.alarm_delay_spin.setRange(0, 300)  # 0-300 seconds (5 minutes max)
        self.alarm_delay_spin.setValue(self.config.get("alarm_delay", 5))
        self.alarm_delay_spin.setSuffix(" sec")
        self.alarm_delay_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 180, 0);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(255, 180, 0);
            }
        """)
        form_layout.addRow("Alarm Delay:", self.alarm_delay_spin)
        
        # Enable Alarm
        self.enable_alarm_check = QPushButton()
        self.enable_alarm_check.setCheckable(True)
        self.enable_alarm_check.setChecked(self.config.get("enable_alarm", True))
        self.enable_alarm_check.setText("✅ ENABLED" if self.enable_alarm_check.isChecked() else "❌ DISABLED")
        self.enable_alarm_check.clicked.connect(lambda: self.enable_alarm_check.setText(
            "✅ ENABLED" if self.enable_alarm_check.isChecked() else "❌ DISABLED"
        ))
        self.enable_alarm_check.setStyleSheet("""
            QPushButton {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 100);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:checked {
                background: rgb(0, 100, 50);
                border: 2px solid rgb(0, 255, 100);
            }
            QPushButton:hover {
                background: rgb(40, 50, 65);
            }
        """)
        form_layout.addRow("Enable Alarm Output:", self.enable_alarm_check)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Info label
        info_label = QLabel("ℹ️ Configure the Modbus device ID and coil address\nCoil will turn ON when any temperature\nis outside the configured limits.")
        info_label.setStyleSheet("""
            QLabel {
                color: rgb(150, 170, 190);
                font-size: 11px;
                font-style: italic;
                padding: 10px;
                background: rgb(25, 35, 50);
                border-radius: 5px;
            }
        """)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgb(60, 70, 85);
                color: rgb(200, 220, 240);
                border: 1px solid rgb(80, 90, 105);
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: rgb(70, 80, 95);
            }
            QPushButton:pressed {
                background: rgb(50, 60, 75);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setMinimumHeight(35)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 200, 255), stop:1 rgb(0, 150, 200));
                color: rgb(10, 20, 30);
                border: 1px solid rgb(0, 220, 255);
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 220, 255), stop:1 rgb(0, 170, 220));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 150, 200), stop:1 rgb(0, 100, 150));
            }
        """)
        save_btn.clicked.connect(self.save_configuration)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background: rgb(20, 30, 45);
            }
            QLabel {
                background: transparent;
            }
        """)
    
    def load_config(self):
        """Load configuration from encrypted file"""
        try:
            # Try to load from encrypted file
            data = load_encrypted_config("modbus_config.dat")
            if data is not None:
                return data.get("CylinderHead", {
                    "low_limit": 250,
                    "high_limit": 600,
                    "coil_address": 0,
                    "device_id": 5,
                    "alarm_delay": 5,
                    "enable_alarm": True
                })
        except Exception as e:
            print(f"Error loading config: {e}")
        return {"low_limit": 250, "high_limit": 600, "coil_address": 0, "device_id": 5, "alarm_delay": 5, "enable_alarm": False}
    
    def save_configuration(self):
        """Save configuration to encrypted file"""
        try:
            # Load existing config from encrypted file
            config_data = load_encrypted_config("modbus_config.dat")
            if config_data is None:
                config_data = {}
            
            # Update CylinderHead section
            config_data["CylinderHead"] = {
                "low_limit": self.low_limit_spin.value(),
                "high_limit": self.high_limit_spin.value(),
                "coil_address": self.coil_address_spin.value(),
                "device_id": self.device_id_spin.value(),
                "alarm_delay": self.alarm_delay_spin.value(),
                "enable_alarm": self.enable_alarm_check.isChecked()
            }
            
            # Save back to encrypted file
            if save_encrypted_config(config_data, "modbus_config.dat"):
                QMessageBox.information(self, "Success", "Configuration saved successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save configuration to encrypted file")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{e}")


# ---------------- Main Bearing Configuration Dialog ----------------
class MainBearingConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Main Bearing Configuration")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        # Load current configuration
        self.config = self.load_config()
        
        # Setup UI
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("⚙️ MAIN BEARING ALARM CONFIGURATION")
        title.setStyleSheet("""
            QLabel {
                color: rgb(0, 200, 255);
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Configuration form
        form_group = QGroupBox("Temperature Limits")
        form_group.setStyleSheet("""
            QGroupBox {
                color: rgb(200, 220, 240);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: rgb(0, 200, 255);
            }
        """)
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Low Limit
        self.low_limit_spin = QSpinBox()
        self.low_limit_spin.setRange(0, 500)
        self.low_limit_spin.setValue(self.config.get("low_limit", 80))
        self.low_limit_spin.setSuffix(" °C")
        self.low_limit_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 200, 0);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(255, 200, 0);
            }
        """)
        form_layout.addRow("Lower Limit (Too Cold):", self.low_limit_spin)
        
        # High Limit
        self.high_limit_spin = QSpinBox()
        self.high_limit_spin.setRange(0, 500)
        self.high_limit_spin.setValue(self.config.get("high_limit", 150))
        self.high_limit_spin.setSuffix(" °C")
        self.high_limit_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 60, 100);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(255, 60, 100);
            }
        """)
        form_layout.addRow("Upper Limit (Too Hot):", self.high_limit_spin)
        
        # Coil Address
        self.coil_address_spin = QSpinBox()
        self.coil_address_spin.setRange(0, 255)
        self.coil_address_spin.setValue(self.config.get("coil_address", 1))
        self.coil_address_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 180);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(0, 255, 180);
            }
        """)
        form_layout.addRow("Coil Address:", self.coil_address_spin)
        
        # Device ID
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(self.config.get("device_id", 5))
        self.device_id_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(200, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(200, 200, 255);
            }
        """)
        form_layout.addRow("Relay Device ID:", self.device_id_spin)
        
        # Alarm Delay
        self.alarm_delay_spin = QSpinBox()
        self.alarm_delay_spin.setRange(0, 300)  # 0-300 seconds (5 minutes max)
        self.alarm_delay_spin.setValue(self.config.get("alarm_delay", 5))
        self.alarm_delay_spin.setSuffix(" sec")
        self.alarm_delay_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 180, 0);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(255, 180, 0);
            }
        """)
        form_layout.addRow("Alarm Delay:", self.alarm_delay_spin)
        
        # Enable Alarm
        self.enable_alarm_check = QPushButton()
        self.enable_alarm_check.setCheckable(True)
        self.enable_alarm_check.setChecked(self.config.get("enable_alarm", True))
        self.enable_alarm_check.setText("✅ ENABLED" if self.enable_alarm_check.isChecked() else "❌ DISABLED")
        self.enable_alarm_check.clicked.connect(lambda: self.enable_alarm_check.setText(
            "✅ ENABLED" if self.enable_alarm_check.isChecked() else "❌ DISABLED"
        ))
        self.enable_alarm_check.setStyleSheet("""
            QPushButton {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 100);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:checked {
                background: rgb(0, 100, 50);
                border: 2px solid rgb(0, 255, 100);
            }
            QPushButton:hover {
                background: rgb(40, 50, 65);
            }
        """)
        form_layout.addRow("Enable Alarm Output:", self.enable_alarm_check)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Info label
        info_label = QLabel("ℹ️ Configure the Modbus device ID and coil address\nCoil will turn ON when any temperature\nis outside the configured limits.")
        info_label.setStyleSheet("""
            QLabel {
                color: rgb(150, 170, 190);
                font-size: 11px;
                font-style: italic;
                padding: 10px;
                background: rgb(25, 35, 50);
                border-radius: 5px;
            }
        """)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgb(60, 70, 85);
                color: rgb(200, 220, 240);
                border: 1px solid rgb(80, 90, 105);
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: rgb(70, 80, 95);
            }
            QPushButton:pressed {
                background: rgb(50, 60, 75);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setMinimumHeight(35)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 200, 255), stop:1 rgb(0, 150, 200));
                color: rgb(10, 20, 30);
                border: 1px solid rgb(0, 220, 255);
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 220, 255), stop:1 rgb(0, 170, 220));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 150, 200), stop:1 rgb(0, 100, 150));
            }
        """)
        save_btn.clicked.connect(self.save_configuration)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background: rgb(20, 30, 45);
            }
            QLabel {
                background: transparent;
            }
        """)
    
    def load_config(self):
        """Load configuration from encrypted file"""
        try:
            # Try to load from encrypted file
            data = load_encrypted_config("modbus_config.dat")
            if data is not None:
                return data.get("MainBearing", {
                    "low_limit": 80,
                    "high_limit": 150,
                    "coil_address": 1,
                    "device_id": 5,
                    "alarm_delay": 5,
                    "enable_alarm": True
                })
        except Exception as e:
            print(f"Error loading config: {e}")
        return {"low_limit": 80, "high_limit": 150, "coil_address": 1, "device_id": 5, "alarm_delay": 5, "enable_alarm": False}
    
    def save_configuration(self):
        """Save configuration to encrypted file"""
        try:
            # Load existing config from encrypted file
            config_data = load_encrypted_config("modbus_config.dat")
            if config_data is None:
                config_data = {}
            
            # Update MainBearing section
            config_data["MainBearing"] = {
                "low_limit": self.low_limit_spin.value(),
                "high_limit": self.high_limit_spin.value(),
                "coil_address": self.coil_address_spin.value(),
                "device_id": self.device_id_spin.value(),
                "alarm_delay": self.alarm_delay_spin.value(),
                "enable_alarm": self.enable_alarm_check.isChecked()
            }
            
            # Save back to encrypted file
            if save_encrypted_config(config_data, "modbus_config.dat"):
                QMessageBox.information(self, "Success", "Configuration saved successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save configuration to encrypted file")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{e}")


# ---------------- Pressure Gauge Configuration Dialog ----------------
class PressureGaugeConfigDialog(QDialog):
    def __init__(self, parent=None, gauge_index=0, gauge_label=""):
        super().__init__(parent)
        self.gauge_index = gauge_index
        self.gauge_label = gauge_label
        self.setWindowTitle(f"{gauge_label} Configuration")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        # Load current configuration
        self.config = self.load_config()
        
        # Setup UI
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel(f"⚙️ {gauge_label.upper()}")
        title.setStyleSheet("""
            QLabel {
                color: rgb(0, 200, 255);
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Configuration form
        form_group = QGroupBox("Gauge Configuration")
        form_group.setStyleSheet("""
            QGroupBox {
                color: rgb(200, 220, 240);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: rgb(0, 200, 255);
            }
        """)
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Gauge Label
        self.label_edit = QLineEdit()
        self.label_edit.setText(self.config.get("label", gauge_label))
        self.label_edit.setPlaceholderText("Enter gauge name...")
        self.label_edit.setStyleSheet("""
            QLineEdit {
                background: rgb(30, 40, 55);
                color: rgb(0, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid rgb(0, 200, 255);
                background: rgb(35, 45, 60);
            }
        """)
        form_layout.addRow("Gauge Label:", self.label_edit)
        
        # Low Limit
        self.low_limit_spin = QDoubleSpinBox()
        self.low_limit_spin.setRange(0, 100)
        self.low_limit_spin.setDecimals(1)
        self.low_limit_spin.setSingleStep(0.5)
        self.low_limit_spin.setValue(self.config.get("low_limit", 2.0))
        self.low_limit_spin.setSuffix(" bar")
        
        # For Fuel Oil (0), Lube Oil (1), Starting Air (5): Low is CRITICAL (red), High is WARNING (yellow)
        # For other gauges: Low is WARNING (yellow), High is CRITICAL (red)
        if gauge_index in [0, 1, 5]:
            # Fuel Oil, Lube Oil, Starting Air - Low is critical RED
            low_color = "rgb(255, 60, 100)"  # Red for critical low
            high_color = "rgb(255, 200, 0)"  # Yellow for warning high
        else:
            # Standard gauges - Low is warning YELLOW, High is critical RED
            low_color = "rgb(255, 200, 0)"   # Yellow for warning low
            high_color = "rgb(255, 60, 100)"  # Red for critical high
        
        self.low_limit_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: rgb(30, 40, 55);
                color: {low_color};
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }}
            QDoubleSpinBox:focus {{
                border: 2px solid {low_color};
            }}
        """)
        form_layout.addRow("Lower Limit (Too Low):", self.low_limit_spin)
        
        # High Limit
        self.high_limit_spin = QDoubleSpinBox()
        self.high_limit_spin.setRange(0, 100)
        self.high_limit_spin.setDecimals(1)
        self.high_limit_spin.setSingleStep(0.5)
        self.high_limit_spin.setValue(self.config.get("high_limit", 8.0))
        self.high_limit_spin.setSuffix(" bar")
        self.high_limit_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: rgb(30, 40, 55);
                color: {high_color};
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }}
            QDoubleSpinBox:focus {{
                border: 2px solid {high_color};
            }}
        """)
        form_layout.addRow("Upper Limit (Too High):", self.high_limit_spin)
        
        # Device ID
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(self.config.get("device_id", 5))
        self.device_id_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(200, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(200, 200, 255);
            }
        """)
        form_layout.addRow("Relay Device ID:", self.device_id_spin)
        
        # Coil Address
        self.coil_address_spin = QSpinBox()
        self.coil_address_spin.setRange(0, 255)
        # Default: Coil 3 for Lube Oil (index 1), Coil 2 for others
        default_coil = 3 if gauge_index == 1 else 2
        self.coil_address_spin.setValue(self.config.get("coil_address", default_coil))
        self.coil_address_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 180);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(0, 255, 180);
            }
        """)
        form_layout.addRow("Coil Address:", self.coil_address_spin)
        
        # Alarm Delay
        self.alarm_delay_spin = QSpinBox()
        self.alarm_delay_spin.setRange(0, 300)  # 0-300 seconds (5 minutes max)
        self.alarm_delay_spin.setValue(self.config.get("alarm_delay", 5))
        self.alarm_delay_spin.setSuffix(" sec")
        self.alarm_delay_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 180, 0);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(255, 180, 0);
            }
        """)
        form_layout.addRow("Alarm Delay:", self.alarm_delay_spin)
        
        # Enable Alarm
        self.enable_alarm_check = QPushButton()
        self.enable_alarm_check.setCheckable(True)
        self.enable_alarm_check.setChecked(self.config.get("enable_alarm", True))
        self.enable_alarm_check.setText("✅ ENABLED" if self.enable_alarm_check.isChecked() else "❌ DISABLED")
        self.enable_alarm_check.clicked.connect(lambda: self.enable_alarm_check.setText(
            "✅ ENABLED" if self.enable_alarm_check.isChecked() else "❌ DISABLED"
        ))
        self.enable_alarm_check.setStyleSheet("""
            QPushButton {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 100);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:checked {
                background: rgb(0, 100, 50);
                border: 2px solid rgb(0, 255, 100);
            }
            QPushButton:hover {
                background: rgb(40, 50, 65);
            }
        """)
        form_layout.addRow("Enable Alarm Output:", self.enable_alarm_check)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Coil info label
        info_label = QLabel(f"ℹ️ Configure the Modbus device ID and coil address\n\nCoil turns ON when pressure is\noutside the configured limits.")
        info_label.setStyleSheet("""
            QLabel {
                color: rgb(150, 170, 190);
                font-size: 11px;
                font-style: italic;
                padding: 10px;
                background: rgb(25, 35, 50);
                border-radius: 5px;
            }
        """)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgb(60, 70, 85);
                color: rgb(200, 220, 240);
                border: 1px solid rgb(80, 90, 105);
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: rgb(70, 80, 95);
            }
            QPushButton:pressed {
                background: rgb(50, 60, 75);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setMinimumHeight(35)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 200, 255), stop:1 rgb(0, 150, 200));
                color: rgb(10, 20, 30);
                border: 1px solid rgb(0, 220, 255);
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 220, 255), stop:1 rgb(0, 170, 220));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 150, 200), stop:1 rgb(0, 100, 150));
            }
        """)
        save_btn.clicked.connect(self.save_configuration)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background: rgb(20, 30, 45);
            }
        """)
    
    def load_config(self):
        """Load configuration from modbus_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modbus_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    gauges_config = data.get("PressureGauges", {})
                    return gauges_config.get(str(self.gauge_index), {
                        "low_limit": 2.0,
                        "high_limit": 8.0,
                        "alarm_delay": 5,
                        "enable_alarm": True
                    })
        except Exception as e:
            print(f"Error loading pressure gauge config: {e}")
        return {"low_limit": 2.0, "high_limit": 8.0, "alarm_delay": 5, "enable_alarm": False}
    
    def save_configuration(self):
        """Save configuration to modbus_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modbus_config.json")
            
            # Load existing config
            config_data = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
            
            # Initialize PressureGauges section if it doesn't exist
            if "PressureGauges" not in config_data:
                config_data["PressureGauges"] = {}
            
            # Update specific gauge configuration
            config_data["PressureGauges"][str(self.gauge_index)] = {
                "label": self.label_edit.text().strip(),
                "low_limit": self.low_limit_spin.value(),
                "high_limit": self.high_limit_spin.value(),
                "coil_address": self.coil_address_spin.value(),
                "device_id": self.device_id_spin.value(),
                "alarm_delay": self.alarm_delay_spin.value(),
                "enable_alarm": self.enable_alarm_check.isChecked()
            }
            
            # Save back to file
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            QMessageBox.information(self, "Success", "Configuration saved successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{e}")


# ---------------- Temperature Gauge Configuration Dialog ----------------
class TemperatureGaugeConfigDialog(QDialog):
    def __init__(self, parent=None, gauge_index=0, gauge_label=""):
        super().__init__(parent)
        self.gauge_index = gauge_index
        self.gauge_label = gauge_label
        self.setWindowTitle(f"{gauge_label} Configuration")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        # Load current configuration
        self.config = self.load_config()
        
        # Setup UI
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel(f"⚙️ {gauge_label.upper()}")
        title.setStyleSheet("""
            QLabel {
                color: rgb(0, 200, 255);
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Configuration form
        form_group = QGroupBox("Gauge Configuration")
        form_group.setStyleSheet("""
            QGroupBox {
                color: rgb(200, 220, 240);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: rgb(0, 200, 255);
            }
        """)
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Gauge Label
        self.label_edit = QLineEdit()
        self.label_edit.setText(self.config.get("label", gauge_label))
        self.label_edit.setPlaceholderText("Enter gauge name...")
        self.label_edit.setStyleSheet("""
            QLineEdit {
                background: rgb(30, 40, 55);
                color: rgb(0, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid rgb(0, 200, 255);
                background: rgb(35, 45, 60);
            }
        """)
        form_layout.addRow("Gauge Label:", self.label_edit)
        
        # Low Limit
        self.low_limit_spin = QSpinBox()
        self.low_limit_spin.setRange(0, 500)
        self.low_limit_spin.setValue(self.config.get("low_limit", 50))
        self.low_limit_spin.setSuffix(" °C")
        self.low_limit_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 200, 0);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(255, 200, 0);
            }
        """)
        form_layout.addRow("Lower Limit (Too Cold):", self.low_limit_spin)
        
        # High Limit
        self.high_limit_spin = QSpinBox()
        self.high_limit_spin.setRange(0, 500)
        self.high_limit_spin.setValue(self.config.get("high_limit", 220))
        self.high_limit_spin.setSuffix(" °C")
        self.high_limit_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 60, 100);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(255, 60, 100);
            }
        """)
        form_layout.addRow("Upper Limit (Too Hot):", self.high_limit_spin)
        
        # Device ID
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(self.config.get("device_id", 5))
        self.device_id_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(200, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(200, 200, 255);
            }
        """)
        form_layout.addRow("Relay Device ID:", self.device_id_spin)
        
        # Coil Address
        self.coil_address_spin = QSpinBox()
        self.coil_address_spin.setRange(0, 255)
        self.coil_address_spin.setValue(self.config.get("coil_address", 4))
        self.coil_address_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 180);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(0, 255, 180);
            }
        """)
        form_layout.addRow("Coil Address:", self.coil_address_spin)
        
        # Alarm Delay
        self.alarm_delay_spin = QSpinBox()
        self.alarm_delay_spin.setRange(0, 300)  # 0-300 seconds (5 minutes max)
        self.alarm_delay_spin.setValue(self.config.get("alarm_delay", 5))
        self.alarm_delay_spin.setSuffix(" sec")
        self.alarm_delay_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 180, 0);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(255, 180, 0);
            }
        """)
        form_layout.addRow("Alarm Delay:", self.alarm_delay_spin)
        
        # Enable Alarm
        self.enable_alarm_check = QPushButton()
        self.enable_alarm_check.setCheckable(True)
        self.enable_alarm_check.setChecked(self.config.get("enable_alarm", True))
        self.enable_alarm_check.setText("✅ ENABLED" if self.enable_alarm_check.isChecked() else "❌ DISABLED")
        self.enable_alarm_check.clicked.connect(lambda: self.enable_alarm_check.setText(
            "✅ ENABLED" if self.enable_alarm_check.isChecked() else "❌ DISABLED"
        ))
        self.enable_alarm_check.setStyleSheet("""
            QPushButton {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 100);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:checked {
                background: rgb(0, 100, 50);
                border: 2px solid rgb(0, 255, 100);
            }
            QPushButton:hover {
                background: rgb(40, 50, 65);
            }
        """)
        form_layout.addRow("Enable Alarm Output:", self.enable_alarm_check)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Info label
        info_label = QLabel(f"ℹ️ Configure the Modbus device ID and coil address\n\nCoil turns ON when temperature is\noutside the configured limits.")
        info_label.setStyleSheet("""
            QLabel {
                color: rgb(150, 170, 190);
                font-size: 11px;
                font-style: italic;
                padding: 10px;
                background: rgb(25, 35, 50);
                border-radius: 5px;
            }
        """)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgb(60, 70, 85);
                color: rgb(200, 220, 240);
                border: 1px solid rgb(80, 90, 105);
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: rgb(70, 80, 95);
            }
            QPushButton:pressed {
                background: rgb(50, 60, 75);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setMinimumHeight(35)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 200, 255), stop:1 rgb(0, 150, 200));
                color: rgb(255, 255, 255);
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 220, 255), stop:1 rgb(0, 170, 220));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 150, 200), stop:1 rgb(0, 100, 150));
            }
        """)
        save_btn.clicked.connect(self.save_configuration)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background: rgb(20, 30, 45);
            }
        """)
    
    def load_config(self):
        """Load configuration from modbus_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modbus_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    if "EngineTemperatures" in data and str(self.gauge_index) in data["EngineTemperatures"]:
                        return data["EngineTemperatures"][str(self.gauge_index)]
        except Exception as e:
            print(f"Error loading temperature gauge config: {e}")
        return {"label": self.gauge_label, "low_limit": 50, "high_limit": 220, "coil_address": 4, "device_id": 5, "alarm_delay": 5, "enable_alarm": False}
    
    def save_configuration(self):
        """Save configuration to modbus_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modbus_config.json")
            
            # Load existing config
            config_data = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
            
            # Initialize EngineTemperatures section if it doesn't exist
            if "EngineTemperatures" not in config_data:
                config_data["EngineTemperatures"] = {}
            
            # Update specific gauge configuration
            config_data["EngineTemperatures"][str(self.gauge_index)] = {
                "label": self.label_edit.text().strip(),
                "low_limit": self.low_limit_spin.value(),
                "high_limit": self.high_limit_spin.value(),
                "coil_address": self.coil_address_spin.value(),
                "device_id": self.device_id_spin.value(),
                "alarm_delay": self.alarm_delay_spin.value(),
                "enable_alarm": self.enable_alarm_check.isChecked()
            }
            
            # Save back to file
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            QMessageBox.information(self, "Success", "Configuration saved successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{e}")


# ---------------- Temperature Display Widget ----------------
class CylinderHeadTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.setMinimumSize(800, 400)
        self.setStyleSheet(CYLINDER_HEAD_BG_STYLE)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Load bar configurations from config file
        self.bars_config = self.load_bars_config()
        self.left_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'left']
        self.right_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'right']
        
        # Temperature data for each bar (keyed by bar ID)
        self.current_temperatures = {}
        self.target_temperatures = {}
        for bar_id in self.bars_config:
            self.current_temperatures[bar_id] = 0.0
            self.target_temperatures[bar_id] = 0
        
        # Hover state tracking for professional hover effects
        self.hovered_bar = None
        self.hover_opacity = {}  # Track hover opacity for each bar
        self.hovered_remove_button = None  # Track which remove button is hovered
        self.remove_button_hover_opacity = {}  # Track hover opacity for remove buttons
        for bar_id in self.bars_config:
            self.hover_opacity[bar_id] = 0.0
            self.remove_button_hover_opacity[bar_id] = 0.0
        
        # Configuration for 3-color logic (global settings)
        self.config = self.load_config()
        self.low_limit = self.config.get("low_limit", 250)
        self.high_limit = self.config.get("high_limit", 600)
        self.coil_address = self.config.get("coil_address", 0)
        self.enable_alarm = self.config.get("enable_alarm", True)
        self.relay_device_id = self.config.get("device_id", 5)
        self.alarm_delay = self.config.get("alarm_delay", 5)
        
        # Modbus client reference (will be set by HMIWindow)
        self.modbus_client = None
        
        # Alarm state tracking
        self.alarm_active = False
        self.last_alarm_state = None
        self.alarm_start_time = None
        
        # Admin mode state
        self.admin_mode = False
        
        # Storage for clickable areas
        self.bar_rects = {}  # Store bar rectangles for click detection
        
        # Pagination state
        self.bars_per_page = 18  # Maximum 18 bars per page (9 left + 9 right)
        self.current_page = 0  # Current page index (0-based)
        self.left_current_page = 0  # Current page for left section
        self.right_current_page = 0  # Current page for right section
        
        # UI Elements
        self.setup_ui()
        
        # Initialize pagination controls
        self.update_pagination_controls()
        
        # Animation timer - 60 FPS for ultra-smooth animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_bars)
        self.animation_timer.start(16)  # 16ms = ~60 fps
    
    def setup_ui(self):
        """Setup UI elements including buttons"""
        # Settings button - positioned at top-right
        self.settings_btn = QPushButton("⚙️", self)
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(40, 50, 65), stop:1 rgb(30, 40, 55));
                color: rgb(0, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 20px;
                font-size: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 200, 255), stop:1 rgb(0, 150, 200));
                color: rgb(10, 20, 30);
                border: 2px solid rgb(0, 220, 255);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 150, 200), stop:1 rgb(0, 100, 150));
            }
        """)
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setToolTip("Configure Cylinder Head Alarms")
        
        # Add button (+) - Microsoft style design
        self.add_btn = QPushButton("+", self)
        self.add_btn.setFixedSize(30, 200)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(45, 45, 45, 180), stop:1 rgba(60, 60, 60, 180));
                color: rgb(255, 255, 255);
                border: 1px solid rgba(120, 120, 120, 100);
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 120, 215, 180), stop:1 rgba(0, 100, 180, 180));
                border: 1px solid rgba(0, 120, 215, 200);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 90, 158, 200), stop:1 rgba(0, 70, 130, 200));
            }
        """)
        self.add_btn.clicked.connect(self.show_add_bar_dialog)
        self.add_btn.setToolTip("Add New Temperature Bar")
        self.add_btn.setVisible(False)  # Hidden by default, shown in admin mode
        
        # Pagination navigation buttons
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(45, 45, 45, 180), stop:1 rgba(60, 60, 60, 180));
                color: rgb(255, 255, 255);
                border: 1px solid rgba(120, 120, 120, 100);
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 120, 215, 180), stop:1 rgba(0, 100, 180, 180));
                border: 1px solid rgba(0, 120, 215, 200);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 90, 158, 200), stop:1 rgba(0, 70, 130, 200));
            }
            QPushButton:disabled {
                background: rgba(30, 30, 30, 100);
                color: rgba(120, 120, 120, 150);
                border: 1px solid rgba(60, 60, 60, 100);
            }
        """
        
        # Left section pagination buttons
        self.left_prev_btn = QPushButton("◀ Prev", self)
        self.left_prev_btn.setFixedSize(60, 25)
        self.left_prev_btn.setCursor(Qt.PointingHandCursor)
        self.left_prev_btn.setStyleSheet(button_style)
        self.left_prev_btn.clicked.connect(self.prev_left_page)
        self.left_prev_btn.setToolTip("Previous page for left section")
        self.left_prev_btn.setVisible(False)
        
        self.left_next_btn = QPushButton("Next ▶", self)
        self.left_next_btn.setFixedSize(60, 25)
        self.left_next_btn.setCursor(Qt.PointingHandCursor)
        self.left_next_btn.setStyleSheet(button_style)
        self.left_next_btn.clicked.connect(self.next_left_page)
        self.left_next_btn.setToolTip("Next page for left section")
        self.left_next_btn.setVisible(False)
        
        # Right section pagination buttons
        self.right_prev_btn = QPushButton("◀ Prev", self)
        self.right_prev_btn.setFixedSize(60, 25)
        self.right_prev_btn.setCursor(Qt.PointingHandCursor)
        self.right_prev_btn.setStyleSheet(button_style)
        self.right_prev_btn.clicked.connect(self.prev_right_page)
        self.right_prev_btn.setToolTip("Previous page for right section")
        self.right_prev_btn.setVisible(False)
        
        self.right_next_btn = QPushButton("Next ▶", self)
        self.right_next_btn.setFixedSize(60, 25)
        self.right_next_btn.setCursor(Qt.PointingHandCursor)
        self.right_next_btn.setStyleSheet(button_style)
        self.right_next_btn.clicked.connect(self.next_right_page)
        self.right_next_btn.setToolTip("Next page for right section")
        self.right_next_btn.setVisible(False)
        
        # Page indicator labels
        self.left_page_label = QLabel("", self)
        self.left_page_label.setStyleSheet("""
            color: rgb(200, 220, 240);
            font-size: 10px;
            font-weight: bold;
            background: rgba(30, 40, 55, 150);
            border: 1px solid rgba(60, 80, 100, 100);
            border-radius: 3px;
            padding: 2px 6px;
        """)
        self.left_page_label.setAlignment(Qt.AlignCenter)
        self.left_page_label.setVisible(False)
        
        self.right_page_label = QLabel("", self)
        self.right_page_label.setStyleSheet("""
            color: rgb(200, 220, 240);
            font-size: 10px;
            font-weight: bold;
            background: rgba(30, 40, 55, 150);
            border: 1px solid rgba(60, 80, 100, 100);
            border-radius: 3px;
            padding: 2px 6px;
        """)
        self.right_page_label.setAlignment(Qt.AlignCenter)
        self.right_page_label.setVisible(False)
    
    def resizeEvent(self, event):
        """Handle resize events to update button positions"""
        super().resizeEvent(event)
        self.settings_btn.move(self.width() - 50, 10)
        # Position add button on the right side
        self.add_btn.move(self.width() - 40, (self.height() - 200) // 2)
        
        # Position pagination buttons and labels
        width = self.width()
        height = self.height()
        
        # Calculate section positions (similar to paintEvent calculations)
        scale_factor = min(width / 1280, height / 500)
        scale_width = max(50, int(width * 0.055))
        gap_between_scale_and_bars = max(20, int(width * 0.031))
        section_gap = max(30, int(width * 0.039))
        spacing = max(30, int(width * 0.048))
        
        # Calculate section widths (based on current page)
        current_left_bars = self.get_current_page_bars('left')
        current_right_bars = self.get_current_page_bars('right')
        left_section_width = len(current_left_bars) * spacing
        right_section_width = len(current_right_bars) * spacing
        total_bars_width = left_section_width + section_gap + right_section_width
        total_content_width = scale_width + gap_between_scale_and_bars + total_bars_width
        
        # Center the content
        offset_x = max(20, (width - total_content_width) // 2)
        scale_left = offset_x + 40
        left_section_start = scale_left + gap_between_scale_and_bars
        right_section_start = left_section_start + left_section_width + section_gap
        
        # Position left section pagination controls
        left_center = left_section_start + left_section_width // 2
        self.left_prev_btn.move(left_center - 70, height - 40)
        self.left_next_btn.move(left_center + 10, height - 40)
        self.left_page_label.move(left_center - 25, height - 60)
        self.left_page_label.setFixedSize(50, 15)
        
        # Position right section pagination controls
        right_center = right_section_start + right_section_width // 2
        self.right_prev_btn.move(right_center - 70, height - 40)
        self.right_next_btn.move(right_center + 10, height - 40)
        self.right_page_label.move(right_center - 25, height - 60)
        self.right_page_label.setFixedSize(50, 15)
    
    def load_bars_config(self):
        """Load bar configurations from encrypted file"""
        try:
            data = load_encrypted_config("modbus_config.dat")
            if data is not None and "CylinderHeadBars" in data:
                return data["CylinderHeadBars"]
        except Exception as e:
            print(f"Error loading Cylinder Head bars config: {e}")
        
        # Return default configuration if not found
        return self.create_default_bars_config()
    
    def create_default_bars_config(self):
        """Create default 18 bars configuration"""
        bars_config = {}
        
        # Left section (9 bars) - addresses 0-8, device 2
        for i in range(9):
            bars_config[str(i)] = {
                "label": f"T{i+1}",
                "address": i,
                "device_id": 2,
                "type": "input",
                "section": "left"
            }
        
        # Right section (9 bars) - addresses 9-17, device 2 for first 7, device 3 for last 2
        for i in range(9, 18):
            device_id = 2 if i < 16 else 3
            address = i if i < 16 else (i - 16)
            bars_config[str(i)] = {
                "label": f"T{(i-9)+1}",
                "address": address,
                "device_id": device_id,
                "type": "input",
                "section": "right"
            }
        
        return bars_config
    
    def save_bars_config(self):
        """Save bar configurations to encrypted file"""
        try:
            data = load_encrypted_config("modbus_config.dat") or {}
            data["CylinderHeadBars"] = self.bars_config
            save_encrypted_config(data, "modbus_config.dat")
            print("Cylinder Head bars configuration saved successfully")
        except Exception as e:
            print(f"Error saving Cylinder Head bars config: {e}")
    
    def set_admin_mode(self, admin_mode):
        """Set admin mode and show/hide admin controls"""
        self.admin_mode = admin_mode
        # Add button should only be visible in developer mode, not admin mode
        # self.add_btn.setVisible(admin_mode)  # Removed - now controlled by developer mode
        self.update()  # Trigger repaint to show/hide remove buttons
    
    def show_add_bar_dialog(self):
        """Show dialog to select section for new bar"""
        # Check if Developer Mode is active
        if not self.is_developer_mode_active():
            QMessageBox.warning(self, "Access Restricted", 
                               "🔒 This modification feature requires Developer Mode to be activated.\n\n"
                               "Please enable Developer Mode to add new temperature bars.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Temperature Bar")
        dialog.setFixedSize(300, 150)
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(25, 35, 50), stop:1 rgb(15, 25, 40));
                border: 2px solid rgb(60, 80, 100);
            }
            QLabel { color: rgb(200, 220, 240); font-size: 12px; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 120, 215), stop:1 rgb(0, 100, 180));
                color: white;
                border: 1px solid rgb(0, 120, 215);
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 140, 235), stop:1 rgb(0, 120, 200));
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select section for new temperature bar:"))
        
        button_layout = QHBoxLayout()
        left_btn = QPushButton("Left Section")
        right_btn = QPushButton("Right Section")
        cancel_btn = QPushButton("Cancel")
        
        left_btn.clicked.connect(lambda: self.add_new_bar("left", dialog))
        right_btn.clicked.connect(lambda: self.add_new_bar("right", dialog))
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(left_btn)
        button_layout.addWidget(right_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def add_new_bar(self, section, dialog):
        """Add a new temperature bar to the specified section"""
        dialog.accept()
        
        # Find next available ID
        existing_ids = [int(bar_id) for bar_id in self.bars_config.keys()]
        new_id = str(max(existing_ids) + 1) if existing_ids else "0"
        
        # Determine next address and device ID
        section_bars = [bar for bar in self.bars_config.values() if bar.get('section') == section]
        next_address = len(section_bars)
        device_id = 2  # Default device ID
        
        # Create new bar configuration
        new_bar = {
            "label": f"T{len(section_bars) + 1}",
            "address": next_address,
            "device_id": device_id,
            "type": "input",
            "section": section
        }
        
        # Add to configuration
        self.bars_config[new_id] = new_bar
        self.current_temperatures[new_id] = 0.0
        self.target_temperatures[new_id] = 0
        
        # Update section lists
        self.left_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'left']
        self.right_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'right']
        
        # Save configuration
        self.save_bars_config()
        
        # Trigger repaint
        self.update()
        
        print(f"Added new temperature bar to {section} section: {new_bar}")
    
    def remove_bar(self, bar_id):
        """Remove a temperature bar with confirmation"""
        # Check if Developer Mode is active
        if not self.is_developer_mode_active():
            QMessageBox.warning(self, "Access Restricted", 
                               "🔒 This modification feature requires Developer Mode to be activated.\n\n"
                               "Please enable Developer Mode to remove temperature bars.")
            return
        
        bar = self.bars_config.get(bar_id)
        if not bar:
            return
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self, 
            "Remove Temperature Bar",
            f"Remove temperature bar '{bar['label']}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove from configuration
            del self.bars_config[bar_id]
            del self.current_temperatures[bar_id]
            del self.target_temperatures[bar_id]
            
            # Update section lists
            self.left_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'left']
            self.right_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'right']
            
            # Save configuration
            self.save_bars_config()
            
            # Update pagination controls
            self.update_pagination_controls()
            
            # Trigger repaint
            self.update()
            
            print(f"Removed temperature bar: {bar['label']}")
    
    def open_bar_config(self, bar_id):
        """Open configuration dialog for a specific bar"""
        # Check if Developer Mode is active
        if not self.is_developer_mode_active():
            QMessageBox.warning(self, "Access Restricted", 
                               "🔒 This modification feature requires Developer Mode to be activated.\n\n"
                               "Please enable Developer Mode to configure temperature bars.")
            return
        
        bar = self.bars_config.get(bar_id)
        if not bar:
            return
        
        dialog = CylinderHeadBarConfigDialog(self, bar, bar_id)
        if dialog.exec_() == QDialog.Accepted:
            # Get updated configuration from dialog
            updated_config = dialog.get_config()
            self.bars_config[bar_id] = updated_config
            # Save configuration and update display
            self.save_bars_config()
            self.update()
    
    def prev_left_page(self):
        """Navigate to previous page for left section"""
        if self.left_current_page > 0:
            self.left_current_page -= 1
            self.update_pagination_controls()
            self.update()
    
    def next_left_page(self):
        """Navigate to next page for left section"""
        left_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'left']
        max_pages = (len(left_bars) + 8) // 9  # 9 bars per page for left section
        if self.left_current_page < max_pages - 1:
            self.left_current_page += 1
            self.update_pagination_controls()
            self.update()
    
    def prev_right_page(self):
        """Navigate to previous page for right section"""
        if self.right_current_page > 0:
            self.right_current_page -= 1
            self.update_pagination_controls()
            self.update()
    
    def next_right_page(self):
        """Navigate to next page for right section"""
        right_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'right']
        max_pages = (len(right_bars) + 8) // 9  # 9 bars per page for right section
        if self.right_current_page < max_pages - 1:
            self.right_current_page += 1
            self.update_pagination_controls()
            self.update()
    
    def update_pagination_controls(self):
        """Update pagination button states and labels"""
        left_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'left']
        right_bars = [bar for bar in self.bars_config.values() if bar.get('section') == 'right']
        
        left_max_pages = max(1, (len(left_bars) + 8) // 9)
        right_max_pages = max(1, (len(right_bars) + 8) // 9)
        
        # Auto-switch to page 1 if current page is now empty (after deletion)
        if self.left_current_page >= left_max_pages and len(left_bars) > 0:
            self.left_current_page = 0  # Switch to page 1 (0-indexed)
        if self.right_current_page >= right_max_pages and len(right_bars) > 0:
            self.right_current_page = 0  # Switch to page 1 (0-indexed)
        
        # Show/hide left section pagination controls
        show_left_pagination = len(left_bars) > 9
        self.left_prev_btn.setVisible(show_left_pagination)
        self.left_next_btn.setVisible(show_left_pagination)
        self.left_page_label.setVisible(show_left_pagination)
        
        if show_left_pagination:
            self.left_prev_btn.setEnabled(self.left_current_page > 0)
            self.left_next_btn.setEnabled(self.left_current_page < left_max_pages - 1)
            self.left_page_label.setText(f"{self.left_current_page + 1}/{left_max_pages}")
        
        # Show/hide right section pagination controls
        show_right_pagination = len(right_bars) > 9
        self.right_prev_btn.setVisible(show_right_pagination)
        self.right_next_btn.setVisible(show_right_pagination)
        self.right_page_label.setVisible(show_right_pagination)
        
        if show_right_pagination:
            self.right_prev_btn.setEnabled(self.right_current_page > 0)
            self.right_next_btn.setEnabled(self.right_current_page < right_max_pages - 1)
            self.right_page_label.setText(f"{self.right_current_page + 1}/{right_max_pages}")
    
    def get_current_page_bars(self, section):
        """Get bars for the current page of a specific section with placeholders to maintain consistent positioning"""
        all_bars = [(bar_id, bar) for bar_id, bar in self.bars_config.items() if bar.get('section') == section]
        
        if section == 'left':
            current_page = self.left_current_page
        else:
            current_page = self.right_current_page
        
        start_index = current_page * 9
        end_index = start_index + 9
        
        # Get the bars for this page
        page_bars = all_bars[start_index:end_index]
        
        # Fill remaining positions with placeholders to always have 9 items
        while len(page_bars) < 9:
            placeholder_id = f"placeholder_{section}_{len(page_bars)}"
            placeholder_bar = {
                'section': section,
                'label': '',
                'is_placeholder': True,
                'low_limit': 0,
                'high_limit': 100,
                'coil_address': 0,
                'device_id': 1,
                'alarm_delay': 5,
                'enable_alarm': False
            }
            page_bars.append((placeholder_id, placeholder_bar))
        
        return page_bars
    
    def mousePressEvent(self, event):
        """Handle mouse clicks for remove buttons and bar configuration"""
        # Handle remove button clicks (developer mode only)
        if self.is_developer_mode_active() and hasattr(self, 'remove_buttons'):
            for bar_id, button_rect in self.remove_buttons.items():
                # Skip placeholder bars
                if bar_id.startswith('placeholder_'):
                    continue
                if button_rect.contains(event.pos()):
                    self.remove_bar(bar_id)
                    return
        
        # Handle bar clicks for configuration (function handles developer mode check internally)
        if hasattr(self, 'bar_rects'):
            for bar_id, bar_rect in self.bar_rects.items():
                # Skip placeholder bars
                if bar_id.startswith('placeholder_'):
                    continue
                if bar_rect.contains(event.pos()):
                    self.open_bar_config(bar_id)
                    return
        
        super().mousePressEvent(event)
    
    def load_config(self):
        """Load configuration from encrypted file"""
        try:
            data = load_encrypted_config("modbus_config.dat")
            if data is not None:
                return data.get("CylinderHead", {
                    "low_limit": 250,
                    "high_limit": 600,
                    "coil_address": 0,
                    "device_id": 5,
                    "alarm_delay": 5,
                    "enable_alarm": True
                })
        except Exception as e:
            print(f"Error loading Cylinder Head config: {e}")
        return {"low_limit": 250, "high_limit": 600, "coil_address": 0, "device_id": 5, "alarm_delay": 5, "enable_alarm": False}
    
    def open_settings(self):
        """Open settings dialog with password protection"""
        # Check if admin is logged in
        admin_logged_in = getattr(self.parent_window, 'admin_logged_in', False)
        
        if not admin_logged_in:
            password, ok = QInputDialog.getText(self, "Administrator Access",
                                               "Enter admin password:",
                                               QLineEdit.Password)
            # Get admin password from parent window
            admin_password = getattr(self.parent_window, 'admin_password', 'admin123')
            if not (ok and password == admin_password):
                if ok:
                    QMessageBox.warning(self, "Access Denied", "Incorrect password!")
                return
        
        # Open configuration dialog
        dialog = CylinderHeadConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Reload configuration
            self.config = self.load_config()
            self.low_limit = self.config.get("low_limit", 250)
            self.high_limit = self.config.get("high_limit", 600)
            self.coil_address = self.config.get("coil_address", 0)
            self.relay_device_id = self.config.get("device_id", 5)
            self.alarm_delay = self.config.get("alarm_delay", 5)
            self.enable_alarm = self.config.get("enable_alarm", True)
            self.alarm_start_time = None  # Reset delay timer on config change
            print(f"Configuration updated: Low={self.low_limit}°C, High={self.high_limit}°C, Device={self.relay_device_id}, Coil={self.coil_address}, Delay={self.alarm_delay}s")
    
    def set_developer_mode(self, enabled):
        """Set developer mode and show/hide developer controls"""
        # Show/hide add button based on developer mode
        self.add_btn.setVisible(enabled)
        # Trigger repaint to show/hide remove buttons
        self.update()
    
    def is_developer_mode_active(self):
        """Check if Developer Mode is currently active from parent window"""
        if self.parent_window and hasattr(self.parent_window, 'developer_mode_active'):
            return self.parent_window.developer_mode_active
        return False
    
    def set_modbus_client(self, client):
        """Set the Modbus client for coil writing"""
        self.modbus_client = client
    
    def check_and_write_alarm(self):
        """Check temperatures and write to coil if alarm conditions are met (with delay)"""
        if not self.enable_alarm or not self.modbus_client:
            return
        
        # Check if any temperature is out of range
        alarm_condition_met = False
        alarm_details = []
        for bar_id, temp in self.current_temperatures.items():
            actual_temp = temp / 10.0
            bar = self.bars_config.get(bar_id, {})
            label = bar.get('label', f'T{bar_id}')
            
            if actual_temp > 0:  # Only check if we have valid data
                if actual_temp < self.low_limit:
                    alarm_condition_met = True
                    alarm_details.append(f"{label}={actual_temp:.1f}°C (LOW, limit={self.low_limit}°C)")
                elif actual_temp > self.high_limit:
                    alarm_condition_met = True
                    alarm_details.append(f"{label}={actual_temp:.1f}°C (HIGH, limit={self.high_limit}°C)")
        
        # Alarm delay logic
        if alarm_condition_met:
            if self.alarm_start_time is None:
                # First time alarm condition triggered - start timer
                self.alarm_start_time = time.time()
                print(f"⏱️ Cylinder Head: Alarm condition detected, starting {self.alarm_delay}s delay timer...")
                return  # Don't trigger yet
            else:
                # Check if enough time has elapsed
                elapsed = time.time() - self.alarm_start_time
                if elapsed < self.alarm_delay:
                    # Still in delay period
                    return  # Don't trigger yet
                # Delay period complete - proceed to trigger alarm
        else:
            # No alarm condition - reset timer
            if self.alarm_start_time is not None:
                print(f"✅ Cylinder Head: Alarm condition cleared before delay expired")
            self.alarm_start_time = None
            # If alarm was active, turn it off
            alarm_condition_met = False
        
        # Only write coil if state has changed
        if alarm_condition_met != self.last_alarm_state:
            try:
                result = self.modbus_client.write_coil(
                    address=self.coil_address,
                    value=alarm_condition_met,
                    device_id=self.relay_device_id
                )
                if result and not result.isError():
                    status = "ON" if alarm_condition_met else "OFF"
                    print(f"\n{'='*60}")
                    print(f"🚨 CYLINDER HEAD ALARM: COIL WRITE SUCCESSFUL")
                    print(f"{'='*60}")
                    print(f"  Device ID: {self.relay_device_id}")
                    print(f"  Coil Address: {self.coil_address}")
                    print(f"  Coil Value: {status}")
                    print(f"  Delay: {self.alarm_delay}s (elapsed)")
                    if alarm_condition_met:
                        print(f"  Alarm Reason(s):")
                        for detail in alarm_details:
                            print(f"    - {detail}")
                    print(f"{'='*60}\n")
                    self.last_alarm_state = alarm_condition_met
                    self.alarm_active = alarm_condition_met
                else:
                    print(f"⚠️ Failed to write coil to Device {self.relay_device_id}, Address {self.coil_address} (Device may not be connected): {result}")
            except Exception as e:
                print(f"⚠️ Cylinder Head: Cannot write alarm coil (Relay device not connected or communication error): {e}")
        else:
            self.alarm_active = alarm_condition_met

    def update_temps(self, values):
        """Update temperature values for bars (legacy compatibility)"""
        # For backward compatibility, map values to existing bars
        bar_ids = sorted(self.bars_config.keys(), key=lambda x: int(x))
        for i, value in enumerate(values):
            if i < len(bar_ids):
                bar_id = bar_ids[i]
                self.target_temperatures[bar_id] = value
    
    def read_individual_bar_data(self, bar_id, bar_config):
        """Read Modbus data for an individual bar"""
        if not self.modbus_client:
            return 0
        
        try:
            address = bar_config.get('address', 0)
            device_id = bar_config.get('device_id', 1)
            reg_type = bar_config.get('type', 'input')
            
            if reg_type == 'input':
                result = self.modbus_client.read_input_registers(address=address, count=1, device_id=device_id)
            elif reg_type == 'holding':
                result = self.modbus_client.read_holding_registers(address=address, count=1, device_id=device_id)
            else:
                print(f"Unsupported register type: {reg_type}")
                return 0
            
            if result and not result.isError():
                return result.registers[0]
            else:
                print(f"Error reading bar {bar_id}: {result}")
                return 0
                
        except Exception as e:
            print(f"Exception reading bar {bar_id}: {e}")
            return 0
    
    def update_all_bars_from_modbus(self):
        """Update all bars with real Modbus data"""
        for bar_id, bar_config in self.bars_config.items():
            value = self.read_individual_bar_data(bar_id, bar_config)
            self.target_temperatures[bar_id] = value
    
    def set_thresholds(self, thresholds):
        """Update temperature thresholds for color logic"""
        self.thresholds = thresholds
    
    def animate_bars(self):
        # Smooth easing animation - NO BOUNCE, pure smooth motion
        easing_factor = 0.08  # Lower = slower, smoother (0.08 = ~2 seconds to reach target)
        threshold = 0.05      # Snap to target when very close
        
        needs_update = False
        
        for bar_id in self.bars_config:
            target = self.target_temperatures.get(bar_id, 0)
            current = self.current_temperatures.get(bar_id, 0.0)
            
            # Calculate distance to target
            distance = target - current
            
            # If very close to target, snap to it
            if abs(distance) < threshold:
                self.current_temperatures[bar_id] = target
            else:
                # Exponential easing - smooth approach with NO overshoot or bounce
                # Move a fraction of the remaining distance each frame
                self.current_temperatures[bar_id] += distance * easing_factor
                needs_update = True
        
        # Animate hover effects with smooth transitions
        hover_easing = 0.15  # Faster easing for hover effects
        for bar_id in self.bars_config:
            # Animate bar hover effects
            target_opacity = 1.0 if self.hovered_bar == bar_id else 0.0
            current_opacity = self.hover_opacity.get(bar_id, 0.0)
            
            # Calculate distance to target opacity
            opacity_distance = target_opacity - current_opacity
            
            # If very close to target, snap to it
            if abs(opacity_distance) < 0.01:
                self.hover_opacity[bar_id] = target_opacity
            else:
                # Smooth opacity transition
                self.hover_opacity[bar_id] += opacity_distance * hover_easing
                needs_update = True
            
            # Animate remove button hover effects
            remove_target_opacity = 1.0 if self.hovered_remove_button == bar_id else 0.0
            remove_current_opacity = self.remove_button_hover_opacity.get(bar_id, 0.0)
            
            # Calculate distance to target opacity for remove button
            remove_opacity_distance = remove_target_opacity - remove_current_opacity
            
            # If very close to target, snap to it
            if abs(remove_opacity_distance) < 0.01:
                self.remove_button_hover_opacity[bar_id] = remove_target_opacity
            else:
                # Smooth opacity transition for remove button
                self.remove_button_hover_opacity[bar_id] += remove_opacity_distance * hover_easing
                needs_update = True
        
        # Check alarm conditions and write coil
        self.check_and_write_alarm()
        
        # Only trigger repaint if values are still changing
        if needs_update:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        width = self.width()
        height = self.height()

        # ---- Calculate responsive dimensions based on screen size ----
        scale_factor = min(width / 1280, height / 500)  # Base reference: 1280x500
        
        scale_top = int(height * 0.15)  # 15% from top
        scale_bottom = int(height * 0.80)  # 80% from top
        scale_height = scale_bottom - scale_top
        
        bar_width = max(20, int(width * 0.028))  # ~2.8% of width
        spacing = max(30, int(width * 0.048))  # ~4.8% of width
        scale_width = max(50, int(width * 0.055))  # ~5.5% of width
        gap_between_scale_and_bars = max(20, int(width * 0.031))  # ~3.1% of width
        section_gap = max(30, int(width * 0.039))  # ~3.9% of width
        
        # Calculate total content width for both sections (based on current page)
        current_left_bars = self.get_current_page_bars('left')
        current_right_bars = self.get_current_page_bars('right')
        left_section_width = len(current_left_bars) * spacing
        right_section_width = len(current_right_bars) * spacing
        total_bars_width = left_section_width + section_gap + right_section_width
        total_content_width = scale_width + gap_between_scale_and_bars + total_bars_width
        
        # Center the content
        offset_x = max(20, (width - total_content_width) // 2)
        scale_left = offset_x + 40
        
        # ---- Draw horizontal grid lines ----
        line_width = max(1, int(scale_factor * 1))
        painter.setPen(QPen(QColor(30, 40, 55, 80), line_width))
        for temp in range(0, 701, 100):
            y = scale_bottom - (temp / 700) * scale_height
            painter.drawLine(scale_left, int(y), 
                           scale_left + gap_between_scale_and_bars + total_bars_width, int(y))

        # ---- Draw Scale (Left) with gradient ----
        # Create gradient from blue (bottom) to red (top)
        scale_gradient = QLinearGradient(scale_left, scale_bottom, scale_left, scale_top)
        scale_gradient.setColorAt(0, QColor(0, 180, 255))      # Blue at bottom (0°C)
        scale_gradient.setColorAt(0.286, QColor(0, 255, 180))  # Green at ~200°C
        scale_gradient.setColorAt(0.571, QColor(255, 180, 0))  # Amber at ~400°C
        scale_gradient.setColorAt(0.857, QColor(255, 60, 100))  # Red at ~600°C
        scale_gradient.setColorAt(1, QColor(255, 60, 100))     # Red at top (700°C)
        
        scale_line_width = max(2, int(scale_factor * 3))
        pen = QPen(scale_gradient, scale_line_width)
        painter.setPen(pen)
        painter.drawLine(scale_left, scale_top, scale_left, scale_bottom)

        # Draw tick marks and labels (every 100°C)
        font_size = max(8, int(10 * scale_factor))
        painter.setFont(QFont("Inter", font_size, QFont.Medium))
        for temp in range(0, 701, 100):
            y = scale_bottom - (temp / 700) * scale_height
            
            # Determine tick color based on temperature
            if temp < 200:
                tick_color = QColor(0, 180, 255, 180)
            elif temp < 400:
                tick_color = QColor(0, 255, 180, 180)
            elif temp < 600:
                tick_color = QColor(255, 180, 0, 180)
            else:
                tick_color = QColor(255, 60, 100, 180)
            
            # Highlight major ticks
            tick_length_major = max(8, int(10 * scale_factor))
            tick_length_minor = max(4, int(6 * scale_factor))
            tick_width_major = max(1, int(2 * scale_factor))
            tick_width_minor = max(1, int(1 * scale_factor))
            
            if temp % 200 == 0:
                painter.setPen(QPen(tick_color, tick_width_major))
                painter.drawLine(scale_left - tick_length_major, int(y), scale_left + tick_length_major, int(y))
                painter.setPen(QColor(200, 220, 240))
            else:
                painter.setPen(QPen(tick_color, tick_width_minor))
                painter.drawLine(scale_left - tick_length_minor, int(y), scale_left + tick_length_minor, int(y))
                painter.setPen(QColor(150, 170, 190))
            
            text_width = max(35, int(42 * scale_factor))
            text_height = max(16, int(20 * scale_factor))
            painter.drawText(scale_left - text_width - 8, int(y) - text_height // 2, text_width, text_height, Qt.AlignRight | Qt.AlignVCenter, f"{temp}")

        # ---- Draw Section Labels ----
        title_font_size = max(10, int(14 * scale_factor))
        painter.setFont(QFont("Inter", title_font_size, QFont.Bold))
        painter.setPen(QColor(255, 255, 255))
        
        # Left section label
        left_section_start = scale_left + gap_between_scale_and_bars
        left_label_center = left_section_start + left_section_width // 2
        label_width = max(180, int(250 * scale_factor))  # Increased width to prevent cutoff
        label_height = max(25, int(30 * scale_factor))
        label_offset = max(35, int(50 * scale_factor))
        # Use elided text to prevent cutoff on small screens
        painter.setFont(QFont("Segoe UI", max(10, int(13 * scale_factor)), QFont.Bold))
        painter.drawText(left_label_center - label_width // 2, scale_top - label_offset, label_width, label_height, Qt.AlignCenter, "CYLINDER HEAD LEFT")
        
        # Right section label
        right_section_start = left_section_start + left_section_width + section_gap
        right_label_center = right_section_start + right_section_width // 2
        painter.drawText(right_label_center - label_width // 2, scale_top - label_offset, label_width, label_height, Qt.AlignCenter, "CYLINDER HEAD RIGHT")
        
        # ---- Draw Temperature Bars ----
        max_bar_height = scale_height

        # Get bars for current page of each section
        left_bars = self.get_current_page_bars('left')
        right_bars = self.get_current_page_bars('right')
        
        # Update pagination controls
        self.update_pagination_controls()
        
        # Draw left section bars
        for i, (bar_id, bar) in enumerate(left_bars):
            bar_x = left_section_start + i * spacing
            self._draw_temperature_bar(painter, bar, bar_id, bar_x, scale_top, scale_bottom, 
                                     bar_width, max_bar_height, scale_factor)
        
        # Draw right section bars
        for i, (bar_id, bar) in enumerate(right_bars):
            bar_x = right_section_start + i * spacing
            self._draw_temperature_bar(painter, bar, bar_id, bar_x, scale_top, scale_bottom, 
                                     bar_width, max_bar_height, scale_factor)
    
    def _draw_temperature_bar(self, painter, bar_config, bar_id, bar_x, scale_top, scale_bottom, 
                             bar_width, max_bar_height, scale_factor):
        """Helper method to draw a single temperature bar"""
        # Check if this is a placeholder bar
        is_placeholder = bar_config.get('is_placeholder', False)
        
        if is_placeholder:
            # Draw only a faint background container for placeholder
            container_rect = QRect(int(bar_x), int(scale_top), bar_width, int(max_bar_height))
            bg_gradient = QLinearGradient(bar_x, scale_top, bar_x, scale_bottom)
            bg_gradient.setColorAt(0, QColor(15, 20, 30, 50))  # Very faint background
            bg_gradient.setColorAt(1, QColor(10, 15, 25, 50))
            painter.setBrush(bg_gradient)
            border_width = max(1, int(1 * scale_factor))
            painter.setPen(QPen(QColor(25, 35, 45, 80), border_width))  # Very faint border
            painter.drawRect(container_rect)
            return  # Don't draw anything else for placeholders
        
        # Get temperature value (convert from raw to actual)
        temp = self.current_temperatures.get(bar_id, 0)
        actual_temp = temp / 10  # Convert to decimal
        
        # Clamp temperature to max scale to prevent overflow
        clamped_temp = min(actual_temp, 700)
        bar_height = (clamped_temp / 700) * max_bar_height
        bar_y = scale_bottom - bar_height

        # Determine color based on 3-color temperature logic (Tony Stark inspired)
        # Warning Yellow = Too Cold (< low_limit)
        # Tech Green = Normal (low_limit <= temp <= high_limit)
        # Repulsor Red = Too Hot (> high_limit)
        if actual_temp <= 0:
            # No data - use dark gray with subtle blue tint
            color = QColor(50, 60, 75)
        elif actual_temp < self.low_limit:
            # Too cold - Warning Yellow (gold alert)
            color = QColor(255, 200, 0)  # #FFC800 - Bright warning yellow/gold
        elif actual_temp <= self.high_limit:
            # Normal - Tech Green (HUD display green)
            color = QColor(0, 255, 180)  # #00FFB4 - Vibrant tech green
        else:
            # Too hot - Repulsor Blast Red (hot red-orange)
            color = QColor(255, 60, 100)  # #FF3C64 - Hot red with energy

        # Draw background container with subtle gradient
        container_rect = QRect(int(bar_x), int(scale_top), bar_width, int(max_bar_height))
        
        # Store bar rectangle for click detection (only for real bars)
        self.bar_rects[bar_id] = container_rect
        
        bg_gradient = QLinearGradient(bar_x, scale_top, bar_x, scale_bottom)
        bg_gradient.setColorAt(0, QColor(20, 30, 45, 100))
        bg_gradient.setColorAt(1, QColor(15, 20, 35, 100))
        painter.setBrush(bg_gradient)
        border_width = max(1, int(1.5 * scale_factor))
        painter.setPen(QPen(QColor(40, 60, 80), border_width))
        painter.drawRect(container_rect)

        # Draw filled bar with gradient
        bar_padding = max(1, int(2 * scale_factor))
        if bar_height > bar_padding:
            bar_rect = QRectF(bar_x + bar_padding, bar_y + bar_padding, bar_width - bar_padding * 2, bar_height - bar_padding)
            bar_gradient = QLinearGradient(bar_x, bar_y, bar_x, scale_bottom)
            bar_gradient.setColorAt(0, color.lighter(110))
            bar_gradient.setColorAt(1, color)
            painter.setBrush(bar_gradient)
            painter.setPen(Qt.NoPen)
            painter.drawRect(bar_rect)

            # Draw outer glow effect
            max_glow = max(2, int(3 * scale_factor))
            for glow_offset in range(max_glow, 0, -1):
                glow_alpha = 20 * (max_glow + 1 - glow_offset)
                glow_color = QColor(color.red(), color.green(), color.blue(), glow_alpha)
                painter.setPen(QPen(glow_color, glow_offset))
                painter.setBrush(Qt.NoBrush)
                glow_rect = QRectF(bar_x - glow_offset, bar_y - glow_offset, 
                                  bar_width + glow_offset * 2, bar_height + glow_offset * 2)
                painter.drawRect(glow_rect)

        # Draw professional hover effect (JetBrains-style)
        hover_opacity = self.hover_opacity.get(bar_id, 0.0)
        if hover_opacity > 0.01:  # Only draw if there's visible hover effect
            # Create subtle highlight overlay on the container
            hover_alpha = int(25 * hover_opacity)  # Max 25 alpha for subtle effect
            hover_color = QColor(100, 150, 255, hover_alpha)  # Soft blue highlight
            
            # Draw hover background overlay
            painter.setBrush(hover_color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(container_rect)
            
            # Draw subtle border highlight
            border_alpha = int(60 * hover_opacity)  # Max 60 alpha for border
            border_color = QColor(120, 170, 255, border_alpha)  # Slightly brighter blue
            border_width = max(1, int(1.5 * scale_factor))
            painter.setPen(QPen(border_color, border_width))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(container_rect)

        # Draw label below bar using the configured label
        painter.setPen(QColor(140, 160, 190))
        label_font_size = max(7, int(9 * scale_factor))
        painter.setFont(QFont("Inter", label_font_size, QFont.Medium))
        label_y_offset = max(12, int(15 * scale_factor))
        label_height = max(16, int(20 * scale_factor))
        painter.drawText(int(bar_x), scale_bottom + label_y_offset, bar_width, label_height, 
                        Qt.AlignCenter, bar_config['label'])

        # Draw digital temperature display below label with color matching bar
        painter.setPen(color)
        temp_font_size = max(8, int(10 * scale_factor))
        painter.setFont(QFont("JetBrains Mono", temp_font_size, QFont.Bold))
        temp_y_offset = max(30, int(38 * scale_factor))
        temp_height = max(18, int(22 * scale_factor))
        temp_width_extra = max(12, int(15 * scale_factor))
        painter.drawText(int(bar_x - temp_width_extra), scale_bottom + temp_y_offset, 
                        bar_width + temp_width_extra * 2, temp_height, Qt.AlignCenter, f"{actual_temp:.1f}°C")
        
        # Draw remove button in developer mode only
        if self.is_developer_mode_active():
            remove_btn_size = max(16, int(20 * scale_factor))
            # Position at the sharp top-right corner of the bar
            remove_btn_x = bar_x + bar_width - remove_btn_size
            remove_btn_y = scale_top
            
            # Store button position for click detection
            if not hasattr(self, 'remove_buttons'):
                self.remove_buttons = {}
            self.remove_buttons[bar_id] = QRect(int(remove_btn_x), int(remove_btn_y), remove_btn_size, remove_btn_size)
            
            # Load and draw the remove image
            try:
                remove_pixmap = QPixmap("imgs/remove.png")
                if not remove_pixmap.isNull():
                    # Scale the image to fit the button size
                    scaled_pixmap = remove_pixmap.scaled(remove_btn_size, remove_btn_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    # Check if this button is being hovered (for hover effect)
                    hover_opacity = getattr(self, 'remove_button_hover_opacity', {}).get(bar_id, 0.0)
                    
                    # Draw hover background if hovering
                    if hover_opacity > 0.01:
                        hover_alpha = int(100 * hover_opacity)
                        painter.setBrush(QColor(255, 255, 255, hover_alpha))
                        painter.setPen(Qt.NoPen)
                        painter.drawRect(int(remove_btn_x), int(remove_btn_y), remove_btn_size, remove_btn_size)
                    
                    # Draw the image
                    painter.drawPixmap(int(remove_btn_x), int(remove_btn_y), scaled_pixmap)
                else:
                    # Fallback to original design if image fails to load
                    painter.setBrush(QColor(220, 50, 50, 180))
                    painter.setPen(QPen(QColor(255, 255, 255), max(1, int(1.5 * scale_factor))))
                    painter.drawEllipse(int(remove_btn_x), int(remove_btn_y), remove_btn_size, remove_btn_size)
                    
                    # Draw X symbol
                    painter.setPen(QPen(QColor(255, 255, 255), max(2, int(2.5 * scale_factor))))
                    margin = remove_btn_size // 4
                    painter.drawLine(int(remove_btn_x + margin), int(remove_btn_y + margin),
                                   int(remove_btn_x + remove_btn_size - margin), int(remove_btn_y + remove_btn_size - margin))
                    painter.drawLine(int(remove_btn_x + remove_btn_size - margin), int(remove_btn_y + margin),
                                   int(remove_btn_x + margin), int(remove_btn_y + remove_btn_size - margin))
            except Exception:
                # Fallback to original design if any error occurs
                painter.setBrush(QColor(220, 50, 50, 180))
                painter.setPen(QPen(QColor(255, 255, 255), max(1, int(1.5 * scale_factor))))
                painter.drawEllipse(int(remove_btn_x), int(remove_btn_y), remove_btn_size, remove_btn_size)
                
                # Draw X symbol
                painter.setPen(QPen(QColor(255, 255, 255), max(2, int(2.5 * scale_factor))))
                margin = remove_btn_size // 4
                painter.drawLine(int(remove_btn_x + margin), int(remove_btn_y + margin),
                               int(remove_btn_x + remove_btn_size - margin), int(remove_btn_y + remove_btn_size - margin))
                painter.drawLine(int(remove_btn_x + remove_btn_size - margin), int(remove_btn_y + margin),
                               int(remove_btn_x + margin), int(remove_btn_y + remove_btn_size - margin))

    def mouseMoveEvent(self, event):
        """Handle mouse movement for hover effects on temperature bars and remove buttons"""
        # Check for remove button hover first (higher priority)
        hovered_remove_button = None
        if self.is_developer_mode_active() and hasattr(self, 'remove_buttons'):
            for bar_id, button_rect in self.remove_buttons.items():
                if button_rect.contains(event.pos()):
                    hovered_remove_button = bar_id
                    break
        
        # Find which bar (if any) the mouse is hovering over (only if not hovering remove button)
        hovered_bar = None
        if not hovered_remove_button:
            for bar_id, bar_rect in self.bar_rects.items():
                if bar_rect.contains(event.pos()):
                    hovered_bar = bar_id
                    break
        
        # Update hover states if they changed
        if self.hovered_bar != hovered_bar:
            self.hovered_bar = hovered_bar
        
        if self.hovered_remove_button != hovered_remove_button:
            self.hovered_remove_button = hovered_remove_button
        
        # Set cursor based on what's being hovered
        if self.is_developer_mode_active() and (hovered_bar or hovered_remove_button):
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        
        super().mouseMoveEvent(event)


# ---------------- Main Bearing Temperature Widget ----------------
class MainBearingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.setMinimumSize(800, 400)
        self.setStyleSheet(CYLINDER_HEAD_BG_STYLE)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Load bar configurations from config file
        self.bars_config = self.load_bars_config()
        
        # Temperature data for each bar (keyed by bar ID)
        self.current_temperatures = {}
        self.target_temperatures = {}
        
        # Animation velocities for smooth transitions
        self.velocities = {}
        
        # Hover state tracking for professional hover effects
        self.hovered_bar = None
        self.hover_opacity = {}  # Track hover opacity for each bar
        self.hovered_remove_button = None  # Track which remove button is hovered
        self.remove_button_hover_opacity = {}  # Track hover opacity for remove buttons
        for bar_id in self.bars_config:
            self.hover_opacity[bar_id] = 0.0
            self.remove_button_hover_opacity[bar_id] = 0.0
        
        # Configuration for 3-color logic
        self.config = self.load_config()
        self.low_limit = self.config.get("low_limit", 80)
        self.high_limit = self.config.get("high_limit", 150)
        self.coil_address = self.config.get("coil_address", 1)
        self.enable_alarm = self.config.get("enable_alarm", True)
        self.relay_device_id = self.config.get("device_id", 5)
        self.alarm_delay = self.config.get("alarm_delay", 5)
        
        # Modbus client reference (will be set by HMIWindow)
        self.modbus_client = None
        
        # Alarm state tracking
        self.alarm_active = False
        self.last_alarm_state = None
        self.alarm_start_time = None
        
        # Storage for clickable areas
        self.bar_rects = {}
        
        # Pagination state (10 bars per page)
        self.bars_per_page = 10
        self.current_page = 0
        
        # UI Elements
        self.setup_ui()
        
        # Initialize pagination controls
        self.update_pagination_controls()
        
        # Animation timer - 60 FPS for ultra-smooth animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_bars)
        self.animation_timer.start(16)  # 16ms = ~60 fps
    
    def setup_ui(self):
        """Setup UI elements including buttons"""
        # Settings button - positioned at top-right
        self.settings_btn = QPushButton("⚙️", self)
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(40, 50, 65), stop:1 rgb(30, 40, 55));
                color: rgb(0, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 20px;
                font-size: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 200, 255), stop:1 rgb(0, 150, 200));
                color: rgb(10, 20, 30);
                border: 2px solid rgb(0, 220, 255);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 150, 200), stop:1 rgb(0, 100, 150));
            }
        """)
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setToolTip("Configure Main Bearing Alarms")
        
        # Add button (+) - Microsoft style design
        self.add_btn = QPushButton("+", self)
        self.add_btn.setFixedSize(30, 200)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(45, 45, 45, 180), stop:1 rgba(60, 60, 60, 180));
                color: rgb(255, 255, 255);
                border: 1px solid rgba(120, 120, 120, 100);
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 120, 215, 180), stop:1 rgba(0, 100, 180, 180));
                border: 1px solid rgba(0, 120, 215, 200);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 90, 158, 200), stop:1 rgba(0, 70, 130, 200));
            }
        """)
        self.add_btn.clicked.connect(self.show_add_bar_dialog)
        self.add_btn.setToolTip("Add New Main Bearing Bar")
        self.add_btn.setVisible(False)  # Hidden by default, shown in developer mode
        
        # Pagination navigation buttons
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(45, 45, 45, 180), stop:1 rgba(60, 60, 60, 180));
                color: rgb(255, 255, 255);
                border: 1px solid rgba(120, 120, 120, 100);
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 120, 215, 180), stop:1 rgba(0, 100, 180, 180));
                border: 1px solid rgba(0, 120, 215, 200);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 90, 158, 200), stop:1 rgba(0, 70, 130, 200));
            }
            QPushButton:disabled {
                background: rgba(30, 30, 30, 100);
                color: rgba(100, 100, 100, 150);
                border: 1px solid rgba(60, 60, 60, 100);
            }
        """
        
        # Previous page button
        self.prev_btn = QPushButton("◀", self)
        self.prev_btn.setFixedSize(30, 30)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setStyleSheet(button_style)
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setVisible(False)
        
        # Next page button
        self.next_btn = QPushButton("▶", self)
        self.next_btn.setFixedSize(30, 30)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setStyleSheet(button_style)
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setVisible(False)
        
        # Page indicator label
        self.page_label = QLabel("Page 1/1", self)
        self.page_label.setStyleSheet("""
            QLabel {
                color: rgb(200, 220, 240);
                font-size: 11px;
                font-weight: bold;
                background: rgba(30, 40, 55, 150);
                border: 1px solid rgba(60, 80, 100, 100);
                border-radius: 3px;
                padding: 2px 6px;
            }
        """)
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setVisible(False)
    
    def resizeEvent(self, event):
        """Handle resize events to update button positions"""
        super().resizeEvent(event)
        self.settings_btn.move(self.width() - 50, 10)
        # Position add button on the right side
        self.add_btn.move(self.width() - 40, (self.height() - 200) // 2)
        
        # Position pagination buttons and labels
        width = self.width()
        height = self.height()
        
        # Calculate center position
        center_x = width // 2
        
        # Position buttons and label horizontally centered at bottom
        button_spacing = 40
        self.prev_btn.move(center_x - button_spacing - 15, height - 50)
        self.next_btn.move(center_x + button_spacing - 15, height - 50)
        self.page_label.move(center_x - 25, height - 50)
        self.page_label.setFixedSize(50, 30)
    
    def load_config(self):
        """Load configuration from encrypted file"""
        try:
            data = load_encrypted_config("modbus_config.dat")
            if data is not None:
                return data.get("MainBearing", {
                    "low_limit": 80,
                    "high_limit": 150,
                    "coil_address": 1,
                    "device_id": 5,
                    "alarm_delay": 5,
                    "enable_alarm": True
                })
        except Exception as e:
            print(f"Error loading Main Bearing config: {e}")
        return {"low_limit": 80, "high_limit": 150, "coil_address": 1, "device_id": 5, "alarm_delay": 5, "enable_alarm": False}
    
    def load_bars_config(self):
        """Load bar configurations from encrypted file"""
        try:
            data = load_encrypted_config("modbus_config.dat")
            if data is not None and "MainBearingBars" in data:
                return data["MainBearingBars"]
        except Exception as e:
            print(f"Error loading Main Bearing bars config: {e}")
        
        # Return default configuration if not found
        return self.create_default_bars_config()
    
    def create_default_bars_config(self):
        """Create default 10 bars configuration"""
        bars_config = {}
        
        # 10 bars - addresses 0-9, device 4
        for i in range(10):
            bars_config[str(i)] = {
                "label": f"B{i+1}",
                "address": i,
                "device_id": 4,
                "type": "input"
            }
        
        return bars_config
    
    def save_bars_config(self):
        """Save bar configurations to encrypted file"""
        try:
            data = load_encrypted_config("modbus_config.dat") or {}
            data["MainBearingBars"] = self.bars_config
            save_encrypted_config(data, "modbus_config.dat")
            print("Main Bearing bars configuration saved successfully")
        except Exception as e:
            print(f"Error saving Main Bearing bars config: {e}")
    
    def open_settings(self):
        """Open settings dialog with password protection"""
        # Check if admin is logged in
        admin_logged_in = getattr(self.parent_window, 'admin_logged_in', False)
        
        if not admin_logged_in:
            password, ok = QInputDialog.getText(self, "Administrator Access",
                                               "Enter admin password:",
                                               QLineEdit.Password)
            # Get admin password from parent window
            admin_password = getattr(self.parent_window, 'admin_password', 'admin123')
            if not (ok and password == admin_password):
                if ok:
                    QMessageBox.warning(self, "Access Denied", "Incorrect password!")
                return
        
        # Open configuration dialog
        dialog = MainBearingConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Reload configuration
            self.config = self.load_config()
            self.low_limit = self.config.get("low_limit", 80)
            self.high_limit = self.config.get("high_limit", 150)
            self.coil_address = self.config.get("coil_address", 1)
            self.relay_device_id = self.config.get("device_id", 5)
            self.alarm_delay = self.config.get("alarm_delay", 5)
            self.enable_alarm = self.config.get("enable_alarm", True)
            self.alarm_start_time = None  # Reset delay timer on config change
            print(f"Main Bearing Configuration updated: Low={self.low_limit}°C, High={self.high_limit}°C, Device={self.relay_device_id}, Coil={self.coil_address}, Delay={self.alarm_delay}s")
    
    def set_developer_mode(self, enabled):
        """Set developer mode and show/hide developer controls"""
        self.add_btn.setVisible(enabled)
        self.update()
    
    def is_developer_mode_active(self):
        """Check if Developer Mode is currently active from parent window"""
        if self.parent_window and hasattr(self.parent_window, 'developer_mode_active'):
            return self.parent_window.developer_mode_active
        return False
    
    def show_add_bar_dialog(self):
        """Show dialog to add a new bar"""
        if not self.is_developer_mode_active():
            QMessageBox.warning(self, "Access Restricted", 
                               "🔒 This modification feature requires Developer Mode to be activated.\n\n"
                               "Please enable Developer Mode to add new bearing bars.")
            return
        
        # Find next available bar ID
        existing_ids = [int(k) for k in self.bars_config.keys() if k.isdigit()]
        next_id = max(existing_ids) + 1 if existing_ids else 0
        
        # Create new bar with default configuration
        new_bar_config = {
            "label": f"B{next_id + 1}",
            "address": next_id,
            "device_id": 4,
            "type": "input"
        }
        
        # Open configuration dialog
        dialog = MainBearingBarConfigDialog(self, new_bar_config, next_id)
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_config()
            self.bars_config[str(next_id)] = config
            self.save_bars_config()
            
            # Initialize temperature data for new bar
            self.current_temperatures[str(next_id)] = 0
            self.target_temperatures[str(next_id)] = 0
            self.velocities[str(next_id)] = 0.0
            
            # Update pagination
            self.update_pagination_controls()
            self.update()
            
            QMessageBox.information(self, "Bar Added", 
                                   f"New bearing bar '{config['label']}' added successfully!")
    
    def remove_bar(self, bar_id):
        """Remove a bearing bar with confirmation"""
        if not self.is_developer_mode_active():
            QMessageBox.warning(self, "Access Restricted", 
                               "🔒 This modification feature requires Developer Mode to be activated.\n\n"
                               "Please enable Developer Mode to remove bearing bars.")
            return
        
        bar = self.bars_config.get(bar_id, {})
        label = bar.get('label', f'B{bar_id}')
        
        reply = QMessageBox.question(self, "Remove Bar", 
                                    f"Are you sure you want to remove bearing bar '{label}'?\n\n"
                                    f"This action cannot be undone.",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Remove from configuration
            if bar_id in self.bars_config:
                del self.bars_config[bar_id]
                self.save_bars_config()
            
            # Remove from temperature data
            if bar_id in self.current_temperatures:
                del self.current_temperatures[bar_id]
            if bar_id in self.target_temperatures:
                del self.target_temperatures[bar_id]
            if bar_id in self.velocities:
                del self.velocities[bar_id]
            
            # Update pagination
            self.update_pagination_controls()
            self.update()
            
            QMessageBox.information(self, "Bar Removed", 
                                   f"Bearing bar '{label}' removed successfully!")
    
    def open_bar_config(self, bar_id):
        """Open configuration dialog for a specific bar"""
        if not self.is_developer_mode_active():
            QMessageBox.warning(self, "Access Restricted", 
                               "🔒 This modification feature requires Developer Mode to be activated.\n\n"
                               "Please enable Developer Mode to configure bearing bars.")
            return
        
        bar_config = self.bars_config.get(bar_id, {})
        dialog = MainBearingBarConfigDialog(self, bar_config, bar_id)
        
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_config()
            self.bars_config[bar_id] = config
            self.save_bars_config()
            self.update()
            
            QMessageBox.information(self, "Configuration Saved", 
                                   f"Configuration for bearing bar '{config['label']}' saved successfully!")
    
    def update_pagination_controls(self):
        """Update pagination button states and visibility"""
        total_bars = len(self.bars_config)
        total_pages = (total_bars + self.bars_per_page - 1) // self.bars_per_page if total_bars > 0 else 1
        
        # Auto-switch to page 1 if current page is now empty (after deletion)
        if self.current_page >= total_pages and total_pages > 0:
            self.current_page = 0  # Switch to page 1 (0-indexed)
        
        # Show pagination controls only if more than one page
        show_pagination = total_pages > 1
        self.prev_btn.setVisible(show_pagination)
        self.next_btn.setVisible(show_pagination)
        self.page_label.setVisible(show_pagination)
        
        if show_pagination:
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < total_pages - 1)
            self.page_label.setText(f"Page {self.current_page + 1}/{total_pages}")
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_pagination_controls()
            self.update()
    
    def next_page(self):
        """Go to next page"""
        total_bars = len(self.bars_config)
        total_pages = (total_bars + self.bars_per_page - 1) // self.bars_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_pagination_controls()
            self.update()
    
    def get_visible_bars(self):
        """Get bars for current page"""
        all_bars = sorted(self.bars_config.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
        start_idx = self.current_page * self.bars_per_page
        end_idx = start_idx + self.bars_per_page
        return all_bars[start_idx:end_idx]
    
    def mousePressEvent(self, event):
        """Handle mouse clicks for remove buttons and bar configuration"""
        # Handle remove button clicks (developer mode only)
        if self.is_developer_mode_active() and hasattr(self, 'remove_buttons'):
            for bar_id, button_rect in self.remove_buttons.items():
                if button_rect.contains(event.pos()):
                    self.remove_bar(bar_id)
                    return
        
        # Handle bar clicks for configuration (developer mode only)
        if self.is_developer_mode_active():
            for bar_id, bar_rect in self.bar_rects.items():
                if bar_rect.contains(event.pos()):
                    self.open_bar_config(bar_id)
                    return
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement for hover effects on temperature bars and remove buttons"""
        # Check for remove button hover first (higher priority)
        hovered_remove_button = None
        if self.is_developer_mode_active() and hasattr(self, 'remove_buttons'):
            for bar_id, button_rect in self.remove_buttons.items():
                if button_rect.contains(event.pos()):
                    hovered_remove_button = bar_id
                    break
        
        # Find which bar (if any) the mouse is hovering over (only if not hovering remove button)
        hovered_bar = None
        if not hovered_remove_button:
            for bar_id, bar_rect in self.bar_rects.items():
                if bar_rect.contains(event.pos()):
                    hovered_bar = bar_id
                    break
        
        # Update hover states if they changed
        if self.hovered_bar != hovered_bar:
            self.hovered_bar = hovered_bar
        
        if self.hovered_remove_button != hovered_remove_button:
            self.hovered_remove_button = hovered_remove_button
        
        # Set cursor based on what's being hovered
        if self.is_developer_mode_active() and (hovered_bar or hovered_remove_button):
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        
        super().mouseMoveEvent(event)
    
    def set_modbus_client(self, client):
        """Set the Modbus client for coil writing"""
        self.modbus_client = client
    
    def check_and_write_alarm(self):
        """Check temperatures and write to coil if alarm conditions are met (with delay)"""
        if not self.enable_alarm or not self.modbus_client:
            return
        
        # Check if any temperature is out of range
        alarm_condition_met = False
        alarm_details = []
        for bar_id, temp in self.current_temperatures.items():
            actual_temp = temp / 10.0
            bar = self.bars_config.get(bar_id, {})
            label = bar.get('label', f'B{bar_id}')
            
            if actual_temp > 0:  # Only check if we have valid data
                if actual_temp < self.low_limit:
                    alarm_condition_met = True
                    alarm_details.append(f"{label}={actual_temp:.1f}°C (LOW, limit={self.low_limit}°C)")
                elif actual_temp > self.high_limit:
                    alarm_condition_met = True
                    alarm_details.append(f"{label}={actual_temp:.1f}°C (HIGH, limit={self.high_limit}°C)")
        
        # Alarm delay logic
        if alarm_condition_met:
            if self.alarm_start_time is None:
                # First time alarm condition triggered - start timer
                self.alarm_start_time = time.time()
                print(f"⏱️ Main Bearing: Alarm condition detected, starting {self.alarm_delay}s delay timer...")
                return  # Don't trigger yet
            else:
                # Check if enough time has elapsed
                elapsed = time.time() - self.alarm_start_time
                if elapsed < self.alarm_delay:
                    # Still in delay period
                    return  # Don't trigger yet
                # Delay period complete - proceed to trigger alarm
        else:
            # No alarm condition - reset timer
            if self.alarm_start_time is not None:
                print(f"✅ Main Bearing: Alarm condition cleared before delay expired")
            self.alarm_start_time = None
            # If alarm was active, turn it off
            alarm_condition_met = False
        
        # Only write coil if state has changed
        if alarm_condition_met != self.last_alarm_state:
            try:
                result = self.modbus_client.write_coil(
                    address=self.coil_address,
                    value=alarm_condition_met,
                    device_id=self.relay_device_id
                )
                if result and not result.isError():
                    status = "ON" if alarm_condition_met else "OFF"
                    print(f"\n{'='*60}")
                    print(f"🚨 MAIN BEARING ALARM: COIL WRITE SUCCESSFUL")
                    print(f"{'='*60}")
                    print(f"  Device ID: {self.relay_device_id}")
                    print(f"  Coil Address: {self.coil_address}")
                    print(f"  Coil Value: {status}")
                    print(f"  Delay: {self.alarm_delay}s (elapsed)")
                    if alarm_condition_met:
                        print(f"  Alarm Reason(s):")
                        for detail in alarm_details:
                            print(f"    - {detail}")
                    print(f"{'='*60}\n")
                    self.last_alarm_state = alarm_condition_met
                    self.alarm_active = alarm_condition_met
                else:
                    print(f"⚠️ Failed to write coil to Device {self.relay_device_id}, Address {self.coil_address} (Device may not be connected): {result}")
            except Exception as e:
                print(f"⚠️ Main Bearing: Cannot write alarm coil (Relay device not connected or communication error): {e}")
        else:
            self.alarm_active = alarm_condition_met

    def update_temps(self, values):
        """Update temperature values from Modbus data"""
        # Update target temperatures for all configured bars
        for i, (bar_id, bar_config) in enumerate(self.bars_config.items()):
            if i < len(values):
                self.target_temperatures[bar_id] = values[i]
            else:
                self.target_temperatures[bar_id] = 0
    
    def set_thresholds(self, thresholds):
        """Update temperature thresholds for color logic"""
        self.thresholds = thresholds
    
    def animate_bars(self):
        """Smooth easing animation"""
        easing_factor = 0.08
        threshold = 0.05
        
        needs_update = False
        
        for bar_id in self.bars_config.keys():
            target = self.target_temperatures.get(bar_id, 0)
            current = self.current_temperatures.get(bar_id, 0.0)
            
            distance = target - current
            
            if abs(distance) < threshold:
                self.current_temperatures[bar_id] = target
            else:
                self.current_temperatures[bar_id] += distance * easing_factor
                needs_update = True
        
        # Animate hover effects with smooth transitions
        hover_easing = 0.15  # Faster easing for hover effects
        for bar_id in self.bars_config:
            # Animate bar hover effects
            target_opacity = 1.0 if self.hovered_bar == bar_id else 0.0
            current_opacity = self.hover_opacity.get(bar_id, 0.0)
            
            # Calculate distance to target opacity
            opacity_distance = target_opacity - current_opacity
            
            # If very close to target, snap to it
            if abs(opacity_distance) < 0.01:
                self.hover_opacity[bar_id] = target_opacity
            else:
                # Smooth opacity transition
                self.hover_opacity[bar_id] += opacity_distance * hover_easing
                needs_update = True
            
            # Animate remove button hover effects
            remove_target_opacity = 1.0 if self.hovered_remove_button == bar_id else 0.0
            remove_current_opacity = self.remove_button_hover_opacity.get(bar_id, 0.0)
            
            # Calculate distance to target opacity for remove button
            remove_opacity_distance = remove_target_opacity - remove_current_opacity
            
            # If very close to target, snap to it
            if abs(remove_opacity_distance) < 0.01:
                self.remove_button_hover_opacity[bar_id] = remove_target_opacity
            else:
                # Smooth opacity transition for remove button
                self.remove_button_hover_opacity[bar_id] += remove_opacity_distance * hover_easing
                needs_update = True
        
        # Check alarm conditions
        self.check_and_write_alarm()
        
        if needs_update:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        width = self.width()
        height = self.height()

        # ---- Calculate responsive dimensions based on screen size ----
        scale_factor = min(width / 1280, height / 500)  # Base reference: 1280x500
        
        scale_top = int(height * 0.15)  # 15% from top
        scale_bottom = int(height * 0.80)  # 80% from top
        scale_height = scale_bottom - scale_top
        
        bar_width = max(30, int(width * 0.039))  # ~3.9% of width
        spacing = max(50, int(width * 0.066))  # ~6.6% of width
        scale_width = max(50, int(width * 0.055))  # ~5.5% of width
        gap_between_scale_and_bars = max(20, int(width * 0.031))  # ~3.1% of width
        
        # Get visible bars for current page
        visible_bars = self.get_visible_bars()
        num_visible = len(visible_bars)
        
        if num_visible == 0:
            # No bars to display
            painter.setPen(QColor(150, 170, 190))
            painter.setFont(QFont("Inter", 14))
            painter.drawText(0, 0, width, height, Qt.AlignCenter, "No bearing bars configured")
            return
        
        # Calculate total content width
        total_bars_width = num_visible * spacing
        total_content_width = scale_width + gap_between_scale_and_bars + total_bars_width
        
        # Center the content
        offset_x = max(20, (width - total_content_width) // 2)
        scale_left = offset_x + 40
        
        # ---- Draw horizontal grid lines ----
        line_width = max(1, int(scale_factor * 1))
        painter.setPen(QPen(QColor(30, 40, 55, 80), line_width))
        for temp in range(0, 301, 50):
            y = scale_bottom - (temp / 300) * scale_height
            painter.drawLine(scale_left, int(y), 
                           scale_left + gap_between_scale_and_bars + total_bars_width, int(y))

        # ---- Draw Scale (Left) with gradient ----
        scale_gradient = QLinearGradient(scale_left, scale_bottom, scale_left, scale_top)
        scale_gradient.setColorAt(0, QColor(0, 180, 255))      # Blue at bottom (0°C)
        scale_gradient.setColorAt(0.667, QColor(0, 255, 180))  # Green at ~200°C
        scale_gradient.setColorAt(1, QColor(255, 180, 0))      # Amber at 300°C
        
        scale_line_width = max(2, int(scale_factor * 3))
        pen = QPen(scale_gradient, scale_line_width)
        painter.setPen(pen)
        painter.drawLine(scale_left, scale_top, scale_left, scale_bottom)

        # Draw tick marks and labels (every 50°C)
        font_size = max(8, int(10 * scale_factor))
        painter.setFont(QFont("Inter", font_size, QFont.Medium))
        for temp in range(0, 301, 50):
            y = scale_bottom - (temp / 300) * scale_height
            
            # Determine tick color based on temperature
            if temp < 100:
                tick_color = QColor(0, 180, 255, 180)
            elif temp < 200:
                tick_color = QColor(0, 255, 180, 180)
            else:
                tick_color = QColor(255, 180, 0, 180)
            
            # Highlight major ticks (every 100°C)
            tick_length_major = max(8, int(10 * scale_factor))
            tick_length_minor = max(4, int(6 * scale_factor))
            tick_width_major = max(1, int(2 * scale_factor))
            tick_width_minor = max(1, int(1 * scale_factor))
            
            if temp % 100 == 0:
                painter.setPen(QPen(tick_color, tick_width_major))
                painter.drawLine(scale_left - tick_length_major, int(y), scale_left + tick_length_major, int(y))
                painter.setPen(QColor(200, 220, 240))
            else:
                painter.setPen(QPen(tick_color, tick_width_minor))
                painter.drawLine(scale_left - tick_length_minor, int(y), scale_left + tick_length_minor, int(y))
                painter.setPen(QColor(150, 170, 190))
            
            text_width = max(35, int(42 * scale_factor))
            text_height = max(16, int(20 * scale_factor))
            painter.drawText(scale_left - text_width - 8, int(y) - text_height // 2, text_width, text_height, Qt.AlignRight | Qt.AlignVCenter, f"{temp}")

        # ---- Draw Section Label ----
        title_font_size = max(10, int(14 * scale_factor))
        painter.setFont(QFont("Inter", title_font_size, QFont.Bold))
        painter.setPen(QColor(255, 255, 255))
        
        # Center label
        bars_start = scale_left + gap_between_scale_and_bars
        label_center = bars_start + total_bars_width // 2
        label_width = max(250, int(350 * scale_factor))  # Increased width to prevent cutoff
        label_height = max(25, int(30 * scale_factor))
        label_offset = max(35, int(50 * scale_factor))
        painter.setFont(QFont("Segoe UI", max(10, int(13 * scale_factor)), QFont.Bold))
        painter.drawText(label_center - label_width // 2, scale_top - label_offset, label_width, label_height, Qt.AlignCenter, "MAIN BEARING TEMPERATURE")
        
        # ---- Draw Temperature Bars ----
        max_bar_height = scale_height
        
        # Clear bar rects and remove buttons for click detection
        self.bar_rects = {}
        self.remove_buttons = {}

        for i, (bar_id, bar_config) in enumerate(visible_bars):
            bar_x = bars_start + i * spacing
            
            temp = self.current_temperatures.get(bar_id, 0)
            actual_temp = temp / 10  # Convert to decimal
            clamped_temp = min(actual_temp, 300)
            bar_height = (clamped_temp / 300) * max_bar_height
            bar_y = scale_bottom - bar_height
            
            # Store bar rectangle for click detection
            self.bar_rects[bar_id] = QRect(int(bar_x), int(scale_top), bar_width, int(max_bar_height))

            # Determine color based on 3-color temperature logic
            if actual_temp <= 0:
                color = QColor(50, 60, 75)
            elif actual_temp < self.low_limit:
                color = QColor(255, 200, 0)
            elif actual_temp <= self.high_limit:
                color = QColor(0, 255, 180)
            else:
                color = QColor(255, 60, 100)

            # Draw background container with subtle gradient
            container_rect = QRect(int(bar_x), int(scale_top), bar_width, int(max_bar_height))
            bg_gradient = QLinearGradient(bar_x, scale_top, bar_x, scale_bottom)
            bg_gradient.setColorAt(0, QColor(20, 30, 45, 100))
            bg_gradient.setColorAt(1, QColor(15, 20, 35, 100))
            painter.setBrush(bg_gradient)
            border_width = max(1, int(1.5 * scale_factor))
            painter.setPen(QPen(QColor(40, 60, 80), border_width))
            painter.drawRect(container_rect)

            # Draw filled bar with gradient
            bar_padding = max(1, int(2 * scale_factor))
            if bar_height > bar_padding:
                bar_rect = QRectF(bar_x + bar_padding, bar_y + bar_padding, bar_width - bar_padding * 2, bar_height - bar_padding)
                bar_gradient = QLinearGradient(bar_x, bar_y, bar_x, scale_bottom)
                bar_gradient.setColorAt(0, color.lighter(110))
                bar_gradient.setColorAt(1, color)
                painter.setBrush(bar_gradient)
                painter.setPen(Qt.NoPen)
                painter.drawRect(bar_rect)

                # Draw outer glow effect
                max_glow = max(2, int(3 * scale_factor))
                for glow_offset in range(max_glow, 0, -1):
                    glow_alpha = 20 * (max_glow + 1 - glow_offset)
                    glow_color = QColor(color.red(), color.green(), color.blue(), glow_alpha)
                    painter.setPen(QPen(glow_color, glow_offset))
                    painter.setBrush(Qt.NoBrush)
                    glow_rect = QRectF(bar_x - glow_offset, bar_y - glow_offset, 
                                      bar_width + glow_offset * 2, bar_height + glow_offset * 2)
                    painter.drawRect(glow_rect)

            # Draw professional hover effect (JetBrains-style)
            hover_opacity = self.hover_opacity.get(bar_id, 0.0)
            if hover_opacity > 0.01:  # Only draw if there's visible hover effect
                # Create subtle highlight overlay on the container
                hover_alpha = int(25 * hover_opacity)  # Max 25 alpha for subtle effect
                hover_color = QColor(100, 150, 255, hover_alpha)  # Soft blue highlight
                
                # Draw hover background overlay
                painter.setBrush(hover_color)
                painter.setPen(Qt.NoPen)
                painter.drawRect(container_rect)
                
                # Draw subtle border highlight
                border_alpha = int(60 * hover_opacity)  # Max 60 alpha for border
                border_color = QColor(120, 170, 255, border_alpha)  # Slightly brighter blue
                border_width = max(1, int(1.5 * scale_factor))
                painter.setPen(QPen(border_color, border_width))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(container_rect)

            # Draw label below bar
            label = bar_config.get('label', f'B{bar_id}')
            painter.setPen(QColor(140, 160, 190))
            label_font_size = max(7, int(9 * scale_factor))
            painter.setFont(QFont("Inter", label_font_size, QFont.Medium))
            label_y_offset = max(12, int(15 * scale_factor))
            label_height = max(16, int(20 * scale_factor))
            painter.drawText(int(bar_x), scale_bottom + label_y_offset, bar_width, label_height, Qt.AlignCenter, label)
            
            # Draw remove button in developer mode only
            if self.is_developer_mode_active():
                remove_btn_size = max(16, int(20 * scale_factor))
                # Position at the sharp top-right corner of the bar
                remove_btn_x = bar_x + bar_width - remove_btn_size
                remove_btn_y = scale_top
                
                # Store button rect for click detection
                self.remove_buttons[bar_id] = QRect(int(remove_btn_x), int(remove_btn_y), remove_btn_size, remove_btn_size)
                
                # Load and draw the remove image
                try:
                    remove_pixmap = QPixmap("imgs/remove.png")
                    if not remove_pixmap.isNull():
                        # Scale the image to fit the button size
                        scaled_pixmap = remove_pixmap.scaled(remove_btn_size, remove_btn_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        
                        # Check if this button is being hovered (for hover effect)
                        hover_opacity = getattr(self, 'remove_button_hover_opacity', {}).get(bar_id, 0.0)
                        
                        # Draw hover background if hovering
                        if hover_opacity > 0.01:
                            hover_alpha = int(100 * hover_opacity)
                            painter.setBrush(QColor(255, 255, 255, hover_alpha))
                            painter.setPen(Qt.NoPen)
                            painter.drawRect(int(remove_btn_x), int(remove_btn_y), remove_btn_size, remove_btn_size)
                        
                        # Draw the image
                        painter.drawPixmap(int(remove_btn_x), int(remove_btn_y), scaled_pixmap)
                    else:
                        # Fallback to original design if image fails to load
                        painter.setBrush(QColor(255, 60, 60, 200))
                        painter.setPen(QPen(QColor(255, 255, 255), 1))
                        painter.drawEllipse(int(remove_btn_x), int(remove_btn_y), remove_btn_size, remove_btn_size)
                        
                        # Draw X
                        painter.setPen(QPen(QColor(255, 255, 255), 2))
                        margin = remove_btn_size // 4
                        painter.drawLine(int(remove_btn_x + margin), int(remove_btn_y + margin),
                                       int(remove_btn_x + remove_btn_size - margin), int(remove_btn_y + remove_btn_size - margin))
                        painter.drawLine(int(remove_btn_x + remove_btn_size - margin), int(remove_btn_y + margin),
                                       int(remove_btn_x + margin), int(remove_btn_y + remove_btn_size - margin))
                except Exception:
                    # Fallback to original design if any error occurs
                    painter.setBrush(QColor(255, 60, 60, 200))
                    painter.setPen(QPen(QColor(255, 255, 255), 1))
                    painter.drawEllipse(int(remove_btn_x), int(remove_btn_y), remove_btn_size, remove_btn_size)
                    
                    # Draw X
                    painter.setPen(QPen(QColor(255, 255, 255), 2))
                    margin = remove_btn_size // 4
                    painter.drawLine(int(remove_btn_x + margin), int(remove_btn_y + margin),
                                   int(remove_btn_x + remove_btn_size - margin), int(remove_btn_y + remove_btn_size - margin))
                    painter.drawLine(int(remove_btn_x + remove_btn_size - margin), int(remove_btn_y + margin),
                                   int(remove_btn_x + margin), int(remove_btn_y + remove_btn_size - margin))

            # Draw digital temperature display below label with color matching bar
            painter.setPen(color)
            temp_font_size = max(8, int(10 * scale_factor))
            painter.setFont(QFont("JetBrains Mono", temp_font_size, QFont.Bold))
            temp_y_offset = max(30, int(38 * scale_factor))
            temp_height = max(18, int(22 * scale_factor))
            temp_width_extra = max(12, int(15 * scale_factor))
            painter.drawText(int(bar_x - temp_width_extra), scale_bottom + temp_y_offset, bar_width + temp_width_extra * 2, temp_height, Qt.AlignCenter, f"{actual_temp:.1f}°C")

        painter.end()
    
    def mousePressEvent(self, event):
        """Handle mouse clicks for remove buttons and bar configuration"""
        # Handle remove button clicks (developer mode only)
        if self.is_developer_mode_active() and hasattr(self, 'remove_buttons'):
            for bar_id, button_rect in self.remove_buttons.items():
                if button_rect.contains(event.pos()):
                    self.remove_bar(bar_id)
                    return
        
        # Handle bar clicks for configuration (developer mode only)
        if self.is_developer_mode_active():
            for bar_id, bar_rect in self.bar_rects.items():
                if bar_rect.contains(event.pos()):
                    self.open_bar_config(bar_id)
                    return
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement for hover effects on temperature bars"""
        # Find which bar (if any) the mouse is hovering over
        hovered_bar = None
        for bar_id, bar_rect in self.bar_rects.items():
            if bar_rect.contains(event.pos()):
                hovered_bar = bar_id
                break
        
        # Update hover state if it changed
        if self.hovered_bar != hovered_bar:
            self.hovered_bar = hovered_bar
            # Set cursor to pointer when hovering over bars in developer mode
            if self.is_developer_mode_active() and hovered_bar:
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        
        super().mouseMoveEvent(event)


# ---------------- Circular Pressure Gauge Widget ----------------
class CircularPressureGauge(QWidget):
    def __init__(self, label, max_value=10, reverse_colors=False, gauge_index=0, parent_window=None):
        super().__init__()
        self.label = label
        self.parent_window = parent_window
        self.max_value = max_value
        self.reverse_colors = reverse_colors  # For gauges where low values are dangerous (like oil pressure)
        self.gauge_index = gauge_index
        self.current_value = 0.0
        self.target_value = 0.0
        self.setMinimumSize(220, 250)
        self.setCursor(Qt.PointingHandCursor)  # Show clickable cursor
        
        # Load configuration from JSON
        self.config = self.load_config()
        self.low_limit = self.config.get("low_limit", 2.0)
        self.high_limit = self.config.get("high_limit", 8.0)
        self.enable_alarm = self.config.get("enable_alarm", True)
        self.relay_device_id = self.config.get("device_id", 5)
        # Default: Coil 3 for Lube Oil (index 1), Coil 2 for others
        default_coil = 3 if gauge_index == 1 else 2
        self.coil_address = self.config.get("coil_address", default_coil)
        self.alarm_delay = self.config.get("alarm_delay", 5)
        
        # Modbus client reference (will be set by EnginePressuresTab)
        self.modbus_client = None
        
        # Alarm state tracking
        self.alarm_active = False
        self.last_alarm_state = None
        self.alarm_start_time = None  # Track when alarm condition first occurred
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_value)
        self.animation_timer.start(16)  # 60 FPS
    
    def load_config(self):
        """Load configuration from modbus_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modbus_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    gauges_config = data.get("PressureGauges", {})
                    return gauges_config.get(str(self.gauge_index), {
                        "low_limit": 2.0,
                        "high_limit": 8.0,
                        "enable_alarm": True
                    })
        except Exception as e:
            print(f"Error loading pressure gauge {self.gauge_index} config: {e}")
        return {"low_limit": 2.0, "high_limit": 8.0, "enable_alarm": False}
    
    def mousePressEvent(self, event):
        """Handle mouse click to open configuration dialog"""
        if event.button() == Qt.LeftButton:
            # Check if admin is logged in
            admin_logged_in = getattr(self.parent_window, 'admin_logged_in', False)
            
            if not admin_logged_in:
                password, ok = QInputDialog.getText(self, "Administrator Access",
                                                   "Enter admin password:",
                                                   QLineEdit.Password)
                # Get admin password from parent window
                admin_password = getattr(self.parent_window, 'admin_password', 'admin123')
                if not (ok and password == admin_password):
                    if ok:
                        QMessageBox.warning(self, "Access Denied", "Incorrect password!")
                    return
            
            # Open configuration dialog
            dialog = PressureGaugeConfigDialog(self, gauge_index=self.gauge_index, gauge_label=self.label)
            if dialog.exec_() == QDialog.Accepted:
                # Reload configuration
                self.config = self.load_config()
                self.low_limit = self.config.get("low_limit", 2.0)
                self.high_limit = self.config.get("high_limit", 8.0)
                self.relay_device_id = self.config.get("device_id", 5)
                default_coil = 3 if self.gauge_index == 1 else 2
                self.coil_address = self.config.get("coil_address", default_coil)
                self.alarm_delay = self.config.get("alarm_delay", 5)
                self.enable_alarm = self.config.get("enable_alarm", True)
                self.alarm_start_time = None  # Reset delay timer on config change
                new_label = self.config.get("label", self.label)
                if new_label != self.label:
                    self.label = new_label
                    print(f"Gauge label updated to: {self.label}")
                self.update()  # Trigger repaint to show new label
                print(f"{self.label} Configuration updated: Low={self.low_limit} bar, High={self.high_limit} bar, Device={self.relay_device_id}, Coil={self.coil_address}, Delay={self.alarm_delay}s")
    
    def set_modbus_client(self, client):
        """Set the Modbus client for coil writing"""
        self.modbus_client = client
    
    def check_and_write_alarm(self):
        """Check pressure and write to coil if alarm conditions are met (with delay)"""
        if not self.enable_alarm or not self.modbus_client:
            return
        
        # Check if pressure is out of range
        alarm_condition_met = False
        alarm_reason = ""
        
        if self.current_value > 0:  # Only check if we have valid data
            if self.current_value < self.low_limit:
                alarm_condition_met = True
                alarm_reason = f"{self.current_value:.1f} bar (LOW, limit={self.low_limit} bar)"
            elif self.current_value > self.high_limit:
                alarm_condition_met = True
                alarm_reason = f"{self.current_value:.1f} bar (HIGH, limit={self.high_limit} bar)"
        
        # Alarm delay logic
        if alarm_condition_met:
            if self.alarm_start_time is None:
                # First time alarm condition triggered - start timer
                self.alarm_start_time = time.time()
                print(f"⏱️ {self.label}: Alarm condition detected, starting {self.alarm_delay}s delay timer...")
                return  # Don't trigger yet
            else:
                # Check if enough time has elapsed
                elapsed = time.time() - self.alarm_start_time
                if elapsed < self.alarm_delay:
                    # Still in delay period
                    return  # Don't trigger yet
                # Delay period complete - proceed to trigger alarm
        else:
            # No alarm condition - reset timer
            if self.alarm_start_time is not None:
                print(f"✅ {self.label}: Alarm condition cleared before delay expired")
            self.alarm_start_time = None
            # If alarm was active, turn it off
            alarm_condition_met = False
        
        # Only write coil if state has changed
        if alarm_condition_met != self.last_alarm_state:
            try:
                result = self.modbus_client.write_coil(
                    address=self.coil_address,
                    value=alarm_condition_met,
                    device_id=self.relay_device_id
                )
                if result and not result.isError():
                    status = "ON" if alarm_condition_met else "OFF"
                    print(f"\n{'='*60}")
                    print(f"🚨 {self.label.upper()} ALARM: COIL WRITE SUCCESSFUL")
                    print(f"{'='*60}")
                    print(f"  Device ID: {self.relay_device_id}")
                    print(f"  Coil Address: {self.coil_address}")
                    print(f"  Coil Value: {status}")
                    print(f"  Delay: {self.alarm_delay}s (elapsed)")
                    if alarm_condition_met:
                        print(f"  Alarm Reason: {alarm_reason}")
                    print(f"{'='*60}\n")
                    self.last_alarm_state = alarm_condition_met
                    self.alarm_active = alarm_condition_met
                    
                    # Record alarm in history
                    if alarm_condition_met:
                        alarm_type = "LOW" if self.current_value < self.low_limit else "HIGH"
                        limit = self.low_limit if alarm_type == "LOW" else self.high_limit
                        add_alarm_to_history(self.label, "Pressure", alarm_type, 
                                           round(self.current_value, 2), limit, "bar")
                    else:
                        clear_alarm_from_history(self.label, "")
                else:
                    print(f"⚠️ Failed to write coil to Device {self.relay_device_id}, Address {self.coil_address} (Device may not be connected): {result}")
            except Exception as e:
                print(f"⚠️ {self.label}: Cannot write alarm coil (Relay device not connected or communication error): {e}")
        else:
            self.alarm_active = alarm_condition_met
    
    def set_value(self, value):
        self.target_value = max(0, min(value, self.max_value))
    
    def set_thresholds(self, thresholds):
        """Update pressure thresholds for color logic"""
        self.thresholds = thresholds
    
    def animate_value(self):
        # Smooth easing with realistic damping
        easing_factor = 0.12  # Faster response for gauges
        threshold = 0.005
        
        distance = self.target_value - self.current_value
        
        if abs(distance) < threshold:
            self.current_value = self.target_value
        else:
            # Exponential easing for smooth, natural movement
            self.current_value += distance * easing_factor
            self.update()  # Trigger repaint for smooth animation
        
        # Check alarm conditions and write coil
        self.check_and_write_alarm()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        width = self.width()
        height = self.height()
        
        # Calculate responsive dimensions
        scale_factor = min(width / 280, height / 300)  # Base reference: 280x300
        
        # Calculate gauge dimensions
        label_space = max(30, int(50 * scale_factor))
        gauge_size = min(width, height - label_space)
        center_x = width / 2
        center_y = (height - label_space) / 2 + max(10, int(15 * scale_factor))
        radius = gauge_size / 2 - max(10, int(15 * scale_factor))
        
        # Draw subtle outer glow (minimal)
        glow_layers = max(2, int(3 * scale_factor))
        for i in range(glow_layers):
            alpha = 15 - i * 5
            painter.setPen(QPen(QColor(0, 180, 255, alpha), 1))
            painter.setBrush(Qt.NoBrush)
            glow_offset = max(6, int(8 * scale_factor))
            painter.drawEllipse(QPointF(center_x, center_y), radius + glow_offset + i, radius + glow_offset + i)
        
        # Draw main gauge background - clean and simple
        bg_gradient = QRadialGradient(center_x, center_y, radius)
        bg_gradient.setColorAt(0, QColor(18, 25, 38))
        bg_gradient.setColorAt(1, QColor(25, 35, 50))
        painter.setBrush(bg_gradient)
        border_width = max(1, int(2 * scale_factor))
        painter.setPen(QPen(QColor(40, 60, 85), border_width))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)
        
        # Draw clean outer ring
        ring_width = max(1, int(1.5 * scale_factor))
        ring_inset = max(3, int(5 * scale_factor))
        painter.setPen(QPen(QColor(50, 75, 105), ring_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), radius - ring_inset, radius - ring_inset)
        
        # Calculate value ratio for coloring
        value_ratio = self.current_value / self.max_value
        
        # Determine color based on 3-color logic
        # Special logic for gauges 0, 1, and 5: Red=Low (critical), Green=Normal, Yellow=High (warning)
        # Other gauges: Yellow=Low (warning), Green=Normal, Red=High (critical)
        if self.current_value <= 0:
            # No data - use dark gray with subtle blue tint
            arc_color = QColor(50, 60, 75)
            needle_color = QColor(50, 60, 75)
        elif self.gauge_index in [0, 1, 5]:
            # Fuel Oil (0), Lube Oil (1), Starting Air (5) - Low pressure is CRITICAL (RED)
            if self.current_value < self.low_limit:
                # Too low - CRITICAL RED (low pressure is dangerous!)
                arc_color = QColor(255, 60, 100)  # #FF3C64 - Critical red
                needle_color = QColor(255, 60, 100)
            elif self.current_value <= self.high_limit:
                # Normal - Tech Green
                arc_color = QColor(0, 255, 180)  # #00FFB4 - Vibrant tech green
                needle_color = QColor(0, 255, 180)
            else:
                # Too high - Warning Yellow
                arc_color = QColor(255, 200, 0)  # #FFC800 - Warning yellow
                needle_color = QColor(255, 200, 0)
        else:
            # Standard gauges - Low is warning, High is critical
            if self.current_value < self.low_limit:
                # Too low - Warning Yellow
                arc_color = QColor(255, 200, 0)  # #FFC800 - Warning yellow/gold
                needle_color = QColor(255, 200, 0)
            elif self.current_value <= self.high_limit:
                # Normal - Tech Green
                arc_color = QColor(0, 255, 180)  # #00FFB4 - Vibrant tech green
                needle_color = QColor(0, 255, 180)
            else:
                # Too high - Critical Red
                arc_color = QColor(255, 60, 100)  # #FF3C64 - Hot red with energy
                needle_color = QColor(255, 60, 100)
        
        # Draw progress arc (clean single arc)
        start_angle = 225 * 16
        span_per_unit = -270 * 16 / self.max_value
        current_span = int(span_per_unit * self.current_value)
        
        arc_inset = max(8, int(12 * scale_factor))
        arc_width_bg = max(4, int(6 * scale_factor))
        arc_width_dark = max(5, int(8 * scale_factor))
        arc_width_main = max(3, int(5 * scale_factor))
        
        if self.current_value > 0:
            # Subtle background arc
            painter.setPen(QPen(QColor(30, 45, 65), arc_width_bg))
            painter.drawArc(int(center_x - radius + arc_inset), int(center_y - radius + arc_inset),
                           int((radius - arc_inset) * 2), int((radius - arc_inset) * 2),
                           start_angle, -270 * 16)
            
            # Active arc with subtle glow
            painter.setPen(QPen(arc_color.darker(120), arc_width_dark))
            painter.drawArc(int(center_x - radius + arc_inset), int(center_y - radius + arc_inset),
                           int((radius - arc_inset) * 2), int((radius - arc_inset) * 2),
                           start_angle, current_span)
            
            painter.setPen(QPen(arc_color, arc_width_main))
            painter.drawArc(int(center_x - radius + arc_inset), int(center_y - radius + arc_inset),
                           int((radius - arc_inset) * 2), int((radius - arc_inset) * 2),
                           start_angle, current_span)
        
        # Draw tick marks - dynamic based on max_value
        tick_font_size = max(11, int(14 * scale_factor))
        painter.setFont(QFont("Segoe UI", tick_font_size, QFont.Normal))
        
        # Calculate appropriate tick interval based on max_value and gauge type
        def get_tick_interval(max_val, gauge_idx):
            # Special handling for specific gauges
            if gauge_idx == 0 and max_val == 15:
                return 3  # 0, 3, 6, 9, 12, 15 for 15 bar gauge
            elif gauge_idx == 7 and max_val == 5:
                return 1  # 0, 1, 2, 3, 4, 5 for 5 bar gauge
            elif max_val <= 10:
                return 2  # 0, 2, 4, 6, 8, 10
            elif max_val <= 20:
                return 5  # 0, 5, 10, 15, 20
            elif max_val <= 30:
                return 5  # 0, 5, 10, 15, 20, 25, 30
            elif max_val <= 50:
                return 10  # 0, 10, 20, 30, 40, 50
            elif max_val <= 100:
                return 20  # 0, 20, 40, 60, 80, 100
            else:
                return max_val // 5  # Divide into 5 segments
        
        tick_interval = get_tick_interval(self.max_value, self.gauge_index)
        tick_values = []
        current_val = 0
        while current_val <= self.max_value:
            tick_values.append(current_val)
            current_val += tick_interval
        
        # Ensure max_value is always included
        if tick_values[-1] != self.max_value:
            tick_values.append(self.max_value)
        
        num_ticks = len(tick_values)
        
        for i, tick_value in enumerate(tick_values):
            # Calculate angle based on value position
            value_ratio_tick = tick_value / self.max_value
            angle_deg = 225 - (270 * value_ratio_tick)
            angle_rad = math.radians(angle_deg)
            
            # Draw all major ticks for better readability
            tick_start_offset = max(16, int(22 * scale_factor))
            tick_end_offset = max(22, int(30 * scale_factor))
            tick_start_x = center_x + (radius - tick_start_offset) * math.cos(angle_rad)
            tick_start_y = center_y - (radius - tick_start_offset) * math.sin(angle_rad)
            tick_end_x = center_x + (radius - tick_end_offset) * math.cos(angle_rad)
            tick_end_y = center_y - (radius - tick_end_offset) * math.sin(angle_rad)
            
            tick_width = max(1, int(2 * scale_factor))
            painter.setPen(QPen(QColor(100, 130, 160), tick_width))
            painter.drawLine(int(tick_start_x), int(tick_start_y), int(tick_end_x), int(tick_end_y))
            
            # Draw labels with actual values
            label_offset = max(32, int(45 * scale_factor))
            label_x = center_x + (radius - label_offset) * math.cos(angle_rad)
            label_y = center_y - (radius - label_offset) * math.sin(angle_rad)
            painter.setPen(QColor(180, 200, 220))
            label_size = max(24, int(32 * scale_factor))
            label_height = max(18, int(24 * scale_factor))
            
            # Format label based on value (show integer for whole numbers, decimal for others)
            if tick_value == int(tick_value):
                label_text = str(int(tick_value))
            else:
                label_text = f"{tick_value:.1f}"
            
            painter.drawText(int(label_x - label_size // 2), int(label_y - label_height // 2), 
                           label_size, label_height, Qt.AlignCenter, label_text)
        
        # Calculate needle angle
        needle_angle_deg = 225 - (270 * value_ratio)
        needle_angle_rad = math.radians(needle_angle_deg)
        
        # Draw needle - sleek and minimal
        needle_offset = max(25, int(35 * scale_factor))
        needle_length = radius - needle_offset
        needle_end_x = center_x + needle_length * math.cos(needle_angle_rad)
        needle_end_y = center_y - needle_length * math.sin(needle_angle_rad)
        
        # Subtle needle glow
        needle_glow_layers = max(3, int(4 * scale_factor))
        for glow_size in range(needle_glow_layers, 0, -1):
            glow_alpha = 20 + (needle_glow_layers - glow_size) * 15
            painter.setPen(QPen(QColor(needle_color.red(), needle_color.green(), needle_color.blue(), glow_alpha), glow_size))
            painter.drawLine(int(center_x), int(center_y), int(needle_end_x), int(needle_end_y))
        
        # Main needle
        needle_width = max(1.5, int(2.5 * scale_factor))
        painter.setPen(QPen(needle_color, needle_width))
        painter.drawLine(int(center_x), int(center_y), int(needle_end_x), int(needle_end_y))
        
        # Center hub - clean and simple
        hub_outer_radius = max(6, int(8 * scale_factor))
        hub_inner_radius = max(2, int(3 * scale_factor))
        hub_border_width = max(1, int(2 * scale_factor))
        
        painter.setBrush(QColor(20, 30, 45))
        painter.setPen(QPen(needle_color, hub_border_width))
        painter.drawEllipse(QPointF(center_x, center_y), hub_outer_radius, hub_outer_radius)
        
        painter.setBrush(needle_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(center_x, center_y), hub_inner_radius, hub_inner_radius)
        
        # Digital value display - clean typography
        value_font_size = max(18, int(24 * scale_factor))  # Increased from 12/16 to 18/24
        painter.setFont(QFont("Segoe UI", value_font_size, QFont.Bold))  # Changed to Bold
        painter.setPen(QColor(220, 235, 250))
        # Show 2 decimal places for 5 bar gauge (index 7), 1 decimal for others
        if self.gauge_index == 7 and self.max_value == 5:
            value_text = f"{self.current_value:.2f}"
        else:
            value_text = f"{self.current_value:.1f}"
        value_y_offset = max(25, int(35 * scale_factor))
        value_width = max(80, int(100 * scale_factor))  # Increased width
        value_height = max(28, int(35 * scale_factor))  # Increased height
        painter.drawText(int(center_x - value_width // 2), int(center_y + value_y_offset), value_width, value_height, Qt.AlignCenter, value_text)
        
        # Unit label
        unit_font_size = max(10, int(13 * scale_factor))  # Increased from 7/9 to 10/13
        painter.setFont(QFont("Segoe UI", unit_font_size, QFont.Normal))
        painter.setPen(QColor(120, 150, 180))
        unit_y_offset = max(50, int(65 * scale_factor))  # Adjusted offset
        unit_width = max(55, int(70 * scale_factor))  # Increased width
        unit_height = max(18, int(24 * scale_factor))  # Increased height
        painter.drawText(int(center_x - unit_width // 2), int(center_y + unit_y_offset), unit_width, unit_height, Qt.AlignCenter, "bar")
        
        # Gauge label at bottom - clean
        label_font_size = max(10, int(13 * scale_factor))  # Increased from 7/9 to 10/13
        painter.setFont(QFont("Segoe UI", label_font_size, QFont.Medium))  # Changed to Medium weight
        painter.setPen(QColor(160, 185, 210))
        label_y = height - max(28, int(38 * scale_factor))  # Adjusted offset
        label_height = max(26, int(34 * scale_factor))  # Increased height
        painter.drawText(5, label_y, width - 10, label_height, Qt.AlignCenter, self.label)
        
        painter.end()


# ---------------- Circular Temperature Gauge Widget ----------------
class CircularTemperatureGauge(QWidget):
    def __init__(self, label, max_value=250, gauge_index=0, parent_window=None):
        super().__init__()
        self.label = label
        self.parent_window = parent_window
        self.max_value = max_value
        self.gauge_index = gauge_index
        self.current_value = 0.0
        self.target_value = 0
        self.setMinimumSize(220, 250)  # Match pressure gauge size
        self.setCursor(Qt.PointingHandCursor)  # Show clickable cursor
        
        # Load configuration from JSON
        self.config = self.load_config()
        self.low_limit = self.config.get("low_limit", 50)
        self.high_limit = self.config.get("high_limit", 220)
        self.enable_alarm = self.config.get("enable_alarm", True)
        self.relay_device_id = self.config.get("device_id", 5)
        self.coil_address = self.config.get("coil_address", 4)
        self.alarm_delay = self.config.get("alarm_delay", 5)
        
        # Modbus client reference (will be set by EngineTemperaturesTab)
        self.modbus_client = None
        
        # Alarm state tracking
        self.alarm_active = False
        self.last_alarm_state = None
        self.alarm_start_time = None  # Track when alarm condition first occurred
        
        # Animation timer for smooth value transitions
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_value)
        self.animation_timer.start(16)  # 60 FPS
        
        # Default thresholds (can be overridden)
        self.thresholds = {"warning": self.low_limit, "critical": self.high_limit}
    
    def set_value(self, value):
        """Set target temperature value"""
        self.target_value = max(0, min(self.max_value, value))
    
    def set_thresholds(self, thresholds):
        """Update temperature thresholds for color logic"""
        self.thresholds = thresholds
    
    def animate_value(self):
        """Smooth animation towards target value"""
        easing_factor = 0.08
        threshold = 0.1
        
        distance = self.target_value - self.current_value
        
        if abs(distance) < threshold:
            self.current_value = self.target_value
        else:
            self.current_value += distance * easing_factor
            self.update()
        
        # Check and write alarm state
        self.check_and_write_alarm()
    
    def get_color_for_value(self, value):
        """Get color based on temperature value and thresholds"""
        # Get configured limits
        low_limit = self.thresholds.get("warning", 50)   # Low temperature threshold
        high_limit = self.thresholds.get("critical", 220)  # High temperature threshold
        
        # 3-level color logic for temperature monitoring:
        # Yellow = Too Cold (below low_limit)
        # Green = Normal (between low_limit and high_limit)
        # Red = Too Hot (above high_limit)
        
        if value <= 0:
            # No data - Dark gray
            return QColor(50, 60, 75)
        elif value < low_limit:
            # Too Cold - Warning Yellow
            return QColor(255, 200, 0)  # #FFC800 - Bright warning yellow
        elif value <= high_limit:
            # Normal Range - Tech Green
            return QColor(0, 255, 180)  # #00FFB4 - Vibrant tech green
        else:
            # Too Hot - Critical Red
            return QColor(255, 60, 100)  # #FF3C64 - Hot red with energy
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        width = self.width()
        height = self.height()
        
        # Calculate responsive dimensions (matching pressure gauge)
        scale_factor = min(width / 280, height / 300)  # Base reference: 280x300
        
        # Calculate gauge dimensions
        label_space = max(30, int(50 * scale_factor))
        gauge_size = min(width, height - label_space)
        center_x = width / 2
        center_y = (height - label_space) / 2 + max(10, int(15 * scale_factor))
        radius = gauge_size / 2 - max(10, int(15 * scale_factor))
        
        # Get color based on current temperature
        gauge_color = self.get_color_for_value(self.current_value)
        
        # Draw subtle outer glow (minimal) - matching pressure gauge
        glow_layers = max(2, int(3 * scale_factor))
        for i in range(glow_layers):
            alpha = 15 - i * 5
            painter.setPen(QPen(QColor(0, 180, 255, alpha), 1))
            painter.setBrush(Qt.NoBrush)
            glow_offset = max(6, int(8 * scale_factor))
            painter.drawEllipse(QPointF(center_x, center_y), radius + glow_offset + i, radius + glow_offset + i)
        
        # Draw main gauge background - clean and simple (matching pressure gauge)
        bg_gradient = QRadialGradient(center_x, center_y, radius)
        bg_gradient.setColorAt(0, QColor(18, 25, 38))
        bg_gradient.setColorAt(1, QColor(25, 35, 50))
        painter.setBrush(bg_gradient)
        border_width = max(1, int(2 * scale_factor))
        painter.setPen(QPen(QColor(40, 60, 85), border_width))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)
        
        # Draw clean outer ring (matching pressure gauge)
        ring_width = max(1, int(1.5 * scale_factor))
        ring_inset = max(3, int(5 * scale_factor))
        painter.setPen(QPen(QColor(50, 75, 105), ring_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), radius - ring_inset, radius - ring_inset)
        
        # Calculate value ratio for coloring
        value_ratio = self.current_value / self.max_value
        
        # Draw progress arc (clean single arc) - matching pressure gauge style
        start_angle = 225 * 16
        span_per_unit = -270 * 16 / self.max_value
        current_span = int(span_per_unit * self.current_value)
        
        arc_inset = max(8, int(12 * scale_factor))
        arc_width_bg = max(4, int(6 * scale_factor))
        arc_width_dark = max(5, int(8 * scale_factor))
        arc_width_main = max(3, int(5 * scale_factor))
        
        if self.current_value > 0:
            # Subtle background arc
            painter.setPen(QPen(QColor(30, 45, 65), arc_width_bg))
            painter.drawArc(int(center_x - radius + arc_inset), int(center_y - radius + arc_inset),
                           int((radius - arc_inset) * 2), int((radius - arc_inset) * 2),
                           start_angle, -270 * 16)
            
            # Active arc with subtle glow
            painter.setPen(QPen(gauge_color.darker(120), arc_width_dark))
            painter.drawArc(int(center_x - radius + arc_inset), int(center_y - radius + arc_inset),
                           int((radius - arc_inset) * 2), int((radius - arc_inset) * 2),
                           start_angle, current_span)
            
            painter.setPen(QPen(gauge_color, arc_width_main))
            painter.drawArc(int(center_x - radius + arc_inset), int(center_y - radius + arc_inset),
                           int((radius - arc_inset) * 2), int((radius - arc_inset) * 2),
                           start_angle, current_span)
        
        # Digital temperature value display with °C in center
        value_font_size = max(20, int(26 * scale_factor))  # Slightly decreased for better proportion
        painter.setFont(QFont("Segoe UI", value_font_size, QFont.Bold))
        painter.setPen(QColor(220, 235, 250))
        temp_text = f"{self.current_value:.0f}°C"
        value_width = max(110, int(130 * scale_factor))
        value_height = max(30, int(36 * scale_factor))
        painter.drawText(int(center_x - value_width // 2), int(center_y - value_height // 2), value_width, value_height, Qt.AlignCenter, temp_text)
        
        # Gauge label at bottom - clean (matching pressure gauge)
        label_font_size = max(10, int(13 * scale_factor))
        painter.setFont(QFont("Segoe UI", label_font_size, QFont.Medium))
        painter.setPen(QColor(160, 185, 210))
        label_y = height - max(28, int(38 * scale_factor))
        label_height = max(26, int(34 * scale_factor))
        painter.drawText(5, label_y, width - 10, label_height, Qt.AlignCenter, self.label)
        
        painter.end()
    
    def load_config(self):
        """Load configuration from modbus_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modbus_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    if "EngineTemperatures" in data and str(self.gauge_index) in data["EngineTemperatures"]:
                        return data["EngineTemperatures"][str(self.gauge_index)]
        except Exception as e:
            print(f"Error loading temperature gauge config: {e}")
        return {"label": self.label, "low_limit": 50, "high_limit": 220, "coil_address": 4, "device_id": 5, "alarm_delay": 5, "enable_alarm": False}
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to open configuration"""
        if event.button() == Qt.LeftButton:
            # Check if admin is logged in
            admin_logged_in = getattr(self.parent_window, 'admin_logged_in', False)
            
            if not admin_logged_in:
                password, ok = QInputDialog.getText(self, "Administrator Access",
                                                   "Enter admin password:",
                                                   QLineEdit.Password)
                # Get admin password from parent window
                admin_password = getattr(self.parent_window, 'admin_password', 'admin123')
                if not (ok and password == admin_password):
                    if ok:
                        QMessageBox.warning(self, "Access Denied", "Incorrect password!")
                    return
            
            # Open configuration dialog
            dialog = TemperatureGaugeConfigDialog(self, gauge_index=self.gauge_index, gauge_label=self.label)
            if dialog.exec_() == QDialog.Accepted:
                # Reload configuration
                self.config = self.load_config()
                self.low_limit = self.config.get("low_limit", 50)
                self.high_limit = self.config.get("high_limit", 220)
                self.relay_device_id = self.config.get("device_id", 5)
                self.coil_address = self.config.get("coil_address", 4)
                self.alarm_delay = self.config.get("alarm_delay", 5)
                self.enable_alarm = self.config.get("enable_alarm", True)
                self.alarm_start_time = None  # Reset delay timer on config change
                # Update thresholds
                self.thresholds = {"warning": self.low_limit, "critical": self.high_limit}
                # Update label if it was changed
                new_label = self.config.get("label", self.label)
                if new_label != self.label:
                    self.label = new_label
                    print(f"Temperature gauge label updated to: {self.label}")
                self.update()  # Trigger repaint to show new label
                print(f"{self.label} Configuration updated: Low={self.low_limit}°C, High={self.high_limit}°C, Device={self.relay_device_id}, Coil={self.coil_address}, Delay={self.alarm_delay}s")
    
    def set_modbus_client(self, client):
        """Set the Modbus client for coil writing"""
        self.modbus_client = client
    
    def check_and_write_alarm(self):
        """Check temperature and write to coil if alarm conditions are met (with delay)"""
        if not self.enable_alarm or not self.modbus_client:
            return
        
        # Determine if alarm condition is met
        alarm_condition_met = False
        alarm_reason = ""
        if self.current_value > 0:  # Only check if we have valid data
            if self.current_value < self.low_limit:
                alarm_condition_met = True
                alarm_reason = f"{self.current_value:.1f}°C (LOW, limit={self.low_limit}°C)"
            elif self.current_value > self.high_limit:
                alarm_condition_met = True
                alarm_reason = f"{self.current_value:.1f}°C (HIGH, limit={self.high_limit}°C)"
        
        # Alarm delay logic
        if alarm_condition_met:
            if self.alarm_start_time is None:
                # First time alarm condition triggered - start timer
                self.alarm_start_time = time.time()
                print(f"⏱️ {self.label}: Alarm condition detected, starting {self.alarm_delay}s delay timer...")
                return  # Don't trigger yet
            else:
                # Check if enough time has elapsed
                elapsed = time.time() - self.alarm_start_time
                if elapsed < self.alarm_delay:
                    # Still in delay period
                    return  # Don't trigger yet
                # Delay period complete - proceed to trigger alarm
        else:
            # No alarm condition - reset timer
            if self.alarm_start_time is not None:
                print(f"✅ {self.label}: Alarm condition cleared before delay expired")
            self.alarm_start_time = None
            # If alarm was active, turn it off
            alarm_condition_met = False
        
        # Only write if state changed
        if alarm_condition_met != self.last_alarm_state:
            try:
                result = self.modbus_client.write_coil(
                    address=self.coil_address,
                    value=alarm_condition_met,
                    device_id=self.relay_device_id
                )
                if result and not result.isError():
                    self.last_alarm_state = alarm_condition_met
                    self.alarm_active = alarm_condition_met
                    status = "ON" if alarm_condition_met else "OFF"
                    print(f"\n{'='*60}")
                    print(f"🚨 {self.label.upper()} ALARM: {status}")
                    print(f"{'='*60}")
                    print(f"  Device ID: {self.relay_device_id}")
                    print(f"  Coil Address: {self.coil_address}")
                    print(f"  Delay: {self.alarm_delay}s (elapsed)")
                    if alarm_condition_met:
                        print(f"  Alarm Reason: {alarm_reason}")
                    print(f"{'='*60}\n")
                    
                    # Record alarm in history
                    if alarm_condition_met:
                        alarm_type = "LOW" if self.current_value < self.low_limit else "HIGH"
                        limit = self.low_limit if alarm_type == "LOW" else self.high_limit
                        add_alarm_to_history(self.label, "Temperature", alarm_type, 
                                           round(self.current_value, 1), limit, "°C")
                    else:
                        clear_alarm_from_history(self.label, "")
                else:
                    print(f"⚠️ Failed to write coil for {self.label} (Device may not be connected): {result}")
            except Exception as e:
                print(f"⚠️ {self.label}: Cannot write alarm coil (Relay device not connected or communication error): {e}")


# ---------------- Cylinder Head Bar Configuration Dialog ----------------
class CylinderHeadBarConfigDialog(QDialog):
    def __init__(self, parent=None, bar_config=None, bar_index=None):
        super().__init__(parent)
        self.bar_config = bar_config or {}
        self.bar_index = bar_index
        self.setWindowTitle("Temperature Bar Configuration")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        # Setup UI
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("🌡️ TEMPERATURE BAR CONFIGURATION")
        title.setStyleSheet("""
            QLabel {
                color: rgb(0, 200, 255);
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Configuration form
        form_group = QGroupBox("Bar Settings")
        form_group.setStyleSheet("""
            QGroupBox {
                color: rgb(200, 220, 240);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: rgb(0, 200, 255);
            }
        """)
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Label
        self.label_edit = QLineEdit()
        # Extract number from bar_index if it's a string like "bar_1", "bar_2", etc.
        default_label = "T1"
        if bar_index is not None:
            try:
                if isinstance(bar_index, str) and bar_index.startswith("bar_"):
                    bar_num = int(bar_index.split("_")[1])
                    default_label = f"T{bar_num}"
                elif isinstance(bar_index, int):
                    default_label = f"T{bar_index + 1}"
                else:
                    default_label = f"T{bar_index}"
            except (ValueError, IndexError):
                default_label = "T1"
        
        self.label_edit.setText(self.bar_config.get("label", default_label))
        self.label_edit.setPlaceholderText("Enter bar label (e.g., T1, T2, etc.)")
        self.label_edit.setStyleSheet("""
            QLineEdit {
                background: rgb(30, 40, 55);
                color: rgb(0, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid rgb(0, 200, 255);
                background: rgb(35, 45, 60);
            }
        """)
        form_layout.addRow("Label:", self.label_edit)
        
        # Register Type
        self.register_type_combo = QComboBox()
        self.register_type_combo.addItems(["input", "holding", "coil", "discrete"])
        self.register_type_combo.setCurrentText(self.bar_config.get("type", "input"))
        self.register_type_combo.setStyleSheet("""
            QComboBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 200, 0);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QComboBox:focus {
                border: 2px solid rgb(255, 200, 0);
            }
            QComboBox::drop-down {
                border: none;
                background: rgb(40, 50, 65);
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid rgb(255, 200, 0);
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background: rgb(30, 40, 55);
                color: rgb(255, 200, 0);
                border: 1px solid rgb(60, 80, 100);
                selection-background-color: rgb(0, 120, 180);
            }
        """)
        form_layout.addRow("Register Type:", self.register_type_combo)
        
        # Address
        self.address_spin = QSpinBox()
        self.address_spin.setRange(0, 65535)
        self.address_spin.setValue(self.bar_config.get("address", 0))
        self.address_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 180);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(0, 255, 180);
            }
        """)
        form_layout.addRow("Modbus Address:", self.address_spin)
        
        # Device ID
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(self.bar_config.get("device_id", 1))
        self.device_id_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(200, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(200, 200, 255);
            }
        """)
        form_layout.addRow("Device ID:", self.device_id_spin)
        
        # Section
        self.section_combo = QComboBox()
        self.section_combo.addItems(["left", "right"])
        self.section_combo.setCurrentText(self.bar_config.get("section", "left"))
        self.section_combo.setStyleSheet("""
            QComboBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 100, 200);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QComboBox:focus {
                border: 2px solid rgb(255, 100, 200);
            }
            QComboBox::drop-down {
                border: none;
                background: rgb(40, 50, 65);
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid rgb(255, 100, 200);
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background: rgb(30, 40, 55);
                color: rgb(255, 100, 200);
                border: 1px solid rgb(60, 80, 100);
                selection-background-color: rgb(0, 120, 180);
            }
        """)
        form_layout.addRow("Section:", self.section_combo)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Info label
        info_label = QLabel("ℹ️ Configure the Modbus parameters for this temperature bar.\nThe bar will read live data from the specified address and device.")
        info_label.setStyleSheet("""
            QLabel {
                color: rgb(150, 170, 190);
                font-size: 11px;
                font-style: italic;
                padding: 10px;
                background: rgb(25, 35, 50);
                border-radius: 5px;
            }
        """)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgb(60, 70, 85);
                color: rgb(200, 220, 240);
                border: 1px solid rgb(80, 90, 105);
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background: rgb(70, 80, 95);
                border: 1px solid rgb(90, 100, 115);
            }
            QPushButton:pressed {
                background: rgb(50, 60, 75);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setMinimumHeight(40)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 200, 255), stop:1 rgb(0, 150, 200));
                color: rgb(10, 20, 30);
                border: 1px solid rgb(0, 220, 255);
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 220, 255), stop:1 rgb(0, 170, 220));
                border: 1px solid rgb(0, 240, 255);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 150, 200), stop:1 rgb(0, 100, 150));
            }
        """)
        save_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background: rgb(20, 30, 45);
            }
            QLabel {
                background: transparent;
            }
        """)
    
    def get_config(self):
        """Get the configuration from the dialog"""
        return {
            "label": self.label_edit.text().strip(),
            "type": self.register_type_combo.currentText(),
            "address": self.address_spin.value(),
            "device_id": self.device_id_spin.value(),
            "section": self.section_combo.currentText()
        }


# ---------------- Main Bearing Bar Configuration Dialog ----------------
class MainBearingBarConfigDialog(QDialog):
    def __init__(self, parent=None, bar_config=None, bar_index=None):
        super().__init__(parent)
        self.bar_config = bar_config or {}
        self.bar_index = bar_index
        self.setWindowTitle("Main Bearing Bar Configuration")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        # Setup UI
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("🌡️ MAIN BEARING BAR CONFIGURATION")
        title.setStyleSheet("""
            QLabel {
                color: rgb(0, 200, 255);
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Configuration form
        form_group = QGroupBox("Bar Settings")
        form_group.setStyleSheet("""
            QGroupBox {
                color: rgb(200, 220, 240);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: rgb(0, 200, 255);
            }
        """)
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Label
        self.label_edit = QLineEdit()
        default_label = "B1"
        if bar_index is not None:
            try:
                if isinstance(bar_index, str) and bar_index.startswith("bar_"):
                    bar_num = int(bar_index.split("_")[1])
                    default_label = f"B{bar_num}"
                elif isinstance(bar_index, int):
                    default_label = f"B{bar_index + 1}"
                else:
                    default_label = f"B{bar_index}"
            except (ValueError, IndexError):
                default_label = "B1"
        
        self.label_edit.setText(self.bar_config.get("label", default_label))
        self.label_edit.setPlaceholderText("Enter bar label (e.g., B1, B2, etc.)")
        self.label_edit.setStyleSheet("""
            QLineEdit {
                background: rgb(30, 40, 55);
                color: rgb(0, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid rgb(0, 200, 255);
                background: rgb(35, 45, 60);
            }
        """)
        form_layout.addRow("Label:", self.label_edit)
        
        # Register Type
        self.register_type_combo = QComboBox()
        self.register_type_combo.addItems(["input", "holding", "coil", "discrete"])
        self.register_type_combo.setCurrentText(self.bar_config.get("type", "input"))
        self.register_type_combo.setStyleSheet("""
            QComboBox {
                background: rgb(30, 40, 55);
                color: rgb(255, 200, 0);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QComboBox:focus {
                border: 2px solid rgb(255, 200, 0);
            }
            QComboBox::drop-down {
                border: none;
                background: rgb(40, 50, 65);
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid rgb(255, 200, 0);
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background: rgb(30, 40, 55);
                color: rgb(255, 200, 0);
                border: 1px solid rgb(60, 80, 100);
                selection-background-color: rgb(0, 120, 180);
            }
        """)
        form_layout.addRow("Register Type:", self.register_type_combo)
        
        # Address
        self.address_spin = QSpinBox()
        self.address_spin.setRange(0, 65535)
        self.address_spin.setValue(self.bar_config.get("address", 0))
        self.address_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(0, 255, 180);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(0, 255, 180);
            }
        """)
        form_layout.addRow("Modbus Address:", self.address_spin)
        
        # Device ID
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(self.bar_config.get("device_id", 1))
        self.device_id_spin.setStyleSheet("""
            QSpinBox {
                background: rgb(30, 40, 55);
                color: rgb(200, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid rgb(200, 200, 255);
            }
        """)
        form_layout.addRow("Device ID:", self.device_id_spin)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Info label
        info_label = QLabel("ℹ️ Configure the Modbus parameters for this main bearing bar.\nThe bar will read live data from the specified address and device.")
        info_label.setStyleSheet("""
            QLabel {
                color: rgb(150, 170, 190);
                font-size: 11px;
                font-style: italic;
                padding: 10px;
                background: rgb(25, 35, 50);
                border-radius: 5px;
            }
        """)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgb(60, 70, 85);
                color: rgb(200, 220, 240);
                border: 1px solid rgb(80, 90, 105);
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background: rgb(70, 80, 95);
                border: 1px solid rgb(90, 100, 115);
            }
            QPushButton:pressed {
                background: rgb(50, 60, 75);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setMinimumHeight(40)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 200, 255), stop:1 rgb(0, 150, 200));
                color: rgb(10, 20, 30);
                border: 1px solid rgb(0, 220, 255);
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 220, 255), stop:1 rgb(0, 170, 220));
                border: 1px solid rgb(0, 240, 255);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 150, 200), stop:1 rgb(0, 100, 150));
            }
        """)
        save_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background: rgb(20, 30, 45);
            }
            QLabel {
                background: transparent;
            }
        """)
    
    def get_config(self):
        """Get the configuration from the dialog"""
        return {
            "label": self.label_edit.text().strip(),
            "type": self.register_type_combo.currentText(),
            "address": self.address_spin.value(),
            "device_id": self.device_id_spin.value()
        }


# ---------------- Engine Pressures Tab ----------------
class EnginePressuresTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.setMinimumSize(800, 450)
        self.setStyleSheet(CYLINDER_HEAD_BG_STYLE)
        
        # Create layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 30, 20, 20)
        main_layout.setSpacing(15)
        
        # Title
        self.title = QLabel("ENGINE PRESSURES")
        self.title.setFont(QFont("Inter", 18, QFont.Bold))
        self.title.setStyleSheet("color: rgb(255, 255, 255);")
        self.title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.title)
        
        # Create gauge grid (2 rows x 4 columns)
        grid_layout = QVBoxLayout()
        grid_layout.setSpacing(20)
        
        # Gauge labels and their corresponding max values and color behavior
        gauge_config = [
            {"label": "Fuel Oil Pressure Inlet", "max_value": 15, "reverse_colors": False},  # Changed to 15 bar
            {"label": "Lube Oil Pressure Inlet", "max_value": 10, "reverse_colors": True},  # Low pressure is dangerous
            {"label": "LT Water Pressure", "max_value": 10, "reverse_colors": False},
            {"label": "HT Water Pressure", "max_value": 10, "reverse_colors": False},
            {"label": "Charge Air Pressure", "max_value": 10, "reverse_colors": False},
            {"label": "Starting Air Pressure", "max_value": 30, "reverse_colors": False},  # Set to 30 range as requested
            {"label": "Lube Oil Differential Pressure", "max_value": 10, "reverse_colors": False},
            {"label": "Crank Case Pressure", "max_value": 5, "reverse_colors": False}  # Changed to 5 bar
        ]
        
        # Create gauges
        self.gauges = []
        
        # First row (4 gauges)
        self.row1_layout = QHBoxLayout()
        self.row1_layout.setSpacing(20)
        for i in range(4):
            config = gauge_config[i]
            gauge = CircularPressureGauge(config["label"], max_value=config["max_value"], reverse_colors=config["reverse_colors"], gauge_index=i, parent_window=self.parent_window)
            self.gauges.append(gauge)
            self.row1_layout.addWidget(gauge, 1)  # Add stretch factor
        grid_layout.addLayout(self.row1_layout)
        
        # Second row (4 gauges)
        self.row2_layout = QHBoxLayout()
        self.row2_layout.setSpacing(20)
        for i in range(4, 8):
            config = gauge_config[i]
            gauge = CircularPressureGauge(config["label"], max_value=config["max_value"], reverse_colors=config["reverse_colors"], gauge_index=i, parent_window=self.parent_window)
            self.gauges.append(gauge)
            self.row2_layout.addWidget(gauge, 1)  # Add stretch factor
        grid_layout.addLayout(self.row2_layout)
        
        main_layout.addLayout(grid_layout, 1)  # Add stretch factor to grid
        
        self.setLayout(main_layout)
    
    def resizeEvent(self, event):
        """Handle resize events to update font sizes"""
        super().resizeEvent(event)
        width = self.width()
        height = self.height()
        
        # Calculate scale factor based on screen size
        scale_factor = min(width / 1280, height / 600)
        
        # Update title font size
        title_font_size = max(12, int(18 * scale_factor))
        self.title.setFont(QFont("Inter", title_font_size, QFont.Bold))
        
        # Update spacing
        spacing = max(12, int(20 * scale_factor))
        self.row1_layout.setSpacing(spacing)
        self.row2_layout.setSpacing(spacing)
    
    def set_modbus_client(self, client):
        """Set the Modbus client for all pressure gauges"""
        for gauge in self.gauges:
            gauge.set_modbus_client(client)
    
    def update_pressures(self, values, is_test_mode=False):
        """Update pressure values from Modbus data or test mode"""
        for i, value in enumerate(values[:8]):
            if i < len(self.gauges):
                if is_test_mode:
                    # Test mode: values are already in register format, just divide by 10
                    actual_pressure = value / 10.0
                else:
                    # Real Modbus mode: Convert 4-20mA sensor reading to actual pressure
                    # 4mA = 0 pressure, 20mA = max pressure (16mA span)
                    # Based on your readings: 4mA ≈ 320 raw, 13mA ≈ 1000+ raw
                    
                    # Get pressure range for this specific gauge
                    if i == 0:  # Fuel Oil Pressure Inlet (0-15 bar)
                        pressure_max = 15
                    elif i == 5:  # Starting Air Pressure (0-30 bar)
                        pressure_max = 30
                    elif i == 7:  # Crank Case Pressure (0-5 bar)
                        pressure_max = 5
                    else:  # Other gauges (0-10 bar)
                        pressure_max = 10
                    
                    # 4-20mA scaling with offset correction
                    # Different calibration for different gauge ranges
                    if i == 0:  # Fuel Oil Pressure Inlet (15 bar)
                        raw_4ma = 397   # Calibrate based on your actual 4mA reading
                        raw_20ma = 1998 # Calibrate based on your actual 20mA reading
                    elif i == 5:  # Starting Air Pressure (30 bar)
                        raw_4ma = 397   # Adjusted for 30 bar gauge
                        raw_20ma = 1999 # Adjusted based on 17mA showing 30 bar
                    elif i == 7:  # Crank Case Pressure (5 bar)
                        raw_4ma = 398   # Calibrate based on your actual 4mA reading
                        raw_20ma = 2000 # Calibrate based on your actual 20mA reading
                    else:  # Other 10 bar gauges
                        raw_4ma = 320   # Raw value at 4mA (0 pressure)
                        raw_20ma = 1600 # Estimated raw value at 20mA (full scale)
                    
                    # Correct 4-20mA formula: subtract 4mA offset first
                    if value >= raw_4ma:
                        # Scale from 4mA-20mA range to 0-max_pressure range
                        actual_pressure = ((value - raw_4ma) / (raw_20ma - raw_4ma)) * pressure_max
                        actual_pressure = max(0, min(actual_pressure, pressure_max))  # Clamp to valid range
                    else:
                        # Below 4mA - should be 0
                        actual_pressure = 0
                
                self.gauges[i].set_value(actual_pressure)
    
    def set_thresholds(self, pressure_thresholds):
        """Update pressure thresholds for all gauges"""
        gauge_labels = [
            "Fuel Oil Pressure Inlet",
            "Lube Oil Pressure Inlet", 
            "LT Water Pressure",
            "HT Water Pressure",
            "Charge Air Pressure",
            "Starting Air Pressure",
            "Lube Oil Differential Pressure",
            "Crank Case Pressure"
        ]
        
        for i, gauge in enumerate(self.gauges):
            if i < len(gauge_labels):
                gauge_name = gauge_labels[i]
                if gauge_name in pressure_thresholds:
                    gauge.set_thresholds(pressure_thresholds[gauge_name])
    
    def update_gauge_labels(self, gauge_labels):
        """Update gauge labels from configuration"""
        for i, gauge in enumerate(self.gauges):
            gauge_key = f"gauge_{i}"
            if gauge_key in gauge_labels:
                new_label = gauge_labels[gauge_key]
                gauge.label = new_label
                gauge.update()  # Trigger repaint to show new label


# ---------------- Editable Label Widget ----------------
class EditableLabel(QLabel):
    def __init__(self, text, callback=None):
        super().__init__(text)
        self.original_text = text
        self.callback = callback
        self.edit_mode = False
        self.line_edit = None
        self.setCursor(Qt.PointingHandCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.edit_mode:
            self.start_editing()
        super().mousePressEvent(event)
    
    def start_editing(self):
        if self.edit_mode:
            return
            
        self.edit_mode = True
        self.line_edit = QLineEdit(self.text(), self.parent())
        
        # Calculate proper size for the input field
        font_metrics = self.line_edit.fontMetrics()
        text_width = font_metrics.boundingRect(self.text()).width()
        min_width = max(200, text_width + 60)  # Ensure enough space for text
        
        # Position and size the line edit with proper height
        label_rect = self.geometry()
        edit_height = max(30, label_rect.height())  # Minimum 30px height
        self.line_edit.setGeometry(label_rect.x(), label_rect.y(), min_width, edit_height)
        
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background: #0d1117;
                border: 2px solid #58a6ff;
                padding: 4px 8px;
                color: #e6edf3;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.2px;
                selection-background-color: #1f6feb;
            }
        """)
        
        # Show the line edit over the label
        self.line_edit.show()
        self.line_edit.raise_()
        self.line_edit.selectAll()
        self.line_edit.setFocus()
        self.line_edit.editingFinished.connect(self.finish_editing)
        self.line_edit.returnPressed.connect(self.finish_editing)
        
        # Install event filter to detect focus loss
        self.line_edit.installEventFilter(self)
        
    def finish_editing(self):
        if not self.edit_mode or not self.line_edit:
            return
        
        # Prevent multiple calls
        if hasattr(self, '_finishing_edit') and self._finishing_edit:
            return
        self._finishing_edit = True
            
        new_text = self.line_edit.text().strip()
        if new_text and new_text != self.text():
            self.setText(new_text.upper())
            if self.callback:
                self.callback(self.original_text, new_text)
        
        # Remove the overlay line edit
        self.line_edit.hide()
        self.line_edit.deleteLater()
        self.line_edit = None
        self.edit_mode = False
        self._finishing_edit = False
    
    def eventFilter(self, obj, event):
        """Handle events for the line edit to detect focus loss"""
        if obj == self.line_edit and self.edit_mode:
            if event.type() == QEvent.FocusOut:
                # Delay the finish_editing call to avoid conflicts
                QTimer.singleShot(0, self.finish_editing)
                return True
        return super().eventFilter(obj, event)


# ---------------- Engine Temperatures Tab ----------------
class EngineTemperaturesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.is_authenticated = False
        self.setMinimumSize(800, 600)
        self.setStyleSheet(CYLINDER_HEAD_BG_STYLE)
        
        # Default configuration values
        self.config = {
            "temperature_thresholds": {
                "cylinder_head": {"warning": 400, "critical": 600},
                "main_bearing": {"warning": 150, "critical": 250}
            },
            "pressure_thresholds": {
                "Fuel Oil Pressure Inlet": {"warning": 6, "critical": 8},
                "Lube Oil Pressure Inlet": {"warning": 3, "critical": 2},  # Reverse logic
                "LT Water Pressure": {"warning": 6, "critical": 8},
                "HT Water Pressure": {"warning": 6, "critical": 8},
                "Charge Air Pressure": {"warning": 6, "critical": 8},
                "Starting Air Pressure": {"warning": 18, "critical": 24},
                "Lube Oil Differential Pressure": {"warning": 6, "critical": 8},
                "Crank Case Pressure": {"warning": 6, "critical": 8}
            },
            "gauge_labels": {
                "gauge_0": "Fuel Oil Pressure Inlet",
                "gauge_1": "Lube Oil Pressure Inlet", 
                "gauge_2": "LT Water Pressure",
                "gauge_3": "HT Water Pressure",
                "gauge_4": "Charge Air Pressure",
                "gauge_5": "Starting Air Pressure",
                "gauge_6": "Lube Oil Differential Pressure",
                "gauge_7": "Crank Case Pressure"
            }
        }
        
        self.load_configuration()
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 30, 20, 20)
        main_layout.setSpacing(15)
        
        # Title
        self.title = QLabel("SYSTEM CONFIGURATION")
        self.title.setFont(QFont("Inter", 18, QFont.Bold))
        self.title.setStyleSheet("color: rgb(255, 255, 255);")
        self.title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.title)
        
        # Create stacked widget for login/config views
        self.stacked_widget = QStackedWidget()
        
        # Login page
        self.login_widget = self.create_login_widget()
        self.stacked_widget.addWidget(self.login_widget)
        
        # Configuration page
        self.config_widget = self.create_config_widget()
        self.stacked_widget.addWidget(self.config_widget)
        
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)
        
        # Show login page initially
        self.stacked_widget.setCurrentIndex(0)
    
    def create_login_widget(self):
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #0a0e1a;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Industrial login panel matching main app theme
        login_panel = QWidget()
        login_panel.setFixedSize(450, 320)
        login_panel.setStyleSheet("""
            QWidget {
                background-color: #161b22;
                border: 1.5px solid #30363d;
                border-radius: 6px;
            }
        """)
        
        panel_layout = QVBoxLayout(login_panel)
        panel_layout.setContentsMargins(40, 30, 40, 30)
        panel_layout.setSpacing(20)
        
        # Company branding matching main app style
        brand_label = QLabel("MOHSIN ELECTRONICS")
        brand_label.setAlignment(Qt.AlignCenter)
        brand_label.setStyleSheet("""
            QLabel {
                color: #8b949e;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 2px;
                margin-bottom: 5px;
                background: transparent;
                border: none;
            }
        """)
        panel_layout.addWidget(brand_label)
        
        # Main title
        title_label = QLabel("SYSTEM CONFIGURATION")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #e6edf3;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 1px;
                margin-bottom: 5px;
                background: transparent;
                border: none;
            }
        """)
        panel_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Administrator Access Required")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #8b949e;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 400;
                margin-bottom: 15px;
                background: transparent;
                border: none;
            }
        """)
        panel_layout.addWidget(subtitle_label)
        
        # Password field matching main app style
        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.Password)
        self.password_field.setPlaceholderText("Enter password")
        self.password_field.setFixedHeight(40)
        self.password_field.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                border: 1.5px solid #30363d;
                border-radius: 6px;
                padding: 8px 14px;
                color: #e6edf3;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 14px;
                selection-background-color: #1f6feb;
            }
            QLineEdit:focus {
                border: 1.5px solid #58a6ff;
                outline: none;
            }
            QLineEdit:hover {
                border: 1.5px solid #58a6ff;
                background-color: #161b22;
            }
            QLineEdit::placeholder {
                color: #8b949e;
            }
        """)
        self.password_field.returnPressed.connect(self.authenticate)
        panel_layout.addWidget(self.password_field)
        
        # Login button matching main app style
        self.login_btn = QPushButton("AUTHENTICATE")
        self.login_btn.setFixedHeight(40)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f6feb, stop:1 #1a5cd7);
                color: #ffffff;
                border: 1.5px solid #58a6ff;
                border-radius: 6px;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2672f3, stop:1 #1f6feb);
                border: 1.5px solid #79c0ff;
            }
            QPushButton:pressed {
                background: #1a5cd7;
                border: 1.5px solid #58a6ff;
            }
        """)
        self.login_btn.clicked.connect(self.authenticate)
        panel_layout.addWidget(self.login_btn)
        
        # Security notice
        security_label = QLabel("Authorized personnel only")
        security_label.setAlignment(Qt.AlignCenter)
        security_label.setStyleSheet("""
            QLabel {
                color: #f85149;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 600;
                margin-top: 10px;
                background: transparent;
                border: none;
            }
        """)
        panel_layout.addWidget(security_label)
        
        layout.addWidget(login_panel)
        widget.setLayout(layout)
        return widget
    
    def create_config_widget(self):
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #0a0e1a;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Industrial header
        header_panel = QWidget()
        header_panel.setFixedHeight(65)
        header_panel.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #161b22, stop:1 #1c2128);
                border: 2px solid #30363d;
                border-left: 3px solid #58a6ff;
            }
        """)
        
        header_layout = QHBoxLayout(header_panel)
        header_layout.setContentsMargins(25, 15, 25, 15)
        
        # Branding section
        brand_container = QWidget()
        brand_layout = QVBoxLayout(brand_container)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(3)
        
        brand_small = QLabel("MOHSIN ELECTRONICS")
        brand_small.setStyleSheet("""
            QLabel {
                color: #58a6ff;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2.5px;
                background: transparent;
                border: none;
            }
        """)
        
        status_label = QLabel("System Configuration")
        status_label.setStyleSheet("""
            QLabel {
                color: #e6edf3;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 0.5px;
                background: transparent;
                border: none;
            }
        """)
        
        brand_layout.addWidget(brand_small)
        brand_layout.addWidget(status_label)
        
        # Logout button
        logout_btn = QPushButton("LOGOUT")
        logout_btn.setFixedSize(100, 35)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #da3633, stop:1 #b91c1c);
                color: #ffffff;
                border: 2px solid #f85149;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f85149, stop:1 #da3633);
                border: 2px solid #ff7b72;
            }
            QPushButton:pressed {
                background: #b91c1c;
                border: 2px solid #da3633;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        
        header_layout.addWidget(brand_container)
        header_layout.addStretch()
        header_layout.addWidget(logout_btn)
        main_layout.addWidget(header_panel)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #30363d;
                background: transparent;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: #161b22;
                color: #8b949e;
                border: 2px solid #30363d;
                padding: 12px 25px;
                margin-right: 2px;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 1.2px;
                min-width: 180px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f6feb, stop:1 #1a5cd7);
                color: #ffffff;
                border: 2px solid #58a6ff;
                border-bottom: 3px solid #58a6ff;
                font-weight: 700;
            }
            QTabBar::tab:hover:!selected {
                background: #1c2128;
                color: #c9d1d9;
                border: 2px solid #484f58;
            }
        """)
        
        # Temperature section with scroll area
        temp_scroll = QScrollArea()
        temp_scroll.setWidgetResizable(True)
        temp_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 12px;
                border: 1px solid #30363d;
            }
            QScrollBar::handle:vertical {
                background: #58a6ff;
                border: 1px solid #1f6feb;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #79c0ff;
                border: 1px solid #58a6ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        temp_widget = QWidget()
        temp_widget.setStyleSheet("QWidget { background: transparent; }")
        temp_layout = QVBoxLayout()
        temp_layout.setSpacing(15)
        temp_layout.setContentsMargins(15, 15, 15, 15)
        
        temp_cards = self.create_temperature_cards()
        for card in temp_cards:
            temp_layout.addWidget(card)
        temp_layout.addStretch()
        temp_widget.setLayout(temp_layout)
        temp_scroll.setWidget(temp_widget)
        
        # Pressure section with scroll area
        pressure_scroll = QScrollArea()
        pressure_scroll.setWidgetResizable(True)
        pressure_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 12px;
                border: 1px solid #30363d;
            }
            QScrollBar::handle:vertical {
                background: #58a6ff;
                border: 1px solid #1f6feb;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #79c0ff;
                border: 1px solid #58a6ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        pressure_widget = QWidget()
        pressure_widget.setStyleSheet("QWidget { background: transparent; }")
        pressure_layout = QGridLayout()
        pressure_layout.setSpacing(15)
        pressure_layout.setContentsMargins(15, 15, 15, 15)
        
        pressure_cards = self.create_pressure_cards()
        row, col = 0, 0
        for card in pressure_cards:
            pressure_layout.addWidget(card, row, col)
            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1
        pressure_layout.setRowStretch(row + 1, 1)
        pressure_widget.setLayout(pressure_layout)
        pressure_scroll.setWidget(pressure_widget)
        
        # Add tabs to tab widget
        self.tab_widget.addTab(temp_scroll, "TEMPERATURE THRESHOLDS")
        self.tab_widget.addTab(pressure_scroll, "PRESSURE THRESHOLDS")
        
        main_layout.addWidget(self.tab_widget)
        
        # Action buttons
        button_panel = QWidget()
        button_panel.setFixedHeight(60)
        button_panel.setStyleSheet("""
            QWidget {
                background: #161b22;
                border: 2px solid #30363d;
                border-top: 2px solid #484f58;
            }
        """)
        button_layout = QHBoxLayout(button_panel)
        button_layout.setContentsMargins(20, 10, 20, 10)
        
        reset_btn = QPushButton("RESET TO DEFAULTS")
        reset_btn.setFixedSize(170, 38)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0883e, stop:1 #d97706);
                color: #ffffff;
                border: 2px solid #fb923c;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fb923c, stop:1 #f0883e);
                border: 2px solid #fdba74;
            }
            QPushButton:pressed {
                background: #d97706;
                border: 2px solid #f0883e;
            }
        """)
        reset_btn.clicked.connect(self.reset_to_defaults)
        
        save_btn = QPushButton("SAVE CONFIGURATION")
        save_btn.setFixedSize(170, 38)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #238636, stop:1 #1a7f37);
                color: #ffffff;
                border: 2px solid #2ea043;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2ea043, stop:1 #238636);
                border: 2px solid #3fb950;
            }
            QPushButton:pressed {
                background: #1a7f37;
                border: 2px solid #2ea043;
            }
        """)
        save_btn.clicked.connect(self.save_configuration)
        
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        main_layout.addWidget(button_panel)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_temperature_cards(self):
        """Create modern card-based UI for temperature thresholds"""
        self.temp_controls = {}
        cards = []
        
        for section, thresholds in self.config["temperature_thresholds"].items():
            section_label = section.replace("_", " ").title()
            
            # Create card container
            card = QWidget()
            card.setStyleSheet("""
                QWidget {
                    background: #161b22;
                    border: 2px solid #30363d;
                    border-left: 3px solid #58a6ff;
                }
            """)
            card.setMinimumHeight(155)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(25, 20, 25, 20)
            card_layout.setSpacing(15)
            
            # Card title
            title = QLabel(section_label.upper())
            title.setStyleSheet("""
                QLabel {
                    color: #e6edf3;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 13px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    background: transparent;
                    border: none;
                    padding-bottom: 3px;
                    border-bottom: 1px solid #30363d;
                }
            """)
            card_layout.addWidget(title)
            
            # Threshold controls in horizontal layout
            controls_layout = QHBoxLayout()
            controls_layout.setSpacing(20)
            
            # Warning threshold section
            warning_container = QWidget()
            warning_container.setStyleSheet("QWidget { background: transparent; border: none; }")
            warning_layout = QVBoxLayout(warning_container)
            warning_layout.setContentsMargins(0, 0, 0, 0)
            warning_layout.setSpacing(8)
            
            warning_label = QLabel("⚠️ WARNING THRESHOLD")
            warning_label.setStyleSheet("""
                QLabel {
                    color: #fb923c;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1px;
                    background: transparent;
                    border: none;
                }
            """)
            
            warning_spin = QSpinBox()
            warning_spin.setRange(0, 1000)
            warning_spin.setValue(thresholds["warning"])
            warning_spin.setSuffix(" °C")
            warning_spin.setFixedHeight(40)
            warning_spin.setStyleSheet(self.get_modern_spinbox_style())
            
            warning_layout.addWidget(warning_label)
            warning_layout.addWidget(warning_spin)
            
            # Critical threshold section
            critical_container = QWidget()
            critical_container.setStyleSheet("QWidget { background: transparent; border: none; }")
            critical_layout = QVBoxLayout(critical_container)
            critical_layout.setContentsMargins(0, 0, 0, 0)
            critical_layout.setSpacing(8)
            
            critical_label = QLabel("🔴 CRITICAL THRESHOLD")
            critical_label.setStyleSheet("""
                QLabel {
                    color: #f85149;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1px;
                    background: transparent;
                    border: none;
                }
            """)
            
            critical_spin = QSpinBox()
            critical_spin.setRange(0, 1000)
            critical_spin.setValue(thresholds["critical"])
            critical_spin.setSuffix(" °C")
            critical_spin.setFixedHeight(40)
            critical_spin.setStyleSheet(self.get_modern_spinbox_style())
            
            critical_layout.addWidget(critical_label)
            critical_layout.addWidget(critical_spin)
            
            controls_layout.addWidget(warning_container)
            controls_layout.addWidget(critical_container)
            
            card_layout.addLayout(controls_layout)
            
            self.temp_controls[section] = {
                "warning": warning_spin,
                "critical": critical_spin
            }
            
            cards.append(card)
        
        return cards
    
    def create_pressure_cards(self):
        """Create modern card-based UI for pressure thresholds"""
        self.pressure_controls = {}
        cards = []
        
        # Get current gauge labels
        gauge_labels = self.config.get("gauge_labels", {})
        gauge_index = 0
        
        for gauge_name, thresholds in self.config["pressure_thresholds"].items():
            
            # Create card container
            card = QWidget()
            card.setStyleSheet("""
                QWidget {
                    background: #161b22;
                    border: 2px solid #30363d;
                    border-left: 3px solid #58a6ff;
                }
            """)
            card.setMinimumHeight(185)  # Increased height for edit hint
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 18, 20, 18)
            card_layout.setSpacing(8)
            
            # Get current label for this gauge
            gauge_key = f"gauge_{gauge_index}"
            current_label = gauge_labels.get(gauge_key, gauge_name)
            
            # Editable card title
            title = EditableLabel(current_label.upper(), 
                                lambda old, new, gk=gauge_key: self.update_gauge_label(gk, old, new))
            title.setStyleSheet("""
                QLabel {
                    color: #e6edf3;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 1.2px;
                    background: transparent;
                    border: none;
                    padding-bottom: 3px;
                    border-bottom: 1px solid #30363d;
                }
                QLabel:hover {
                    color: #58a6ff;
                    border-bottom: 1px solid #58a6ff;
                }
            """)
            title.setWordWrap(True)
            title.setToolTip("Click to edit gauge label")
            card_layout.addWidget(title)
            
            # Edit hint
            edit_hint = QLabel("📝 Click title to edit")
            edit_hint.setStyleSheet("""
                QLabel {
                    color: #6e7681;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 9px;
                    font-weight: 500;
                    font-style: italic;
                    background: transparent;
                    border: none;
                    margin-bottom: 5px;
                }
            """)
            card_layout.addWidget(edit_hint)
            
            # Threshold controls
            controls_container = QWidget()
            controls_container.setStyleSheet("QWidget { background: transparent; border: none; }")
            controls_layout = QVBoxLayout(controls_container)
            controls_layout.setContentsMargins(0, 0, 0, 0)
            controls_layout.setSpacing(10)
            
            # Warning threshold
            warning_label = QLabel("⚠️ WARNING")
            warning_label.setStyleSheet("""
                QLabel {
                    color: #fb923c;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1px;
                    background: transparent;
                    border: none;
                }
            """)
            
            warning_spin = QDoubleSpinBox()
            warning_spin.setRange(0.0, 100.0)
            warning_spin.setDecimals(1)
            warning_spin.setValue(thresholds["warning"])
            warning_spin.setSuffix(" bar")
            warning_spin.setFixedHeight(38)
            warning_spin.setStyleSheet(self.get_modern_spinbox_style())
            
            # Critical threshold
            critical_label = QLabel("🔴 CRITICAL")
            critical_label.setStyleSheet("""
                QLabel {
                    color: #f85149;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1px;
                    background: transparent;
                    border: none;
                }
            """)
            
            critical_spin = QDoubleSpinBox()
            critical_spin.setRange(0.0, 100.0)
            critical_spin.setDecimals(1)
            critical_spin.setValue(thresholds["critical"])
            critical_spin.setSuffix(" bar")
            critical_spin.setFixedHeight(38)
            critical_spin.setStyleSheet(self.get_modern_spinbox_style())
            
            controls_layout.addWidget(warning_label)
            controls_layout.addWidget(warning_spin)
            controls_layout.addWidget(critical_label)
            controls_layout.addWidget(critical_spin)
            
            card_layout.addWidget(controls_container)
            
            self.pressure_controls[gauge_name] = {
                "warning": warning_spin,
                "critical": critical_spin
            }
            
            cards.append(card)
            gauge_index += 1
        
        return cards
    
    def get_modern_spinbox_style(self):
        """Industrial spinbox styling"""
        return """
            QSpinBox, QDoubleSpinBox {
                background: #0d1117;
                border: 2px solid #30363d;
                padding: 8px 12px;
                color: #58a6ff;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 15px;
                font-weight: 700;
                selection-background-color: #1f6feb;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #58a6ff;
                background: #0d1117;
                outline: none;
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border: 2px solid #484f58;
                background: #161b22;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                background: #30363d;
                border: 1px solid #484f58;
                width: 18px;
                margin: 1px;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background: #58a6ff;
                border: 1px solid #58a6ff;
            }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid #e6edf3;
                margin-bottom: 2px;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #e6edf3;
                margin-top: 2px;
            }
        """
    
    def get_spinbox_style(self):
        return """
            QSpinBox, QDoubleSpinBox {
                background-color: #0d1117;
                border: 1.5px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #e6edf3;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 400;
                selection-background-color: #1f6feb;
                min-height: 20px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1.5px solid #58a6ff;
                outline: none;
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border: 1.5px solid #58a6ff;
                background-color: #161b22;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                background-color: #30363d;
                border: 1px solid #30363d;
                border-radius: 3px;
                width: 16px;
                margin: 1px;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #58a6ff;
                border: 1px solid #58a6ff;
            }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 6px solid #e6edf3;
                margin-bottom: 2px;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #e6edf3;
                margin-top: 2px;
            }
        """
    
    def authenticate(self):
        password = self.password_field.text()
        # Get admin password from parent window
        admin_password = getattr(self.parent_window, 'admin_password', 'admin123')
        
        if password == admin_password:
            self.is_authenticated = True
            self.stacked_widget.setCurrentIndex(1)
            self.password_field.clear()
        else:
            QMessageBox.warning(self, "Access Denied", "Incorrect password!")
            self.password_field.clear()
    
    def logout(self):
        self.is_authenticated = False
        self.stacked_widget.setCurrentIndex(0)
    
    def update_gauge_label(self, gauge_key, old_label, new_label):
        """Update gauge label in configuration"""
        if "gauge_labels" not in self.config:
            self.config["gauge_labels"] = {}
        
        self.config["gauge_labels"][gauge_key] = new_label
        
        # Show confirmation message
        QMessageBox.information(self, "Label Updated", 
                              f"Gauge label updated to: {new_label}\n\nRemember to save configuration to persist changes.")
    
    def save_configuration(self):
        # Update config from controls
        for section, controls in self.temp_controls.items():
            self.config["temperature_thresholds"][section]["warning"] = controls["warning"].value()
            self.config["temperature_thresholds"][section]["critical"] = controls["critical"].value()
        
        for gauge_name, controls in self.pressure_controls.items():
            self.config["pressure_thresholds"][gauge_name]["warning"] = controls["warning"].value()
            self.config["pressure_thresholds"][gauge_name]["critical"] = controls["critical"].value()
        
        # Save to file
        try:
            with open("hmi_config.json", "w") as f:
                json.dump(self.config, f, indent=4)
            QMessageBox.information(self, "Success", "Configuration saved successfully!")
            
            # Notify parent window to update thresholds
            if self.parent_window:
                self.parent_window.update_thresholds(self.config)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
    
    def load_configuration(self):
        try:
            if os.path.exists("hmi_config.json"):
                with open("hmi_config.json", "r") as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except Exception as e:
            print(f"Failed to load configuration: {e}")
    
    def reset_to_defaults(self):
        reply = QMessageBox.question(self, "Reset Configuration", 
                                   "Are you sure you want to reset all settings to default values?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Reset to default values
            self.config = {
                "temperature_thresholds": {
                    "cylinder_head": {"warning": 400, "critical": 600},
                    "main_bearing": {"warning": 150, "critical": 250}
                },
                "pressure_thresholds": {
                    "Fuel Oil Pressure Inlet": {"warning": 6, "critical": 8},
                    "Lube Oil Pressure Inlet": {"warning": 3, "critical": 2},
                    "LT Water Pressure": {"warning": 6, "critical": 8},
                    "HT Water Pressure": {"warning": 6, "critical": 8},
                    "Charge Air Pressure": {"warning": 6, "critical": 8},
                    "Starting Air Pressure": {"warning": 18, "critical": 24},
                    "Lube Oil Differential Pressure": {"warning": 6, "critical": 8},
                    "Crank Case Pressure": {"warning": 6, "critical": 8}
                },
                "gauge_labels": {
                    "gauge_0": "Fuel Oil Pressure Inlet",
                    "gauge_1": "Lube Oil Pressure Inlet", 
                    "gauge_2": "LT Water Pressure",
                    "gauge_3": "HT Water Pressure",
                    "gauge_4": "Charge Air Pressure",
                    "gauge_5": "Starting Air Pressure",
                    "gauge_6": "Lube Oil Differential Pressure",
                    "gauge_7": "Crank Case Pressure"
                }
            }
            
            # Update controls
            for section, controls in self.temp_controls.items():
                controls["warning"].setValue(self.config["temperature_thresholds"][section]["warning"])
                controls["critical"].setValue(self.config["temperature_thresholds"][section]["critical"])
            
            for gauge_name, controls in self.pressure_controls.items():
                controls["warning"].setValue(self.config["pressure_thresholds"][gauge_name]["warning"])
                controls["critical"].setValue(self.config["pressure_thresholds"][gauge_name]["critical"])
            
            # Refresh the pressure cards to show default labels
            QMessageBox.information(self, "Reset Complete", 
                                  "Configuration reset to defaults.\n\nPlease switch tabs to see updated labels.")


# ---------------- Engine Temperatures Tab ----------------
class EngineTemperaturesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.setStyleSheet(CYLINDER_HEAD_BG_STYLE)
        self.setMinimumSize(800, 600)
        
        # Current section (0 or 1)
        self.current_section = 0
        
        # Temperature gauge labels - Split into two sections
        self.section_labels = [
            # Section 1: Primary Engine Temperatures (8 gauges)
            [
                "Charge Air Temp",
                "Lube Oil Inlet Temp", 
                "Fuel Oil Temp",
                "HT Water Temp Inlet",
                "HT Water Temp Outlet",
                "LT Water Temp Inlet",
                "LT Water Temp Outlet",
                "Alternator Bearing Temp A"
            ],
            # Section 2: Secondary Engine Temperatures (8 gauges)
            [
                "Alternator Bearing Temp B",
                "Winding Temp U",
                "Winding Temp V",
                "Winding Temp W",
                "Engine Temp 13",
                "Engine Temp 14", 
                "Engine Temp 15",
                "Engine Temp 16"
            ]
        ]
        
        # Create all 16 temperature gauges with indices
        self.temp_gauges = []
        gauge_index = 0
        for section_labels in self.section_labels:
            section_gauges = []
            for label in section_labels:
                gauge = CircularTemperatureGauge(label, max_value=250, gauge_index=gauge_index, parent_window=self.parent_window)
                section_gauges.append(gauge)
                gauge_index += 1
            self.temp_gauges.append(section_gauges)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Header with title and navigation
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)
        
        # Title with section indicator
        self.title = QLabel("ENGINE TEMPERATURES - SECTION 1")
        self.title.setStyleSheet("""
            QLabel {
                color: rgb(255, 255, 255);
                font-size: 18px;
                font-weight: 700;
                letter-spacing: 1.5px;
                padding: 15px;
                text-align: center;
            }
        """)
        self.title.setAlignment(Qt.AlignCenter)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)
        
        self.prev_btn = QPushButton("◀ BACK")
        self.prev_btn.setFixedSize(100, 45)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(70, 130, 180), stop:1 rgb(50, 100, 150));
                color: rgb(255, 255, 255);
                border: 1px solid rgb(90, 150, 200);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(90, 150, 200), stop:1 rgb(70, 130, 180));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(50, 100, 150), stop:1 rgb(30, 80, 130));
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 0.3);
                color: rgba(255, 255, 255, 0.5);
                border: 1px solid rgba(100, 100, 100, 0.5);
            }
        """)
        self.prev_btn.clicked.connect(self.go_to_previous_section)
        
        self.next_btn = QPushButton("NEXT ▶")
        self.next_btn.setFixedSize(100, 45)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(70, 130, 180), stop:1 rgb(50, 100, 150));
                color: rgb(255, 255, 255);
                border: 1px solid rgb(90, 150, 200);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(90, 150, 200), stop:1 rgb(70, 130, 180));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(50, 100, 150), stop:1 rgb(30, 80, 130));
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 0.3);
                color: rgba(255, 255, 255, 0.5);
                border: 1px solid rgba(100, 100, 100, 0.5);
            }
        """)
        self.next_btn.clicked.connect(self.go_to_next_section)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        
        header_layout.addWidget(self.title, 1)
        header_layout.addLayout(nav_layout)
        
        # Gauge display area
        self.gauge_container = QWidget()
        self.gauge_container.setStyleSheet("background: transparent;")
        
        # Grid layout for current section (4x2 layout for 8 gauges) - Professional spacing
        self.gauge_layout = QGridLayout(self.gauge_container)
        self.gauge_layout.setContentsMargins(20, 20, 20, 20)  # Balanced margins
        self.gauge_layout.setSpacing(15)  # Optimal spacing for gauge visibility
        
        # Set equal column stretches for 4 columns
        for col in range(4):
            self.gauge_layout.setColumnStretch(col, 1)
        
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.gauge_container, 1)
        
        self.setLayout(main_layout)
        
        # Default thresholds (can be overridden by configuration)
        self.thresholds = {"warning": 180, "critical": 220}
        
        # Initialize display
        self.update_section_display()
    
    def go_to_next_section(self):
        """Switch to next section"""
        if self.current_section < 1:
            self.current_section += 1
            self.update_section_display()
    
    def go_to_previous_section(self):
        """Switch to previous section"""
        if self.current_section > 0:
            self.current_section -= 1
            self.update_section_display()
    
    def update_section_display(self):
        """Update the display to show current section"""
        # Clear current layout
        for i in reversed(range(self.gauge_layout.count())):
            child = self.gauge_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Update title
        section_names = ["SECTION 1", "SECTION 2"]
        self.title.setText(f"ENGINE TEMPERATURES - {section_names[self.current_section]}")
        
        # Add current section gauges to layout (4x2 grid)
        current_gauges = self.temp_gauges[self.current_section]
        for i, gauge in enumerate(current_gauges):
            row = i // 4
            col = i % 4
            self.gauge_layout.addWidget(gauge, row, col)
        
        # Update navigation button states
        self.prev_btn.setEnabled(self.current_section > 0)
        self.next_btn.setEnabled(self.current_section < 1)
    
    def update_temperatures(self, values):
        """Update temperature values for all gauges"""
        # Ensure we have exactly 16 values
        if len(values) >= 16:
            temp_values = values[:16]
        else:
            # Pad with zeros if not enough values
            temp_values = list(values) + [0] * (16 - len(values))
        
        # Update each gauge with its corresponding temperature value
        gauge_index = 0
        for section_gauges in self.temp_gauges:
            for gauge in section_gauges:
                # Convert raw value to temperature (divide by 10 if needed, similar to other sections)
                temp_celsius = temp_values[gauge_index] / 10.0 if temp_values[gauge_index] > 0 else 0
                gauge.set_value(temp_celsius)
                gauge_index += 1
    
    def set_thresholds(self, thresholds):
        """Update temperature thresholds for all gauges"""
        self.thresholds = thresholds
        for section_gauges in self.temp_gauges:
            for gauge in section_gauges:
                gauge.set_thresholds(thresholds)
    
    def set_modbus_client(self, client):
        """Set the Modbus client for all gauges"""
        for section_gauges in self.temp_gauges:
            for gauge in section_gauges:
                gauge.set_modbus_client(client)


# ---------------- Modern Voltage Display Widget ----------------
class ModernVoltageDisplay(QWidget):
    def __init__(self, label, phase_from, phase_to, max_value=500):
        super().__init__()
        self.label = label
        self.phase_from = phase_from
        self.phase_to = phase_to
        self.max_value = max_value
        self.current_value = 0.0
        self.target_value = 0.0
        self.setMinimumSize(280, 120)
        self.setMaximumSize(320, 140)
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_value)
        self.animation_timer.start(16)  # 60 FPS
        
        # Default thresholds for voltage (typically 380-420V for 3-phase)
        self.thresholds = {"low": 350, "nominal_low": 380, "nominal_high": 420, "high": 450}
    
    def set_value(self, value):
        self.target_value = max(0, min(value, self.max_value))
    
    def animate_value(self):
        easing_factor = 0.08
        threshold = 0.1
        
        distance = self.target_value - self.current_value
        
        if abs(distance) < threshold:
            self.current_value = self.target_value
        else:
            self.current_value += distance * easing_factor
            self.update()
    
    def get_voltage_color(self, value):
        """Get color based on voltage level - electrical engineering standards"""
        if value < self.thresholds["low"]:
            return QColor(255, 80, 80)  # Red - Under voltage
        elif value < self.thresholds["nominal_low"]:
            return QColor(255, 180, 0)  # Amber - Low voltage
        elif value <= self.thresholds["nominal_high"]:
            return QColor(0, 255, 150)  # Green - Normal voltage
        elif value <= self.thresholds["high"]:
            return QColor(255, 180, 0)  # Amber - High voltage
        else:
            return QColor(255, 80, 80)  # Red - Over voltage
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        width = self.width()
        height = self.height()
        
        # Get voltage color
        voltage_color = self.get_voltage_color(self.current_value)
        
        # Draw main container with clean industrial styling
        container_gradient = QLinearGradient(0, 0, 0, height)
        container_gradient.setColorAt(0, QColor(20, 25, 35))
        container_gradient.setColorAt(1, QColor(15, 18, 25))
        
        painter.setBrush(container_gradient)
        painter.setPen(QPen(QColor(40, 50, 65), 2))
        painter.drawRoundedRect(2, 2, width - 4, height - 4, 8, 8)
        
        # Draw accent border based on voltage status
        accent_gradient = QLinearGradient(0, 0, width, 0)
        accent_gradient.setColorAt(0, voltage_color.darker(150))
        accent_gradient.setColorAt(0.5, voltage_color)
        accent_gradient.setColorAt(1, voltage_color.darker(150))
        
        painter.setPen(QPen(accent_gradient, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(2, 2, width - 4, height - 4, 8, 8)
        
        # Draw phase indicator in top-left
        phase_font_size = 11
        painter.setFont(QFont("Segoe UI", phase_font_size, QFont.Bold))
        painter.setPen(QColor(120, 140, 160))
        
        phase_text = f"{self.phase_from}-{self.phase_to}"
        painter.drawText(15, 25, phase_text)
        
        # Draw main voltage value - large and centered
        value_font_size = 36
        painter.setFont(QFont("JetBrains Mono", value_font_size, QFont.Bold))
        painter.setPen(voltage_color)
        
        voltage_text = f"{self.current_value:.1f}"
        value_rect = QRectF(15, height * 0.3, width - 80, height * 0.4)
        painter.drawText(value_rect, Qt.AlignLeft | Qt.AlignVCenter, voltage_text)
        
        # Draw unit in top-right
        unit_font_size = 18
        painter.setFont(QFont("Segoe UI", unit_font_size, QFont.Bold))
        painter.setPen(QColor(180, 200, 220))
        
        unit_rect = QRectF(width - 65, height * 0.25, 50, height * 0.3)
        painter.drawText(unit_rect, Qt.AlignCenter, "V")
        
        # Draw label at bottom (positioned above progress bar)
        label_font_size = 9
        painter.setFont(QFont("Segoe UI", label_font_size, QFont.Medium))
        painter.setPen(QColor(140, 160, 180))
        
        label_y = height - 35  # Position label higher to avoid overlap
        label_rect = QRectF(15, label_y, width - 30, 12)
        painter.drawText(label_rect, Qt.AlignLeft | Qt.AlignVCenter, self.label.upper())
        
        # Draw status bar at bottom with proper spacing
        status_height = 6
        status_y = height - status_height - 12  # More space from bottom
        status_width = width - 30
        
        # Background bar
        painter.setBrush(QColor(30, 35, 45))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(15, status_y, status_width, status_height, 3, 3)
        
        # Status fill based on voltage level
        fill_percentage = min(1.0, self.current_value / self.max_value)
        fill_width = int(status_width * fill_percentage)
        
        if fill_width > 0:
            status_gradient = QLinearGradient(15, status_y, 15 + fill_width, status_y)
            status_gradient.setColorAt(0, voltage_color.darker(120))
            status_gradient.setColorAt(1, voltage_color)
            
            painter.setBrush(status_gradient)
            painter.drawRoundedRect(15, status_y, fill_width, status_height, 3, 3)
        
        painter.end()


# ---------------- Modern Current Display Widget ----------------
class ModernCurrentDisplay(QWidget):
    def __init__(self, label, phase_from, phase_to, max_value=100):
        super().__init__()
        self.label = label
        self.phase_from = phase_from
        self.phase_to = phase_to
        self.max_value = max_value
        self.current_value = 0.0
        self.target_value = 0.0
        self.setMinimumSize(280, 120)
        self.setMaximumSize(320, 140)
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_value)
        self.animation_timer.start(16)  # 60 FPS
        
        # Default thresholds for current
        self.thresholds = {"normal": 70, "warning": 85, "critical": 95}
    
    def set_value(self, value):
        self.target_value = max(0, min(value, self.max_value))
    
    def animate_value(self):
        easing_factor = 0.08
        threshold = 0.1
        
        distance = self.target_value - self.current_value
        
        if abs(distance) < threshold:
            self.current_value = self.target_value
        else:
            self.current_value += distance * easing_factor
            self.update()
    
    def get_current_color(self, value):
        """Get color based on current level"""
        percentage = (value / self.max_value) * 100
        
        if percentage <= self.thresholds["normal"]:
            return QColor(0, 255, 150)  # Green - Normal
        elif percentage <= self.thresholds["warning"]:
            return QColor(255, 180, 0)  # Amber - Warning
        else:
            return QColor(255, 80, 80)  # Red - Critical
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        width = self.width()
        height = self.height()
        
        # Get current color
        current_color = self.get_current_color(self.current_value)
        
        # Draw main container with clean industrial styling
        container_gradient = QLinearGradient(0, 0, 0, height)
        container_gradient.setColorAt(0, QColor(20, 25, 35))
        container_gradient.setColorAt(1, QColor(15, 18, 25))
        
        painter.setBrush(container_gradient)
        painter.setPen(QPen(QColor(40, 50, 65), 2))
        painter.drawRoundedRect(2, 2, width - 4, height - 4, 8, 8)
        
        # Draw accent border based on current status
        accent_gradient = QLinearGradient(0, 0, width, 0)
        accent_gradient.setColorAt(0, current_color.darker(150))
        accent_gradient.setColorAt(0.5, current_color)
        accent_gradient.setColorAt(1, current_color.darker(150))
        
        painter.setPen(QPen(accent_gradient, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(2, 2, width - 4, height - 4, 8, 8)
        
        # Draw phase indicator in top-left
        phase_font_size = 11
        painter.setFont(QFont("Segoe UI", phase_font_size, QFont.Bold))
        painter.setPen(QColor(120, 140, 160))
        
        phase_text = self.label  # Use the label directly (L1, L2, L3)
        painter.drawText(15, 25, phase_text)
        
        # Draw main current value - large and centered
        value_font_size = 36
        painter.setFont(QFont("JetBrains Mono", value_font_size, QFont.Bold))
        painter.setPen(current_color)
        
        current_text = f"{self.current_value:.1f}"
        value_rect = QRectF(15, height * 0.3, width - 80, height * 0.4)
        painter.drawText(value_rect, Qt.AlignLeft | Qt.AlignVCenter, current_text)
        
        # Draw unit in top-right
        unit_font_size = 18
        painter.setFont(QFont("Segoe UI", unit_font_size, QFont.Bold))
        painter.setPen(QColor(180, 200, 220))
        
        unit_rect = QRectF(width - 65, height * 0.25, 50, height * 0.3)
        painter.drawText(unit_rect, Qt.AlignCenter, "A")
        
        # Draw status bar at bottom with proper spacing
        status_height = 6
        status_y = height - status_height - 12  # More space from bottom
        status_width = width - 30
        
        # Background bar
        painter.setBrush(QColor(30, 35, 45))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(15, status_y, status_width, status_height, 3, 3)
        
        # Status fill based on current level
        fill_percentage = min(1.0, self.current_value / self.max_value)
        fill_width = int(status_width * fill_percentage)
        
        if fill_width > 0:
            status_gradient = QLinearGradient(15, status_y, 15 + fill_width, status_y)
            status_gradient.setColorAt(0, current_color.darker(120))
            status_gradient.setColorAt(1, current_color)
            
            painter.setBrush(status_gradient)
            painter.drawRoundedRect(15, status_y, fill_width, status_height, 3, 3)
        
        painter.end()


# ---------------- Modern Power Display Widget ----------------
class ModernPowerDisplay(QWidget):
    def __init__(self, label, unit, max_value=1000, decimal_places=1):
        super().__init__()
        self.label = label
        self.unit = unit
        self.max_value = max_value
        self.decimal_places = decimal_places
        self.current_value = 0.0
        self.target_value = 0.0
        self.setMinimumSize(280, 120)
        self.setMaximumSize(320, 140)
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_value)
        self.animation_timer.start(16)  # 60 FPS
        
        # Color thresholds based on parameter type
        if "Power Factor" in label:
            # Power factor: 0.95-1.0 is excellent, 0.85-0.95 is good, below 0.85 is poor
            self.thresholds = {"poor": 0.85, "good": 0.95, "excellent": 1.0}
        else:
            # For KW and KVAR: percentage-based thresholds
            self.thresholds = {"normal": 70, "warning": 85, "critical": 95}
    
    def set_value(self, value):
        self.target_value = max(0, min(value, self.max_value))
    
    def animate_value(self):
        easing_factor = 0.08
        threshold = 0.01
        
        distance = self.target_value - self.current_value
        
        if abs(distance) < threshold:
            self.current_value = self.target_value
        else:
            self.current_value += distance * easing_factor
            self.update()
    
    def get_value_color(self, value):
        """Get color based on parameter type and value"""
        if "Power Factor" in self.label:
            if value >= self.thresholds["excellent"]:
                return QColor(0, 255, 150)  # Green - Excellent
            elif value >= self.thresholds["good"]:
                return QColor(100, 255, 100)  # Light Green - Good
            elif value >= self.thresholds["poor"]:
                return QColor(255, 180, 0)  # Amber - Fair
            else:
                return QColor(255, 80, 80)  # Red - Poor
        else:
            # For KW and KVAR
            percentage = (value / self.max_value) * 100
            if percentage <= self.thresholds["normal"]:
                return QColor(0, 255, 150)  # Green - Normal
            elif percentage <= self.thresholds["warning"]:
                return QColor(255, 180, 0)  # Amber - Warning
            else:
                return QColor(255, 80, 80)  # Red - Critical
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        width = self.width()
        height = self.height()
        
        # Get value color
        value_color = self.get_value_color(self.current_value)
        
        # Draw main container with clean industrial styling
        container_gradient = QLinearGradient(0, 0, 0, height)
        container_gradient.setColorAt(0, QColor(20, 25, 35))
        container_gradient.setColorAt(1, QColor(15, 18, 25))
        
        painter.setBrush(container_gradient)
        painter.setPen(QPen(QColor(40, 50, 65), 2))
        painter.drawRoundedRect(2, 2, width - 4, height - 4, 8, 8)
        
        # Draw accent border based on value status
        accent_gradient = QLinearGradient(0, 0, width, 0)
        accent_gradient.setColorAt(0, value_color.darker(150))
        accent_gradient.setColorAt(0.5, value_color)
        accent_gradient.setColorAt(1, value_color.darker(150))
        
        painter.setPen(QPen(accent_gradient, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(2, 2, width - 4, height - 4, 8, 8)
        
        # Draw label in top-left
        label_font_size = 11
        painter.setFont(QFont("Segoe UI", label_font_size, QFont.Bold))
        painter.setPen(QColor(120, 140, 160))
        
        painter.drawText(15, 25, self.label.upper())
        
        # Draw main value - large and centered
        value_font_size = 36
        painter.setFont(QFont("JetBrains Mono", value_font_size, QFont.Bold))
        painter.setPen(value_color)
        
        if self.decimal_places == 0:
            value_text = f"{int(self.current_value)}"
        else:
            value_text = f"{self.current_value:.{self.decimal_places}f}"
        
        value_rect = QRectF(15, height * 0.3, width - 80, height * 0.4)
        painter.drawText(value_rect, Qt.AlignLeft | Qt.AlignVCenter, value_text)
        
        # Draw unit in top-right (if exists)
        if self.unit:
            unit_font_size = 18
            painter.setFont(QFont("Segoe UI", unit_font_size, QFont.Bold))
            painter.setPen(QColor(180, 200, 220))
            
            unit_rect = QRectF(width - 80, height * 0.25, 65, height * 0.3)
            painter.drawText(unit_rect, Qt.AlignCenter, self.unit)
        
        # Draw status bar at bottom
        status_height = 8
        status_y = height - status_height - 8
        status_width = width - 30
        
        # Background bar
        painter.setBrush(QColor(30, 35, 45))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(15, status_y, status_width, status_height, 4, 4)
        
        # Status fill based on value level
        if "Power Factor" in self.label:
            # Power factor: show as percentage of ideal (1.0)
            fill_percentage = min(1.0, self.current_value / 1.0)
        else:
            fill_percentage = min(1.0, self.current_value / self.max_value)
        
        fill_width = int(status_width * fill_percentage)
        
        if fill_width > 0:
            status_gradient = QLinearGradient(15, status_y, 15 + fill_width, status_y)
            status_gradient.setColorAt(0, value_color.darker(120))
            status_gradient.setColorAt(1, value_color)
            
            painter.setBrush(status_gradient)
            painter.drawRoundedRect(15, status_y, fill_width, status_height, 4, 4)
        
        painter.end()


# ---------------- Modbus Configuration Dialog ----------------
class ModbusConfigDialog(QDialog):
    def __init__(self, parent, group_name, current_config):
        super().__init__(parent)
        self.group_name = group_name
        self.config = current_config.copy() if current_config else []
        self.setWindowTitle(f"Configure {group_name} - Modbus Addresses")
        self.setMinimumSize(750, 400)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(20, 25, 35), stop:1 rgb(15, 18, 25));
                color: rgb(200, 220, 240);
            }
            QTableWidget {
                background-color: rgb(25, 30, 40);
                border: 1px solid rgb(60, 75, 95);
                gridline-color: rgb(40, 50, 65);
                color: rgb(200, 220, 240);
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: rgb(58, 106, 255);
            }
            QHeaderView::section {
                background-color: rgb(35, 45, 60);
                color: rgb(100, 150, 200);
                padding: 8px;
                border: 1px solid rgb(60, 75, 95);
                font-weight: bold;
            }
            QComboBox {
                background-color: rgb(30, 38, 50);
                border: 1px solid rgb(60, 75, 95);
                padding: 5px;
                color: rgb(200, 220, 240);
                min-height: 25px;
            }
            QComboBox:hover {
                border: 1px solid rgb(100, 150, 200);
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: rgb(30, 38, 50);
                border: 1px solid rgb(60, 75, 95);
                selection-background-color: rgb(58, 106, 255);
                color: rgb(200, 220, 240);
            }
            QLineEdit {
                background-color: rgb(30, 38, 50);
                border: 1px solid rgb(60, 75, 95);
                padding: 5px;
                color: rgb(200, 220, 240);
                min-height: 25px;
            }
            QLineEdit:focus {
                border: 1px solid rgb(100, 150, 200);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(58, 106, 255), stop:1 rgb(38, 76, 200));
                color: white;
                border: 1px solid rgb(100, 150, 255);
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(78, 126, 255), stop:1 rgb(58, 96, 220));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(38, 76, 200), stop:1 rgb(28, 56, 150));
            }
            QPushButton#resetBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(255, 180, 0), stop:1 rgb(220, 140, 0));
                border: 1px solid rgb(255, 200, 50);
                color: rgb(20, 25, 35);
            }
            QPushButton#resetBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(255, 200, 50), stop:1 rgb(240, 160, 20));
            }
            QPushButton#cancelBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(80, 90, 110), stop:1 rgb(60, 70, 90));
                border: 1px solid rgb(100, 110, 130);
            }
            QPushButton#cancelBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(100, 110, 130), stop:1 rgb(80, 90, 110));
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel(f"⚙️ {group_name} Configuration")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: rgb(100, 150, 200);")
        layout.addWidget(title)
        
        # Info label
        info = QLabel("Configure Modbus register addresses for each parameter:")
        info.setStyleSheet("color: rgb(150, 170, 190); margin-bottom: 5px;")
        layout.addWidget(info)
        
        # Address range info
        range_info = QLabel(
            "📋 Address Ranges: Input (30001-39999) | Holding (40001-49999) | Coil (1-9999) | Discrete (10001-19999)"
        )
        range_info.setStyleSheet("""
            color: rgb(100, 180, 255);
            background-color: rgba(58, 106, 255, 0.1);
            border: 1px solid rgb(58, 106, 255);
            border-radius: 3px;
            padding: 8px;
            margin-bottom: 10px;
            font-size: 11px;
        """)
        range_info.setWordWrap(True)
        layout.addWidget(range_info)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Label", "Register Type", "Address", "Device ID"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setRowCount(len(self.config))
        
        # Populate table with current configuration
        for row, param in enumerate(self.config):
            # Label
            label_edit = QLineEdit(param.get("label", ""))
            self.table.setCellWidget(row, 0, label_edit)
            
            # Register Type
            type_combo = QComboBox()
            type_combo.addItems(["input", "holding", "coil", "discrete"])
            current_type = param.get("type", "input")
            type_combo.setCurrentText(current_type)
            # Connect signal to update address when type changes
            type_combo.currentTextChanged.connect(lambda text, r=row: self.update_address_for_type(r, text))
            self.table.setCellWidget(row, 1, type_combo)
            
            # Address - set appropriate placeholder based on type
            addr_edit = QLineEdit(str(param.get("address", 30001)))
            placeholder_map = {
                "input": "e.g. 30001",
                "holding": "e.g. 40001",
                "coil": "e.g. 1",
                "discrete": "e.g. 10001"
            }
            addr_edit.setPlaceholderText(placeholder_map.get(current_type, "e.g. 30001"))
            self.table.setCellWidget(row, 2, addr_edit)
            
            # Device ID
            device_edit = QLineEdit(str(param.get("device_id", 5)))
            device_edit.setPlaceholderText("e.g. 1")
            self.table.setCellWidget(row, 3, device_edit)
        
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Reset to defaults button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setObjectName("resetBtn")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # Save button
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def update_address_for_type(self, row, register_type):
        """Update address field when register type changes"""
        # Get current address widget
        addr_widget = self.table.cellWidget(row, 2)
        if not addr_widget:
            return
        
        # Get current address value
        try:
            current_addr = int(addr_widget.text())
        except ValueError:
            current_addr = None
        
        # Determine base address and range for the selected type
        type_ranges = {
            "input": (30001, 39999, "e.g. 30001"),
            "holding": (40001, 49999, "e.g. 40001"),
            "coil": (1, 9999, "e.g. 1"),
            "discrete": (10001, 19999, "e.g. 10001")
        }
        
        if register_type in type_ranges:
            base_addr, max_addr, placeholder = type_ranges[register_type]
            
            # If current address is not in the new range, update it to the base address
            if current_addr is None or current_addr < base_addr or current_addr > max_addr:
                addr_widget.setText(str(base_addr))
            
            # Update placeholder text
            addr_widget.setPlaceholderText(placeholder)
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        reply = QMessageBox.question(self, "Reset to Defaults",
                                    "Are you sure you want to reset to default configuration?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            defaults = self.get_default_config(self.group_name)
            self.config = defaults
            # Repopulate table
            for row, param in enumerate(self.config):
                self.table.cellWidget(row, 0).setText(param.get("label", ""))
                self.table.cellWidget(row, 1).setCurrentText(param.get("type", "input"))
                self.table.cellWidget(row, 2).setText(str(param.get("address", 30001)))
                self.table.cellWidget(row, 3).setText(str(param.get("device_id", 5)))
            QMessageBox.information(self, "Reset Complete", "Configuration reset to defaults.")
    
    def get_default_config(self, group_name):
        """Get default configuration for a group"""
        if group_name == "Voltage":
            return [
                {"label": "L1-L2 Voltage", "type": "input", "address": 30001, "device_id": 5},
                {"label": "L2-L3 Voltage", "type": "input", "address": 30002, "device_id": 5},
                {"label": "L3-L1 Voltage", "type": "input", "address": 30003, "device_id": 5}
            ]
        elif group_name == "Current":
            return [
                {"label": "L1", "type": "input", "address": 30004, "device_id": 5},
                {"label": "L2", "type": "input", "address": 30005, "device_id": 5},
                {"label": "L3", "type": "input", "address": 30006, "device_id": 5}
            ]
        elif group_name == "Power":
            return [
                {"label": "Active Power", "type": "input", "address": 30007, "device_id": 5},
                {"label": "Power Factor", "type": "input", "address": 30008, "device_id": 5},
                {"label": "Reactive Power", "type": "input", "address": 30009, "device_id": 5}
            ]
        return []
    
    def save_config(self):
        """Validate and save configuration"""
        new_config = []
        
        for row in range(self.table.rowCount()):
            label = self.table.cellWidget(row, 0).text()
            reg_type = self.table.cellWidget(row, 1).currentText()
            address_text = self.table.cellWidget(row, 2).text()
            device_text = self.table.cellWidget(row, 3).text()
            
            # Validate address
            try:
                address = int(address_text)
                if address < 1 or address > 65535:
                    QMessageBox.warning(self, "Invalid Address",
                                      f"Address for '{label}' must be between 1 and 65535.")
                    return
            except ValueError:
                QMessageBox.warning(self, "Invalid Address",
                                  f"Address for '{label}' must be a valid number.")
                return
            
            # Validate device ID
            try:
                device_id = int(device_text)
                if device_id < 1 or device_id > 255:
                    QMessageBox.warning(self, "Invalid Device ID",
                                      f"Device ID for '{label}' must be between 1 and 255.")
                    return
            except ValueError:
                QMessageBox.warning(self, "Invalid Device ID",
                                  f"Device ID for '{label}' must be a valid number.")
                return
            
            new_config.append({
                "label": label,
                "type": reg_type,
                "address": address,
                "device_id": device_id
            })
        
        self.config = new_config
        self.accept()
    
    def get_config(self):
        """Return the configuration"""
        return self.config


# ---------------- Electrical Voltage Configuration Dialog ----------------
class ElectricalVoltageConfigDialog(QDialog):
    """Configuration dialog for voltage monitoring with set value feature"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voltage Configuration")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.config = self.load_config()
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("⚡ VOLTAGE ALARM CONFIGURATION")
        title.setStyleSheet("QLabel { color: rgb(0, 200, 255); font-size: 16px; font-weight: bold; padding: 10px; }")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Limits Group
        limits_group = QGroupBox("Voltage Limits (All 3 Phases)")
        limits_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(0, 200, 255); }
        """)
        limits_layout = QFormLayout()
        
        self.low_limit_spin = QDoubleSpinBox()
        self.low_limit_spin.setRange(0, 500)
        self.low_limit_spin.setValue(self.config.get("low_limit", 350))
        self.low_limit_spin.setSuffix(" V")
        self.low_limit_spin.setDecimals(1)
        limits_layout.addRow("Lower Limit:", self.low_limit_spin)
        
        self.high_limit_spin = QDoubleSpinBox()
        self.high_limit_spin.setRange(0, 500)
        self.high_limit_spin.setValue(self.config.get("high_limit", 450))
        self.high_limit_spin.setSuffix(" V")
        self.high_limit_spin.setDecimals(1)
        limits_layout.addRow("Upper Limit:", self.high_limit_spin)
        
        self.limits_coil_spin = QSpinBox()
        self.limits_coil_spin.setRange(0, 255)
        self.limits_coil_spin.setValue(self.config.get("limits_coil_address", 10))
        limits_layout.addRow("Limits Coil Address:", self.limits_coil_spin)
        
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)
        
        # Modbus Data Source Configuration (for all 3 voltage phases)
        modbus_group = QGroupBox("Modbus Data Source (All 3 Phases)")
        modbus_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(255, 200, 100); }
        """)
        modbus_layout = QFormLayout()
        
        # Register Type
        self.register_type_combo = QComboBox()
        self.register_type_combo.addItems(["Holding Register (4x)", "Input Register (3x)"])
        current_reg_type = self.config.get("register_type", "input")
        self.register_type_combo.setCurrentIndex(0 if current_reg_type == "holding" else 1)
        self.register_type_combo.currentIndexChanged.connect(self.update_address_range)
        modbus_layout.addRow("Register Type:", self.register_type_combo)
        
        # Starting Address
        self.start_address_spin = QSpinBox()
        self.start_address_spin.setRange(30001, 39999)
        self.start_address_spin.setValue(self.config.get("start_address", 30001))
        modbus_layout.addRow("Starting Address:", self.start_address_spin)
        
        # Data Source Device ID
        self.data_device_id_spin = QSpinBox()
        self.data_device_id_spin.setRange(1, 255)
        self.data_device_id_spin.setValue(self.config.get("data_device_id", 1))
        modbus_layout.addRow("Data Source Device ID:", self.data_device_id_spin)
        
        modbus_group.setLayout(modbus_layout)
        layout.addWidget(modbus_group)
        
        # Set Value Group (Voltage Only)
        setvalue_group = QGroupBox("Set Value Monitoring (Optional)")
        setvalue_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(100, 255, 100); }
        """)
        setvalue_layout = QFormLayout()
        
        self.enable_setvalue_check = QCheckBox("Enable Set Value Monitoring")
        self.enable_setvalue_check.setChecked(self.config.get("enable_setvalue", False))
        setvalue_layout.addRow("", self.enable_setvalue_check)
        
        self.set_value_spin = QDoubleSpinBox()
        self.set_value_spin.setRange(0, 500)
        self.set_value_spin.setValue(self.config.get("set_value", 400))
        self.set_value_spin.setSuffix(" V")
        self.set_value_spin.setDecimals(1)
        setvalue_layout.addRow("Target Set Value:", self.set_value_spin)
        
        self.above_setvalue_coil_spin = QSpinBox()
        self.above_setvalue_coil_spin.setRange(0, 255)
        self.above_setvalue_coil_spin.setValue(self.config.get("above_setvalue_coil", 11))
        setvalue_layout.addRow("Above Set Value Coil:", self.above_setvalue_coil_spin)
        
        self.below_setvalue_coil_spin = QSpinBox()
        self.below_setvalue_coil_spin.setRange(0, 255)
        self.below_setvalue_coil_spin.setValue(self.config.get("below_setvalue_coil", 12))
        setvalue_layout.addRow("Below Set Value Coil:", self.below_setvalue_coil_spin)
        
        setvalue_group.setLayout(setvalue_layout)
        layout.addWidget(setvalue_group)
        
        # Device Settings
        device_group = QGroupBox("Device Settings")
        device_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(0, 200, 255); }
        """)
        device_layout = QFormLayout()
        
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(self.config.get("device_id", 5))
        device_layout.addRow("Relay Device ID:", self.device_id_spin)
        
        self.alarm_delay_spin = QSpinBox()
        self.alarm_delay_spin.setRange(0, 300)
        self.alarm_delay_spin.setValue(self.config.get("alarm_delay", 5))
        self.alarm_delay_spin.setSuffix(" sec")
        device_layout.addRow("Alarm Delay:", self.alarm_delay_spin)
        
        self.enable_alarm_check = QCheckBox("Enable Alarm Output")
        self.enable_alarm_check.setChecked(self.config.get("enable_alarm", True))
        device_layout.addRow("", self.enable_alarm_check)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_configuration)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("QDialog { background: rgb(20, 30, 45); }")
        
        # Set initial address range
        self.update_address_range()
    
    def update_address_range(self):
        """Update address range based on register type"""
        if self.register_type_combo.currentIndex() == 0:  # Holding Register
            self.start_address_spin.setRange(40001, 49999)
            if self.start_address_spin.value() < 40001:
                self.start_address_spin.setValue(40001)
        else:  # Input Register
            self.start_address_spin.setRange(30001, 39999)
            if self.start_address_spin.value() > 39999:
                self.start_address_spin.setValue(30001)
    
    def load_config(self):
        try:
            data = load_encrypted_config("modbus_config.dat")
            if data:
                return data.get("ElectricalVoltage", {})
        except:
            pass
        return {"low_limit": 350, "high_limit": 450, "limits_coil_address": 10, "enable_setvalue": False, 
                "set_value": 400, "above_setvalue_coil": 11, "below_setvalue_coil": 12, 
                "device_id": 5, "alarm_delay": 5, "enable_alarm": False,
                "register_type": "input", "start_address": 30001, "data_device_id": 1}
    
    def save_configuration(self):
        try:
            config_data = load_encrypted_config("modbus_config.dat") or {}
            reg_type = "holding" if self.register_type_combo.currentIndex() == 0 else "input"
            config_data["ElectricalVoltage"] = {
                "low_limit": self.low_limit_spin.value(),
                "high_limit": self.high_limit_spin.value(),
                "limits_coil_address": self.limits_coil_spin.value(),
                "enable_setvalue": self.enable_setvalue_check.isChecked(),
                "set_value": self.set_value_spin.value(),
                "above_setvalue_coil": self.above_setvalue_coil_spin.value(),
                "below_setvalue_coil": self.below_setvalue_coil_spin.value(),
                "device_id": self.device_id_spin.value(),
                "alarm_delay": self.alarm_delay_spin.value(),
                "enable_alarm": self.enable_alarm_check.isChecked(),
                "register_type": reg_type,
                "start_address": self.start_address_spin.value(),
                "data_device_id": self.data_device_id_spin.value()
            }
            if save_encrypted_config(config_data, "modbus_config.dat"):
                QMessageBox.information(self, "Success", "Voltage configuration saved!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save configuration")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")


# ---------------- Electrical Current Configuration Dialog ----------------
class ElectricalCurrentConfigDialog(QDialog):
    """Configuration dialog for current monitoring"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Current Configuration")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.config = self.load_config()
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("⚡ CURRENT ALARM CONFIGURATION")
        title.setStyleSheet("QLabel { color: rgb(0, 200, 255); font-size: 16px; font-weight: bold; padding: 10px; }")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Limits Group
        limits_group = QGroupBox("Current Limits (All 3 Phases)")
        limits_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(0, 200, 255); }
        """)
        limits_layout = QFormLayout()
        
        self.low_limit_spin = QDoubleSpinBox()
        self.low_limit_spin.setRange(0, 200)
        self.low_limit_spin.setValue(self.config.get("low_limit", 10))
        self.low_limit_spin.setSuffix(" A")
        self.low_limit_spin.setDecimals(1)
        limits_layout.addRow("Lower Limit:", self.low_limit_spin)
        
        self.high_limit_spin = QDoubleSpinBox()
        self.high_limit_spin.setRange(0, 200)
        self.high_limit_spin.setValue(self.config.get("high_limit", 90))
        self.high_limit_spin.setSuffix(" A")
        self.high_limit_spin.setDecimals(1)
        limits_layout.addRow("Upper Limit:", self.high_limit_spin)
        
        self.coil_address_spin = QSpinBox()
        self.coil_address_spin.setRange(0, 255)
        self.coil_address_spin.setValue(self.config.get("coil_address", 13))
        limits_layout.addRow("Coil Address:", self.coil_address_spin)
        
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)
        
        # Modbus Data Source Configuration (for all 3 current phases)
        modbus_group = QGroupBox("Modbus Data Source (All 3 Phases)")
        modbus_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(255, 200, 100); }
        """)
        modbus_layout = QFormLayout()
        
        # Register Type
        self.register_type_combo = QComboBox()
        self.register_type_combo.addItems(["Holding Register (4x)", "Input Register (3x)"])
        current_reg_type = self.config.get("register_type", "input")
        self.register_type_combo.setCurrentIndex(0 if current_reg_type == "holding" else 1)
        self.register_type_combo.currentIndexChanged.connect(self.update_address_range)
        modbus_layout.addRow("Register Type:", self.register_type_combo)
        
        # Starting Address
        self.start_address_spin = QSpinBox()
        self.start_address_spin.setRange(30001, 39999)
        self.start_address_spin.setValue(self.config.get("start_address", 30004))
        modbus_layout.addRow("Starting Address:", self.start_address_spin)
        
        # Data Source Device ID
        self.data_device_id_spin = QSpinBox()
        self.data_device_id_spin.setRange(1, 255)
        self.data_device_id_spin.setValue(self.config.get("data_device_id", 1))
        modbus_layout.addRow("Data Source Device ID:", self.data_device_id_spin)
        
        modbus_group.setLayout(modbus_layout)
        layout.addWidget(modbus_group)
        
        # Device Settings
        device_group = QGroupBox("Device Settings")
        device_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(0, 200, 255); }
        """)
        device_layout = QFormLayout()
        
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(self.config.get("device_id", 5))
        device_layout.addRow("Relay Device ID:", self.device_id_spin)
        
        self.alarm_delay_spin = QSpinBox()
        self.alarm_delay_spin.setRange(0, 300)
        self.alarm_delay_spin.setValue(self.config.get("alarm_delay", 5))
        self.alarm_delay_spin.setSuffix(" sec")
        device_layout.addRow("Alarm Delay:", self.alarm_delay_spin)
        
        self.enable_alarm_check = QCheckBox("Enable Alarm Output")
        self.enable_alarm_check.setChecked(self.config.get("enable_alarm", True))
        device_layout.addRow("", self.enable_alarm_check)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_configuration)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("QDialog { background: rgb(20, 30, 45); }")
        
        # Set initial address range
        self.update_address_range()
    
    def update_address_range(self):
        """Update address range based on register type"""
        if self.register_type_combo.currentIndex() == 0:  # Holding Register
            self.start_address_spin.setRange(40001, 49999)
            if self.start_address_spin.value() < 40001:
                self.start_address_spin.setValue(40001)
        else:  # Input Register
            self.start_address_spin.setRange(30001, 39999)
            if self.start_address_spin.value() > 39999:
                self.start_address_spin.setValue(30001)
    
    def load_config(self):
        try:
            data = load_encrypted_config("modbus_config.dat")
            if data:
                return data.get("ElectricalCurrent", {})
        except:
            pass
        return {"low_limit": 10, "high_limit": 90, "coil_address": 13, "device_id": 5, "alarm_delay": 5, "enable_alarm": False,
                "register_type": "input", "start_address": 30004, "data_device_id": 1}
    
    def save_configuration(self):
        try:
            config_data = load_encrypted_config("modbus_config.dat") or {}
            reg_type = "holding" if self.register_type_combo.currentIndex() == 0 else "input"
            config_data["ElectricalCurrent"] = {
                "low_limit": self.low_limit_spin.value(),
                "high_limit": self.high_limit_spin.value(),
                "coil_address": self.coil_address_spin.value(),
                "device_id": self.device_id_spin.value(),
                "alarm_delay": self.alarm_delay_spin.value(),
                "enable_alarm": self.enable_alarm_check.isChecked(),
                "register_type": reg_type,
                "start_address": self.start_address_spin.value(),
                "data_device_id": self.data_device_id_spin.value()
            }
            if save_encrypted_config(config_data, "modbus_config.dat"):
                QMessageBox.information(self, "Success", "Current configuration saved!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save configuration")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")


# ---------------- Electrical Power Configuration Dialog ----------------
class ElectricalPowerConfigDialog(QDialog):
    """Configuration dialog for power parameters (Active Power and Reactive Power - individual configs)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Power Configuration")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.config = self.load_config()
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("⚡ POWER ALARM CONFIGURATION")
        title.setStyleSheet("QLabel { color: rgb(0, 200, 255); font-size: 16px; font-weight: bold; padding: 10px; }")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Active Power Group
        active_group = QGroupBox("Active Power (kW)")
        active_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(0, 200, 255); }
        """)
        active_layout = QFormLayout()
        
        self.active_low_spin = QDoubleSpinBox()
        self.active_low_spin.setRange(0, 2000)
        self.active_low_spin.setValue(self.config.get("active_low_limit", 100))
        self.active_low_spin.setSuffix(" kW")
        active_layout.addRow("Lower Limit:", self.active_low_spin)
        
        self.active_high_spin = QDoubleSpinBox()
        self.active_high_spin.setRange(0, 2000)
        self.active_high_spin.setValue(self.config.get("active_high_limit", 900))
        self.active_high_spin.setSuffix(" kW")
        active_layout.addRow("Upper Limit:", self.active_high_spin)
        
        self.active_coil_spin = QSpinBox()
        self.active_coil_spin.setRange(0, 255)
        self.active_coil_spin.setValue(self.config.get("active_coil_address", 14))
        active_layout.addRow("Coil Address:", self.active_coil_spin)
        
        self.active_enable_check = QCheckBox("Enable Active Power Alarm")
        self.active_enable_check.setChecked(self.config.get("active_enable_alarm", True))
        active_layout.addRow("", self.active_enable_check)
        
        active_group.setLayout(active_layout)
        layout.addWidget(active_group)
        
        # Active Power Modbus Source
        active_modbus_group = QGroupBox("Active Power Data Source")
        active_modbus_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(255, 200, 100); }
        """)
        active_modbus_layout = QFormLayout()
        
        self.active_register_type_combo = QComboBox()
        self.active_register_type_combo.addItems(["Holding Register (4x)", "Input Register (3x)"])
        active_reg_type = self.config.get("active_register_type", "input")
        self.active_register_type_combo.setCurrentIndex(0 if active_reg_type == "holding" else 1)
        self.active_register_type_combo.currentIndexChanged.connect(lambda: self.update_power_address_range("active"))
        active_modbus_layout.addRow("Register Type:", self.active_register_type_combo)
        
        self.active_address_spin = QSpinBox()
        self.active_address_spin.setRange(30001, 39999)
        self.active_address_spin.setValue(self.config.get("active_address", 30007))
        active_modbus_layout.addRow("Address:", self.active_address_spin)
        
        self.active_data_device_id_spin = QSpinBox()
        self.active_data_device_id_spin.setRange(1, 255)
        self.active_data_device_id_spin.setValue(self.config.get("active_data_device_id", 1))
        active_modbus_layout.addRow("Data Source Device ID:", self.active_data_device_id_spin)
        
        active_modbus_group.setLayout(active_modbus_layout)
        layout.addWidget(active_modbus_group)
        
        # Power Factor Group
        pf_group = QGroupBox("Power Factor (Read Only)")
        pf_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(150, 150, 255); }
        """)
        pf_layout = QFormLayout()
        
        self.pf_register_type_combo = QComboBox()
        self.pf_register_type_combo.addItems(["Holding Register (4x)", "Input Register (3x)"])
        pf_reg_type = self.config.get("pf_register_type", "input")
        self.pf_register_type_combo.setCurrentIndex(0 if pf_reg_type == "holding" else 1)
        self.pf_register_type_combo.currentIndexChanged.connect(lambda: self.update_power_address_range("pf"))
        pf_layout.addRow("Register Type:", self.pf_register_type_combo)
        
        self.pf_address_spin = QSpinBox()
        self.pf_address_spin.setRange(30001, 39999)
        self.pf_address_spin.setValue(self.config.get("pf_address", 30008))
        pf_layout.addRow("Address:", self.pf_address_spin)
        
        self.pf_data_device_id_spin = QSpinBox()
        self.pf_data_device_id_spin.setRange(1, 255)
        self.pf_data_device_id_spin.setValue(self.config.get("pf_data_device_id", 1))
        pf_layout.addRow("Data Source Device ID:", self.pf_data_device_id_spin)
        
        pf_group.setLayout(pf_layout)
        layout.addWidget(pf_group)
        
        # Reactive Power Group
        reactive_group = QGroupBox("Reactive Power (kVAR)")
        reactive_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(255, 150, 100); }
        """)
        reactive_layout = QFormLayout()
        
        self.reactive_low_spin = QDoubleSpinBox()
        self.reactive_low_spin.setRange(0, 1000)
        self.reactive_low_spin.setValue(self.config.get("reactive_low_limit", 50))
        self.reactive_low_spin.setSuffix(" kVAR")
        reactive_layout.addRow("Lower Limit:", self.reactive_low_spin)
        
        self.reactive_high_spin = QDoubleSpinBox()
        self.reactive_high_spin.setRange(0, 1000)
        self.reactive_high_spin.setValue(self.config.get("reactive_high_limit", 500))
        self.reactive_high_spin.setSuffix(" kVAR")
        reactive_layout.addRow("Upper Limit:", self.reactive_high_spin)
        
        self.reactive_coil_spin = QSpinBox()
        self.reactive_coil_spin.setRange(0, 255)
        self.reactive_coil_spin.setValue(self.config.get("reactive_coil_address", 15))
        reactive_layout.addRow("Coil Address:", self.reactive_coil_spin)
        
        self.reactive_enable_check = QCheckBox("Enable Reactive Power Alarm")
        self.reactive_enable_check.setChecked(self.config.get("reactive_enable_alarm", True))
        reactive_layout.addRow("", self.reactive_enable_check)
        
        reactive_group.setLayout(reactive_layout)
        layout.addWidget(reactive_group)
        
        # Reactive Power Modbus Source
        reactive_modbus_group = QGroupBox("Reactive Power Data Source")
        reactive_modbus_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(255, 200, 100); }
        """)
        reactive_modbus_layout = QFormLayout()
        
        self.reactive_register_type_combo = QComboBox()
        self.reactive_register_type_combo.addItems(["Holding Register (4x)", "Input Register (3x)"])
        reactive_reg_type = self.config.get("reactive_register_type", "input")
        self.reactive_register_type_combo.setCurrentIndex(0 if reactive_reg_type == "holding" else 1)
        self.reactive_register_type_combo.currentIndexChanged.connect(lambda: self.update_power_address_range("reactive"))
        reactive_modbus_layout.addRow("Register Type:", self.reactive_register_type_combo)
        
        self.reactive_address_spin = QSpinBox()
        self.reactive_address_spin.setRange(30001, 39999)
        self.reactive_address_spin.setValue(self.config.get("reactive_address", 30009))
        reactive_modbus_layout.addRow("Address:", self.reactive_address_spin)
        
        self.reactive_data_device_id_spin = QSpinBox()
        self.reactive_data_device_id_spin.setRange(1, 255)
        self.reactive_data_device_id_spin.setValue(self.config.get("reactive_data_device_id", 1))
        reactive_modbus_layout.addRow("Data Source Device ID:", self.reactive_data_device_id_spin)
        
        reactive_modbus_group.setLayout(reactive_modbus_layout)
        layout.addWidget(reactive_modbus_group)
        
        # Device Settings
        device_group = QGroupBox("Device Settings")
        device_group.setStyleSheet("""
            QGroupBox { color: rgb(200, 220, 240); border: 2px solid rgb(60, 80, 100); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; color: rgb(0, 200, 255); }
        """)
        device_layout = QFormLayout()
        
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(self.config.get("device_id", 5))
        device_layout.addRow("Relay Device ID:", self.device_id_spin)
        
        self.alarm_delay_spin = QSpinBox()
        self.alarm_delay_spin.setRange(0, 300)
        self.alarm_delay_spin.setValue(self.config.get("alarm_delay", 5))
        self.alarm_delay_spin.setSuffix(" sec")
        device_layout.addRow("Alarm Delay:", self.alarm_delay_spin)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # Info
        info_label = QLabel("ℹ️ Note: Power Factor has no alarm configuration")
        info_label.setStyleSheet("QLabel { color: rgb(150, 170, 190); font-size: 11px; font-style: italic; padding: 10px; background: rgb(25, 35, 50); border-radius: 5px; }")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_configuration)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("QDialog { background: rgb(20, 30, 45); }")
        
        # Set initial address ranges
        self.update_power_address_range("active")
        self.update_power_address_range("pf")
        self.update_power_address_range("reactive")
    
    def update_power_address_range(self, power_type):
        """Update address range based on register type for specific power parameter"""
        if power_type == "active":
            combo = self.active_register_type_combo
            spin = self.active_address_spin
        elif power_type == "pf":
            combo = self.pf_register_type_combo
            spin = self.pf_address_spin
        else:  # reactive
            combo = self.reactive_register_type_combo
            spin = self.reactive_address_spin
        
        if combo.currentIndex() == 0:  # Holding Register
            spin.setRange(40001, 49999)
            if spin.value() < 40001:
                spin.setValue(40001)
        else:  # Input Register
            spin.setRange(30001, 39999)
            if spin.value() > 39999:
                spin.setValue(30001)
    
    def load_config(self):
        try:
            data = load_encrypted_config("modbus_config.dat")
            if data:
                return data.get("ElectricalPower", {})
        except:
            pass
        return {
            "active_low_limit": 100, "active_high_limit": 900, "active_coil_address": 14, "active_enable_alarm": False,
            "active_register_type": "input", "active_address": 30007, "active_data_device_id": 1,
            "pf_register_type": "input", "pf_address": 30008, "pf_data_device_id": 1,
            "reactive_low_limit": 50, "reactive_high_limit": 500, "reactive_coil_address": 15, "reactive_enable_alarm": False,
            "reactive_register_type": "input", "reactive_address": 30009, "reactive_data_device_id": 1,
            "device_id": 5, "alarm_delay": 5
        }
    
    def save_configuration(self):
        try:
            config_data = load_encrypted_config("modbus_config.dat") or {}
            active_reg_type = "holding" if self.active_register_type_combo.currentIndex() == 0 else "input"
            pf_reg_type = "holding" if self.pf_register_type_combo.currentIndex() == 0 else "input"
            reactive_reg_type = "holding" if self.reactive_register_type_combo.currentIndex() == 0 else "input"
            
            config_data["ElectricalPower"] = {
                "active_low_limit": self.active_low_spin.value(),
                "active_high_limit": self.active_high_spin.value(),
                "active_coil_address": self.active_coil_spin.value(),
                "active_enable_alarm": self.active_enable_check.isChecked(),
                "active_register_type": active_reg_type,
                "active_address": self.active_address_spin.value(),
                "active_data_device_id": self.active_data_device_id_spin.value(),
                "pf_register_type": pf_reg_type,
                "pf_address": self.pf_address_spin.value(),
                "pf_data_device_id": self.pf_data_device_id_spin.value(),
                "reactive_low_limit": self.reactive_low_spin.value(),
                "reactive_high_limit": self.reactive_high_spin.value(),
                "reactive_coil_address": self.reactive_coil_spin.value(),
                "reactive_enable_alarm": self.reactive_enable_check.isChecked(),
                "reactive_register_type": reactive_reg_type,
                "reactive_address": self.reactive_address_spin.value(),
                "reactive_data_device_id": self.reactive_data_device_id_spin.value(),
                "device_id": self.device_id_spin.value(),
                "alarm_delay": self.alarm_delay_spin.value()
            }
            if save_encrypted_config(config_data, "modbus_config.dat"):
                QMessageBox.information(self, "Success", "Power configuration saved!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save configuration")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")


# ---------------- Electrical Parameter Tab ----------------
class ElectricalParameterTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.setMinimumSize(800, 600)
        self.setStyleSheet(CYLINDER_HEAD_BG_STYLE)
        
        # Load configuration
        self.load_config()
        
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 20, 15, 15)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("ELECTRICAL PARAMETERS")
        title.setFont(QFont("Inter", 18, QFont.Bold))
        title.setStyleSheet("color: rgb(255, 255, 255);")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 12px;
                border: 1px solid #30363d;
            }
            QScrollBar::handle:vertical {
                background: #58a6ff;
                border: 1px solid #1f6feb;
                min-height: 30px;
            }
        """)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # === 3-PHASE VOLTAGE SECTION ===
        voltage_section_layout = QVBoxLayout()
        
        # Voltage header with gear button
        voltage_header = QHBoxLayout()
        voltage_title = QLabel("3-PHASE VOLTAGE")
        voltage_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        voltage_title.setStyleSheet("color: rgb(100, 150, 200);")
        voltage_header.addWidget(voltage_title)
        voltage_header.addStretch()
        
        voltage_gear_btn = QPushButton("⚙️")
        voltage_gear_btn.setFixedSize(32, 32)
        voltage_gear_btn.setCursor(Qt.PointingHandCursor)
        voltage_gear_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(58, 106, 255), stop:1 rgb(38, 76, 200));
                color: white;
                border: 1px solid rgb(100, 150, 255);
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(78, 126, 255), stop:1 rgb(58, 96, 220));
            }
        """)
        voltage_gear_btn.clicked.connect(lambda: self.open_settings('Voltage'))
        voltage_header.addWidget(voltage_gear_btn)
        voltage_section_layout.addLayout(voltage_header)
        
        voltage_section = QGroupBox()
        voltage_section.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgb(70, 90, 120);
                border-radius: 0px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
        
        voltage_layout = QHBoxLayout(voltage_section)
        voltage_layout.setSpacing(15)
        voltage_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create voltage displays
        self.voltage_displays = []
        voltage_configs = [
            ("L1-L2 Voltage", "L1", "L2"),
            ("L2-L3 Voltage", "L2", "L3"),
            ("L3-L1 Voltage", "L3", "L1")
        ]
        
        for label, phase_from, phase_to in voltage_configs:
            display = ModernVoltageDisplay(label, phase_from, phase_to, max_value=500)
            self.voltage_displays.append(display)
            voltage_layout.addWidget(display)
        
        # Configuration warning label for voltage
        self.voltage_warning = QLabel("⚠️ No Configuration Set - Click the gear icon to configure Modbus addresses")
        self.voltage_warning.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 180, 0, 0.2);
                color: rgb(255, 200, 100);
                border: 2px dashed rgb(255, 180, 0);
                border-radius: 5px;
                padding: 15px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        self.voltage_warning.setAlignment(Qt.AlignCenter)
        voltage_section_layout.addWidget(voltage_section)
        voltage_section_layout.addWidget(self.voltage_warning)
        content_layout.addLayout(voltage_section_layout)
        
        # === AMPERAGE SECTION ===
        amperage_section_layout = QVBoxLayout()
        
        # Amperage header with gear button
        amperage_header = QHBoxLayout()
        amperage_title = QLabel("AMPERAGE PER PHASE")
        amperage_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        amperage_title.setStyleSheet("color: rgb(100, 150, 200);")
        amperage_header.addWidget(amperage_title)
        amperage_header.addStretch()
        
        amperage_gear_btn = QPushButton("⚙️")
        amperage_gear_btn.setFixedSize(32, 32)
        amperage_gear_btn.setCursor(Qt.PointingHandCursor)
        amperage_gear_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(58, 106, 255), stop:1 rgb(38, 76, 200));
                color: white;
                border: 1px solid rgb(100, 150, 255);
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(78, 126, 255), stop:1 rgb(58, 96, 220));
            }
        """)
        amperage_gear_btn.clicked.connect(lambda: self.open_settings('Current'))
        amperage_header.addWidget(amperage_gear_btn)
        amperage_section_layout.addLayout(amperage_header)
        
        amperage_section = QGroupBox()
        amperage_section.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgb(70, 90, 120);
                border-radius: 0px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
        
        amperage_layout = QHBoxLayout(amperage_section)
        amperage_layout.setSpacing(15)
        amperage_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create amperage displays
        self.amperage_displays = []
        amperage_configs = [
            ("L1", "L1", "L2"),
            ("L2", "L2", "L3"),
            ("L3", "L3", "L1")
        ]
        
        for label, phase_from, phase_to in amperage_configs:
            display = ModernCurrentDisplay(label, phase_from, phase_to, max_value=100)
            self.amperage_displays.append(display)
            amperage_layout.addWidget(display)
        
        # Configuration warning label for current
        self.current_warning = QLabel("⚠️ No Configuration Set - Click the gear icon to configure Modbus addresses")
        self.current_warning.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 180, 0, 0.2);
                color: rgb(255, 200, 100);
                border: 2px dashed rgb(255, 180, 0);
                border-radius: 5px;
                padding: 15px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        self.current_warning.setAlignment(Qt.AlignCenter)
        amperage_section_layout.addWidget(amperage_section)
        amperage_section_layout.addWidget(self.current_warning)
        content_layout.addLayout(amperage_section_layout)
        
        # === POWER PARAMETERS SECTION ===
        power_section_layout = QVBoxLayout()
        
        # Power header with gear button
        power_header = QHBoxLayout()
        power_title = QLabel("POWER PARAMETERS")
        power_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        power_title.setStyleSheet("color: rgb(100, 150, 200);")
        power_header.addWidget(power_title)
        power_header.addStretch()
        
        power_gear_btn = QPushButton("⚙️")
        power_gear_btn.setFixedSize(32, 32)
        power_gear_btn.setCursor(Qt.PointingHandCursor)
        power_gear_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(58, 106, 255), stop:1 rgb(38, 76, 200));
                color: white;
                border: 1px solid rgb(100, 150, 255);
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(78, 126, 255), stop:1 rgb(58, 96, 220));
            }
        """)
        power_gear_btn.clicked.connect(lambda: self.open_settings('Power'))
        power_header.addWidget(power_gear_btn)
        power_section_layout.addLayout(power_header)
        
        power_section = QGroupBox()
        power_section.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgb(70, 90, 120);
                border-radius: 0px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
        
        power_layout = QHBoxLayout(power_section)
        power_layout.setSpacing(20)
        power_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create power displays
        self.power_displays = []
        power_configs = [
            ("Active Power", "kW", 1000, 1),
            ("Power Factor", "", 1.0, 3),
            ("Reactive Power", "kVAR", 1000, 1)
        ]
        
        for label, unit, max_val, decimals in power_configs:
            display = ModernPowerDisplay(label, unit, max_val, decimals)
            self.power_displays.append(display)
            power_layout.addWidget(display)
        
        # Configuration warning label for power
        self.power_warning = QLabel("⚠️ No Configuration Set - Click the gear icon to configure Modbus addresses")
        self.power_warning.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 180, 0, 0.2);
                color: rgb(255, 200, 100);
                border: 2px dashed rgb(255, 180, 0);
                border-radius: 5px;
                padding: 15px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        self.power_warning.setAlignment(Qt.AlignCenter)
        power_section_layout.addWidget(power_section)
        power_section_layout.addWidget(self.power_warning)
        content_layout.addLayout(power_section_layout)
        
        # Add stretch to push content to top
        content_layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, 1)
        
        self.setLayout(main_layout)
        
        # Store modbus client reference
        self.modbus_client = None
        
        # Update warning visibility based on configuration
        self.update_warning_visibility()
    
    def load_config(self):
        """Load Modbus configuration from encrypted file"""
        # Default ElectricalParameters structure
        default_electrical_params = {
            "Voltage": [],
            "Current": [],
            "Power": []
        }
        
        try:
            # Try to load from encrypted file
            self.config = load_encrypted_config("modbus_config.dat")
            if self.config is not None:
                # Ensure ElectricalParameters section exists, but don't overwrite other sections
                if "ElectricalParameters" not in self.config:
                    self.config["ElectricalParameters"] = default_electrical_params
                    # Only save if we added the missing section
                    self.save_config()
            else:
                # File doesn't exist - this should be handled by HMIWindow.load_initial_configuration()
                # Just set a minimal config for this tab
                self.config = {"ElectricalParameters": default_electrical_params}
        except Exception as e:
            print(f"Error loading Modbus configuration: {e}")
            self.config = {"ElectricalParameters": default_electrical_params}
    
    def save_config(self):
        """Save Modbus configuration to encrypted file"""
        try:
            if save_encrypted_config(self.config, "modbus_config.dat"):
                print("Modbus configuration saved successfully")
                # Update warning visibility after saving
                self.update_warning_visibility()
            else:
                print("Error saving Modbus configuration to encrypted file")
        except Exception as e:
            print(f"Error saving Modbus configuration: {e}")
    
    def update_warning_visibility(self):
        """Show or hide warning labels based on configuration status"""
        electrical_config = self.config.get("ElectricalParameters", {})
        
        # Check each section
        voltage_config = electrical_config.get("Voltage", [])
        current_config = electrical_config.get("Current", [])
        power_config = electrical_config.get("Power", [])
        
        # Show/hide warnings
        self.voltage_warning.setVisible(len(voltage_config) == 0)
        self.current_warning.setVisible(len(current_config) == 0)
        self.power_warning.setVisible(len(power_config) == 0)
    
    def open_settings(self, group_name):
        """Open settings dialog for a specific group with password protection"""
        # Password prompt
        password, ok = QInputDialog.getText(
            self, "Admin Access", 
            "Enter Administrator Password:", 
            QLineEdit.Password
        )
        
        if not ok:
            return
        
        # Get admin password from parent window
        admin_password = getattr(self.parent_window, 'admin_password', 'admin123')
        if password != admin_password:
            QMessageBox.warning(self, "Access Denied", "Incorrect password.")
            return
        
        # Get current configuration for this group
        current_config = self.config.get("ElectricalParameters", {}).get(group_name, [])
        
        # If empty, provide template with 3 empty rows
        if not current_config:
            labels_map = {
                "Voltage": ["L1-L2 Voltage", "L2-L3 Voltage", "L3-L1 Voltage"],
                "Current": ["L1", "L2", "L3"],
                "Power": ["Active Power", "Power Factor", "Reactive Power"]
            }
            labels = labels_map.get(group_name, ["Parameter 1", "Parameter 2", "Parameter 3"])
            current_config = [
                {"label": labels[0], "type": "input", "address": 30001, "device_id": 5},
                {"label": labels[1], "type": "input", "address": 30002, "device_id": 5},
                {"label": labels[2], "type": "input", "address": 30003, "device_id": 5}
            ]
        
        # Open configuration dialog
        dialog = ModbusConfigDialog(self, group_name, current_config)
        
        if dialog.exec_() == QDialog.Accepted:
            # Save the new configuration
            new_config = dialog.get_config()
            
            if "ElectricalParameters" not in self.config:
                self.config["ElectricalParameters"] = {}
            
            self.config["ElectricalParameters"][group_name] = new_config
            self.save_config()
            
            QMessageBox.information(
                self, "Configuration Saved",
                f"{group_name} configuration saved successfully.\n\n"
                "The new settings will be used on the next data read."
            )
    
    def set_modbus_client(self, client):
        """Set the Modbus client for this tab"""
        self.modbus_client = client
    
    def clear_displays(self):
        """Clear all electrical parameter displays to zero"""
        # Clear all voltage displays
        for display in self.voltage_displays:
            display.set_value(0)
        
        # Clear all amperage displays
        for display in self.amperage_displays:
            display.set_value(0)
        
        # Clear all power displays
        for display in self.power_displays:
            display.set_value(0)
    
    def read_modbus_value(self, param):
        """Read a single Modbus value based on configuration"""
        if not self.modbus_client:
            return None
        
        try:
            addr = param["address"]
            reg_type = param["type"]
            dev_id = param["device_id"]
            
            if reg_type == "input":
                # Input registers: addresses 30001-39999 → offset = address - 30001
                result = self.modbus_client.read_input_registers(
                    address=addr - 30001, 
                    count=1, 
                    device_id=dev_id
                )
            elif reg_type == "holding":
                # Holding registers: addresses 40001-49999 → offset = address - 40001
                result = self.modbus_client.read_holding_registers(
                    address=addr - 40001, 
                    count=1, 
                    device_id=dev_id
                )
            elif reg_type == "coil":
                # Coils: addresses 1-9999 → offset = address - 1
                result = self.modbus_client.read_coils(
                    address=addr - 1, 
                    count=1, 
                    device_id=dev_id
                )
            elif reg_type == "discrete":
                # Discrete inputs: addresses 10001-19999 → offset = address - 10001
                result = self.modbus_client.read_discrete_inputs(
                    address=addr - 10001, 
                    count=1, 
                    device_id=dev_id
                )
            else:
                return None
            
            if result and not result.isError():
                if hasattr(result, "registers"):
                    return result.registers[0]
                elif hasattr(result, "bits"):
                    return result.bits[0]
            
            return None
            
        except Exception as e:
            print(f"Error reading Modbus address {param['address']}: {e}")
            return None
    
    def update_electrical_data(self, values=None):
        """Update electrical parameter values - now uses configuration-based reading"""
        # If values are provided (legacy/test mode), use them
        if values is not None:
            # Legacy update for test mode
            if len(values) < 9:
                return
            
            for i, display in enumerate(self.voltage_displays):
                if i < len(values):
                    voltage = (values[i] / 1000.0) * 500
                    display.set_value(voltage)
            
            for i, display in enumerate(self.amperage_displays):
                value_index = i + 3
                if value_index < len(values):
                    current = (values[value_index] / 1000.0) * 100
                    display.set_value(current)
            
            power_indices = [6, 7, 8]
            for i, display in enumerate(self.power_displays):
                value_index = power_indices[i]
                if value_index < len(values):
                    if i == 0:
                        power = (values[value_index] / 1000.0) * 1000
                        display.set_value(power)
                    elif i == 1:
                        pf = values[value_index] / 1000.0
                        display.set_value(pf)
                    elif i == 2:
                        reactive = (values[value_index] / 1000.0) * 1000
                        display.set_value(reactive)
            return
        
        # Configuration-based reading using new dialog format
        if not self.modbus_client:
            return
        
        # Load voltage configuration
        voltage_config = load_encrypted_config("modbus_config.dat")
        if voltage_config and "ElectricalVoltage" in voltage_config:
            v_cfg = voltage_config["ElectricalVoltage"]
            reg_type = v_cfg.get("register_type", "input")
            start_addr = v_cfg.get("start_address", 30001)
            device_id = v_cfg.get("data_device_id", 1)
            
            # Read 3 consecutive registers for 3 voltage phases
            for i in range(3):
                addr = start_addr + i
                value = self.read_modbus_register(device_id, reg_type, addr)
                if value is not None and i < len(self.voltage_displays):
                    # Scale value to voltage (0-500V range)
                    voltage = (value / 1000.0) * 500
                    self.voltage_displays[i].set_value(voltage)
        
        # Load current configuration
        current_config = load_encrypted_config("modbus_config.dat")
        if current_config and "ElectricalCurrent" in current_config:
            c_cfg = current_config["ElectricalCurrent"]
            reg_type = c_cfg.get("register_type", "input")
            start_addr = c_cfg.get("start_address", 30004)
            device_id = c_cfg.get("data_device_id", 1)
            
            # Read 3 consecutive registers for 3 current phases
            for i in range(3):
                addr = start_addr + i
                value = self.read_modbus_register(device_id, reg_type, addr)
                if value is not None and i < len(self.amperage_displays):
                    # Scale value to current (0-100A range)
                    current = (value / 1000.0) * 100
                    self.amperage_displays[i].set_value(current)
        
        # Load power configuration
        power_config = load_encrypted_config("modbus_config.dat")
        if power_config and "ElectricalPower" in power_config:
            p_cfg = power_config["ElectricalPower"]
            
            # Active Power
            active_reg_type = p_cfg.get("active_register_type", "input")
            active_addr = p_cfg.get("active_address", 30007)
            active_device_id = p_cfg.get("active_data_device_id", 1)
            value = self.read_modbus_register(active_device_id, active_reg_type, active_addr)
            if value is not None:
                power = (value / 1000.0) * 1000  # Scale to 0-1000kW
                self.power_displays[0].set_value(power)
            
            # Power Factor
            pf_reg_type = p_cfg.get("pf_register_type", "input")
            pf_addr = p_cfg.get("pf_address", 30008)
            pf_device_id = p_cfg.get("pf_data_device_id", 1)
            value = self.read_modbus_register(pf_device_id, pf_reg_type, pf_addr)
            if value is not None:
                pf = value / 1000.0  # Scale to 0-1.0
                self.power_displays[1].set_value(pf)
            
            # Reactive Power
            reactive_reg_type = p_cfg.get("reactive_register_type", "input")
            reactive_addr = p_cfg.get("reactive_address", 30009)
            reactive_device_id = p_cfg.get("reactive_data_device_id", 1)
            value = self.read_modbus_register(reactive_device_id, reactive_reg_type, reactive_addr)
            if value is not None:
                reactive = (value / 1000.0) * 1000  # Scale to 0-1000kVAR
                self.power_displays[2].set_value(reactive)
    
    def read_modbus_register(self, device_id, register_type, address):
        """Read a single Modbus register"""
        if not self.modbus_client:
            return None
        
        try:
            # Convert address to 0-based (Modbus addresses are 1-based in user interface)
            modbus_address = address - 1 if address >= 30001 else address
            if address >= 40001:
                modbus_address = address - 40001
            elif address >= 30001:
                modbus_address = address - 30001
            
            # Read based on register type
            if register_type == "holding":
                result = self.modbus_client.read_holding_registers(modbus_address, 1, slave=device_id)
            else:  # input
                result = self.modbus_client.read_input_registers(modbus_address, 1, slave=device_id)
            
            if not result.isError():
                return result.registers[0]
            else:
                print(f"Error reading {register_type} register {address} from device {device_id}")
                return None
        except Exception as e:
            print(f"Exception reading Modbus register {address}: {e}")
            return None
    
    def open_settings(self, section_type):
        """Open configuration dialog for electrical parameters"""
        # Check if admin is logged in
        admin_logged_in = getattr(self.parent_window, 'admin_logged_in', False)
        
        if not admin_logged_in:
            password, ok = QInputDialog.getText(self, "Administrator Access",
                                               "Enter admin password:",
                                               QLineEdit.Password)
            # Get admin password from parent window
            admin_password = getattr(self.parent_window, 'admin_password', 'admin123')
            if not (ok and password == admin_password):
                if ok:
                    QMessageBox.warning(self, "Access Denied", "Incorrect password!")
                return
        
        # Open appropriate configuration dialog based on section type
        if section_type == 'Voltage':
            dialog = ElectricalVoltageConfigDialog(self)
        elif section_type == 'Current':
            dialog = ElectricalCurrentConfigDialog(self)
        elif section_type == 'Power':
            dialog = ElectricalPowerConfigDialog(self)
        else:
            return
        
        if dialog.exec_() == QDialog.Accepted:
            # Reload configuration
            self.load_config()
            print(f"{section_type} configuration updated successfully")


# ---------------- History Tab ----------------
class HistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.setMinimumSize(800, 600)
        self.setStyleSheet(CYLINDER_HEAD_BG_STYLE)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 20, 15, 15)
        main_layout.setSpacing(10)
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("ALARM HISTORY")
        title.setFont(QFont("Inter", 18, QFont.Bold))
        title.setStyleSheet("color: rgb(0, 200, 255); padding: 5px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filter controls
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("color: rgb(180, 200, 220); font-size: 12px; font-weight: bold;")
        header_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Pressure", "Temperature", "Cylinder Head", "Main Bearing", "Triggered Only", "Cleared Only"])
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background: rgba(30, 40, 55, 0.9);
                color: rgb(200, 220, 240);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 120px;
                font-size: 11px;
            }
            QComboBox:hover {
                border: 2px solid rgb(0, 150, 255);
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: rgb(30, 40, 55);
                color: rgb(200, 220, 240);
                selection-background-color: rgb(0, 120, 200);
            }
        """)
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        header_layout.addWidget(self.filter_combo)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 120, 200), stop:1 rgb(0, 90, 160));
                color: white;
                border: 1px solid rgb(0, 150, 255);
                border-radius: 4px;
                padding: 6px 15px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 150, 255), stop:1 rgb(0, 120, 200));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(0, 90, 160), stop:1 rgb(0, 70, 130));
            }
        """)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.load_history)
        header_layout.addWidget(refresh_btn)
        
        # Clear history button
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(180, 60, 60), stop:1 rgb(140, 40, 40));
                color: white;
                border: 1px solid rgb(200, 80, 80);
                border-radius: 4px;
                padding: 6px 15px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(200, 80, 80), stop:1 rgb(160, 60, 60));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(140, 40, 40), stop:1 rgb(100, 20, 20));
            }
        """)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_history)
        header_layout.addWidget(clear_btn)
        
        main_layout.addLayout(header_layout)
        
        # Statistics panel
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        
        self.total_label = QLabel("Total: 0")
        self.total_label.setStyleSheet("color: rgb(180, 200, 220); font-size: 11px; font-weight: bold; padding: 5px;")
        stats_layout.addWidget(self.total_label)
        
        self.triggered_label = QLabel("Triggered: 0")
        self.triggered_label.setStyleSheet("color: rgb(255, 100, 100); font-size: 11px; font-weight: bold; padding: 5px;")
        stats_layout.addWidget(self.triggered_label)
        
        self.cleared_label = QLabel("Cleared: 0")
        self.cleared_label.setStyleSheet("color: rgb(100, 255, 100); font-size: 11px; font-weight: bold; padding: 5px;")
        stats_layout.addWidget(self.cleared_label)
        
        stats_layout.addStretch()
        main_layout.addLayout(stats_layout)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(["Date/Time", "Gauge Name", "Type", "Alarm", "Value", "Limit", "Status"])
        
        # Set column widths
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Date/Time
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Gauge Name
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Alarm
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Value
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Limit
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Status
        
        self.history_table.setStyleSheet("""
            QTableWidget {
                background: rgb(15, 22, 35);
                color: rgb(160, 180, 200);
                border: 2px solid rgb(50, 70, 90);
                border-radius: 6px;
                gridline-color: rgb(35, 50, 65);
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgb(30, 42, 55);
                background: rgb(20, 30, 45);
            }
            QTableWidget::item:alternate {
                background: rgb(25, 35, 50);
            }
            QTableWidget::item:selected {
                background: rgba(0, 100, 180, 0.5);
                color: rgb(220, 235, 250);
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(40, 55, 75), stop:1 rgb(30, 45, 65));
                color: rgb(0, 180, 240);
                padding: 8px;
                border: 1px solid rgb(50, 70, 90);
                font-weight: bold;
                font-size: 11px;
            }
            QScrollBar:vertical {
                background: rgb(25, 35, 50);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgb(0, 100, 180);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgb(0, 130, 220);
            }
        """)
        
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        
        main_layout.addWidget(self.history_table, 1)
        
        self.setLayout(main_layout)
        
        # Store all history for filtering
        self.all_history = []
        
        # Load initial history
        self.load_history()
    
    def generate_test_alarm(self):
        """Generate a random test alarm for demonstration"""
        gauge_types = ["Pressure", "Temperature"]
        gauge_names = [
            "Fuel Oil Pressure Inlet", "Lube Oil Pressure Inlet", "LT Water Pressure",
            "Charge Air Temp", "Lube Oil Inlet Temp", "HT Water Temp Inlet"
        ]
        alarm_types = ["HIGH", "LOW"]
        
        gauge_type = random.choice(gauge_types)
        gauge_name = random.choice(gauge_names)
        alarm_type = random.choice(alarm_types)
        
        if gauge_type == "Pressure":
            value = random.uniform(0.5, 12.0)
            limit = random.uniform(2.0, 10.0)
            unit = "bar"
        else:
            value = random.uniform(30, 250)
            limit = random.uniform(50, 220)
            unit = "°C"
        
        add_alarm_to_history(gauge_name, gauge_type, alarm_type, 
                           round(value, 1), round(limit, 1), unit)
        self.load_history()
    
    def load_history(self):
        """Load alarm history from config file"""
        try:
            config = load_encrypted_config()
            if config and "AlarmHistory" in config:
                self.all_history = config["AlarmHistory"]
            else:
                self.all_history = []
            
            self.apply_filter()
            
        except Exception as e:
            print(f"Error loading alarm history: {e}")
            self.all_history = []
            self.history_table.setRowCount(0)
    
    def apply_filter(self):
        """Apply selected filter to history"""
        filter_text = self.filter_combo.currentText()
        
        # Filter history based on selection
        if filter_text == "All":
            filtered_history = self.all_history
        elif filter_text == "Triggered Only":
            filtered_history = [h for h in self.all_history if h.get("status") == "TRIGGERED"]
        elif filter_text == "Cleared Only":
            filtered_history = [h for h in self.all_history if h.get("status") == "CLEARED"]
        else:
            # Filter by gauge type
            filtered_history = [h for h in self.all_history if h.get("gauge_type") == filter_text]
        
        # Update statistics
        total = len(self.all_history)
        triggered = len([h for h in self.all_history if h.get("status") == "TRIGGERED"])
        cleared = len([h for h in self.all_history if h.get("status") == "CLEARED"])
        
        self.total_label.setText(f"Total: {total}")
        self.triggered_label.setText(f"Triggered: {triggered}")
        self.cleared_label.setText(f"Cleared: {cleared}")
        
        # Populate table
        self.populate_table(filtered_history)
    
    def populate_table(self, history):
        """Populate table with history records"""
        self.history_table.setRowCount(len(history))
        
        for row, record in enumerate(history):
            # Date/Time
            timestamp_item = QTableWidgetItem(record.get("timestamp", ""))
            timestamp_item.setFont(QFont("Courier New", 10))
            timestamp_item.setForeground(QColor(140, 160, 180))  # Darker gray-blue
            self.history_table.setItem(row, 0, timestamp_item)
            
            # Gauge Name
            gauge_name_item = QTableWidgetItem(record.get("gauge_name", ""))
            gauge_name_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            gauge_name_item.setForeground(QColor(170, 190, 210))  # Medium gray-blue
            self.history_table.setItem(row, 1, gauge_name_item)
            
            # Type
            gauge_type_item = QTableWidgetItem(record.get("gauge_type", ""))
            gauge_type_item.setForeground(QColor(130, 150, 170))  # Darker gray-blue
            self.history_table.setItem(row, 2, gauge_type_item)
            
            # Alarm Type
            alarm_type_item = QTableWidgetItem(record.get("alarm_type", ""))
            if record.get("alarm_type") == "HIGH":
                alarm_type_item.setForeground(QColor(255, 120, 80))  # Softer red-orange
            elif record.get("alarm_type") == "LOW":
                alarm_type_item.setForeground(QColor(255, 180, 80))  # Softer yellow-orange
            alarm_type_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.history_table.setItem(row, 3, alarm_type_item)
            
            # Value
            value = record.get("value", 0)
            unit = record.get("unit", "")
            value_item = QTableWidgetItem(f"{value}{unit}" if value > 0 else "-")
            value_item.setFont(QFont("Courier New", 10))
            value_item.setForeground(QColor(140, 160, 180))  # Darker gray-blue
            self.history_table.setItem(row, 4, value_item)
            
            # Limit
            limit = record.get("limit", 0)
            limit_item = QTableWidgetItem(f"{limit}{unit}" if limit > 0 else "-")
            limit_item.setFont(QFont("Courier New", 10))
            limit_item.setForeground(QColor(140, 160, 180))  # Darker gray-blue
            self.history_table.setItem(row, 5, limit_item)
            
            # Status
            status_item = QTableWidgetItem(record.get("status", ""))
            if record.get("status") == "TRIGGERED":
                status_item.setForeground(QColor(255, 90, 90))  # Softer red
                status_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            else:
                status_item.setForeground(QColor(80, 220, 120))  # Softer green
            self.history_table.setItem(row, 6, status_item)
    
    def clear_history(self):
        """Clear all alarm history after confirmation"""
        reply = QMessageBox.question(self, "Clear History", 
                                     "Are you sure you want to clear all alarm history?\n\nThis action cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Ask for admin password
            password, ok = QInputDialog.getText(self, "Administrator Access",
                                               "Enter admin password:",
                                               QLineEdit.Password)
            admin_password = getattr(self.parent_window, 'admin_password', 'admin123')
            
            if ok and password == admin_password:
                try:
                    config = load_encrypted_config()
                    if config is None:
                        config = {}
                    
                    config["AlarmHistory"] = []
                    save_encrypted_config(config)
                    
                    self.all_history = []
                    self.apply_filter()
                    
                    QMessageBox.information(self, "Success", "Alarm history cleared successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to clear history: {str(e)}")
            elif ok:
                QMessageBox.warning(self, "Access Denied", "Incorrect password!")


# ---------------- Report Tab ----------------
class ReportTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.setMinimumSize(800, 600)
        self.setStyleSheet(CYLINDER_HEAD_BG_STYLE)
        
        # Load configuration for color determination
        self.config = self.load_config()
        
        # Initialize data arrays
        self.cylinder_head_temps = [0.0] * 18  # 9 left + 9 right
        self.main_bearing_temps = [0.0] * 10
        self.pressure_values = [0.0] * 8
        self.engine_temps = [0.0] * 16
        self.electrical_values = [0.0] * 9  # 3 voltage + 3 current + 3 power params
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(5)
        
        # Title
        title = QLabel("COMPREHENSIVE SYSTEM REPORT")
        title.setFont(QFont("Inter", 18, QFont.Bold))
        title.setStyleSheet("color: rgb(0, 200, 255); padding: 5px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Scroll area for content overflow
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px solid rgb(60, 80, 100);
                border-radius: 8px;
                background: rgba(30, 40, 55, 0.9);
            }
            QScrollBar:vertical {
                background: rgb(40, 50, 65);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgb(0, 150, 255);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgb(0, 180, 255);
            }
        """)
        
        # Main content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(8, 8, 8, 8)
        
        # Create grid layout for efficient space usage
        main_grid = QGridLayout()
        main_grid.setSpacing(8)
        main_grid.setContentsMargins(0, 0, 0, 0)
        
        # === ROW 1: CYLINDER HEAD TEMPERATURES + MAIN BEARING TEMPERATURES ===
        # Cylinder Head Temperatures (Left side)
        cylinder_group = self.create_data_group("CYLINDER HEAD TEMPERATURES", "")
        cylinder_grid = QGridLayout()
        cylinder_grid.setHorizontalSpacing(100)  # Increased gap between L and R columns
        cylinder_grid.setVerticalSpacing(3)     # Keep vertical spacing tight
        
        self.cylinder_left_labels = []
        self.cylinder_right_labels = []
        
        # Create compact digital boxes for cylinder temperatures
        for i in range(9):
            # Left cylinder
            left_box = self.create_digital_box(f"L{i+1}", "0.0°C", "rgb(100, 100, 100)")
            cylinder_grid.addWidget(left_box, i, 0)
            self.cylinder_left_labels.append(left_box.findChild(QLabel, "value"))
            
            # Right cylinder
            right_box = self.create_digital_box(f"R{i+1}", "0.0°C", "rgb(100, 100, 100)")
            cylinder_grid.addWidget(right_box, i, 1)
            self.cylinder_right_labels.append(right_box.findChild(QLabel, "value"))
        
        cylinder_group.setLayout(cylinder_grid)
        main_grid.addWidget(cylinder_group, 0, 0)
        
        # Main Bearing Temperatures (Right side)
        bearing_group = self.create_data_group("MAIN BEARING TEMPERATURES", "")
        bearing_grid = QGridLayout()
        bearing_grid.setHorizontalSpacing(100)  # Increased gap between columns
        bearing_grid.setVerticalSpacing(3)     # Keep vertical spacing tight
        bearing_grid.setAlignment(Qt.AlignTop)  # Align to top, no stretching
        
        self.bearing_labels = []
        for i in range(10):
            bearing_box = self.create_digital_box(f"MB{i+1}", "0.0°C", "rgb(100, 100, 100)")
            # Fill first column completely (9 items), then second column (1 item)
            if i < 9:
                bearing_grid.addWidget(bearing_box, i, 0)  # First column: MB1-MB9
            else:
                bearing_grid.addWidget(bearing_box, i - 9, 1)  # Second column: MB10
            self.bearing_labels.append(bearing_box.findChild(QLabel, "value"))
        
        bearing_group.setLayout(bearing_grid)
        main_grid.addWidget(bearing_group, 0, 1, Qt.AlignTop)
        
        # === ROW 2: ENGINE PRESSURES + ENGINE TEMPERATURES ===
        # Engine Pressures (Left side)
        pressure_group = self.create_data_group("ENGINE PRESSURES", "")
        pressure_grid = QGridLayout()
        pressure_grid.setSpacing(3)
        
        pressure_names = ["Lube Oil In", "Lube Oil Out", "Fuel Oil", "Charge Air", "HT Water", "Start Air", "Press 7", "Press 8"]
        
        self.pressure_labels = []
        for i, name in enumerate(pressure_names):
            pressure_box = self.create_digital_box(name, "0.0 bar", "rgb(100, 100, 100)")
            # Fill first column completely (8 items), then second column (0 items for 8 total)
            # Since we have 8 items, put 8 in first column, 0 in second
            pressure_grid.addWidget(pressure_box, i, 0)  # All 8 in first column
            self.pressure_labels.append(pressure_box.findChild(QLabel, "value"))
        
        pressure_group.setLayout(pressure_grid)
        main_grid.addWidget(pressure_group, 1, 0, Qt.AlignTop)
        
        # Engine Temperatures (Right side)
        engine_temp_group = self.create_data_group("ENGINE TEMPERATURES", "")
        engine_temp_grid = QGridLayout()
        engine_temp_grid.setHorizontalSpacing(100)  # Increased gap between columns
        engine_temp_grid.setVerticalSpacing(3)     # Keep vertical spacing tight
        
        engine_temp_names = ["Charge Air", "Lube Oil In", "Fuel Oil", "HT Water In", "HT Water Out", "LT Water In", "LT Water Out", "Alt Bear A", "Alt Bear B", "Wind U", "Wind V", "Wind W", "Eng T13", "Eng T14", "Eng T15", "Eng T16"]
        
        self.engine_temp_labels = []
        for i, name in enumerate(engine_temp_names):
            temp_box = self.create_digital_box(name, "0.0°C", "rgb(100, 100, 100)")
            # Fill first column completely (8 items), then second column (8 items)
            if i < 8:
                engine_temp_grid.addWidget(temp_box, i, 0)  # First column: items 1-8
            else:
                engine_temp_grid.addWidget(temp_box, i - 8, 1)  # Second column: items 9-16
            self.engine_temp_labels.append(temp_box.findChild(QLabel, "value"))
        
        engine_temp_group.setLayout(engine_temp_grid)
        main_grid.addWidget(engine_temp_group, 1, 1, Qt.AlignTop)
        
        # === ROW 3: ELECTRICAL PARAMETERS + SYSTEM STATUS ===
        # Electrical Parameters (Left side)
        electrical_group = self.create_data_group("ELECTRICAL PARAMETERS", "")
        electrical_grid = QGridLayout()
        electrical_grid.setSpacing(3)
        
        electrical_names = ["L1-L2 V", "L2-L3 V", "L3-L1 V", "L1 A", "L2 A", "L3 A", "Act Pwr", "PF", "React Pwr"]
        electrical_units = ["V", "V", "V", "A", "A", "A", "kW", "", "kVAR"]
        electrical_colors = ["rgb(100, 100, 100)"] * 9  # Gray for initial state
        
        self.electrical_labels = []
        for i, (name, unit, color) in enumerate(zip(electrical_names, electrical_units, electrical_colors)):
            elec_box = self.create_digital_box(name, f"0.0 {unit}", color)
            # Fill first column completely (9 items), then second column (0 items for 9 total)
            # Since we have 9 items, put all 9 in first column
            electrical_grid.addWidget(elec_box, i, 0)  # All 9 in first column
            self.electrical_labels.append(elec_box.findChild(QLabel, "value"))
        
        electrical_group.setLayout(electrical_grid)
        main_grid.addWidget(electrical_group, 2, 0, Qt.AlignTop)
        
        # System Status (Right side)
        status_group = self.create_data_group("SYSTEM STATUS", "")
        status_grid = QGridLayout()
        status_grid.setSpacing(3)
        
        # Connection status box
        conn_box = self.create_digital_box("Connection", "DISCONNECTED", "rgb(255, 100, 100)")
        self.connection_status = conn_box.findChild(QLabel, "value")
        status_grid.addWidget(conn_box, 0, 0)
        
        # Last update box
        update_box = self.create_digital_box("Last Update", "Never", "rgb(180, 200, 220)")
        self.last_update = update_box.findChild(QLabel, "value")
        status_grid.addWidget(update_box, 1, 0)
        
        status_group.setLayout(status_grid)
        main_grid.addWidget(status_group, 2, 1, Qt.AlignTop)
        
        # Add main grid to content layout
        content_layout.addLayout(main_grid)
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)
    
    def load_config(self):
        """Load configuration from modbus_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modbus_config.json")
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Config file doesn't exist yet - will be created by main window
            return {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def get_cylinder_head_color(self, temp):
        """Get color for cylinder head temperature based on configuration"""
        if temp <= 0:
            return "rgb(100, 100, 100)"  # Gray for no data
        
        config = self.config.get("CylinderHead", {})
        low_limit = config.get("low_limit", 250)
        high_limit = config.get("high_limit", 500)
        
        if temp < low_limit:
            return "rgb(100, 255, 255)"  # Cyan for low
        elif temp <= high_limit:
            return "rgb(100, 255, 100)"  # Green for normal
        else:
            return "rgb(255, 100, 100)"  # Red for high
    
    def get_main_bearing_color(self, temp):
        """Get color for main bearing temperature based on configuration"""
        if temp <= 0:
            return "rgb(100, 100, 100)"  # Gray for no data
        
        config = self.config.get("MainBearing", {})
        low_limit = config.get("low_limit", 80)
        high_limit = config.get("high_limit", 150)
        
        if temp < low_limit:
            return "rgb(100, 255, 255)"  # Cyan for low
        elif temp <= high_limit:
            return "rgb(100, 255, 100)"  # Green for normal
        else:
            return "rgb(255, 100, 100)"  # Red for high
    
    def get_pressure_color(self, pressure, index):
        """Get color for pressure based on configuration"""
        if pressure <= 0:
            return "rgb(100, 100, 100)"  # Gray for no data
        
        pressure_config = self.config.get("PressureGauges", {}).get(str(index), {})
        low_limit = pressure_config.get("low_limit", 2.0)
        high_limit = pressure_config.get("high_limit", 8.0)
        
        if pressure < low_limit:
            return "rgb(255, 100, 100)"  # Red for low pressure (dangerous)
        elif pressure <= high_limit:
            return "rgb(100, 255, 100)"  # Green for normal
        else:
            return "rgb(255, 255, 100)"  # Yellow for high
    
    def get_engine_temp_color(self, temp, index):
        """Get color for engine temperature based on configuration"""
        if temp <= 0:
            return "rgb(100, 100, 100)"  # Gray for no data
        
        temp_config = self.config.get("EngineTemperatures", {}).get(str(index), {})
        low_limit = temp_config.get("low_limit", 50)
        high_limit = temp_config.get("high_limit", 220)
        
        if temp < low_limit:
            return "rgb(100, 255, 255)"  # Cyan for low
        elif temp <= high_limit:
            return "rgb(100, 255, 100)"  # Green for normal
        else:
            return "rgb(255, 100, 100)"  # Red for high
    
    def create_data_group(self, title, station):
        """Create a professional SCADA-style data group"""
        group = QGroupBox()
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 11px;
                color: rgb(0, 200, 255);
                border: 2px solid rgb(60, 80, 100);
                border-radius: 6px;
                margin-top: 15px;
                padding-top: 10px;
                background: rgba(25, 35, 50, 0.8);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 2px 10px 2px 10px;
                color: rgb(0, 200, 255);
                background: rgba(25, 35, 50, 1.0);
                border-radius: 3px;
            }}
        """)
        group.setTitle(title)
        return group
    
    def create_digital_box(self, label_text, value_text, color):
        """Create a professional digital display box"""
        container = QWidget()
        container.setFixedHeight(55)  # Increased height for larger fonts
        container.setStyleSheet(f"""
            QWidget {{
                background: rgba(20, 30, 45, 0.9);
                border: none;
                border-radius: 4px;
                margin: 1px;
            }}
        """)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        
        # Label
        label = QLabel(label_text)
        label.setStyleSheet("color: rgb(180, 200, 220); font-size: 18px; font-weight: bold;")
        label.setFixedWidth(120)  # Increased width to accommodate larger font
        
        # Value
        value = QLabel(value_text)
        value.setObjectName("value")  # For finding later
        value.setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-size: 20px; font-weight: bold;")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        layout.addWidget(label)
        layout.addWidget(value)
        
        return container
    
    def create_section_header(self, layout, title, station):
        """Create a styled section header"""
        header_layout = QHBoxLayout()
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Inter", 14, QFont.Bold))
        title_label.setStyleSheet("color: rgb(0, 200, 255); padding: 8px;")
        
        station_label = QLabel(f"({station})")
        station_label.setStyleSheet("color: rgb(150, 170, 190); font-size: 11px; padding: 8px;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(station_label)
        header_layout.addStretch()
        
        # Add separator line
        separator = QLabel()
        separator.setFixedHeight(2)
        separator.setStyleSheet("background: rgb(60, 80, 100); margin: 5px 0px;")
        
        layout.addLayout(header_layout)
        layout.addWidget(separator)
    
    def update_cylinder_head_data(self, temps):
        """Update cylinder head temperature values"""
        if len(temps) >= 18:
            # Convert raw register values to actual temperatures (divide by 10)
            actual_temps = [temp / 10.0 for temp in temps[:18]]
            self.cylinder_head_temps = actual_temps
            
            # Update left side (first 9)
            for i in range(9):
                temp = actual_temps[i]
                color = self.get_cylinder_head_color(temp)
                self.cylinder_left_labels[i].setText(f"{temp:.1f} °C")
                self.cylinder_left_labels[i].setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-size: 15px; font-weight: bold;")
            
            # Update right side (next 9)
            for i in range(9):
                temp = actual_temps[i + 9]
                color = self.get_cylinder_head_color(temp)
                self.cylinder_right_labels[i].setText(f"{temp:.1f} °C")
                self.cylinder_right_labels[i].setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-size: 15px; font-weight: bold;")
    
    def update_main_bearing_data(self, temps):
        """Update main bearing temperature values"""
        if len(temps) >= 10:
            # Convert raw register values to actual temperatures (divide by 10)
            actual_temps = [temp / 10.0 for temp in temps[:10]]
            self.main_bearing_temps = actual_temps
            for i in range(10):
                temp = actual_temps[i]
                color = self.get_main_bearing_color(temp)
                self.bearing_labels[i].setText(f"{temp:.1f} °C")
                self.bearing_labels[i].setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-size: 15px; font-weight: bold;")
    
    def update_pressure_data(self, pressures):
        """Update pressure values"""
        if len(pressures) >= 8:
            self.pressure_values = pressures[:8]
            for i in range(8):
                pressure = self.pressure_values[i]
                color = self.get_pressure_color(pressure, i)
                self.pressure_labels[i].setText(f"{pressure:.1f} bar")
                self.pressure_labels[i].setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-size: 15px; font-weight: bold;")
    
    def update_engine_temperatures(self, temps):
        """Update engine temperature values"""
        if len(temps) >= 16:
            # Convert raw register values to actual temperatures (divide by 10)
            actual_temps = [temp / 10.0 for temp in temps[:16]]
            self.engine_temps = actual_temps
            for i in range(16):
                temp = actual_temps[i]
                color = self.get_engine_temp_color(temp, i)
                self.engine_temp_labels[i].setText(f"{temp:.1f} °C")
                self.engine_temp_labels[i].setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-size: 15px; font-weight: bold;")
    
    def update_electrical_data(self, values):
        """Update electrical parameter values"""
        if len(values) >= 9:
            # Electrical values should already be in proper engineering units
            self.electrical_values = values[:9]
            units = ["V", "V", "V", "A", "A", "A", "kW", "", "kVAR"]
            colors = [
                "rgb(255, 200, 100)", "rgb(255, 200, 100)", "rgb(255, 200, 100)",
                "rgb(100, 200, 255)", "rgb(100, 200, 255)", "rgb(100, 200, 255)",
                "rgb(200, 255, 100)", "rgb(255, 255, 100)", "rgb(255, 150, 200)"
            ]
            
            for i in range(9):
                value = self.electrical_values[i]
                unit = units[i]
                color = colors[i]
                
                if i == 7:  # Power Factor - special formatting (0.000 format)
                    pf_value = value / 1000.0 if value > 10 else value  # Convert if needed
                    self.electrical_labels[i].setText(f"{pf_value:.3f}")
                else:
                    self.electrical_labels[i].setText(f"{value:.1f} {unit}")
                
                self.electrical_labels[i].setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-size: 15px; font-weight: bold;")
    
    def update_connection_status(self, connected):
        """Update connection status"""
        if connected:
            self.connection_status.setText("CONNECTED")
            self.connection_status.setStyleSheet("color: rgb(100, 255, 100); font-family: 'Courier New'; font-size: 15px; font-weight: bold;")
        else:
            self.connection_status.setText("DISCONNECTED")
            self.connection_status.setStyleSheet("color: rgb(255, 100, 100); font-family: 'Courier New'; font-size: 15px; font-weight: bold;")
        
        # Update timestamp
        import time
        current_time = time.strftime('%H:%M:%S')
        self.last_update.setText(current_time)
        self.last_update.setStyleSheet("color: rgb(180, 200, 220); font-family: 'Courier New'; font-size: 15px; font-weight: bold;")
    
    def get_temperature_color(self, temp):
        """Get color based on temperature value"""
        if temp <= 0:
            return "rgb(100, 100, 100)"  # Gray for no data
        elif temp < 200:
            return "rgb(100, 255, 255)"  # Cyan for cool
        elif temp < 350:
            return "rgb(100, 255, 100)"  # Green for normal
        elif temp < 450:
            return "rgb(255, 255, 100)"  # Yellow for warm
        else:
            return "rgb(255, 100, 100)"  # Red for hot
    
    def get_pressure_color(self, pressure, index):
        """Get color based on pressure value and gauge type"""
        if pressure <= 0:
            return "rgb(100, 100, 100)"  # Gray for no data
        
        # Special handling for oil pressure (reverse logic)
        if index == 0:  # Lube Oil Pressure Inlet
            if pressure < 2:
                return "rgb(255, 100, 100)"  # Red for low oil pressure (dangerous)
            elif pressure < 5:
                return "rgb(255, 255, 100)"  # Yellow for warning
            else:
                return "rgb(100, 255, 100)"  # Green for good pressure
        else:
            # Normal pressure logic
            if pressure < 2:
                return "rgb(100, 255, 255)"  # Cyan for low
            elif pressure < 7:
                return "rgb(100, 255, 100)"  # Green for normal
            elif pressure < 9:
                return "rgb(255, 255, 100)"  # Yellow for high
            else:
                return "rgb(255, 100, 100)"  # Red for very high


# ---------------- Main HMI Window ----------------
class HMIWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Industrial HMI - Cylinder Head Temperatures")
        self.setGeometry(100, 100, 1320, 700)
        self.setStyleSheet(MAIN_WINDOW_STYLE)

        # --- Layout ---
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)

        # Top control bar
        self.control_bar = QHBoxLayout()
        self.control_bar.setSpacing(8)
        self.port_label = QLabel("COM PORT")
        self.port_label.setStyleSheet(PORT_LABEL_STYLE)

        self.port_box = QComboBox()
        self.port_box.setMinimumWidth(150)
        self.port_box.setMinimumHeight(32)
        self.port_box.setStyleSheet(COMBOBOX_STYLE)
        self.refresh_ports()

        self.connect_btn = QPushButton("CONNECT")
        self.connect_btn.setMinimumWidth(120)
        self.connect_btn.setMinimumHeight(32)
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.setStyleSheet(CONNECT_BUTTON_STYLE)
        self.connect_btn.clicked.connect(self.connect_modbus)

        self.status_label = QLabel("● DISCONNECTED")
        self.status_label.setStyleSheet(STATUS_DISCONNECTED_STYLE)

        # Test Mode Button
        self.test_mode_btn = QPushButton("TEST MODE")
        self.test_mode_btn.setMinimumWidth(110)
        self.test_mode_btn.setMinimumHeight(32)
        self.test_mode_btn.setCursor(Qt.PointingHandCursor)
        self.test_mode_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(255, 180, 0), stop:1 rgb(220, 140, 0));
                color: rgb(20, 25, 35);
                border: 1px solid rgb(255, 200, 50);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(255, 200, 50), stop:1 rgb(240, 160, 20));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(220, 140, 0), stop:1 rgb(180, 100, 0));
            }
        """)
        self.test_mode_btn.clicked.connect(self.toggle_test_mode)
        
        # Admin Login Button
        self.admin_logged_in = False
        self.admin_btn = QPushButton("🔐 ADMIN LOGIN")
        self.admin_btn.setMinimumWidth(130)
        self.admin_btn.setMinimumHeight(32)
        self.admin_btn.setCursor(Qt.PointingHandCursor)
        self.admin_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(60, 80, 120), stop:1 rgb(40, 60, 100));
                color: rgb(200, 220, 240);
                border: 1px solid rgb(80, 100, 140);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(80, 100, 140), stop:1 rgb(60, 80, 120));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(40, 60, 100), stop:1 rgb(20, 40, 80));
            }
        """)
        self.admin_btn.clicked.connect(self.toggle_admin_login)
        
        # Developer Mode Button
        self.developer_mode_active = False
        self.dev_mode_btn = QPushButton("🔧 DEV MODE")
        self.dev_mode_btn.setMinimumWidth(120)
        self.dev_mode_btn.setMinimumHeight(32)
        self.dev_mode_btn.setCursor(Qt.PointingHandCursor)
        self.dev_mode_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(60, 40, 80), stop:1 rgb(50, 30, 70));
                color: rgb(200, 150, 255);
                border: 1px solid rgb(80, 60, 100);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(80, 60, 100), stop:1 rgb(70, 50, 90));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(50, 30, 70), stop:1 rgb(40, 20, 60));
            }
        """)
        self.dev_mode_btn.clicked.connect(self.toggle_developer_mode)

        self.control_bar.addWidget(self.port_label)
        self.control_bar.addWidget(self.port_box)
        self.control_bar.addWidget(self.connect_btn)
        self.control_bar.addWidget(self.status_label)
        self.control_bar.addStretch()
        self.control_bar.addWidget(self.test_mode_btn)
        self.control_bar.addWidget(self.dev_mode_btn)
        self.control_bar.addWidget(self.admin_btn)

        # Content area with stacked widget
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(CONTENT_STACK_STYLE)

        # Create sections
        self.cylinder_tab = CylinderHeadTab(parent=self)
        self.content_stack.addWidget(self.cylinder_tab)
        
        self.bearing_tab = MainBearingTab(parent=self)
        self.content_stack.addWidget(self.bearing_tab)
        
        self.pressures_tab = EnginePressuresTab(parent=self)
        self.content_stack.addWidget(self.pressures_tab)
        
        self.engine_temps_tab = EngineTemperaturesTab(parent=self)
        self.content_stack.addWidget(self.engine_temps_tab)
        
        self.electrical_tab = ElectricalParameterTab(parent=self)
        self.content_stack.addWidget(self.electrical_tab)
        
        self.history_tab = HistoryTab(parent=self)
        self.content_stack.addWidget(self.history_tab)
        
        self.report_tab = ReportTab(parent=self)
        self.content_stack.addWidget(self.report_tab)
        
        # Bottom navigation bar
        self.nav_bar = QHBoxLayout()
        self.nav_bar.setSpacing(5)
        
        # Navigation buttons
        self.nav_buttons = []
        nav_items = [
            ("CYLINDER HEAD", 0),
            ("MAIN BEARING", 1),
            ("ENGINE PRESSURES", 2),
            ("ENGINE TEMPERATURES", 3),
            ("ELECTRICAL PARAMETERS", 4),
            ("HISTORY", 5),
            ("REPORT", 6)
        ]
        
        for label, index in nav_items:
            btn = QPushButton(label)
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=index: self.switch_section(idx))
            btn.setProperty("nav_index", index)
            self.nav_buttons.append(btn)
            self.nav_bar.addWidget(btn)
        
        # Style navigation buttons
        self.update_nav_button_styles()
        
        # Set initial section
        self.current_section = 0
        self.nav_buttons[0].setProperty("active", True)
        self.update_nav_button_styles()

        self.main_layout.addLayout(self.control_bar)
        self.main_layout.addWidget(self.content_stack, 1)
        self.main_layout.addLayout(self.nav_bar)
        self.setLayout(self.main_layout)

        # Modbus setup
        self.client = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_data)
        
        # Connection monitoring
        self.failed_attempts = 0
        self.max_failed_attempts = 3
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.is_connected = False
        
        # Test mode
        self.test_mode = False
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.generate_test_data)
        
        # Test data storage for smooth animation
        # Initialize with realistic starting values across all ranges (raw register format)
        
        # Cylinder Head Temperatures: Mix of normal, warning, and critical values
        # Normal: <400°C (4000), Warning: 400-600°C (4000-6000), Critical: >600°C (6000+)
        self.test_cylinder_temps = []
        for i in range(18):
            rand = random.random()
            if rand < 0.6:  # 60% normal range
                self.test_cylinder_temps.append(random.randint(2800, 3900))  # 280-390°C
            elif rand < 0.85:  # 25% warning range
                self.test_cylinder_temps.append(random.randint(4100, 5800))  # 410-580°C
            else:  # 15% critical range
                self.test_cylinder_temps.append(random.randint(6100, 7000))  # 610-700°C
        
        # Main Bearing Temperatures: Mix of normal, warning, and critical values
        # Normal: <150°C (1500), Warning: 150-250°C (1500-2500), Critical: >250°C (2500+)
        self.test_bearing_temps = []
        for i in range(10):
            rand = random.random()
            if rand < 0.7:  # 70% normal range
                self.test_bearing_temps.append(random.randint(700, 1400))   # 70-140°C
            elif rand < 0.9:  # 20% warning range
                self.test_bearing_temps.append(random.randint(1600, 2400))  # 160-240°C
            else:  # 10% critical range
                self.test_bearing_temps.append(random.randint(2600, 3000))  # 260-300°C
        
        # Test engine temperatures: Mix of normal, warning, and critical values
        # Range: 50-250°C (stored as register values * 10)
        self.test_engine_temps = []
        for i in range(16):
            rand = random.random()
            if rand < 0.65:  # 65% normal range (50-180°C)
                self.test_engine_temps.append(random.randint(500, 1800))   # 50-180°C
            elif rand < 0.85:  # 20% warning range (180-220°C)
                self.test_engine_temps.append(random.randint(1800, 2200))  # 180-220°C
            else:  # 15% critical range (220-250°C)
                self.test_engine_temps.append(random.randint(2200, 2500))  # 220-250°C
        
        # Test electrical parameters with realistic warning/critical distributions
        self.test_electrical_params = []
        electrical_configs = [
            # [normal_range, warning_range, critical_range] for each parameter
            ([385, 415], [375, 384, 416, 425], [350, 374, 426, 450]),  # Voltage L1-L2
            ([385, 415], [375, 384, 416, 425], [350, 374, 426, 450]),  # Voltage L2-L3
            ([385, 415], [375, 384, 416, 425], [350, 374, 426, 450]),  # Voltage L3-L1
            ([20, 60], [61, 80], [81, 100]),                           # Current L1
            ([20, 60], [61, 80], [81, 100]),                           # Current L2
            ([20, 60], [61, 80], [81, 100]),                           # Current L3
            ([200, 600], [601, 800], [801, 1000]),                     # Active Power (kW)
            ([920, 990], [880, 919], [800, 879]),                      # Power Factor (0.80-0.99)
            ([50, 200], [201, 350], [351, 500])                        # Reactive Power (kVAR)
        ]
        
        for i, config in enumerate(electrical_configs):
            rand = random.random()
            if rand < 0.65:  # 65% normal range
                normal_range = config[0]
                self.test_electrical_params.append(random.randint(normal_range[0], normal_range[1]))
            elif rand < 0.85:  # 20% warning range
                warning_range = config[1]
                if len(warning_range) == 4:  # Voltage has two warning ranges (low and high)
                    if random.random() < 0.5:
                        self.test_electrical_params.append(random.randint(warning_range[0], warning_range[1]))
                    else:
                        self.test_electrical_params.append(random.randint(warning_range[2], warning_range[3]))
                else:
                    self.test_electrical_params.append(random.randint(warning_range[0], warning_range[1]))
            else:  # 15% critical range
                critical_range = config[2]
                if len(critical_range) == 4:  # Voltage has two critical ranges (low and high)
                    if random.random() < 0.5:
                        self.test_electrical_params.append(random.randint(critical_range[0], critical_range[1]))
                    else:
                        self.test_electrical_params.append(random.randint(critical_range[2], critical_range[3]))
                else:
                    self.test_electrical_params.append(random.randint(critical_range[0], critical_range[1]))
        
        # Test pressures with realistic warning/critical distributions
        # Values in register format (multiply actual bar values by 10)
        self.test_pressures = []
        pressure_configs = [
            # [normal_range, warning_range, critical_range, is_reverse, max_range]
            ([20, 80], [90, 110], [120, 150], False, 15),   # Fuel Oil Pressure Inlet (0-15 bar)
            ([40, 80], [25, 35], [10, 20], True, 10),       # Lube Oil Pressure Inlet (0-10 bar, reverse)
            ([20, 60], [70, 80], [90, 100], False, 10),     # LT Water Pressure (0-10 bar)
            ([20, 60], [70, 80], [90, 100], False, 10),     # HT Water Pressure (0-10 bar)
            ([20, 60], [70, 80], [90, 100], False, 10),     # Charge Air Pressure (0-10 bar)
            ([80, 200], [210, 240], [250, 300], False, 30), # Starting Air Pressure (0-30 bar)
            ([20, 60], [70, 80], [90, 100], False, 10),     # Lube Oil Differential Pressure (0-10 bar)
            ([10, 30], [35, 40], [45, 50], False, 5)        # Crank Case Pressure (0-5 bar)
        ]
        
        for i, (normal, warning, critical, is_reverse, max_range) in enumerate(pressure_configs):
            rand = random.random()
            if rand < 0.6:  # 60% normal range
                self.test_pressures.append(random.randint(normal[0], normal[1]))
            elif rand < 0.8:  # 20% warning range
                self.test_pressures.append(random.randint(warning[0], warning[1]))
            else:  # 20% critical range
                self.test_pressures.append(random.randint(critical[0], critical[1]))
        
        # Load initial configuration
        self.load_initial_configuration()
    
    def resizeEvent(self, event):
        """Handle resize events to update control sizes"""
        super().resizeEvent(event)
        width = self.width()
        height = self.height()
        
        # Calculate scale factor
        scale_factor = min(width / 1320, height / 700)
        
        # Update control bar spacing and margins
        spacing = max(6, int(12 * scale_factor))
        self.control_bar.setSpacing(spacing)
        self.nav_bar.setSpacing(max(4, int(8 * scale_factor)))
        
        # Update main layout margins and spacing
        margin = max(8, int(16 * scale_factor))
        self.main_layout.setContentsMargins(margin, margin, margin, margin)
        self.main_layout.setSpacing(max(6, int(12 * scale_factor)))
        
        # Update button sizes
        btn_height = max(32, int(38 * scale_factor))
        self.port_box.setFixedHeight(btn_height)
        self.connect_btn.setFixedHeight(btn_height)
        self.test_mode_btn.setFixedHeight(btn_height)
        
        port_box_width = max(150, int(200 * scale_factor))
        connect_btn_width = max(120, int(160 * scale_factor))
        test_btn_width = max(110, int(140 * scale_factor))
        
        self.port_box.setFixedWidth(port_box_width)
        self.connect_btn.setFixedWidth(connect_btn_width)
        self.test_mode_btn.setFixedWidth(test_btn_width)
        
        # Update navigation button heights
        nav_btn_height = max(40, int(50 * scale_factor))
        for btn in self.nav_buttons:
            btn.setFixedHeight(nav_btn_height)
    
    # -------- Load Initial Configuration --------
    def load_initial_configuration(self):
        """Load configuration from encrypted file and apply to all widgets"""
        try:
            # Try to load from encrypted file first
            modbus_config = load_encrypted_config("modbus_config.dat")
            
            # If encrypted file doesn't exist, check for old JSON file and migrate
            if modbus_config is None and os.path.exists("modbus_config.json"):
                print("Migrating from old JSON config to encrypted format...")
                try:
                    with open("modbus_config.json", "r") as f:
                        modbus_config = json.load(f)
                    # Save in encrypted format and remove old file
                    if save_encrypted_config(modbus_config, "modbus_config.dat"):
                        os.remove("modbus_config.json")
                        print("Migration completed successfully")
                except Exception as e:
                    print(f"Migration failed: {e}")
                    modbus_config = None
            
            if modbus_config is not None:
                # Handle admin password - generate if null or missing
                if modbus_config.get("admin_password") is None:
                    # Generate new password on first run
                    new_password = generate_admin_password()
                    modbus_config["admin_password"] = new_password
                    
                    # Save the updated config in encrypted format
                    save_encrypted_config(modbus_config, "modbus_config.dat")
                    
                    # Show the generated password to the user with copy functionality
                    password_dialog = PasswordDisplayDialog(new_password, self)
                    password_dialog.exec_()
                    print(f"Generated admin password: {new_password}")
                
                # Store the admin password for use throughout the application
                self.admin_password = modbus_config["admin_password"]
            else:
                # If no config exists, create it with generated password
                new_password = generate_admin_password()
                default_modbus_config = create_default_modbus_config(new_password)
                
                # Save in encrypted format
                save_encrypted_config(default_modbus_config, "modbus_config.dat")
                
                self.admin_password = new_password
                
                # Show the generated password to the user with copy functionality
                password_dialog = PasswordDisplayDialog(new_password, self)
                password_dialog.exec_()
                print(f"Generated admin password: {new_password}")
                
                # Set modbus_config to the newly created default config
                modbus_config = default_modbus_config
            
            # Apply thresholds from modbus_config (no separate hmi_config needed)
            self.update_thresholds_from_modbus_config(modbus_config)
                
        except Exception as e:
            print(f"Failed to load initial configuration: {e}")
            # Fallback to default password if there's an error
            self.admin_password = "admin123"
    
    # -------- Switch Section --------
    def switch_section(self, index):
        # Update current section
        self.current_section = index
        
        # Switch content (only index 0 has content for now)
        if index < self.content_stack.count():
            self.content_stack.setCurrentIndex(index)
        
        # Update button states
        for btn in self.nav_buttons:
            btn.setProperty("active", btn.property("nav_index") == index)
        
        self.update_nav_button_styles()
    
    # -------- Update Navigation Button Styles --------
    def update_nav_button_styles(self):
        for btn in self.nav_buttons:
            is_active = btn.property("active")
            if is_active:
                btn.setStyleSheet(NAV_BUTTON_ACTIVE_STYLE)
            else:
                btn.setStyleSheet(NAV_BUTTON_INACTIVE_STYLE)

    # -------- COM Port Detection --------
    def refresh_ports(self):
        self.port_box.clear()
        ports = serial.tools.list_ports.comports()
        if ports:
            for p in ports:
                self.port_box.addItem(p.device)
        else:
            self.port_box.addItem("No Ports Found")

    # -------- Modbus Connect --------
    def connect_modbus(self):
        port = self.port_box.currentText()
        if "No" in port:
            QMessageBox.warning(self, "Connection Error", "No COM port available.")
            return

        try:
            self.client = ModbusSerialClient(
                port=port,
                baudrate=9600,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=0.2  # 200ms timeout - prevents UI freezing when stations don't respond
            )
            if self.client.connect():
                self.is_connected = True
                self.failed_attempts = 0
                self.reconnect_attempts = 0
                self.update_status("connected")
                self.timer.start(1000)
                self.connect_btn.setText("DISCONNECT")
                self.connect_btn.clicked.disconnect()
                self.connect_btn.clicked.connect(self.disconnect_modbus)
                # Set modbus client for tabs that need coil writing
                self.cylinder_tab.set_modbus_client(self.client)
                self.bearing_tab.set_modbus_client(self.client)
                self.pressures_tab.set_modbus_client(self.client)
                self.engine_temps_tab.set_modbus_client(self.client)
                self.electrical_tab.set_modbus_client(self.client)
            else:
                QMessageBox.critical(self, "Error", "Failed to connect to Modbus device.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    # -------- Modbus Disconnect --------
    def disconnect_modbus(self):
        if self.client:
            self.timer.stop()
            self.client.close()
            self.client = None
            self.is_connected = False
            self.failed_attempts = 0
            self.reconnect_attempts = 0
            self.update_status("disconnected")
            self.report_tab.update_connection_status(False)
            self.connect_btn.setText("CONNECT")
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.connect_modbus)
            # Clear all data and disconnect modbus clients
            self.cylinder_tab.set_modbus_client(None)
            self.cylinder_tab.update_temps([0] * 18)
            self.bearing_tab.set_modbus_client(None)
            self.bearing_tab.update_temps([0] * 10)
            self.pressures_tab.set_modbus_client(None)
            self.pressures_tab.update_pressures([0] * 8)
            self.engine_temps_tab.set_modbus_client(None)
            self.engine_temps_tab.update_temperatures([0] * 16)
            self.electrical_tab.set_modbus_client(None)
            self.electrical_tab.clear_displays()
            # Clear report tab data
            self.report_tab.update_cylinder_head_data([0] * 18)
            self.report_tab.update_main_bearing_data([0] * 10)
            self.report_tab.update_pressure_data([0] * 8)
            self.report_tab.update_engine_temperatures([0] * 16)
            self.report_tab.update_electrical_data([0] * 9)
    
    # -------- Update Status Display --------
    def update_status(self, status):
        if status == "connected":
            self.status_label.setText("● CONNECTED")
            self.status_label.setStyleSheet(STATUS_CONNECTED_STYLE)
        elif status == "reconnecting":
            self.status_label.setText(f"● RECONNECTING ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
            self.status_label.setStyleSheet(STATUS_RECONNECTING_STYLE)
        elif status == "error":
            self.status_label.setText(f"● NO RESPONSE ({self.failed_attempts}/{self.max_failed_attempts})")
            self.status_label.setStyleSheet(STATUS_ERROR_STYLE)
        else:  # disconnected
            self.status_label.setText("● DISCONNECTED")
            self.status_label.setStyleSheet(STATUS_DISCONNECTED_STYLE)
    
    # -------- Attempt Reconnection --------
    def attempt_reconnection(self):
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.disconnect_modbus()
            QMessageBox.critical(self, "Connection Lost", 
                f"No response from device after {self.max_reconnect_attempts} attempts.\n\n"
                f"Possible causes:\n"
                f"• Wrong COM port is selected\n"
                f"• Device is disconnected or powered off\n"
                f"• Communication cable issue\n"
                f"• Device is not responding\n\n"
                f"Please check the device and reconnect manually.")
            return
        
        self.reconnect_attempts += 1
        self.update_status("reconnecting")
        
        try:
            if self.client:
                self.client.close()
            
            port = self.port_box.currentText()
            self.client = ModbusSerialClient(
                port=port,
                baudrate=9600,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=0.2  # 200ms timeout - prevents UI freezing when stations don't respond
            )
            
            if self.client.connect():
                # Test each station independently - exceptions from one won't affect others
                station1_ok = False
                station2_ok = False
                station3_ok = False
                
                # Test Station 1 independently
                try:
                    test_station1 = self.client.read_input_registers(address=0, count=8, device_id=1)
                    station1_ok = test_station1 and not test_station1.isError()
                    print(f"Connection test Station 1: {'OK' if station1_ok else 'FAILED'}")
                except Exception as e:
                    print(f"Connection test Station 1 EXCEPTION: {e}")
                
                # Test Station 2 independently
                try:
                    test_station2 = self.client.read_input_registers(address=0, count=16, device_id=2)
                    station2_ok = test_station2 and not test_station2.isError()
                    print(f"Connection test Station 2: {'OK' if station2_ok else 'FAILED'}")
                except Exception as e:
                    print(f"Connection test Station 2 EXCEPTION: {e}")
                
                # Test Station 3 independently
                try:
                    test_station3 = self.client.read_input_registers(address=0, count=12, device_id=3)
                    station3_ok = test_station3 and not test_station3.isError()
                    print(f"Connection test Station 3: {'OK' if station3_ok else 'FAILED'}")
                except Exception as e:
                    print(f"Connection test Station 3 EXCEPTION: {e}")
                
                if station1_ok or station2_ok or station3_ok:
                    # At least one station is working - connection successful
                    self.is_connected = True
                    self.failed_attempts = 0
                    self.reconnect_attempts = 0
                    
                    # Update status with partial connection info if needed
                    working_stations = []
                    if station1_ok: working_stations.append("Pressures")
                    if station2_ok: working_stations.append("Cylinder Head")
                    if station3_ok: working_stations.append("Main Bearing")
                    # Note: Engine Temps and Electrical Parameters status not shown (can use various device IDs)
                    
                    if len(working_stations) == 3:
                        self.update_status("connected")
                    else:
                        # Partial connection - show which systems are working
                        status_text = f"● PARTIAL: {', '.join(working_stations)}"
                        self.status_label.setText(status_text)
                        self.status_label.setStyleSheet("""
                            QLabel {
                                color: rgb(255, 180, 0);
                                font-size: 13px;
                                font-weight: 600;
                                letter-spacing: 0.5px;
                                padding: 8px 16px;
                                background: rgba(255, 180, 0, 0.1);
                                border: 1px solid rgba(255, 180, 0, 0.3);
                                border-radius: 6px;
                            }
                        """)
                    
                    self.timer.start(1000)
                else:
                    # Connected but no response - try again
                    self.client.close()
                    QTimer.singleShot(1000, self.attempt_reconnection)
            else:
                # Connection failed - try again
                QTimer.singleShot(1000, self.attempt_reconnection)
        except Exception:
            # Exception occurred - try again
            if self.client:
                try:
                    self.client.close()
                except:
                    pass
            QTimer.singleShot(1000, self.attempt_reconnection)

    # -------- Toggle Test Mode --------
    def toggle_test_mode(self):
        self.test_mode = not self.test_mode
        
        if self.test_mode:
            # Enable test mode
            self.test_mode_btn.setText("EXIT TEST")
            self.test_mode_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgb(255, 60, 100), stop:1 rgb(220, 40, 80));
                    color: rgb(255, 255, 255);
                    border: 1px solid rgb(255, 100, 130);
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgb(255, 80, 120), stop:1 rgb(240, 60, 100));
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgb(220, 40, 80), stop:1 rgb(180, 20, 60));
                }
            """)
            
            # Disable modbus connection if active
            if self.is_connected:
                self.disconnect_modbus()
            
            # Disable connection controls
            self.port_box.setEnabled(False)
            self.connect_btn.setEnabled(False)
            
            # Update status
            self.status_label.setText("● TEST MODE ACTIVE")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: rgb(255, 180, 0);
                    font-size: 13px;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                    padding: 8px 16px;
                    background: rgba(255, 180, 0, 0.1);
                    border: 1px solid rgba(255, 180, 0, 0.3);
                    border-radius: 6px;
                }
            """)
            
            # Start test data generation timer
            self.test_timer.start(1000)  # Update every 1 second
            
            print("✅ Test mode activated - Generating simulated data")
        else:
            self.test_mode_btn.setText("TEST MODE")
            self.test_mode_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgb(255, 180, 0), stop:1 rgb(220, 140, 0));
                    color: rgb(20, 25, 35);
                    border: 1px solid rgb(255, 200, 50);
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgb(255, 200, 50), stop:1 rgb(240, 160, 20));
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgb(220, 140, 0), stop:1 rgb(180, 100, 0));
                }
            """)
            
            # Re-enable connection controls
            self.port_box.setEnabled(True)
            self.connect_btn.setEnabled(True)
            
            # Stop test data generation
            self.test_timer.stop()
            
            # Reset displays to zero
            self.cylinder_tab.update_temps([0] * 18)
            self.bearing_tab.update_temps([0] * 10)
            self.pressures_tab.update_pressures([0] * 8)
            self.engine_temps_tab.update_temperatures([0] * 16)
            self.electrical_tab.update_electrical_data([0] * 9)
            
            # Clear report tab data
            self.report_tab.update_cylinder_head_data([0] * 18)
            self.report_tab.update_main_bearing_data([0] * 10)
            self.report_tab.update_pressure_data([0] * 8)
            self.report_tab.update_engine_temperatures([0] * 16)
            self.report_tab.update_electrical_data([0] * 9)
            
            # Update status
            self.update_status("disconnected")
            self.report_tab.update_connection_status(False)
    
    # -------- Admin Login System --------
    def toggle_admin_login(self):
        """Toggle admin login/logout"""
        if not self.admin_logged_in:
            # Attempt login
            password, ok = QInputDialog.getText(self, "Administrator Login",
                                               "Enter admin password:",
                                               QLineEdit.Password)
            if ok and password == self.admin_password:
                self.admin_logged_in = True
                self.admin_btn.setText("A")
                self.admin_btn.setMinimumWidth(40)
                self.admin_btn.setMaximumWidth(40)
                self.admin_btn.setMinimumHeight(40)
                self.admin_btn.setMaximumHeight(40)
                self.admin_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(0, 200, 100), stop:1 rgb(0, 160, 80));
                        color: rgb(255, 255, 255);
                        border: 2px solid rgb(0, 220, 120);
                        border-radius: 20px;
                        font-size: 18px;
                        font-weight: 700;
                        font-family: 'Segoe UI', Arial, sans-serif;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(0, 220, 120), stop:1 rgb(0, 180, 100));
                        border: 2px solid rgb(0, 255, 140);
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(0, 160, 80), stop:1 rgb(0, 120, 60));
                    }
                """)
                QMessageBox.information(self, "Login Successful", 
                                      f"Welcome, Administrator!\n\nYou can now modify configuration settings without entering password each time.")
                # Enable admin mode for CylinderHeadTab
                self.cylinder_tab.set_admin_mode(True)
                print("✅ Admin logged in successfully")
            elif ok:
                QMessageBox.warning(self, "Login Failed", "Incorrect password!")
        else:
            # Logout
            reply = QMessageBox.question(self, "Logout", 
                                        "Are you sure you want to logout from admin mode?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.admin_logged_in = False
                self.admin_btn.setText("🔐 ADMIN LOGIN")
                self.admin_btn.setMinimumWidth(130)
                self.admin_btn.setMaximumWidth(16777215)  # Reset to default
                self.admin_btn.setMinimumHeight(32)
                self.admin_btn.setMaximumHeight(16777215)  # Reset to default
                self.admin_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(60, 80, 120), stop:1 rgb(40, 60, 100));
                        color: rgb(200, 220, 240);
                        border: 1px solid rgb(80, 100, 140);
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(80, 100, 140), stop:1 rgb(60, 80, 120));
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(40, 60, 100), stop:1 rgb(20, 40, 80));
                    }
                """)
                QMessageBox.information(self, "Logout Successful", 
                                      "You have been logged out from admin mode.\n\nPassword will be required for configuration changes.")
                # Disable admin mode for CylinderHeadTab
                self.cylinder_tab.set_admin_mode(False)
                print("✅ Admin logged out")
    
    # -------- Developer Mode System --------
    def toggle_developer_mode(self):
        """Toggle developer mode on/off"""
        if not self.developer_mode_active:
            # Attempt to enable developer mode
            password, ok = QInputDialog.getText(self, "Developer Mode",
                                               "Enter developer password:",
                                               QLineEdit.Password)
            if ok and password == "DEV AMEEN":
                self.developer_mode_active = True
                self.dev_mode_btn.setText("D")
                self.dev_mode_btn.setMinimumWidth(40)
                self.dev_mode_btn.setMaximumWidth(40)
                self.dev_mode_btn.setMinimumHeight(40)
                self.dev_mode_btn.setMaximumHeight(40)
                self.dev_mode_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(150, 100, 255), stop:1 rgb(120, 80, 200));
                        color: rgb(255, 255, 255);
                        border: 2px solid rgb(170, 120, 255);
                        border-radius: 20px;
                        font-size: 18px;
                        font-weight: 700;
                        font-family: 'Segoe UI', Arial, sans-serif;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(170, 120, 255), stop:1 rgb(140, 100, 220));
                        border: 2px solid rgb(190, 140, 255);
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(120, 80, 200), stop:1 rgb(100, 60, 180));
                    }
                """)
                QMessageBox.information(self, "Developer Mode Activated", 
                                      "Developer Mode is now active!\n\nYou can now modify temperature bars and other development features across all tabs.")
                
                # Enable developer mode for all tabs
                self.cylinder_tab.set_developer_mode(True)
                self.bearing_tab.set_developer_mode(True)
                
                print("✅ Developer Mode activated")
            elif ok:
                QMessageBox.warning(self, "Access Denied", "Incorrect developer password!")
        else:
            # Disable developer mode
            reply = QMessageBox.question(self, "Disable Developer Mode", 
                                        "Are you sure you want to disable Developer Mode?\n\nAll development features will be hidden.",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.developer_mode_active = False
                self.dev_mode_btn.setText("🔧 DEV MODE")
                self.dev_mode_btn.setMinimumWidth(120)
                self.dev_mode_btn.setMaximumWidth(16777215)  # Reset to default
                self.dev_mode_btn.setMinimumHeight(32)
                self.dev_mode_btn.setMaximumHeight(16777215)  # Reset to default
                self.dev_mode_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(60, 40, 80), stop:1 rgb(50, 30, 70));
                        color: rgb(200, 150, 255);
                        border: 1px solid rgb(80, 60, 100);
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(80, 60, 100), stop:1 rgb(70, 50, 90));
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgb(50, 30, 70), stop:1 rgb(40, 20, 60));
                    }
                """)
                QMessageBox.information(self, "Developer Mode Disabled", 
                                      "Developer Mode has been disabled.\n\nDevelopment features are now hidden.")
                
                # Disable developer mode for all tabs
                self.cylinder_tab.set_developer_mode(False)
                self.bearing_tab.set_developer_mode(False)
                
                print("✅ Developer Mode disabled")
    
    # -------- Generate Test Data --------
    def generate_test_data(self):
        # Generate smooth random variations while maintaining realistic range distributions
        
        # Cylinder Head Temperatures: Maintain range distribution with small variations
        for i in range(18):
            current_temp = self.test_cylinder_temps[i]
            change = random.randint(-15, 15)  # Smaller changes for smoother variation
            new_temp = current_temp + change
            
            # Apply range-specific bounds to maintain distribution
            if current_temp < 4000:  # Normal range
                self.test_cylinder_temps[i] = max(2500, min(4200, new_temp))
            elif current_temp < 6000:  # Warning range
                self.test_cylinder_temps[i] = max(3800, min(6200, new_temp))
            else:  # Critical range
                self.test_cylinder_temps[i] = max(5800, min(7200, new_temp))
        
        # Main Bearing Temperatures: Maintain range distribution
        for i in range(10):
            current_temp = self.test_bearing_temps[i]
            change = random.randint(-8, 8)  # Smaller changes
            new_temp = current_temp + change
            
            # Apply range-specific bounds
            if current_temp < 1500:  # Normal range
                self.test_bearing_temps[i] = max(600, min(1600, new_temp))
            elif current_temp < 2500:  # Warning range
                self.test_bearing_temps[i] = max(1400, min(2600, new_temp))
            else:  # Critical range
                self.test_bearing_temps[i] = max(2400, min(3200, new_temp))
        
        # Engine Temperatures: Maintain range distribution
        for i in range(16):
            current_temp = self.test_engine_temps[i]
            change = random.randint(-8, 8)  # Smaller changes
            new_temp = current_temp + change
            
            # Apply range-specific bounds
            if current_temp < 1800:  # Normal range
                self.test_engine_temps[i] = max(400, min(1900, new_temp))
            elif current_temp < 2200:  # Warning range
                self.test_engine_temps[i] = max(1700, min(2300, new_temp))
            else:  # Critical range
                self.test_engine_temps[i] = max(2100, min(2600, new_temp))
        
        # Pressures: Maintain realistic distributions with proper bounds
        # Values in register format (actual bar values * 10)
        pressure_bounds = [
            # [normal_min, normal_max, warning_min, warning_max, critical_min, critical_max]
            [15, 85, 85, 115, 115, 150],     # Fuel Oil Pressure Inlet (0-15 bar)
            [35, 85, 20, 40, 5, 25],         # Lube Oil Pressure Inlet (0-10 bar, reverse)
            [15, 65, 65, 85, 85, 100],       # LT Water Pressure (0-10 bar)
            [15, 65, 65, 85, 85, 100],       # HT Water Pressure (0-10 bar)
            [15, 65, 65, 85, 85, 100],       # Charge Air Pressure (0-10 bar)
            [70, 210, 210, 250, 250, 300],   # Starting Air Pressure (0-30 bar)
            [15, 65, 65, 85, 85, 100],       # Lube Oil Differential Pressure (0-10 bar)
            [8, 32, 32, 42, 42, 50]          # Crank Case Pressure (0-5 bar)
        ]
        
        for i in range(8):
            current_pressure = self.test_pressures[i]
            change = random.randint(-4, 4)  # Smaller changes
            new_pressure = current_pressure + change
            bounds = pressure_bounds[i]
            
            # Determine current range and apply appropriate bounds
            if i == 1:  # Lube Oil Pressure (reverse logic)
                if current_pressure >= bounds[0]:  # Normal range (high pressure is good)
                    self.test_pressures[i] = max(bounds[0], min(bounds[1], new_pressure))
                elif current_pressure >= bounds[2]:  # Warning range
                    self.test_pressures[i] = max(bounds[2], min(bounds[3], new_pressure))
                else:  # Critical range (low pressure is bad)
                    self.test_pressures[i] = max(bounds[4], min(bounds[5], new_pressure))
            else:  # Normal pressure logic
                if current_pressure <= bounds[1]:  # Normal range
                    self.test_pressures[i] = max(bounds[0], min(bounds[1], new_pressure))
                elif current_pressure <= bounds[3]:  # Warning range
                    self.test_pressures[i] = max(bounds[2], min(bounds[3], new_pressure))
                else:  # Critical range
                    self.test_pressures[i] = max(bounds[4], min(bounds[5], new_pressure))
        
        # Electrical Parameters: Maintain realistic distributions
        electrical_bounds = [
            # [normal_min, normal_max, warning_low_min, warning_low_max, warning_high_min, warning_high_max, critical_low_min, critical_low_max, critical_high_min, critical_high_max]
            [380, 420, 370, 384, 416, 430, 340, 374, 426, 460],  # Voltage L1-L2
            [380, 420, 370, 384, 416, 430, 340, 374, 426, 460],  # Voltage L2-L3
            [380, 420, 370, 384, 416, 430, 340, 374, 426, 460],  # Voltage L3-L1
            [15, 65, 65, 85, 85, 105],                            # Current L1
            [15, 65, 65, 85, 85, 105],                            # Current L2
            [15, 65, 65, 85, 85, 105],                            # Current L3
            [150, 650, 650, 850, 850, 1050],                     # Active Power (kW)
            [910, 1000, 870, 920, 790, 880],                     # Power Factor (reverse - lower is worse)
            [30, 220, 220, 370, 370, 520]                        # Reactive Power (kVAR)
        ]
        
        for i in range(9):
            current_value = self.test_electrical_params[i]
            change = random.randint(-8, 8)  # Moderate changes
            new_value = current_value + change
            bounds = electrical_bounds[i]
            
            # Handle voltage parameters (have both low and high warning/critical ranges)
            if i < 3:  # Voltages
                if bounds[0] <= current_value <= bounds[1]:  # Normal range
                    self.test_electrical_params[i] = max(bounds[0], min(bounds[1], new_value))
                elif bounds[2] <= current_value <= bounds[3] or bounds[4] <= current_value <= bounds[5]:  # Warning ranges
                    if current_value <= bounds[3]:  # Low warning
                        self.test_electrical_params[i] = max(bounds[2], min(bounds[3], new_value))
                    else:  # High warning
                        self.test_electrical_params[i] = max(bounds[4], min(bounds[5], new_value))
                else:  # Critical ranges
                    if current_value <= bounds[7]:  # Low critical
                        self.test_electrical_params[i] = max(bounds[6], min(bounds[7], new_value))
                    else:  # High critical
                        self.test_electrical_params[i] = max(bounds[8], min(bounds[9], new_value))
            elif i == 7:  # Power Factor (reverse logic - lower is worse)
                if bounds[0] <= current_value <= bounds[1]:  # Normal range (high values)
                    self.test_electrical_params[i] = max(bounds[0], min(bounds[1], new_value))
                elif bounds[2] <= current_value <= bounds[3]:  # Warning range
                    self.test_electrical_params[i] = max(bounds[2], min(bounds[3], new_value))
                else:  # Critical range (low values)
                    self.test_electrical_params[i] = max(bounds[4], min(bounds[5], new_value))
            else:  # Current and Power parameters (normal logic)
                if current_value <= bounds[1]:  # Normal range
                    self.test_electrical_params[i] = max(bounds[0], min(bounds[1], new_value))
                elif current_value <= bounds[3]:  # Warning range
                    self.test_electrical_params[i] = max(bounds[2], min(bounds[3], new_value))
                else:  # Critical range
                    self.test_electrical_params[i] = max(bounds[4], min(bounds[5], new_value))
        
        # Update displays with test data
        self.cylinder_tab.update_temps(self.test_cylinder_temps)
        self.bearing_tab.update_temps(self.test_bearing_temps)
        self.pressures_tab.update_pressures(self.test_pressures, is_test_mode=True)
        self.engine_temps_tab.update_temperatures(self.test_engine_temps)
        self.electrical_tab.update_electrical_data(self.test_electrical_params)
        
        # Update report tab with test data
        self.report_tab.update_cylinder_head_data(self.test_cylinder_temps)
        self.report_tab.update_main_bearing_data(self.test_bearing_temps)
        # Convert test pressures to actual values (divide by 10 to get bar values)
        actual_test_pressures = [val / 10.0 for val in self.test_pressures]
        self.report_tab.update_pressure_data(actual_test_pressures)
        self.report_tab.update_engine_temperatures(self.test_engine_temps)
        self.report_tab.update_electrical_data(self.test_electrical_params)
        self.report_tab.update_connection_status(True)
        
        # Randomly generate test alarms for history (10% chance per cycle)
        if random.random() < 0.1:
            self.history_tab.generate_test_alarm()
    
    def get_electrical_values_for_report(self):
        """Get current electrical values from electrical tab for report display"""
        try:
            # Get values from electrical displays
            electrical_values = []
            
            # Voltage values (3 values)
            for display in self.electrical_tab.voltage_displays:
                electrical_values.append(display.current_value if hasattr(display, 'current_value') else 0.0)
            
            # Current values (3 values)  
            for display in self.electrical_tab.amperage_displays:
                electrical_values.append(display.current_value if hasattr(display, 'current_value') else 0.0)
            
            # Power values (3 values)
            for display in self.electrical_tab.power_displays:
                electrical_values.append(display.current_value if hasattr(display, 'current_value') else 0.0)
            
            return electrical_values
        except Exception as e:
            print(f"Error getting electrical values for report: {e}")
            return [0.0] * 9

    # -------- Read Data from Modbus --------
    def read_data(self):
        if not self.client or not self.is_connected:
            return
        
        # Skip modbus reading if in test mode
        if self.test_mode:
            return
        
        # Track which stations are working
        station1_working = False
        station2_working = False
        station3_working = False
        station4_working = False
        station5_working = False
        station2_data = None
        station3_data = None
        station4_data = None
        
        # Read Station 1 (Engine Pressures) - 8 pressure values - COMPLETELY INDEPENDENT
        try:
            result_station1 = self.client.read_input_registers(address=0, count=8, device_id=1)
            if result_station1 and not result_station1.isError():
                pressure_values = result_station1.registers[:8]
                # Convert register values to actual pressure values (divide by 10)
                actual_pressures = [val / 10.0 for val in pressure_values]
                self.pressures_tab.update_pressures(pressure_values)
                self.report_tab.update_pressure_data(actual_pressures)
                station1_working = True
                print(f"Station 1 (Pressures): SUCCESS - {pressure_values}")
            else:
                # Station 1 failed - immediately clear pressure data (industrial standard)
                self.pressures_tab.update_pressures([0] * 8)
                self.report_tab.update_pressure_data([0] * 8)
                print("Station 1 (Pressures): FAILED - Data cleared")
        except Exception as e:
            # Station 1 exception - immediately clear pressure data
            self.pressures_tab.update_pressures([0] * 8)
            self.report_tab.update_pressure_data([0] * 8)
            print(f"Station 1 (Pressures): EXCEPTION - Data cleared - {e}")
        
        # Read Station 2 (Cylinder Head partial) - 16 registers - COMPLETELY INDEPENDENT
        try:
            result_station2 = self.client.read_input_registers(address=0, count=16, device_id=2)
            if result_station2 and not result_station2.isError():
                station2_working = True
                station2_data = result_station2.registers
                print(f"Station 2 (Cylinder Head): SUCCESS - {len(station2_data)} values")
            else:
                print("Station 2 (Cylinder Head): FAILED - No response or error")
        except Exception as e:
            print(f"Station 2 (Cylinder Head): EXCEPTION - {e}")
        
        # Read Station 3 (Cylinder Head partial + Main Bearing) - 12 registers - COMPLETELY INDEPENDENT
        try:
            result_station3 = self.client.read_input_registers(address=0, count=12, device_id=3)
            if result_station3 and not result_station3.isError():
                station3_working = True
                station3_data = result_station3.registers
                print(f"Station 3 (Main Bearing): SUCCESS - {len(station3_data)} values")
            else:
                print("Station 3 (Main Bearing): FAILED - No response or error")
        except Exception as e:
            print(f"Station 3 (Main Bearing): EXCEPTION - {e}")
        
        # Read Station 4 (Engine Temperatures) - 16 temperature values - HOLDING REGISTERS
        try:
            result_station4 = self.client.read_holding_registers(address=0, count=16, device_id=4)
            if result_station4 and not result_station4.isError():
                station4_working = True
                station4_data = result_station4.registers
                self.engine_temps_tab.update_temperatures(station4_data)
                self.report_tab.update_engine_temperatures(station4_data)
                print(f"Station 4 (Engine Temperatures): SUCCESS - {len(station4_data)} values")
            else:
                # Station 4 failed - immediately clear temperature data (industrial standard)
                self.engine_temps_tab.update_temperatures([0] * 16)
                self.report_tab.update_engine_temperatures([0] * 16)
                print("Station 4 (Engine Temperatures): FAILED - Data cleared")
        except Exception as e:
            # Station 4 exception - immediately clear temperature data
            self.engine_temps_tab.update_temperatures([0] * 16)
            self.report_tab.update_engine_temperatures([0] * 16)
            print(f"Station 4 (Engine Temperatures): EXCEPTION - Data cleared - {e}")
        
        # Read Station 5 (Electrical Parameters) - Now uses configuration-based reading
        try:
            # Call configuration-based update (reads from JSON config)
            self.electrical_tab.update_electrical_data()
            # Get current electrical values for report
            electrical_values = self.get_electrical_values_for_report()
            self.report_tab.update_electrical_data(electrical_values)
            station5_working = True
            print(f"Station 5 (Electrical Parameters): Configuration-based read attempted")
        except Exception as e:
            # Station 5 exception - immediately clear electrical data
            self.electrical_tab.update_electrical_data([0] * 9)
            self.report_tab.update_electrical_data([0] * 9)
            print(f"Station 5 (Electrical Parameters): EXCEPTION - Data cleared - {e}")
        
        # Update Cylinder Head temperatures - INDEPENDENT OF OTHER STATIONS
        try:
            if station2_data is not None and station3_data is not None:
                # Combine data: Left (9 from station 2) + Right (7 from station 2 + 2 from station 3)
                combined_temps = station2_data[:9] + station2_data[9:16] + station3_data[:2]
                self.cylinder_tab.update_temps(combined_temps)
                self.report_tab.update_cylinder_head_data(combined_temps)
                print("Cylinder Head: Updated with full data")
            elif station2_data is not None:
                # Only Station 2 working - update with partial data, clear missing station 3 data
                partial_temps = station2_data[:9] + station2_data[9:16] + [0, 0]  # Clear missing 2 from station 3
                self.cylinder_tab.update_temps(partial_temps)
                self.report_tab.update_cylinder_head_data(partial_temps)
                print("Cylinder Head: Updated with partial data (Station 2 only, Station 3 cleared)")
            else:
                # Both stations failed - immediately clear all cylinder head data (industrial standard)
                self.cylinder_tab.update_temps([0] * 18)
                self.report_tab.update_cylinder_head_data([0] * 18)
                print("Cylinder Head: Both stations failed - Data cleared")
        except Exception as e:
            print(f"Cylinder Head update EXCEPTION: {e}")
        
        # Update Main Bearing temperatures - INDEPENDENT OF OTHER STATIONS
        try:
            if station3_data is not None:
                # Main bearing temps: 10 temps from station 3 starting at index 2
                bearing_temps = station3_data[2:12]
                self.bearing_tab.update_temps(bearing_temps)
                self.report_tab.update_main_bearing_data(bearing_temps)
                print("Main Bearing: Updated with data")
            else:
                # Station 3 failed - immediately clear main bearing data (industrial standard)
                self.bearing_tab.update_temps([0] * 10)
                self.report_tab.update_main_bearing_data([0] * 10)
                print("Main Bearing: Station 3 failed - Data cleared")
        except Exception as e:
            print(f"Main Bearing update EXCEPTION: {e}")
        
        # Update connection status based on working stations - INDEPENDENT
        try:
            working_stations = []
            if station1_working: working_stations.append("Pressures")
            if station2_working: working_stations.append("Cylinder Head")
            if station3_working: working_stations.append("Main Bearing")
            if station4_working: working_stations.append("Engine Temperatures")
            if station5_working: working_stations.append("Electrical Parameters")
            
            print(f"Working stations: {working_stations}")
            
            if len(working_stations) == 5:
                # All stations working
                self.failed_attempts = 0
                self.reconnect_attempts = 0
                if self.status_label.text() != "● CONNECTED":
                    self.update_status("connected")
                self.report_tab.update_connection_status(True)
            elif len(working_stations) > 0:
                # Partial connection - some stations working
                self.failed_attempts = 0  # Reset since we have some data
                status_text = f"● PARTIAL: {', '.join(working_stations)}"
                self.status_label.setText(status_text)
                self.status_label.setStyleSheet("""
                    QLabel {
                        color: rgb(255, 180, 0);
                        font-size: 13px;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                        padding: 8px 16px;
                        background: rgba(255, 180, 0, 0.1);
                        border: 1px solid rgba(255, 180, 0, 0.3);
                        border-radius: 6px;
                    }
                """)
                self.report_tab.update_connection_status(True)
            else:
                # No stations working - handle as complete failure
                print("No stations working - calling handle_read_failure")
                self.handle_read_failure()
        except Exception as e:
            print(f"Status update EXCEPTION: {e}")
    
    # -------- Handle Read Failure --------
    def handle_read_failure(self):
        self.failed_attempts += 1
        self.update_status("error")
        
        # Only zero out data if we've had multiple consecutive failures
        # This prevents brief network hiccups from clearing all displays
        if self.failed_attempts >= 3:
            self.cylinder_tab.update_temps([0] * 18)
            self.bearing_tab.update_temps([0] * 10)
            self.pressures_tab.update_pressures([0] * 8)
            self.engine_temps_tab.update_temperatures([0] * 16)
        
        if self.failed_attempts >= self.max_failed_attempts:
            # Too many failures - attempt reconnection
            self.timer.stop()
            self.is_connected = False
            
            # Try to reconnect after 1 second
            QTimer.singleShot(1000, self.attempt_reconnection)
    
    # -------- Update Configuration Thresholds --------
    def update_thresholds_from_modbus_config(self, modbus_config):
        """Update color thresholds for all widgets based on modbus configuration"""
        # Extract threshold data from modbus_config format
        
        # Update cylinder head thresholds from CylinderHead section
        if hasattr(self.cylinder_tab, 'set_thresholds') and "CylinderHead" in modbus_config:
            cylinder_config = modbus_config["CylinderHead"]
            cylinder_thresholds = {
                "warning": cylinder_config.get("low_limit", 250),
                "critical": cylinder_config.get("high_limit", 500)
            }
            self.cylinder_tab.set_thresholds(cylinder_thresholds)
        
        # Update main bearing thresholds from MainBearing section
        if hasattr(self.bearing_tab, 'set_thresholds') and "MainBearing" in modbus_config:
            bearing_config = modbus_config["MainBearing"]
            bearing_thresholds = {
                "warning": bearing_config.get("low_limit", 80),
                "critical": bearing_config.get("high_limit", 150)
            }
            self.bearing_tab.set_thresholds(bearing_thresholds)
        
        # Update pressure gauges thresholds from PressureGauges section
        if hasattr(self.pressures_tab, 'set_thresholds') and "PressureGauges" in modbus_config:
            pressure_thresholds = {}
            for gauge_id, gauge_config in modbus_config["PressureGauges"].items():
                gauge_label = gauge_config.get("label", f"Gauge {gauge_id}")
                pressure_thresholds[gauge_label] = {
                    "warning": gauge_config.get("low_limit", 2.0),
                    "critical": gauge_config.get("high_limit", 8.0)
                }
            self.pressures_tab.set_thresholds(pressure_thresholds)
        
        # Update pressure gauge labels from PressureGauges section
        if hasattr(self.pressures_tab, 'update_gauge_labels') and "PressureGauges" in modbus_config:
            gauge_labels = {}
            for gauge_id, gauge_config in modbus_config["PressureGauges"].items():
                gauge_labels[f"gauge_{gauge_id}"] = gauge_config.get("label", f"Gauge {gauge_id}")
            self.pressures_tab.update_gauge_labels(gauge_labels)


# ---------------- Run App ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check if this is first run (no config file exists)
    config_file_path = "modbus_config.dat"
    is_first_run = not os.path.exists(config_file_path)
    
    if is_first_run:
        # For first run, create window directly without splash to handle password dialog
        print("First run detected - initializing without splash screen...")
        window = HMIWindow()
        window.showFullScreen()
    else:
        # Normal run with splash screen
        # Create and show custom splash screen
        splash_image_path = os.path.join(os.path.dirname(__file__), "SPLASH.png")
        splash = CustomSplashScreen(splash_image_path)
        splash.show()
        
        # Process events to ensure splash screen is displayed
        QApplication.processEvents()
        
        # Create loading worker thread
        loading_worker = LoadingWorker()
        
        # Connect worker signals to splash screen updates
        def update_splash_progress(progress, message):
            splash.show_message(message, progress)
        
        def finish_loading():
            try:
                # Create main window after loading is complete
                window = HMIWindow()
                
                # Close splash screen first
                splash.close()
                
                # Process events to ensure splash is closed
                QApplication.processEvents()
                
                # Show main window
                window.showFullScreen()
                
                # Clean up worker thread
                loading_worker.quit()
                loading_worker.wait()
                
            except Exception as e:
                # If there's an error during window creation, close splash and exit gracefully
                print(f"Error during window creation: {e}")
                splash.close()
                QApplication.processEvents()
                app.quit()
        
        # Connect signals
        loading_worker.progress_updated.connect(update_splash_progress)
        loading_worker.finished.connect(finish_loading)
        
        # Start the loading process
        loading_worker.start()
    
    # Run the application
    sys.exit(app.exec_())
