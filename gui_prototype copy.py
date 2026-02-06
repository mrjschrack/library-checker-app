from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QHeaderView
import sys
import threading  
import json
import os
import keyring

from preferences_modal import PreferencesDialog

class LibraryCheckerApp(QtWidgets.QWidget):
    def __init__(self):
        self.csv_path = None
        super().__init__()
        self.libraries = []
        self.load_libraries()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Library Availability Checker')
        self.resize(800, 600)

        # Layouts
        main_layout = QtWidgets.QVBoxLayout()
        top_button_layout = QtWidgets.QHBoxLayout()

        # Buttons
        self.select_csv_btn = QtWidgets.QPushButton('Select Goodreads CSV')
        self.run_search_btn = QtWidgets.QPushButton('Run Search')
        self.prefs_btn = QtWidgets.QPushButton('Preferences / Account')
        self.close_btn = QtWidgets.QPushButton('Close App')

        # Connect buttons
        self.select_csv_btn.clicked.connect(self.select_csv)
        self.run_search_btn.clicked.connect(self.run_search)
        self.close_btn.clicked.connect(self.close)
        self.prefs_btn.clicked.connect(self.open_preferences)

        # Add buttons to layout
        top_button_layout.addWidget(self.select_csv_btn)
        top_button_layout.addWidget(self.run_search_btn)
        top_button_layout.addWidget(self.prefs_btn)
        top_button_layout.addWidget(self.close_btn)

        # Status and progress bar
        self.status_label = QtWidgets.QLabel('Status: Waiting for CSV...')
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)

        # Table widget
        self.table = QtWidgets.QTableWidget()
        self.table.cellClicked.connect(self.cell_clicked)
        self.update_table_headers()

        # Summary Report
        self.summary_box = QtWidgets.QTextEdit()
        self.summary_box.setReadOnly(True)

        # Assemble layout
        main_layout.addLayout(top_button_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.table)
        main_layout.addWidget(self.summary_box)

        self.setLayout(main_layout)

    def load_libraries(self):
        if os.path.exists("user_libraries.json"):
            with open("user_libraries.json") as f:
                self.libraries = json.load(f)
        else:
            self.libraries = []

    def update_table_headers(self):
        self.table.setColumnCount(len(self.libraries) + 1)
        self.table.setHorizontalHeaderLabels(['Title'] + [lib['name'] for lib in self.libraries])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def select_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Goodreads CSV", "", "CSV Files (*.csv)")
        if path:
            self.csv_path = path
            self.status_label.setText(f"Status: Loaded {path}")

    def run_search(self):
        if not self.csv_path:
            QtWidgets.QMessageBox.warning(self, "No CSV Selected", "Please select a CSV file first.")
            return
        self.status_label.setText("Status: Running...")
        self.progress_bar.setValue(0)
        thread = threading.Thread(target=self.scrape_thread)
        thread.start()

    def scrape_thread(self):
        self.load_libraries()
        self.results = []
        import pandas as pd
        import time
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager

        df = pd.read_csv(self.csv_path)
        df = df[df['Bookshelves'].str.contains("to-read", na=False, case=False)]
        titles = df[['Title', 'Author']].head(10)

        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        total = len(titles)
        for idx, row in enumerate(titles.itertuples()):
            title = row.Title
            author = row.Author
            query = f"{title} {author}".replace(" ", "%20")

            for lib in self.libraries:
                from urllib.parse import urljoin
                lib_search_url = urljoin(lib['url'], f"search?query={query}")

                card_number = keyring.get_password('LibraryCheckerApp', f"{lib['name']}_card")
                pin = keyring.get_password('LibraryCheckerApp', f"{lib['name']}_pin")
                driver.get(lib_search_url)

                status = "Unavailable"
                elements = driver.find_elements(By.TAG_NAME, "span")
                for element in elements:
                    text = element.text.lower().strip()
                    if "borrow" in text:
                        status = "Available"
                        break
                    elif "place a hold" in text:
                        status = "Hold"
                        break

                self.results.append((title, lib['name'], status, lib_search_url))

            QtCore.QMetaObject.invokeMethod(self, "update_progress", QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(int, int((idx + 1) / total * 100)),
                QtCore.Q_ARG(str, f"Processing: {title}"))

        driver.quit()
        QtCore.QMetaObject.invokeMethod(self, "scrape_done", QtCore.Qt.QueuedConnection)

    @QtCore.pyqtSlot(int, str)
    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.status_label.setText(f"Status: {text}")

    @QtCore.pyqtSlot()
    def scrape_done(self):
        color_map = {'Available': QtCore.Qt.green, 'Hold': QColor('#FFEB99'), 'Unavailable': QtCore.Qt.lightGray}
        self.table.setRowCount(len(set([r[0] for r in self.results])))
        grouped = {}
        for title, lib_name, status, url in self.results:
            if title not in grouped:
                grouped[title] = {}
            grouped[title][lib_name] = (status, url)

        for i, (title, lib_data) in enumerate(grouped.items()):
            title_item = QTableWidgetItem(title)
            self.table.setItem(i, 0, title_item)
            for col_idx, lib in enumerate(self.libraries):
                lib_name = lib['name']
                if lib_name in lib_data:
                    status, url = lib_data[lib_name]
                    item = QTableWidgetItem(status)
                    item.setBackground(color_map.get(status, QtCore.Qt.lightGray))
                    item.setData(QtCore.Qt.UserRole, url)
                else:
                    item = QTableWidgetItem("-")
                    item.setBackground(QtCore.Qt.lightGray)
                self.table.setItem(i, col_idx + 1, item)

        self.status_label.setText("Status: Done!")
        self.summary_box.setText("""Summary:
- Live scraping complete.
- Selenium driver shut down cleanly.""")

    def cell_clicked(self, row, column):
        if column >= 1:
            item = self.table.item(row, column)
            url = item.data(QtCore.Qt.UserRole)
            if url:
                import webbrowser
                webbrowser.open(url)

    def open_preferences(self):
        dialog = PreferencesDialog(self)
        dialog.preferences_saved.connect(self.refresh_libraries)
        dialog.exec_()

    @QtCore.pyqtSlot()
    def refresh_libraries(self):
        self.load_libraries()
        self.update_table_headers()
        QtWidgets.QMessageBox.information(self, "Saved", "Preferences updated!")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = LibraryCheckerApp()
    window.show()
    sys.exit(app.exec_())
