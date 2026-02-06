from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QHeaderView, QMessageBox
import sys
import threading
import json
import os
import keyring

from preferences_modal import PreferencesDialog

import webbrowser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin


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

        main_layout = QtWidgets.QVBoxLayout()
        top_button_layout = QtWidgets.QHBoxLayout()

        self.select_csv_btn = QtWidgets.QPushButton('Select Goodreads CSV')
        self.run_search_btn = QtWidgets.QPushButton('Run Search')
        self.prefs_btn = QtWidgets.QPushButton('Preferences / Account')
        self.close_btn = QtWidgets.QPushButton('Close App')

        self.select_csv_btn.clicked.connect(self.select_csv)
        self.run_search_btn.clicked.connect(self.run_search)
        self.close_btn.clicked.connect(self.close)
        self.prefs_btn.clicked.connect(self.open_preferences)

        top_button_layout.addWidget(self.select_csv_btn)
        top_button_layout.addWidget(self.run_search_btn)
        top_button_layout.addWidget(self.prefs_btn)
        top_button_layout.addWidget(self.close_btn)

        self.status_label = QtWidgets.QLabel('Status: Waiting for CSV...')
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)

        self.table = QtWidgets.QTableWidget()
        self.table.cellClicked.connect(self.cell_clicked)
        self.update_table_headers()

        self.summary_box = QtWidgets.QTextEdit()
        self.summary_box.setReadOnly(True)

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
            QMessageBox.warning(self, "No CSV Selected", "Please select a CSV file first.")
            return
        self.status_label.setText("Status: Running...")
        self.progress_bar.setValue(0)
        thread = threading.Thread(target=self.scrape_thread)
        thread.start()

    def scrape_thread(self):
        self.load_libraries()
        self.results = []

        import pandas as pd
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
                lib_search_url = urljoin(lib['url'], f"search?query={query}")

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
        # Pass row & column into the worker for later cell update
        if column >= 1:
            item = self.table.item(row, column)
            url = item.data(QtCore.Qt.UserRole)
            if url:
                status = item.text()
                lib_name = self.table.horizontalHeaderItem(column).text()
                if status in ["Available", "Hold"]:
                    action = "Borrow" if status == "Available" else "Hold"
                    threading.Thread(
                        target=self.perform_login_and_action,
                        args=(lib_name, url, action, row, column),
                        daemon=True
                    ).start()
                else:
                    webbrowser.open(url)

    def perform_login_and_action(self, lib_name, action_url, action_type, row, column):
        options = Options()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            card_number = keyring.get_password('LibraryCheckerApp', f"{lib_name}_card")
            pin = keyring.get_password('LibraryCheckerApp', f"{lib_name}_pin")

            login_url = action_url.split('/search?')[0] + '/account/ozone/sign-in'
            driver.get(login_url)

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
            driver.find_element(By.ID, "username").send_keys(card_number)
            driver.find_element(By.ID, "password").send_keys(pin)

            try:
                close_toast = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#system-toast + button"))
                )
                driver.execute_script("arguments[0].click();", close_toast)
                WebDriverWait(driver, 3).until_not(EC.presence_of_element_located((By.ID, "system-toast")))
            except:
                pass

            signin_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "signin-button")))
            for attempt in range(3):
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", signin_button)
                    WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CLASS_NAME, "signin-button")))
                    signin_button.click()
                    break
                except Exception as click_err:
                    if attempt == 2:
                        raise click_err
                    WebDriverWait(driver, 1).until_not(EC.presence_of_element_located((By.ID, "system-toast")))

            WebDriverWait(driver, 5).until(lambda d: "account" not in d.current_url)
            driver.get(action_url)

            try:
                cookie_banner = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "CookieNoticeBanner_bannerBody__9EoNY"))
                )
                driver.execute_script("arguments[0].remove();", cookie_banner)
            except:
                pass

            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "span")))
            buttons = driver.find_elements(By.TAG_NAME, "span")
            for attempt in range(3):
                try:
                    for btn in buttons:
                        if action_type == "Borrow" and "borrow" in btn.text.lower():
                            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                            btn.click()
                            print(f"Successfully clicked 'Borrow' for {lib_name}")
                            # Notify GUI thread of success
                            QtCore.QMetaObject.invokeMethod(
                                self,
                                "_on_action_success",
                                QtCore.Qt.QueuedConnection,
                                QtCore.Q_ARG(int, row),
                                QtCore.Q_ARG(int, column),
                                QtCore.Q_ARG(str, action_type)
                            )
                            return
                        elif action_type == "Hold" and "place a hold" in btn.text.lower():
                            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                            btn.click()
                            print(f"Successfully clicked 'Place a Hold' for {lib_name}")
                            # Notify GUI thread of success
                            QtCore.QMetaObject.invokeMethod(
                                self,
                                "_on_action_success",
                                QtCore.Qt.QueuedConnection,
                                QtCore.Q_ARG(int, row),
                                QtCore.Q_ARG(int, column),
                                QtCore.Q_ARG(str, action_type)
                            )
                            return
                except Exception as click_err:
                    if attempt == 2:
                        raise click_err
                    WebDriverWait(driver, 2).until_not(
                        EC.presence_of_element_located((By.CLASS_NAME, "CookieNoticeBanner_bannerBody__9EoNY"))
                    )

            print(f"No actionable button found for {action_type} at {lib_name}.")

        except Exception as e:
            print(f"Error during login/action for {lib_name}: {e}")
        finally:
            driver.quit()

    @QtCore.pyqtSlot(int, int, str)
    def _on_action_success(self, row, column, action_type):
        # Show confirmation and update the cell
        if action_type.lower() == "hold":
            QMessageBox.information(self, "Hold Successful!", "Your hold was placed.")
            new_text, new_color = "Hold Placed", QColor("blue")
        else:
            QMessageBox.information(self, "Borrow Successful!", "You’ve successfully borrowed this item.")
            new_text, new_color = "Borrowed", QtCore.Qt.green

        item = self.table.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            self.table.setItem(row, column, item)
        item.setText(new_text)
        item.setBackground(new_color)
        item.setData(QtCore.Qt.UserRole, None)

    def open_preferences(self):
        dialog = PreferencesDialog(self)
        dialog.preferences_saved.connect(self.refresh_libraries)
        dialog.exec_()

    @QtCore.pyqtSlot()
    def refresh_libraries(self):
        self.load_libraries()
        self.update_table_headers()
        QMessageBox.information(self, "Saved", "Preferences updated!")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = LibraryCheckerApp()
    window.show()
    sys.exit(app.exec_())
