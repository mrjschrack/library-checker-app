# libby_search_v5.py
# Automated ISBN checker for OverDrive libraries using Selenium with basic GUI
# Author: [Your Name]
# Version: v6 (GUI prototype)
# Last updated: 2025-03-22

import pandas as pd
import time
import argparse
import re
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox, scrolledtext
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

MAX_MISSES = 3

def clean_isbn(isbn):
    if pd.isna(isbn):
        return None
    return str(isbn).replace('="', '').replace('"', '').strip()

def login_to_overdrive(driver, username, password):
    # Placeholder for future login automation
    # driver.get('https://overdrive-login-url')
    # Add Selenium code here to log the user into OverDrive
    pass

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def build_search_query(title, author):
    clean_title = re.sub(r'[^\w\s]', '', title)
    clean_author = re.sub(r'[^\w\s]', '', author)
    query = f"{clean_title} {clean_author}".replace(" ", "%20")
    return query

def check_library_availability(title, author, library_url, driver):
    query = build_search_query(title, author)
    search_url = f"{library_url}/search?query={query}"
    status = "Unknown"

    for attempt in range(3):
        try:
            driver.get(search_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "span"))
            )
            elements = driver.find_elements(By.TAG_NAME, "span")
            for element in elements:
                text = element.text.lower().strip()
                if "place a hold" in text:
                    return "Place a Hold Available", search_url
                elif "borrow" in text:
                    return "Available to Borrow", search_url
            break
        except Exception:
            time.sleep(2)
            continue
    return status, search_url

def run_search(file_path, output_box, progress_var, status_var, window, libraries):
    progress_var.set(0)
    status_var.set("Running...")
    window.update_idletasks()
    try:
        results_df = pd.read_csv("library_availability_results.csv", encoding="latin1")
    except FileNotFoundError:
        results_df = pd.DataFrame(columns=["Title", "Library", "Status", "URL", "Misses", "Active"])

    df = pd.read_csv(file_path, encoding="latin1")
    df['ISBN13'] = df['ISBN13'].apply(clean_isbn)
    df = df.dropna(subset=['ISBN13'])
    df = df[df['Bookshelves'].str.contains("to-read", na=False, case=False)]

    

    driver = setup_driver()
    total_checks = len(df) * len(libraries)
    progress_step = 100 / total_checks
    start_time = time.time()

    for _, row in df.iterrows():
        title = row['Title']
        author = row['Author']

        for library_name, library_url in libraries.items():
            existing = results_df[(results_df['Title'] == title) & (results_df['Library'] == library_name)]

            status, url = check_library_availability(title, author, library_url, driver)

            if not existing.empty:
                idx = existing.index[0]
                if status == "Unknown":
                    results_df.at[idx, "Misses"] += 1
                    if results_df.at[idx, "Misses"] >= MAX_MISSES:
                        results_df.at[idx, "Active"] = "Inactive"
                else:
                    results_df.at[idx, "Misses"] = 0
                    results_df.at[idx, "Active"] = "Active"
                results_df.at[idx, "Status"] = status
                results_df.at[idx, "URL"] = url
            else:
                results_df = pd.concat([results_df, pd.DataFrame.from_records([{
                    "Title": title,
                    "Library": library_name,
                    "Status": status,
                    "URL": url,
                    "Misses": 0 if status != "Unknown" else 1,
                    "Active": "Active"
                }])], ignore_index=True)

            progress_var.set(progress_var.get() + progress_step)
            window.update_idletasks()

    driver.quit()
    end_time = time.time()

    results_df.to_csv("library_availability_results.csv", index=False)

    total_time = end_time - start_time
    avg_time = total_time / total_checks if total_checks else 0

    status_var.set("Done!")

    # Populate Treeview table
    grouped = results_df.groupby("Title")
    for title, group in grouped:
        row = [title]
        for library in ["Denver Public Library", "Poudre River Public Library District", "Across Colorado Digital Consortium"]:
            entry = group[group['Library'] == library]
            if not entry.empty:
                status = entry.iloc[0]['Status']
                url = entry.iloc[0]['URL']
                row.append(f"{status} ({url})")
            else:
                row.append("Unavailable")
        window.tree.insert("", "end", values=row)
    output_box.insert(tk.END, f"Summary Report\n")
    output_box.insert(tk.END, f"- Total books processed: {len(df)}\n")
    output_box.insert(tk.END, f"- Libraries checked: {len(libraries)}\n")
    output_box.insert(tk.END, f"- Total checks performed: {total_checks}\n")
    output_box.insert(tk.END, f"- Total runtime: {time.strftime('%H:%M:%S', time.gmtime(total_time))}\n")
    output_box.insert(tk.END, f"- Average time per check: {round(avg_time, 2)} seconds\n")

# GUI Setup
def launch_gui():
    window = tk.Tk()
    window.title("Library Availability Checker")
    progress_var = tk.DoubleVar()
    status_var = tk.StringVar()
    status_var.set("Waiting for CSV...")


    tk.Label(window, text="Select Goodreads CSV to search:").pack(pady=5)

    def select_file():
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if filepath:
            import threading
            libraries = {
            "Denver Public Library": "https://denver.overdrive.com",
            "Poudre River Public Library District": "https://poudre.overdrive.com",
            "Across Colorado Digital Consortium": "https://coloradodc.overdrive.com"
        }
        threading.Thread(target=run_search, args=(filepath, output_box, progress_var, status_var, window, libraries)).start()

    tk.Button(window, text="Select CSV and Run", command=select_file).pack(pady=5)

    # Progress bar
    progress_bar = ttk.Progressbar(window, orient='horizontal', length=400, mode='determinate', variable=progress_var)
    progress_bar.pack(pady=5)

    # Status label
    status_label = tk.Label(window, textvariable=status_var)
    status_label.pack(pady=5)

    output_box = scrolledtext.ScrolledText(window, width=60, height=5)

    # Close button
    tk.Button(window, text="Close App", command=window.destroy).pack(pady=5)
    output_box.pack(padx=10, pady=5)

    # Table view
    columns = ("Title", "Denver Public Library", "Poudre River Public Library District", "Across Colorado Digital Consortium")
    tree = ttk.Treeview(window, columns=columns, show='headings', height=15)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150)
    tree.pack(padx=10, pady=10)

    # Add link functionality
    def on_click(event):
        item = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        if item and column != "#1":
            col_index = int(column[1:]) - 1
            url = tree.set(item, column=columns[col_index])
            if url.startswith("http"):
                import webbrowser
                webbrowser.open(url)

    tree.bind("<Button-1>", on_click)

    window.tree = tree

    window.mainloop()

if __name__ == "__main__":
    launch_gui()
