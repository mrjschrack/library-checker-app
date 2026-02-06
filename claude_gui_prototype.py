from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QHeaderView
import sys
import threading  
import json
import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

class LibraryCheckerApp(QtWidgets.QWidget):
    def __init__(self):
        self.csv_path = None
        super().__init__()
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

        # Test mode checkbox
        self.test_mode_layout = QtWidgets.QHBoxLayout()
        self.test_mode_checkbox = QtWidgets.QCheckBox("Test Mode (first 3 books only)")
        self.test_mode_layout.addWidget(self.test_mode_checkbox)
        self.test_mode_layout.addStretch()

        # Table widget
        self.table = QtWidgets.QTableWidget()
        self.table.cellClicked.connect(self.cell_clicked)
        # Dynamically load libraries
        self.libraries = []
        if os.path.exists("user_libraries.json"):
            with open("user_libraries.json") as f:
                self.libraries = json.load(f)
        else:
            # Create sample library config if none exists
            self.libraries = [
                {"name": "Sample Library", "url": "https://sample-library.overdrive.com", "type": "overdrive"}
            ]
            with open("user_libraries.json", "w") as f:
                json.dump(self.libraries, f)

        self.table.setColumnCount(len(self.libraries) + 1)
        self.table.setHorizontalHeaderLabels(['Title'] + [lib['name'] for lib in self.libraries])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Summary Report
        self.summary_box = QtWidgets.QTextEdit()
        self.summary_box.setReadOnly(True)

        # Debug log
        self.debug_label = QtWidgets.QLabel("Debug Log:")
        self.debug_log = QtWidgets.QTextEdit()
        self.debug_log.setReadOnly(True)
        self.debug_log.setMaximumHeight(150)

        # Assemble layout
        main_layout.addLayout(top_button_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(self.test_mode_layout)
        main_layout.addWidget(self.table)
        main_layout.addWidget(self.summary_box)
        main_layout.addWidget(self.debug_label)
        main_layout.addWidget(self.debug_log)

        self.setLayout(main_layout)

    def select_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Goodreads CSV", "", "CSV Files (*.csv)")
        if path:
            self.csv_path = path
            self.status_label.setText(f"Status: Loaded {path}")
            self.log_debug(f"CSV file selected: {path}")

    def run_search(self):
        if not self.csv_path:
            QtWidgets.QMessageBox.warning(self, "No CSV Selected", "Please select a CSV file first.")
            return
        
        if not self.libraries:
            QtWidgets.QMessageBox.warning(self, "No Libraries", "Please configure at least one library in Preferences.")
            return
            
        self.status_label.setText("Status: Running...")
        self.progress_bar.setValue(0)
        self.results = []  # Reset results
        self.log_debug("Starting search...")
        
        # Clear previous results
        self.table.setRowCount(0)
        self.summary_box.clear()
        
        thread = threading.Thread(target=self.scrape_thread)
        thread.daemon = True  # Make thread exit when main thread exits
        thread.start()

    def log_debug(self, message):
        """Add message to debug log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        QtCore.QMetaObject.invokeMethod(self, "append_debug", QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, f"[{timestamp}] {message}"))

    @QtCore.pyqtSlot(str)
    def append_debug(self, message):
        """Append message to debug log (called from any thread)"""
        self.debug_log.append(message)
        # Scroll to bottom
        scrollbar = self.debug_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def scrape_thread(self):
        try:
            # Import necessary libraries
            self.log_debug("Loading CSV data...")
            
            # Load the CSV data
            df = pd.read_csv(self.csv_path)
            # Filter for 'to-read' books
            filtered_df = df[df['Bookshelves'].str.contains("to-read", na=False, case=False)]
            
            if filtered_df.empty:
                QtCore.QMetaObject.invokeMethod(self, "show_error", QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(str, "No 'to-read' books found in CSV"))
                return
                
            self.log_debug(f"Found {len(filtered_df)} to-read books")
            
            # Get titles and authors
            if self.test_mode_checkbox.isChecked():
                titles = filtered_df[['Title', 'Author']].head(3)
                self.log_debug("Test mode: using first 3 books only")
            else:
                titles = filtered_df[['Title', 'Author']]
            
            # Setup Selenium
            self.log_debug("Setting up Chrome driver...")
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.set_page_load_timeout(30)  # Set a 30 second timeout for page loads
            
            total = len(titles)
            self.log_debug(f"Beginning search for {total} books across {len(self.libraries)} libraries")
            
            # Process each book
            for idx, row in enumerate(titles.itertuples()):
                title = row.Title
                author = row.Author
                self.log_debug(f"Processing book {idx+1}/{total}: {title} by {author}")
                
                # Process each library for this book
                for lib in self.libraries:
                    lib_name = lib['name']
                    lib_url = lib['url']
                    lib_type = lib.get('type', 'overdrive')  # Default to overdrive
                    
                    # Construct search URL - remove any double slashes in the path
                    query = f"{title} {author}".replace(" ", "+")
                    if lib_url.endswith('/'):
                        lib_search_url = f"{lib_url}search?query={query}"
                    else:
                        lib_search_url = f"{lib_url}/search?query={query}"
                    
                    self.log_debug(f"  Checking {lib_name}: {lib_search_url}")
                    
                    try:
                        # Navigate to the library search page
                        driver.get(lib_search_url)
                        
                        # Wait for page to load (max 10 seconds)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        
                        # Take screenshot for debugging (optional)
                        # driver.save_screenshot(f"search_{idx}_{lib_name.replace(' ', '_')}.png")
                        
                        # Check if "No results found" is present
                        if any(text in driver.page_source for text in 
                              ["No results found", "didn't match any titles", "0 results"]):
                            self.log_debug(f"  No results found")
                            status = "Not Found"
                        else:
                            # Check availability based on library type
                            if lib_type == 'overdrive':
                                status = self.check_overdrive_availability(driver, title, author)
                            else:
                                # Generic check as fallback
                                status = self.check_generic_availability(driver)
                        
                        self.log_debug(f"  Status: {status}")
                        
                    except TimeoutException:
                        self.log_debug("  Error: Page load timed out")
                        status = "Error"
                    except Exception as e:
                        error_msg = str(e)
                        self.log_debug(f"  Error: {error_msg}")
                        status = "Error"
                        
                    # Save result with the correct library name
                    self.results.append((title, author, lib_name, status, lib_search_url))
                
                # Update progress after processing all libraries for this book
                progress_value = int((idx + 1) / total * 100)
                QtCore.QMetaObject.invokeMethod(self, "update_progress", QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(int, progress_value),
                    QtCore.Q_ARG(str, f"Processing: {title}"))
            
            driver.quit()
            self.log_debug("Chrome driver shut down")
            
            QtCore.QMetaObject.invokeMethod(self, "scrape_done", QtCore.Qt.QueuedConnection)
            
        except Exception as e:
            error_msg = f"Error in scraping thread: {str(e)}"
            self.log_debug(error_msg)
            QtCore.QMetaObject.invokeMethod(self, "show_error", QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, error_msg))

    def check_overdrive_availability(self, driver, title, author):
        """Check availability specifically for Overdrive library websites"""
        try:
            # First, check if we have search results
            try:
                # Look for title elements that might contain our book
                title_elements = driver.find_elements(By.CSS_SELECTOR, ".title-element, .title-container, h3.title")
                
                if not title_elements:
                    self.log_debug("  No title elements found")
                    return "Not Found"
                
                # Check if any of the titles match our search
                title_lower = title.lower()
                author_lower = author.lower()
                book_found = False
                
                for element in title_elements:
                    element_text = element.text.lower()
                    # Check if title is similar enough
                    if title_lower in element_text or any(word in element_text for word in title_lower.split() if len(word) > 3):
                        book_found = True
                        self.log_debug(f"  Found matching title: {element.text}")
                        break
                
                if not book_found:
                    self.log_debug("  Book not found in search results")
                    return "Not Found"
                
                # Now check availability
                # Look for availability badges or text
                availability_elements = driver.find_elements(By.CSS_SELECTOR, 
                    ".badge-available, .availability-badge, .availabilityButton")
                
                if availability_elements:
                    for avail_elem in availability_elements:
                        avail_text = avail_elem.text.lower()
                        
                        # Take a screenshot of the availability element for debugging
                        # avail_elem.screenshot(f"avail_{title.replace(' ', '_')[:20]}.png")
                        
                        if any(text in avail_text for text in ["available", "borrow", "check out"]):
                            return "Available"
                        elif any(text in avail_text for text in ["wait list", "place hold", "unavailable"]):
                            return "Hold"
                
                # If we couldn't find specific availability badges, try to look at the page text
                page_text = driver.page_source.lower()
                
                # Check for common availability patterns in Overdrive
                if "copies available" in page_text:
                    return "Available"
                elif "people waiting" in page_text or "wait list" in page_text:
                    return "Hold"
                
                # If we got here, we found the book but couldn't determine availability
                return "Unknown"
                
            except NoSuchElementException:
                self.log_debug("  Could not find elements on page")
                return "Not Found"
                
        except Exception as e:
            self.log_debug(f"  Error in availability check: {str(e)}")
            return "Error"

    def check_generic_availability(self, driver):
        """Generic availability check for non-Overdrive libraries"""
        page_text = driver.page_source.lower()
        
        if any(word in page_text for word in ["currently available", "check out now", "borrow now"]):
            return "Available"
        elif any(word in page_text for word in ["place a hold", "join waitlist", "waiting list"]):
            return "Hold"
        elif "no copies available" in page_text:
            return "Unavailable"
        elif any(text in page_text for text in ["no results", "no titles found", "0 results"]):
            return "Not Found"
        else:
            return "Unknown"

    @QtCore.pyqtSlot(str)
    def show_error(self, message):
        QtWidgets.QMessageBox.critical(self, "Error", message)
        self.status_label.setText(f"Status: Error - {message}")

    @QtCore.pyqtSlot(int, str)
    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.status_label.setText(f"Status: {text}")

    @QtCore.pyqtSlot()
    def scrape_done(self):
        color_map = {
            'Available': QtCore.Qt.green, 
            'Hold': QtCore.Qt.yellow, 
            'Unavailable': QtCore.Qt.lightGray,
            'Not Found': QtCore.Qt.white,
            'Unknown': QtCore.Qt.cyan,
            'Error': QtCore.Qt.red
        }
        
        # Get unique books (title, author pairs)
        unique_books = set([(r[0], r[1]) for r in self.results])
        self.table.setRowCount(len(unique_books))
        
        # Group results by book
        grouped = {}
        for title, author, lib_name, status, url in self.results:
            book_key = (title, author)
            if book_key not in grouped:
                grouped[book_key] = {}
            grouped[book_key][lib_name] = (status, url)
        
        # Fill the table
        for i, ((title, author), lib_data) in enumerate(grouped.items()):
            title_item = QTableWidgetItem(f"{title} ({author})")
            self.table.setItem(i, 0, title_item)
            
            # Fill in library columns
            for col_idx, lib in enumerate(self.libraries):
                lib_name = lib['name']
                if lib_name in lib_data:
                    status, url = lib_data[lib_name]
                    item = QTableWidgetItem(status)
                    item.setBackground(color_map.get(status, QtCore.Qt.lightGray))
                    item.setData(QtCore.Qt.UserRole, url)
                else:
                    item = QTableWidgetItem("Not checked")
                    item.setBackground(QtCore.Qt.white)
                
                self.table.setItem(i, col_idx + 1, item)
        
        # Generate summary
        avail_count = sum(1 for _, _, _, status, _ in self.results if status == 'Available')
        hold_count = sum(1 for _, _, _, status, _ in self.results if status == 'Hold')
        unavail_count = sum(1 for _, _, _, status, _ in self.results if status == 'Unavailable')
        not_found_count = sum(1 for _, _, _, status, _ in self.results if status == 'Not Found')
        unknown_count = sum(1 for _, _, _, status, _ in self.results if status == 'Unknown')
        error_count = sum(1 for _, _, _, status, _ in self.results if status == 'Error')
        
        summary_text = f"""Summary Report:
- Books searched: {len(unique_books)}
- Libraries checked: {len(self.libraries)}
- Available items: {avail_count}
- On hold: {hold_count}
- Unavailable: {unavail_count}
- Not found: {not_found_count}
- Unknown status: {unknown_count}
- Errors: {error_count}

Search complete. Click on any result cell to open the book's page at that library.

Color Legend:
- Green: Available
- Yellow: Hold
- Gray: Unavailable 
- White: Not Found
- Cyan: Unknown status
- Red: Error"""
        
        self.summary_box.setText(summary_text)
        self.status_label.setText("Status: Done!")
        self.log_debug("Search complete")

    def cell_clicked(self, row, column):
        if column > 0:  # Not the title column
            item = self.table.item(row, column)
            if item and item.data(QtCore.Qt.UserRole):
                url = item.data(QtCore.Qt.UserRole)
                self.log_debug(f"Opening URL: {url}")
                import webbrowser
                webbrowser.open(url)

    def open_preferences(self):
        dialog = PreferencesDialog(self)
        if dialog.exec_():
            # Reload libraries after preferences are updated
            if os.path.exists("user_libraries.json"):
                with open("user_libraries.json") as f:
                    self.libraries = json.load(f)
                
                # Update table columns
                self.table.setColumnCount(len(self.libraries) + 1)
                self.table.setHorizontalHeaderLabels(['Title'] + [lib['name'] for lib in self.libraries])
                self.log_debug("Libraries updated from preferences")

class PreferencesDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(500, 400)
        
        layout = QtWidgets.QVBoxLayout()
        
        # Library management section
        library_group = QtWidgets.QGroupBox("Your Libraries")
        library_layout = QtWidgets.QVBoxLayout()
        
        # Library list
        self.library_list = QtWidgets.QListWidget()
        self.load_libraries()
        
        # Library buttons
        lib_button_layout = QtWidgets.QHBoxLayout()
        self.add_lib_btn = QtWidgets.QPushButton("Add Library")
        self.edit_lib_btn = QtWidgets.QPushButton("Edit")
        self.remove_lib_btn = QtWidgets.QPushButton("Remove")
        
        self.add_lib_btn.clicked.connect(self.add_library)
        self.edit_lib_btn.clicked.connect(self.edit_library)
        self.remove_lib_btn.clicked.connect(self.remove_library)
        
        lib_button_layout.addWidget(self.add_lib_btn)
        lib_button_layout.addWidget(self.edit_lib_btn)
        lib_button_layout.addWidget(self.remove_lib_btn)
        
        library_layout.addWidget(self.library_list)
        library_layout.addLayout(lib_button_layout)
        library_group.setLayout(library_layout)
        
        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Help text
        help_text = QtWidgets.QLabel(
            "Add your libraries and their search URLs. The URL should be the base URL of your library's website.\n"
            "Example: https://mylibrary.overdrive.com (do not include /search)"
        )
        help_text.setWordWrap(True)
        
        # Layout assembly
        layout.addWidget(help_text)
        layout.addWidget(library_group)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_libraries(self):
        self.libraries = []
        if os.path.exists("user_libraries.json"):
            with open("user_libraries.json") as f:
                self.libraries = json.load(f)
        
        self.library_list.clear()
        for lib in self.libraries:
            lib_type = lib.get('type', 'overdrive')
            self.library_list.addItem(f"{lib['name']} - {lib['url']} ({lib_type})")
    
    def save_libraries(self):
        with open("user_libraries.json", "w") as f:
            json.dump(self.libraries, f)
    
    def add_library(self):
        name, ok1 = QtWidgets.QInputDialog.getText(
            self, "Add Library", "Library Name:"
        )
        if ok1 and name:
            url, ok2 = QtWidgets.QInputDialog.getText(
                self, "Add Library", "Library URL (e.g., https://library.com):"
            )
            if ok2 and url:
                # Ensure URL doesn't end with /search
                if url.endswith('/search'):
                    url = url[:-7]
                
                # Ask for library type
                lib_type, ok3 = QtWidgets.QInputDialog.getItem(
                    self, "Add Library", "Library Type:", 
                    ["overdrive", "other"], 0, False
                )
                
                if ok3:
                    self.libraries.append({
                        "name": name, 
                        "url": url, 
                        "type": lib_type
                    })
                    self.save_libraries()
                    self.load_libraries()
    
    def edit_library(self):
        current = self.library_list.currentRow()
        if current >= 0:
            lib = self.libraries[current]
            name, ok1 = QtWidgets.QInputDialog.getText(
                self, "Edit Library", "Library Name:", text=lib["name"]
            )
            if ok1 and name:
                url, ok2 = QtWidgets.QInputDialog.getText(
                    self, "Edit Library", "Library URL:", text=lib["url"]
                )
                if ok2 and url:
                    # Ensure URL doesn't end with /search
                    if url.endswith('/search'):
                        url = url[:-7]
                    
                    # Ask for library type
                    lib_type, ok3 = QtWidgets.QInputDialog.getItem(
                        self, "Edit Library", "Library Type:", 
                        ["overdrive", "other"], 
                        0 if lib.get('type', 'overdrive') == 'overdrive' else 1, 
                        False
                    )
                    
                    if ok3:
                        self.libraries[current] = {
                            "name": name, 
                            "url": url, 
                            "type": lib_type
                        }
                        self.save_libraries()
                        self.load_libraries()
    
    def remove_library(self):
        current = self.library_list.currentRow()
        if current >= 0:
            reply = QtWidgets.QMessageBox.question(
                self, "Remove Library",
                f"Are you sure you want to remove {self.libraries[current]['name']}?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                del self.libraries[current]
                self.save_libraries()
                self.load_libraries()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = LibraryCheckerApp()
    window.show()
    sys.exit(app.exec_())