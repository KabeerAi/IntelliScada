# ============================================================
# Stylesheet Configuration for Industrial HMI Application
# ============================================================

# Main window background - Deep Navy Theme (matching sample-ui.py)
MAIN_WINDOW_STYLE = """
    background-color: #050c17;
    color: #e0e6ed;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 14px;
"""

# Page/Tab background - Deep Navy Theme (matching sample-ui.py)
# Pages inside QStackedWidget should have no border - the border is on the QStackedWidget itself
CYLINDER_HEAD_BG_STYLE = """background-color: #0a1525; border: none;"""

# Port label style - Elite Professional Design
PORT_LABEL_STYLE = """
    color: rgb(156, 163, 175);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.05em;
    padding-right: 16px;
    background: transparent;
"""

# ComboBox (Port selector) style - Elite Professional Design
COMBOBOX_STYLE = """
    QComboBox {
        font-size: 13px;
        font-weight: 500;
        padding: 8px 16px;
        background: rgba(17, 24, 39, 0.8);
        color: rgb(209, 213, 219);
        border: 1px solid rgba(75, 85, 99, 0.5);
        border-radius: 0px;
        letter-spacing: 0.01em;
        outline: none;
        min-width: 140px;
    }
    QComboBox:hover {
        border: 1px solid rgba(59, 130, 246, 0.6);
        background: rgba(31, 41, 55, 0.9);
        color: rgb(229, 231, 235);
    }
    QComboBox:focus {
        border: 1px solid rgba(59, 130, 246, 0.8);
        outline: none;
        background: rgba(31, 41, 55, 0.95);
    }
    QComboBox::drop-down {
        border: none;
        width: 28px;
        background: transparent;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid rgba(156, 163, 175, 0.8);
        margin-right: 8px;
    }
    QComboBox QAbstractItemView {
        font-size: 13px;
        background: rgba(17, 24, 39, 0.98);
        color: rgb(209, 213, 219);
        selection-background-color: rgba(59, 130, 246, 0.15);
        selection-color: rgb(243, 244, 246);
        padding: 4px;
        border: 1px solid rgba(75, 85, 99, 0.4);
        border-radius: 0px;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        min-height: 36px;
        padding: 10px 16px;
        border: none;
    }
    QComboBox QAbstractItemView::item:hover {
        background: rgba(59, 130, 246, 0.1);
    }
    QComboBox QAbstractItemView::item:selected {
        background: rgba(59, 130, 246, 0.15);
        border-left: 2px solid rgba(59, 130, 246, 0.8);
    }
"""

# Connect button style - Elite Professional Design
CONNECT_BUTTON_STYLE = """
    QPushButton {
        background: rgba(16, 185, 129, 0.1);
        color: rgb(167, 243, 208);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 0px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.025em;
        outline: none;
    }
    QPushButton:hover {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.5);
        color: rgb(209, 250, 229);
    }
    QPushButton:pressed {
        background: rgba(16, 185, 129, 0.25);
        border: 1px solid rgba(16, 185, 129, 0.6);
    }
"""

# Status label - disconnected - Elite Professional Design
STATUS_DISCONNECTED_STYLE = """
    color: rgb(248, 113, 113);
    font-weight: 500;
    font-size: 13px;
    letter-spacing: 0.025em;
    padding: 8px 16px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 0px;
    outline: none;
"""

# Status label - connected - Elite Professional Design
STATUS_CONNECTED_STYLE = """
    color: rgb(134, 239, 172);
    font-weight: 500;
    font-size: 13px;
    letter-spacing: 0.025em;
    padding: 8px 16px;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.2);
    border-radius: 0px;
    outline: none;
"""

# Status label - reconnecting - Elite Professional Design
STATUS_RECONNECTING_STYLE = """
    color: rgb(251, 191, 36);
    font-weight: 500;
    font-size: 13px;
    letter-spacing: 0.025em;
    padding: 8px 16px;
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.2);
    border-radius: 0px;
    outline: none;
"""

# Status label - error - Elite Professional Design
STATUS_ERROR_STYLE = """
    color: rgb(252, 165, 165);
    font-weight: 500;
    font-size: 13px;
    letter-spacing: 0.025em;
    padding: 8px 16px;
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 0px;
    outline: none;
"""

# Content stack (stacked widget) style - Deep Navy Theme (matching sample-ui.py)
CONTENT_STACK_STYLE = """
    QStackedWidget {
        background-color: #0a1525;
        border: 1px solid #0a1e33;
    }
"""

# Navigation button - active state - Elite Professional Design
NAV_BUTTON_ACTIVE_STYLE = """
    QPushButton {
        background: rgba(59, 130, 246, 0.12);
        color: rgb(224, 231, 255);
        border: none;
        border-bottom: 2px solid rgb(59, 130, 246);
        border-radius: 0px;
        padding: 14px 28px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.02em;
        outline: none;
    }
    QPushButton:hover {
        background: rgba(59, 130, 246, 0.18);
        color: rgb(237, 241, 255);
    }
"""

# Navigation button - inactive state - Elite Professional Design
NAV_BUTTON_INACTIVE_STYLE = """
    QPushButton {
        background: transparent;
        color: rgb(156, 163, 175);
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0px;
        padding: 14px 28px;
        font-size: 13px;
        font-weight: 500;
        letter-spacing: 0.02em;
        outline: none;
    }
    QPushButton:hover {
        background: rgba(55, 65, 81, 0.4);
        color: rgb(209, 213, 219);
        border-bottom: 2px solid rgba(75, 85, 99, 0.6);
    }
    QPushButton:pressed {
        background: rgba(31, 41, 55, 0.6);
        color: rgb(229, 231, 235);
    }
"""

# Mode Button Style - TEST/DEV/ADMIN - Professional Sharp Design
MODE_BUTTON_STYLE = """
    QPushButton {
        background: linear-gradient(to bottom, rgba(0, 120, 200, 0.3), rgba(0, 100, 170, 0.25));
        color: rgb(180, 220, 255);
        border: 1px solid rgba(0, 150, 220, 0.5);
        border-radius: 0px;
        padding: 10px 18px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.7px;
        outline: none;
    }
    QPushButton:hover {
        background: linear-gradient(to bottom, rgba(0, 140, 220, 0.4), rgba(0, 120, 190, 0.35));
        border: 1.5px solid rgba(0, 180, 255, 0.8);
        color: rgb(210, 240, 255);
    }
    QPushButton:pressed {
        background: rgba(0, 80, 150, 0.4);
        border: 1px solid rgba(0, 120, 200, 0.6);
        padding-top: 11px;
        padding-bottom: 9px;
    }
"""

# Microsoft-style Add Button - Professional Sharp Design
MS_ADD_BUTTON_STYLE = """
    QPushButton {
        background: linear-gradient(to bottom, rgba(0, 180, 255, 0.35), rgba(0, 140, 220, 0.3));
        color: rgb(200, 230, 255);
        border: 1px solid rgba(0, 200, 255, 0.5);
        border-radius: 0px;
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.5px;
        padding: 10px 16px;
        outline: none;
    }
    QPushButton:hover {
        background: linear-gradient(to bottom, rgba(0, 200, 255, 0.45), rgba(0, 160, 240, 0.4));
        border: 1.5px solid rgba(0, 230, 255, 0.8);
        color: rgb(220, 245, 255);
    }
    QPushButton:pressed {
        background: rgba(0, 120, 200, 0.4);
        border: 1px solid rgba(0, 180, 240, 0.6);
        padding-top: 11px;
        padding-bottom: 9px;
    }
"""

# Microsoft-style Settings Button - Professional Sharp Design
MS_SETTINGS_BUTTON_STYLE = """
    QPushButton {
        background: linear-gradient(to bottom, rgba(100, 120, 180, 0.3), rgba(80, 100, 160, 0.25));
        color: rgb(200, 220, 240);
        border: 1px solid rgba(100, 150, 220, 0.5);
        border-radius: 0px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.7px;
        padding: 10px 18px;
        outline: none;
    }
    QPushButton:hover {
        background: linear-gradient(to bottom, rgba(120, 140, 200, 0.4), rgba(100, 120, 180, 0.35));
        border: 1.5px solid rgba(150, 180, 255, 0.8);
        color: rgb(220, 240, 255);
    }
    QPushButton:pressed {
        background: rgba(60, 80, 140, 0.4);
        border: 1px solid rgba(100, 150, 230, 0.6);
        padding-top: 11px;
        padding-bottom: 9px;
    }
"""

# Microsoft-style Pagination Button - Professional Sharp Design
MS_PAGINATION_BUTTON_STYLE = """
    QPushButton {
        background: linear-gradient(to bottom, rgba(40, 55, 75, 0.4), rgba(30, 45, 65, 0.35));
        color: rgb(180, 200, 220);
        border: 1px solid rgba(0, 160, 220, 0.4);
        border-radius: 0px;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.3px;
        padding: 8px 14px;
        outline: none;
    }
    QPushButton:hover {
        background: linear-gradient(to bottom, rgba(50, 70, 90, 0.5), rgba(40, 60, 80, 0.45));
        color: rgb(210, 230, 255);
        border: 1.5px solid rgba(0, 200, 255, 0.6);
    }
    QPushButton:pressed {
        background: rgba(20, 35, 55, 0.5);
        border: 1px solid rgba(0, 180, 240, 0.5);
        padding-top: 9px;
        padding-bottom: 7px;
    }
    QPushButton:disabled {
        background: rgba(20, 30, 45, 0.3);
        color: rgba(120, 140, 160, 0.4);
        border: 1px solid rgba(60, 80, 100, 0.2);
    }
"""

# Microsoft-style Page Label - Professional Sharp Design
MS_PAGE_LABEL_STYLE = """
    color: rgb(180, 200, 220);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background: linear-gradient(to bottom, rgba(35, 50, 70, 0.4), rgba(25, 40, 60, 0.35));
    border: 1px solid rgba(0, 160, 220, 0.3);
    border-radius: 0px;
    padding: 6px 12px;
"""

# Top Bar Container - Professional Sharp Design
TOPBAR_STYLE = """
    QWidget {
        background: linear-gradient(to bottom, rgba(25, 35, 50, 0.95), rgba(20, 30, 45, 0.9));
        border-bottom: 1px solid rgba(0, 150, 220, 0.3);
    }
"""

# Award-winning refinements
TOPBAR_REFINEMENT_STYLE = """
    /* Professional spacing and alignment */
    QWidget {
        spacing: 12px;
        padding: 2px 8px;
    }
"""

# Consistent style for tab headings
TAB_HEADING_STYLE = """
    color: rgb(0, 200, 255);
    background-color: transparent;
    padding: 5px;
    font-size: 18px;
    font-weight: bold;
"""
