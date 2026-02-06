import json
import keyring
from PyQt5 import QtWidgets, QtCore

class PreferencesDialog(QtWidgets.QDialog):
    preferences_saved = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences / Account Settings")
        self.setMinimumSize(500, 400)
        self.library_table = QtWidgets.QTableWidget(0, 3)
        self.library_table.setHorizontalHeaderLabels(["Library Name", "Edit", "Delete"])
        self.library_table.horizontalHeader().setStretchLastSection(True)
        self.current_edit_row = None

        self.library_name_input = QtWidgets.QLineEdit()
        self.library_url_input = QtWidgets.QLineEdit()
        self.username_input = QtWidgets.QLineEdit()
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.email_input = QtWidgets.QLineEdit()

        self.edit_section_container = QtWidgets.QGroupBox("Library Details")
        self.edit_section_container.setVisible(False)
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Library Name:", self.library_name_input)
        form_layout.addRow("Library OverDrive URL:", self.library_url_input)
        form_layout.addRow("Card Number:", self.username_input)
        form_layout.addRow("PIN:", self.password_input)
        form_layout.addRow("Email Address:", self.email_input)
        self.edit_section_container.setLayout(form_layout)

        add_button = QtWidgets.QPushButton("+ Add New Library")
        add_button.clicked.connect(self.add_library)

        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.clicked.connect(self.save_and_accept)
        cancel_button = QtWidgets.QPushButton("Exit")
        cancel_button.clicked.connect(self.reject)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.save_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Libraries List:"))
        layout.addWidget(self.library_table)
        layout.addWidget(add_button)
        layout.addWidget(self.edit_section_container)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.load_libraries()

    def save_and_accept(self):
        row_to_update = None
        if hasattr(self, 'current_edit_row') and self.current_edit_row is not None:
            row_to_update = self.current_edit_row
        if row_to_update is None:
            for row in range(self.library_table.rowCount()):
                if self.library_table.item(row, 0) and self.library_table.item(row, 0).isSelected():
                    row_to_update = row
                    break

        if row_to_update is not None:
            lib_name_key = self.library_name_input.text()
            item_data = {
                'url': self.library_url_input.text(),
                'username': self.username_input.text(),
                'password': self.password_input.text(),
                'email': self.email_input.text(),
            }
            keyring.set_password('LibraryCheckerApp', f'{lib_name_key}_card', self.username_input.text())
            keyring.set_password('LibraryCheckerApp', f'{lib_name_key}_pin', self.password_input.text())
            keyring.set_password('LibraryCheckerApp', f'{lib_name_key}_email', self.email_input.text())
            self.library_table.item(row_to_update, 0).setText(lib_name_key)
            self.library_table.item(row_to_update, 0).setData(QtCore.Qt.UserRole, item_data)
            self.current_edit_row = None

        self.save_libraries()
        self.preferences_saved.emit()
        QtWidgets.QMessageBox.information(self, "Saved", "Library entry updated successfully!")

    def save_libraries(self):
        libraries = []
        for row in range(self.library_table.rowCount()):
            lib_name = self.library_table.item(row, 0).text()
            item_data = self.library_table.item(row, 0).data(QtCore.Qt.UserRole)
            if not item_data:
                item_data = {'url': '', 'username': '', 'password': '', 'email': ''}
            libraries.append({
                'name': lib_name,
                'url': item_data.get('url', ''),
                'username': item_data.get('username', ''),
                'password': item_data.get('password', ''),
                'email': item_data.get('email', '')
            })

        with open("user_libraries.json", "w") as f:
            json.dump(libraries, f, indent=4)

    def edit_library(self, row):
        current_name = self.library_table.item(row, 0).text()
        self.library_name_input.setText(current_name)
        item_data = self.library_table.item(row, 0).data(QtCore.Qt.UserRole)
        if item_data:
            self.library_url_input.setText(item_data.get('url', ''))
            self.username_input.setText(item_data.get('username', ''))
            self.password_input.setText(item_data.get('password', ''))
            email = keyring.get_password('LibraryCheckerApp', f"{current_name}_email") or item_data.get('email', '')
            self.email_input.setText(email)
        else:
            self.library_url_input.setText("")
            self.username_input.setText("")
            self.password_input.setText("")
            self.email_input.setText("")

        self.current_edit_row = row
        self.edit_section_container.show()

    def delete_library(self, row):
        self.library_table.removeRow(row)

    def add_library(self):
        self.current_edit_row = None
        row = self.library_table.rowCount()
        self.library_table.insertRow(row)
        name_item = QtWidgets.QTableWidgetItem("")
        self.library_table.setItem(row, 0, name_item)

        edit_btn = QtWidgets.QPushButton("Edit")
        delete_btn = QtWidgets.QPushButton("Delete")
        edit_btn.clicked.connect(lambda checked, r=row: self.edit_library(r))
        delete_btn.clicked.connect(lambda checked, r=row: self.delete_library(r))

        self.library_table.setCellWidget(row, 1, edit_btn)
        self.library_table.setCellWidget(row, 2, delete_btn)

        self.library_name_input.setText("")
        self.library_url_input.setText("")
        self.username_input.setText("")
        self.password_input.setText("")
        self.email_input.setText("")
        self.current_edit_row = row
        self.edit_section_container.show()

    def load_libraries(self):
        try:
            with open("user_libraries.json") as f:
                user_libraries = json.load(f)
        except Exception:
            user_libraries = []

        self.library_table.setRowCount(0)
        for lib in user_libraries:
            row = self.library_table.rowCount()
            self.library_table.insertRow(row)
            name_item = QtWidgets.QTableWidgetItem(lib['name'])
            name_item.setData(QtCore.Qt.UserRole, {
                'url': lib.get('url', ''),
                'username': lib.get('username', ''),
                'password': lib.get('password', ''),
                'email': lib.get('email', '')
            })
            self.library_table.setItem(row, 0, name_item)

            edit_btn = QtWidgets.QPushButton("Edit")
            delete_btn = QtWidgets.QPushButton("Delete")
            edit_btn.clicked.connect(lambda checked, r=row: self.edit_library(r))
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_library(r))

            self.library_table.setCellWidget(row, 1, edit_btn)
            self.library_table.setCellWidget(row, 2, delete_btn)
