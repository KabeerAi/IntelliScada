# ============================================================
# Stylesheet Configuration for Industrial HMI Application
# ============================================================

# Main window background
MAIN_WINDOW_STYLE = """
    background-color: #0d1117; 
    color: #e6edf3; 
    font-family: 'Inter', 'Segoe UI', sans-serif;
"""

# Cylinder head tab background
CYLINDER_HEAD_BG_STYLE = "background-color: #0a0e1a;"

# Port label style
PORT_LABEL_STYLE = """
    color: #8b949e;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    padding-right: 8px;
"""

# ComboBox (Port selector) style
COMBOBOX_STYLE = """
    QComboBox {
        font-size: 14px;
        padding: 8px 14px;
        background-color: #161b22;
        color: #e6edf3;
        border: 1.5px solid #30363d;
    }
    QComboBox:hover {
        border: 1.5px solid #58a6ff;
        background-color: #1c2128;
    }
    QComboBox:focus {
        border: 1.5px solid #58a6ff;
        outline: none;
    }
    QComboBox::drop-down {
        border: none;
        width: 25px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #58a6ff;
        margin-right: 8px;
    }
    QComboBox QAbstractItemView {
        font-size: 14px;
        background-color: #161b22;
        color: #e6edf3;
        selection-background-color: #1f6feb;
        selection-color: #ffffff;
        padding: 4px;
        border: 1px solid #30363d;
    }
    QComboBox QAbstractItemView::item {
        min-height: 35px;
        padding: 8px;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: #1c2128;
    }
"""

# Connect button style
CONNECT_BUTTON_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #238636, stop:1 #1a7f37);
        color: #ffffff;
        border: 1.5px solid #2ea043;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2ea043, stop:1 #238636);
        border: 1.5px solid #3fb950;
    }
    QPushButton:pressed {
        background: #1a7f37;
        border: 1.5px solid #2ea043;
        padding-top: 9px;
        padding-bottom: 7px;
    }
"""

# Status label - disconnected
STATUS_DISCONNECTED_STYLE = """
    color: #f85149;
    font-weight: 600;
    margin-left: 16px;
    font-size: 13px;
    letter-spacing: 0.5px;
    padding: 8px 16px;
    background-color: rgba(248, 81, 73, 0.1);
    border: 1px solid rgba(248, 81, 73, 0.3);
"""

# Status label - connected
STATUS_CONNECTED_STYLE = """
    color: #3fb950;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.5px;
    padding: 8px 16px;
    background-color: rgba(63, 185, 80, 0.1);
    border: 1px solid rgba(63, 185, 80, 0.3);
"""

# Status label - reconnecting
STATUS_RECONNECTING_STYLE = """
    color: #f0883e;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.5px;
    padding: 8px 16px;
    background-color: rgba(240, 136, 62, 0.1);
    border: 1px solid rgba(240, 136, 62, 0.3);
"""

# Status label - error
STATUS_ERROR_STYLE = """
    color: #f85149;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.5px;
    padding: 8px 16px;
    background-color: rgba(248, 81, 73, 0.15);
    border: 1px solid rgba(248, 81, 73, 0.4);
"""

# Content stack (stacked widget) style
CONTENT_STACK_STYLE = """
    QStackedWidget {
        background-color: #0a0e1a;
        border: 1.5px solid #30363d;
    }
"""

# Navigation button - active state
NAV_BUTTON_ACTIVE_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1f6feb, stop:1 #1a5cd7);
        color: #ffffff;
        border: 1.5px solid #58a6ff;
        padding: 12px 20px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.8px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2672f3, stop:1 #1f6feb);
        border: 1.5px solid #79c0ff;
    }
"""

# Navigation button - inactive state
NAV_BUTTON_INACTIVE_STYLE = """
    QPushButton {
        background-color: #161b22;
        color: #8b949e;
        border: 1.5px solid #30363d;
        padding: 12px 20px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.8px;
    }
    QPushButton:hover {
        background-color: #1c2128;
        color: #c9d1d9;
        border: 1.5px solid #58a6ff;
    }
    QPushButton:pressed {
        background-color: #0d1117;
    }
"""

# Microsoft-style Add Button
MS_ADD_BUTTON_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #238636, stop:1 #1a7f37);
        color: #ffffff;
        border: 1.5px solid #2ea043;
        border-radius: 4px;
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 0.5px;
        padding: 8px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2ea043, stop:1 #238636);
        border: 1.5px solid #3fb950;
    }
    QPushButton:pressed {
        background: #1a7f37;
        border: 1.5px solid #2ea043;
        padding-top: 9px;
        padding-bottom: 7px;
    }
"""

# Microsoft-style Settings Button
MS_SETTINGS_BUTTON_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1f6feb, stop:1 #1a5cd7);
        color: #ffffff;
        border: 1.5px solid #58a6ff;
        border-radius: 20px;
        font-size: 18px;
        font-weight: 600;
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
"""

# Microsoft-style Pagination Button
MS_PAGINATION_BUTTON_STYLE = """
    QPushButton {
        background-color: #161b22;
        color: #c9d1d9;
        border: 1.5px solid #30363d;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.3px;
        padding: 6px 12px;
    }
    QPushButton:hover {
        background-color: #1c2128;
        color: #ffffff;
        border: 1.5px solid #58a6ff;
    }
    QPushButton:pressed {
        background-color: #0d1117;
        border: 1.5px solid #58a6ff;
    }
    QPushButton:disabled {
        background-color: #0d1117;
        color: #484f58;
        border: 1.5px solid #21262d;
    }
"""

# Microsoft-style Page Label
MS_PAGE_LABEL_STYLE = """
    color: #c9d1d9;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background-color: rgba(22, 27, 34, 0.8);
    border: 1px solid rgba(48, 54, 61, 0.8);
    border-radius: 3px;
    padding: 4px 8px;
"""
