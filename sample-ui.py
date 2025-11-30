import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QStackedWidget, QButtonGroup
)
from PyQt5.QtCore import Qt, QSize

class SCADAWindow(QWidget):
    """
    Main application window for the SCADA-style interface.
    
    This window uses a QVBoxLayout to stack the main content area
    (a QStackedWidget) on top of a custom navigation bar.
    """
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        """Initializes all UI components."""
        
        # Set main window properties
        self.setWindowTitle("Modern SCADA Interface")
        self.setMinimumSize(1200, 800)
        
        # Create the main vertical layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)  # Add padding around the app
        main_layout.setSpacing(10)  # Space between content and nav bar
        
        # 1. Create the top header bar
        header_bar_widget = self.create_header_bar()
        
        # 2. Create the central content area (StackedWidget)
        self.stacked_widget = self.create_pages()
        
        # 3. Create the bottom navigation bar
        nav_bar_widget = self.create_nav_bar()
        
        # 4. Add widgets to the main layout
        main_layout.addWidget(header_bar_widget) # Add header at the top
        # The '1' adds a stretch factor, making the stacked_widget
        # take up all available vertical space.
        main_layout.addWidget(self.stacked_widget, 1) 
        main_layout.addWidget(nav_bar_widget)
        
        # Set the main layout for the window
        self.setLayout(main_layout)
        
        # Apply the dark-themed stylesheet
        self.setStyleSheet(self.load_stylesheet())

    def create_header_bar(self):
        """
        Creates the top header bar with the company name.
        """
        # Use a QWidget as a container
        header_bar_container = QWidget()
        header_bar_container.setObjectName("HeaderBar")
        
        # Use QHBoxLayout for the content
        header_layout = QHBoxLayout(header_bar_container)
        header_layout.setContentsMargins(15, 5, 15, 5) # Add horizontal padding
        header_layout.setSpacing(10)
        
        # Add a stretchable space to push the label to the right
        header_layout.addStretch(1) 
        
        # Add the company name label
        company_label = QLabel("Company Name")
        company_label.setObjectName("HeaderLabel")
        company_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        header_layout.addWidget(company_label)
        
        return header_bar_container

    def create_pages(self):
        """
        Creates the QStackedWidget and populates it with 8 placeholder pages.
        """
        stacked_widget = QStackedWidget()
        stacked_widget.setObjectName("MainContent")
        
        for i in range(1, 9):
            # Create a simple placeholder page
            page = QWidget()
            page_layout = QVBoxLayout()
            
            # Add a label to identify the page
            label = QLabel(f"Screen {i} Page")
            label.setObjectName("PageLabel")
            label.setAlignment(Qt.AlignCenter)
            
            page_layout.addWidget(label)
            page.setLayout(page_layout)
            
            # Add the page to the stacked widget
            stacked_widget.addWidget(page)
            
        return stacked_widget

    def create_nav_bar(self):
        """
        Creates the bottom navigation bar with 8 buttons.
        """
        # Use a QWidget as a container for the horizontal button layout
        nav_bar_container = QWidget()
        nav_bar_container.setObjectName("NavBar")
        
        # Use QHBoxLayout for the buttons
        nav_layout = QHBoxLayout(nav_bar_container)
        nav_layout.setContentsMargins(5, 5, 5, 5)
        nav_layout.setSpacing(10)
        
        # Use a QButtonGroup to ensure only one button is active at a time
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
        
        for i in range(1, 9):
            button = QPushButton(f"Screen {i}")
            button.setObjectName("NavButton")
            button.setCheckable(True)
            
            # Connect the button's click to a function to change the page
            # We use a lambda and capture the index 'i-1'
            button.clicked.connect(lambda _, idx=i-1: self.stacked_widget.setCurrentIndex(idx))
            
            nav_layout.addWidget(button)
            self.button_group.addButton(button)
            
        # Set the first button as the default active/checked button
        first_button = nav_bar_container.findChild(QPushButton)
        if first_button:
            first_button.setChecked(True)
            
        return nav_bar_container

    def load_stylesheet(self):
        """
        Loads the QSS (Qt StyleSheet) for the dark, modern theme.
        """
        return """
        /* Main window and global styles */
        QWidget {
            background-color: #050c17; /* Deeper, darker navy background */
            color: #e0e6ed;
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-size: 14px;
        }

        /* Top Header Bar */
        QWidget#HeaderBar {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                      stop:0 #01060c, stop:0.5 #030d1a, stop:1 #01060c);
            border-radius: 0; /* Sharp, pro edge */
            max-height: 70px;
            min-height: 70px;
            border-bottom: 1px solid #0a1e33;
            box-shadow: 0 2px 4px rgba(0,0,0,0.25);
        }
        
        /* Company Name Label in Header */
        QLabel#HeaderLabel {
            font-size: 24px;
            font-weight: 700;
            color: #2bb0ef; /* Brighter accent for pro look */
            padding-right: 24px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        /* The main content area */
        QStackedWidget#MainContent {
            background-color: #0a1525; /* Deep navy content pane */
            border: 1px solid #0a1e33;
        }

        /* Placeholder labels on each page */
        QLabel#PageLabel {
            font-size: 48px;
            font-weight: bold;
            color: #1f3a52; /* Muted deep blue placeholder */
        }

        /* Navigation bar container */
        QWidget#NavBar {
            background-color: transparent;
            border-radius: 8px;
            max-height: 80px;
            min-height: 80px;
        }

        /* Navigation buttons */
        QPushButton#NavButton {
            background-color: transparent;
            color: #7a9ebd;
            border: 2px solid #0a1e33;
            border-radius: 6px;
            font-weight: bold;
            font-size: 16px;
            min-height: 60px;
            padding: 0 10px;
            transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
        }

        /* Hover effect for nav buttons */
        QPushButton#NavButton:hover {
            background-color: #0a1e33;
            color: #ffffff;
            border-color: #1f8ac7;
        }

        /* Active/Checked state for nav buttons */
        QPushButton#NavButton:checked {
            background-color: #1f8ac7;
            color: #ffffff;
            border: 2px solid #1f8ac7;
            border-bottom: 4px solid #2bb0ef;
        }
        
        /* Pressed state for nav buttons */
        QPushButton#NavButton:pressed {
            background-color: #186aa5;
            border-color: #2bb0ef;
        }
        
        """

# Main execution block
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SCADAWindow()
    window.show()
    sys.exit(app.exec_())