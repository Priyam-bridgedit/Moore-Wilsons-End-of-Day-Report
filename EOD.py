import io
import threading
import tkinter as tk
from tkinter import messagebox
import pandas as pd
import pyodbc
from tkinter import filedialog
from configparser import ConfigParser
from tkinter import ttk
from tkcalendar import DateEntry  # Make sure to install this library
# import schedule
# import time
# import smtplib
from email.mime.multipart import MIMEMultipart
from io import BytesIO
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import date, datetime, timedelta
import re
from datetime import datetime, timedelta
from queue import Queue
import time
import tkinter as tk
from tkinter import ttk, filedialog
from io import StringIO
import base64
import smtplib
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showerror
from tkcalendar import DateEntry
from configparser import ConfigParser
from datetime import datetime, timedelta
import pyodbc
import pandas as pd
import base64
from tkinter import filedialog
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
from tkinter import font as tkFont
from collections import defaultdict
import tkinter.filedialog
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.units import inch
from reportlab.platypus.flowables import Spacer, PageBreak
from reportlab.lib.units import inch

def on_enter(event):
    """Handles mouse hover over the button."""
    if not getattr(event.widget, "clicked", False):  # Check if button wasn't clicked
        event.widget.configure(bg="lightgrey")  # or whatever your hover color is

def on_leave(event):
    """Handles mouse exit from the button."""
    if not getattr(event.widget, "clicked", False):  # Check if button wasn't clicked
        event.widget.configure(bg='#e6f2ff')


server_entry = None
database_entry = None
username_entry = None
password_entry = None
smtp_server_entry = None
smtp_username_entry = None
smtp_password_entry = None
smtp_from_entry = None
to_email_entry = None
time_entry = None
current_dynamic_content = None
global_lane_data = {}
global_summary_data = []
current_selected_station = None

STATIC_LANES = {
    '1': list(range(1, 27)),  # 1 to 26
    '2': list(range(1, 10)) + [101],
    '3': list(range(1, 5)),
    '4': list(range(1, 9))
}
# Define config globally
config = ConfigParser()
# Function to save both SQL Server and SMTP details to config.ini file
def save_config(config_window):
    config["DATABASE"] = {
        "server": base64.b64encode(server_entry.get().encode()).decode(),
        "database": base64.b64encode(database_entry.get().encode()).decode(),
        "username": base64.b64encode(username_entry.get().encode()).decode(),
        "password": base64.b64encode(password_entry.get().encode()).decode(),
    }

    # config["SMTP"] = {
    #     "server": base64.b64encode(smtp_server_entry.get().encode()).decode(),
    #     "username": base64.b64encode(smtp_username_entry.get().encode()).decode(),
    #     "password": base64.b64encode(smtp_password_entry.get().encode()).decode(),
    #     "from": base64.b64encode(smtp_from_entry.get().encode()).decode(),
    #     "to": base64.b64encode(to_email_entry.get().encode()).decode(),
    #     "time": time_entry.get(),
    # }

    with open("config.ini", "w") as configfile:
        config.write(configfile)

    # status_label.config(text="Configuration saved successfully!", fg="green")
    config_window.destroy()


# Function to schedule the report generation and email sending
time_format = re.compile("^([0-1]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$")

# Create a queue for status updates
status_queue = Queue()

# Define window as a global variable
window = None

STATIC_LANES = {
    'Moore Wilsons Wellington': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26],
    'Moore Wilsons Porirua': [1, 2, 3, 4, 5, 6, 7, 8, 9, 101],
    'Moore Wilsons Lower Hutt': [1, 2, 3, 4],
    'Moore Wilsons Masterton': [1, 2, 3, 4, 5, 6, 7, 8]
}

# Function to generate the report

def populate_treeview(tree, dataframe):
    for row in tree.get_children():
        tree.delete(row)
    for index, row in dataframe.iterrows():
        tree.insert("", "end", values=list(row))

def save_data_to_db(updated_data, start_date_time_str, end_date_time_str, selected_branch, station):
    try:
        # Reading configuration and decoding server, username, and password
        config = ConfigParser()
        config.read("config.ini")
        server = base64.b64decode(config.get("DATABASE", "server").encode()).decode()
        username = base64.b64decode(config.get("DATABASE", "username").encode()).decode()
        password = base64.b64decode(config.get("DATABASE", "password").encode()).decode()

        # Creating connection strings based on the availability of username and password
        if username and password:
            connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE=MW_EOD;UID={username};PWD={password}"
        else:
            connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE=MW_EOD;Trusted_Connection=yes"
        
        # Connect to the SQL Server
        connection = pyodbc.connect(connection_string, autocommit=True)
        cursor = connection.cursor()

        # Check if MW_EOD database exists, if not, create it
        cursor.execute("SELECT name FROM sys.databases WHERE name = 'MW_EOD'")
        result = cursor.fetchone()
        if not result:
            cursor.execute("CREATE DATABASE MW_EOD")
            connection.commit()

        # Always make sure you're in the right DB context after potentially creating it
        cursor.execute("USE MW_EOD")
        
        # Create the UpdatedTransHeaders table if it doesn't exist
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'UpdatedTransHeaders') 
        BEGIN 
            CREATE TABLE dbo.UpdatedTransHeaders (Branch VARCHAR(255), Station VARCHAR(255), PaymentMethod VARCHAR(255), ActualAmount FLOAT, ReportedAmount FLOAT, TotalVariance FLOAT, ProcessingDate DATETIME) 
        END
        """)
        
        # Insert or update data into the table
        for index, row in updated_data.iterrows():
            if row["PaymentMethod"] != "Total":  # Exclude Total from the database
                total_variance = row["ReportedAmount"] - row["ActualAmount"]  # Calculate TotalVariance
                cursor.execute("""
                MERGE INTO UpdatedTransHeaders AS target
                USING (VALUES (?, ?, ?, ?, ?, ?, ?)) AS source (Branch, Station, PaymentMethod, ActualAmount, ReportedAmount, TotalVariance, ProcessingDate)
                ON target.ProcessingDate = ? AND target.PaymentMethod = ? AND target.Branch = ? AND target.Station = ?
                WHEN MATCHED AND (target.ReportedAmount != source.ReportedAmount OR target.TotalVariance != source.TotalVariance) THEN 
                    UPDATE SET ReportedAmount = source.ReportedAmount, TotalVariance = source.TotalVariance
                WHEN NOT MATCHED THEN
                    INSERT (Branch, Station, PaymentMethod, ActualAmount, ReportedAmount, TotalVariance, ProcessingDate) 
                    VALUES (source.Branch, source.Station, source.PaymentMethod, source.ActualAmount, source.ReportedAmount, source.TotalVariance, source.ProcessingDate);
                """, selected_branch, station, row["PaymentMethod"], row["ActualAmount"], row["ReportedAmount"], total_variance, start_date_time_str, start_date_time_str, row["PaymentMethod"], selected_branch, station)
        connection.commit()

        # Create the Lanes table if it doesn't exist
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Lanes') 
        BEGIN 
            CREATE TABLE dbo.Lanes (Branch VARCHAR(255), Lane VARCHAR(255), PRIMARY KEY (Branch, Lane)) 
        END
        """)

        # Insert or update static lanes into the Lanes table
        for branch, lanes in STATIC_LANES.items():
            for lane in lanes:
                cursor.execute("""
                MERGE INTO Lanes AS target
                USING (VALUES (?, ?)) AS source (Branch, Lane)
                ON target.Branch = source.Branch AND target.Lane = source.Lane
                WHEN NOT MATCHED THEN
                    INSERT (Branch, Lane) 
                    VALUES (source.Branch, source.Lane);
                """, branch, str(lane))
        connection.commit()

        # Close the cursor and the connection
        cursor.close()
        connection.close()

    except Exception as e:
        showerror(title="Error", message=f"An error occurred: {e}")



# New function to get lanes from the 'Lanes' table
def fetch_lanes_from_db(branch):
    try:
        # Reading configuration and decoding server, username, and password
        config = ConfigParser()
        config.read("config.ini")
        server = base64.b64decode(config.get("DATABASE", "server").encode()).decode()
        username = base64.b64decode(config.get("DATABASE", "username").encode()).decode()
        password = base64.b64decode(config.get("DATABASE", "password").encode()).decode()

        # Creating connection strings based on the availability of username and password
        if username and password:
            connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE=master;UID={username};PWD={password}"
            connection_string_new_db = f"DRIVER={{SQL Server}};SERVER={server};DATABASE=MW_EOD;UID={username};PWD={password}"
        else:
            connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE=master;Trusted_Connection=yes"
            connection_string_new_db = f"DRIVER={{SQL Server}};SERVER={server};DATABASE=MW_EOD;Trusted_Connection=yes"
        
        # Connect to the SQL Server
        connection = pyodbc.connect(connection_string, autocommit=True)
        cursor = connection.cursor()

        # Check if MW_New database exists
        cursor.execute("SELECT name FROM sys.databases WHERE name = 'MW_EOD'")
        result = cursor.fetchone()

        # If MW_New doesn't exist, create it and commit
        if not result:
            cursor.execute("CREATE DATABASE MW_EOD")
            connection.commit()

        # Close initial connection and cursor
        cursor.close()
        connection.close()

        # Add a delay to ensure database operations complete before proceeding
        time.sleep(1)

        # Now, let's operate within the MW_New database
        connection_new_db = pyodbc.connect(connection_string_new_db)
        cursor_new_db = connection_new_db.cursor()

        # Fetch lanes based on branch
        cursor_new_db.execute("SELECT Lane FROM Lanes WHERE Branch = ?", branch)
        lanes = [row.Lane for row in cursor_new_db.fetchall()]

        cursor_new_db.close()
        connection_new_db.close()
        
        return lanes

    except Exception as e:
        showerror(title="Error", message=f"An error occurred: {e}")
        return []



def display_and_edit_data(dataframe, start_date_time_str, end_date_time_str, selected_branch, station):

    if dataframe is None or dataframe.empty:
        showerror(title="Error", message="No data available to display.")
        return
    display_offset = 6  # This is just an example, you can adjust the number as per your requirement.

    # Fetching selected branch and station directly from the GUI
    selected_branch = branch_dropdown.get()
    selected_station = station

    def format_value(value):
        """Format the value to have 2 decimal places and prepend it with $"""
        return "$ " + f"{value:,.2f}"
    
   
    def clear_widgets():
        for widget in current_dynamic_content.winfo_children():
            widget.destroy()

    
    def show_summary():
        global global_summary_data
        # Step 1: Collect Data Before Destroying Widgets
        summary_data = defaultdict(lambda: {"ActualAmount": 0, "ReportedAmount": 0, "TotalVariance": 0})
        for row_entries in entries:
            payment_method = row_entries[0].get()
            actual_amt = float(row_entries[1].get().replace("$", "").replace(",", "") or 0.0)
            reported_amt = float(row_entries[2].get().replace("$", "").replace(",", "") or 0.0)
            variance = float(row_entries[3].get().replace("$", "").replace(",", "") or 0.0)
            summary_data[payment_method]["ActualAmount"] += actual_amt
            summary_data[payment_method]["ReportedAmount"] += reported_amt
            summary_data[payment_method]["TotalVariance"] += variance

        # Step 2: Now Clear the Widgets
        clear_widgets()

        # Styling configurations
        header_bg = "#4E4E50"  # Dark Gray
        header_fg = "#FFFFFF"  # White
        header_font = ("Arial", 14, "bold")
        content_font = ("Arial", 12)
        padding = 10

        # Create a frame for summary data for better visual structuring
        summary_frame = tk.Frame(current_dynamic_content, bg='#c0e7f0')  # Light Gray background for the frame
        summary_frame.pack(pady=0, padx=20, fill=tk.BOTH, expand=True)

        # Create new summary header
        header_titles = ["PaymentMethod", "ActualAmount", "ReportedAmount", "TotalVariance"]
        for col, title in enumerate(header_titles):
            label = tk.Label(summary_frame, text=title, font=header_font, bg=header_bg, fg=header_fg, padx=padding, pady=padding)
            label.grid(row=0, column=col, sticky="nsew")
            summary_frame.columnconfigure(col, weight=1)  # To make columns stretchable

        # Display the summary data
        for idx, (payment_method, values) in enumerate(summary_data.items()):
            tk.Label(summary_frame, text=payment_method, font=content_font, bg='#c0e7f0', padx=padding, pady=padding).grid(row=idx + 1, column=0, sticky="w")
            tk.Label(summary_frame, text=format_currency(values["ActualAmount"]), font=content_font, bg='#c0e7f0', padx=padding, pady=padding).grid(row=idx + 1, column=1, sticky="w")
            tk.Label(summary_frame, text=format_currency(values["ReportedAmount"]), font=content_font, bg='#c0e7f0', padx=padding, pady=padding).grid(row=idx + 1, column=2, sticky="w")
            tk.Label(summary_frame, text=format_currency(values["TotalVariance"]), font=content_font, bg='#c0e7f0', padx=padding, pady=padding).grid(row=idx + 1, column=3, sticky="w")

        # Adjusting the weight of the rows to make them stretchable
        for idx in range(len(summary_data) + 1):
            summary_frame.rowconfigure(idx, weight=1)

        global_summary_data = summary_data
        print(global_summary_data)

        save1_button = tk.Button(summary_frame, text="Save to PDF", command=save_to_pdf, bg=SAVE_BUTTON_COLOR, fg="white", font=("Arial", 10, "bold"), padx=10, pady=5)
        save1_button.grid(row=len(summary_data) + 2, columnspan=len(header_titles), pady=10)




    # Create original headers and store references in a list
    headers_labels = []
    for col, header in enumerate(dataframe.columns):
        label = tk.Label(current_dynamic_content, text=header, font=("Arial", 12, "bold"), padx=10, pady=5)
        label.grid(row=display_offset, column=col, sticky="w")
        headers_labels.append(label)

    # List to hold the widgets for display and edit data
    edit_widgets = []

    def save_changes():
        updated_data = []

        # 1. Build updated_data from user input
        for row in range(len(dataframe)):
            record = {}

            for col, column_name in enumerate(["PaymentMethod", "ActualAmount", "ReportedAmount"]):
                value = entries[row][col].get().replace("$", "").replace(",", "").strip()

                if not value and column_name == "ReportedAmount" and dataframe.iloc[row]["PaymentMethod"] != "Total":
                    value = dataframe.iloc[row][column_name]

                if column_name != "PaymentMethod":
                    value = float(value or 0.0)
                
                record[column_name] = value

            # Compute the TotalVariance for each record
            record["TotalVariance"] = record["ReportedAmount"] - record["ActualAmount"]
            updated_data.append(record)

        # Convert updated_data to DataFrame
        updated_df = pd.DataFrame(updated_data)

        # Calculate totals for ActualAmount and ReportedAmount
        total_actual = dataframe["ActualAmount"].sum() / 2  # Dividing by 2 to make it half.

        total_reported_list = []
        for idx, entry in enumerate(entries):
            reported_value = float(entry[2].get().replace("$", "").replace(",", "") or dataframe.iloc[idx]["ReportedAmount"])
            if dataframe.iloc[idx]["PaymentMethod"] != "Total":
                print(f"Adding ReportedAmount from Row {idx}: {reported_value}")
                total_reported_list.append(reported_value)

        total_reported = sum(total_reported_list)

        print(f"Total Actual Amount: {total_actual}")
        print(f"Total Reported Amount: {total_reported}")

        # Calculate the total variance
        total_variance = total_reported - total_actual

        # Check if a "Total" row already exists in the dataframe
        total_row_idx = updated_df[updated_df["PaymentMethod"] == "Total"].index

        if total_row_idx.empty:
            # Append a "Total" row if it doesn't exist
            updated_df.loc[len(updated_df)] = ["Total", total_actual, total_reported, total_variance]
        else:
            # Update the "Total" row if it exists
            updated_df.at[total_row_idx[0], "ActualAmount"] = total_actual
            updated_df.at[total_row_idx[0], "ReportedAmount"] = total_reported
            updated_df.at[total_row_idx[0], "TotalVariance"] = total_variance

        # Save to the database
        save_data_to_db(updated_df, start_date_time_str, end_date_time_str, branch_value, station)

        # Now update the GUI to display the changes
        for row in range(min(len(updated_df), len(entries))):
            actual_amount = updated_df.iloc[row]["ActualAmount"]
            reported_amount = updated_df.iloc[row]["ReportedAmount"]
            row_variance = updated_df.iloc[row]["TotalVariance"]

            # Update the ActualAmount
            entries[row][1].delete(0, tk.END)
            entries[row][1].insert(0, format_value(actual_amount))

            # Update the ReportedAmount
            entries[row][2].delete(0, tk.END)
            entries[row][2].insert(0, format_value(reported_amount))

            # Update the TotalVariance
            entries[row][3].config(state='normal')  # Ensure the entry is editable before inserting a new value
            entries[row][3].delete(0, tk.END)
            entries[row][3].insert(0, format_value(row_variance))  # Use the row-specific variance
            entries[row][3].config(state='disabled')  # Disable the entry again after updating the value
            
            print(f"Row {row} - TotalVariance Calculated: {row_variance}")
            print(f"Row {row} - ActualAmount Fetched: {actual_amount}")
            print(f"Row {row} - ReportedAmount Fetched: {reported_amount}")




    
    # Save the value of branch_dropdown before clearing widgets
    branch_value = branch_dropdown.get() 

    # # Clear existing widgets
    # for widget in window.winfo_children():
    #     widget.destroy()

    # Define the columns to be shown in GUI
    columns_to_display = ["PaymentMethod", "ActualAmount", "ReportedAmount", "TotalVariance"]

    empty_label = tk.Label(current_dynamic_content, text="")
    empty_label.grid(row=0 + display_offset, column=0, columnspan=len(columns_to_display), pady=(0, 0))

# Set a style for the header labels
    HEADER_FONT = ("Arial", 12, "bold")
    HEADER_BG = "#4E4E4E"  # Dark Grey
    HEADER_FG = "white"
    ENTRY_BG = "#F4F6F7"  # Light Grey
    ENTRY_FG = "black"
    SAVE_BUTTON_COLOR = "#007BFF"
    
    # Create a Label for each column header with the new style
    for col, column_name in enumerate(columns_to_display):
        header_label = tk.Label(current_dynamic_content, text=column_name, font=HEADER_FONT, bg=HEADER_BG, fg=HEADER_FG, padx=5, pady=5)
        header_label.grid(row=0 + display_offset, column=col, sticky="nsew")  # Use sticky to expand the label in its cell
    
    # Making columns resizable and adjusting their weights ensures even distribution of available space.
    for col in range(len(columns_to_display)):
        current_dynamic_content.grid_columnconfigure(col, weight=1)



    styles = getSampleStyleSheet()


    def save_to_pdf():
        global global_summary_data
        
        file_path = tkinter.filedialog.asksaveasfilename(defaultextension=".pdf",
                                                        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not file_path:
            return

        pdf = SimpleDocTemplate(file_path, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Fetch Branch and Date from GUI components
        selected_branch = branch_dropdown.get()
        processing_date = start_date_entry.get_date().strftime('%d/%m/%Y')  # convert to dd/mm/yyyy format

        # Insert Branch and Processing Date
        elements.append(Paragraph(f"Branch: {selected_branch}", styles['Title']))
        elements.append(Paragraph(f"Processing Date: {processing_date}", styles['Title']))
        elements.append(Spacer(1, 0.5*inch))  # Adding a space

        for lane, lane_data in global_lane_data.items():
            elements.append(Paragraph(f"Lane: {lane}", styles['Heading2']))  # Using different style
            data = [lane_data.columns.tolist()]
            for row in lane_data.iterrows():
                 data.append([round(value, 2) if isinstance(value, float) else value for value in row[1].values])

            t = Table(data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.aliceblue, colors.beige])  # alternate row colors
            ]))

            elements.append(t)
            elements.append(Spacer(1, 0.5*inch))  # Adding space between each lane

        elements.append(Paragraph("Summary Data", styles['Heading2']))
        data = [["PaymentMethod", "ActualAmount", "ReportedAmount", "TotalVariance"]]
        for payment_method, summary_data in global_summary_data.items():
            data.append([
                payment_method,
                format_currency(round(summary_data["ActualAmount"], 2)),
                format_currency(round(summary_data["ReportedAmount"], 2)),
                format_currency(round(summary_data["TotalVariance"], 2))
            ])

        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.aliceblue, colors.beige])
        ]))

        elements.append(t)
        pdf.build(elements)

    def format_currency(value):
        # This function returns the value formatted with two decimal places and prepended with a `$`
        return f"${value:.2f}"

    entries = []
    for row in range(len(dataframe)):
        row_entries = []
        if 'TotalAmount' in dataframe.columns:
            dataframe.rename(columns={'TotalAmount': 'ActualAmount'}, inplace=True)

        for col, column_name in enumerate(columns_to_display):
            if column_name == "PaymentMethod":
                entry = tk.Entry(current_dynamic_content, justify=tk.LEFT, bg=ENTRY_BG, fg=ENTRY_FG, borderwidth=2)
            else:
                entry = tk.Entry(current_dynamic_content, justify=tk.RIGHT, bg=ENTRY_BG, fg=ENTRY_FG, borderwidth=2)

            if column_name == "ActualAmount":
                value = dataframe.iloc[row].get("ActualAmount", 0)
                if isinstance(value, pd.Series):
                    value = value.sum()
                entry.insert(0, format_currency(float(value or 0)))

            elif column_name == "ReportedAmount":
                reported_var = tk.StringVar(current_dynamic_content)
                entry = tk.Entry(current_dynamic_content, justify=tk.RIGHT, textvariable=reported_var, bg=ENTRY_BG, fg=ENTRY_FG, borderwidth=2)
                entry.insert(0, "0.00")

                def update_total_variance(entries):
                    """Update the 'Total' row for TotalVariance."""
                    total_variance = sum(
                        [float(entry[3].get().replace("$", "").replace(",", "")) for entry in entries[:-1]])  # excluding the 'Total' row itself
                    total_variance_entry = entries[-1][3]  # assuming 'Total' is the last row
                    total_variance_entry.config(state='normal')
                    total_variance_entry.delete(0, tk.END)
                    total_variance_entry.insert(0, format_currency(total_variance))
                    total_variance_entry.config(state='disabled')

                def update_total_reported_amount(entries):
                    """Update the 'Total' row for ReportedAmount."""
                    total_reported = sum(
                        [float(entry[2].get().replace("$", "").replace(",", "")) for entry in entries[:-1]])  # excluding the 'Total' row itself
                    total_entry = entries[-1][2]  # assuming 'Total' is the last row
                    total_entry.config(state='normal')
                    total_entry.delete(0, tk.END)
                    total_entry.insert(0, format_currency(total_reported))
                    total_entry.config(state='disabled')

                    # After updating 'Total' for ReportedAmount, also update 'Total' for TotalVariance
                    update_total_variance(entries)

                def update_variance(event, r=None, rv=None): 
                    actual_value = float(entries[r][1].get().replace("$", "").replace(",", "") or 0.0)
                    reported_value = float(rv.get().replace("$", "").replace(",", "") or 0.0)
                    variance = reported_value - actual_value

                    # Update the TotalVariance entry for the current row
                    variance_entry = entries[r][3]
                    variance_entry.config(state='normal')
                    variance_entry.delete(0, tk.END)
                    variance_entry.insert(0, format_currency(variance))
                    
                    # Setting the background color of the TotalVariance field based on the computed variance
                    if variance < 0 or variance > 0:
                        variance_entry.config(bg='red', fg='white')  # red background for negative variance
                    elif variance == 0:
                        variance_entry.config(bg='white', fg='black')  # white background for zero variance
                    # else:
                    #     variance_entry.config(bg='green', fg='white')  # green background for positive variance

                    variance_entry.config(state='disabled', disabledbackground=variance_entry.cget('bg'), disabledforeground=variance_entry.cget('fg'))

                    # Update the 'Total' row for ReportedAmount
                    update_total_reported_amount(entries)



                # Use lambda to pass the current row to update_variance
                entry.bind("<FocusOut>", lambda event, r=row, rv=reported_var: update_variance(event, r, rv))

            elif column_name == "TotalVariance":
                if "TotalVariance" in dataframe.columns:
                    value = dataframe.iloc[row]["TotalVariance"]
                    if isinstance(value, pd.Series):
                        value = value.sum()
                    entry.insert(0, format_currency(float(value)))
                    entry.config(state='disabled', disabledbackground=ENTRY_BG, disabledforeground=ENTRY_FG)
                    # If it's the "Total" row, change the color
                    if dataframe.iloc[row]["PaymentMethod"] == "Total":
                        entry.config(disabledbackground='red', disabledforeground='white')

                else:
                    entry.insert(0, "N/A")

            else:
                if column_name not in dataframe.columns:
                    showerror(title="Error", message=f"Column {column_name} is missing from the data.")
                    return
                entry.insert(0, dataframe.iloc[row][column_name])

            if column_name != "ReportedAmount":
                entry.config(state='disabled')

            entry.grid(row=row + 1 + display_offset, column=col, sticky="nsew", padx=5, pady=2)

            row_entries.append(entry)

        entries.append(row_entries)
    # Save button styling
    save_button = tk.Button(current_dynamic_content, text="Save", command=save_changes, bg=SAVE_BUTTON_COLOR, fg="white", font=("Arial", 10, "bold"), padx=10, pady=5)
    save_button.grid(row=len(dataframe) + 2 + display_offset, column=1, pady=10)

    # Add the Summary button next to the Save button
    summary_button = tk.Button(current_dynamic_content, text="Summary", command=show_summary, bg=SAVE_BUTTON_COLOR, fg="white", font=("Arial", 10, "bold"), padx=10, pady=5)
    summary_button.grid(row=len(dataframe) + 2 + display_offset, column=2, pady=10)


    

    # Adding a binding to the save button to change its color on hover, creating a nice effect.
    def on_enter(event):
        save_button.config(background="#0056b3")

    def on_leave(event):
        save_button.config(background=SAVE_BUTTON_COLOR)

    save_button.bind("<Enter>", on_enter)
    save_button.bind("<Leave>", on_leave)




def clear_dynamic_frame():
    global current_dynamic_content
    if current_dynamic_content:
        for widget in current_dynamic_content.winfo_children():
            widget.destroy()
        current_dynamic_content.pack_forget()


def generate_report_for_selected_station(station):
    global global_lane_data
    try:
        # Fetching the date from the GUI and setting default times
        start_date = datetime.strptime(start_date_entry.get(), "%d/%m/%y").date()
        start_date_time_str = f"{start_date} 00:00:00"
        end_date_time_str = f"{start_date} 23:59:59"
        
        # Fetching selected branch directly from the dropdown
        selected_branch = branch_dropdown.get()

        data = generate_report_2(start_date_time_str, selected_branch, station)

        if data is None:
            showerror(title="Error", message="Failed to fetch data.")
            return

        display_and_edit_data(data, start_date_time_str, end_date_time_str, selected_branch, station)
        
        fetched_data_for_station = generate_report_2(start_date_time_str, selected_branch, station)

        if fetched_data_for_station is not None:
            global_lane_data[station] = fetched_data_for_station
            display_and_edit_data(fetched_data_for_station, start_date_time_str, end_date_time_str, selected_branch, station)
        else:
            showerror(title="Error", message="Failed to fetch data.")
            return
        # s
    except Exception as e:
        showerror(title="Error", message=f"An error occurred: {e}")

def show_stations_for_selected_branch():
    
    # Fetching stations for the selected branch
    clear_dynamic_frame()
    try:
        # Database connection
        config = ConfigParser()
        config.read("config.ini")
        server = base64.b64decode(config.get("DATABASE", "server").encode()).decode()
        databases = base64.b64decode(config.get("DATABASE", "database").encode()).decode().split(',')
        print("Decoded Databases:", databases)

        username = base64.b64decode(config.get("DATABASE", "username").encode()).decode()
        password = base64.b64decode(config.get("DATABASE", "password").encode()).decode()

        stations = []

        for db in databases:
            connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={db.strip()}"
            
            if username and password:
                connection_string += f";UID={username};PWD={password}"
            else:
                connection_string += ";Trusted_Connection=yes"
                
            connection = pyodbc.connect(connection_string)
            # Fetch stations for the selected branch using JOIN between Branches and TransHeaders tables
            stations_query = f"""SELECT DISTINCT th.Station
                                 FROM AKPOS.dbo.TransHeaders th
                                 INNER JOIN AKPOS.dbo.Branches br ON th.Branch = br.ID
                                 WHERE br.Name = '{branch_dropdown.get()}';"""
            stations += [int(s) for s in pd.read_sql_query(stations_query, connection)['Station'].tolist()]  # Convert to int here
            connection.close()

            # Fetch lanes data from the Lanes table
            lanes_from_db = fetch_lanes_from_db(branch_dropdown.get())
            
            # If the lanes data from Lanes table is empty or None, then use STATIC_LANES for that branch
            if not lanes_from_db:
                lanes_from_db = STATIC_LANES.get(branch_dropdown.get(), [])

            # Convert lanes to integer format
            lanes_from_db = [int(lane) for lane in lanes_from_db]  # Convert to int here

            # Merge the fetched stations and lanes from Lanes table
            stations = sorted(list(set(stations + lanes_from_db)))

            print(stations)


        # Dynamically create buttons for each station
        # Styling
        btn_font = tkFont.Font(family="Arial", size=10, weight="bold")  # Decreased font size for smaller buttons
        title_font = tkFont.Font(family="Arial", size=14, weight="bold")

        # Main frame for stations
        stations_frame = tk.Frame(dynamic_frame, padx=20)
        global current_dynamic_content
        current_dynamic_content = stations_frame
        stations_frame.grid(row=0, column=0, sticky="nsew", pady=(5, 10))  # Reduced top padding for pushing upwards

        # Adjust the row weight to push stations_frame upwards
        dynamic_frame.grid_rowconfigure(0, weight=0)
        dynamic_frame.grid_rowconfigure(1, weight=2)

        # Calculating grid layout dimensions
        max_cols = 7  # Define how many buttons per row

        # Determine the max width and height for the buttons
        max_width = 10
        BUTTON_WIDTH = max_width 
        BUTTON_HEIGHT = 1  # Fixed height for each button

        for idx, station in enumerate(stations):
            btn_text = f"Lane: {station}"
            station_button = tk.Button(stations_frame, text=btn_text, font=btn_font, 
                                        width=BUTTON_WIDTH, height=BUTTON_HEIGHT, 
                                        bg='#e6f2ff', borderwidth=1, relief='solid', anchor="center")
            
            # Wrap the actions in a new function
            def on_station_button_click(st, btn):
                # First, reset all buttons to their default color and reset their clicked flags
                for child in stations_frame.winfo_children():
                    if isinstance(child, tk.Button):
                        child.config(bg='#e6f2ff')
                        setattr(child, "clicked", False)
                
                # Now, set the current button's color to green and its clicked flag to True
                btn.config(bg='green')
                btn.config(fg='white')
                setattr(btn, "clicked", True)
                
                generate_report_for_selected_station(st)

            station_button.config(command=lambda st=station, btn=station_button: on_station_button_click(st, btn))  # Set the command after the button is initialized
            
            # Hover effects
            station_button.bind("<Enter>", on_enter)
            station_button.bind("<Leave>", on_leave)
            
            station_button.grid(row=(idx // max_cols), column=idx % max_cols, padx=0, pady=0, sticky="nsew", columnspan=1)

        # Ensure that each column and row of the grid is treated uniformly:
        for col in range(max_cols):
            stations_frame.grid_columnconfigure(col, weight=1, uniform="col")

        last_station_row = (len(stations) // max_cols)

        # Pushing buttons upwards by reducing the additional space
        for space_row in range(1, 3):  # Adding only 2 blank labels for spacing
            empty_label = tk.Label(stations_frame, text="")
            empty_label.grid(row=len(stations) // max_cols + space_row, column=0, columnspan=max_cols, pady=(2, 2), sticky="nsew")
        # # Merge dynamic and static stations and remove duplicates
        # stations = sorted(list(set(stations + static_stations)))
        # Adding blank labels for space after the dynamic buttons
        
        for space_row in range(1, 25):  # adding 4 blank labels for spacing
            empty_label = tk.Label(stations_frame, text="")
            empty_label.grid(row=last_station_row + space_row, column=0, columnspan=max_cols, pady=(10, 0))

        

            empty_label_1 = tk.Label(stations_frame, text="")
            empty_label_1.grid(row=last_station_row + 1, column=0, columnspan=max_cols, pady=(10, 0))

            empty_label_2 = tk.Label(stations_frame, text="")
            empty_label_2.grid(row=last_station_row + 2, column=0, columnspan=max_cols, pady=(10, 0))

            empty_label_3 = tk.Label(stations_frame, text="")
            empty_label_3.grid(row=last_station_row + 2, column=0, columnspan=max_cols, pady=(10, 0))

            empty_label_4 = tk.Label(stations_frame, text="")
            empty_label_4.grid(row=last_station_row + 2, column=0, columnspan=max_cols, pady=(10, 0))

            empty_label_5 = tk.Label(stations_frame, text="")
            empty_label_5.grid(row=last_station_row + 2, column=0, columnspan=max_cols, pady=(10, 0))

            empty_label_6 = tk.Label(stations_frame, text="")
            empty_label_6.grid(row=last_station_row + 2, column=0, columnspan=max_cols, pady=(10, 0))

        # Adjusting main window style
        window.config(bg='#d9d9d9')

    except Exception as e:
        print(f"An error occurred: {e}")
        showerror(title="Error", message=f"An error occurred: {e}")

def generate_report_2(start_date_str, selected_branch, selected_station):
    print(f"Selected Branch: {selected_branch}")
    print(f"Selected Station: {selected_station}")

    start_date_time_str = start_date_str
    end_date_time_str = f"{start_date_str[:-8]}23:59:59" 
    print(f"Start Date Time: {start_date_time_str}")
    results = []

    try:
        config = ConfigParser()
        config.read("config.ini")
        server = base64.b64decode(config.get("DATABASE", "server").encode()).decode()
        databases = base64.b64decode(config.get("DATABASE", "database").encode()).decode().split(',')
        print("Decoded Databases:", databases)
        
        username = base64.b64decode(config.get("DATABASE", "username").encode()).decode()
        password = base64.b64decode(config.get("DATABASE", "password").encode()).decode()
        df = pd.DataFrame()
        data_found_in_mw_new = False

        for db in databases:
            print(f"Trying to connect to database: {db.strip()}")

            if username and password:
                connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={db.strip()};UID={username};PWD={password}"
            else:
                connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={db.strip()};Trusted_Connection=yes"

            connection = pyodbc.connect(connection_string)

            if db.strip() == "MW_EOD":
                check_query = f"""
                SELECT COUNT(*) 
                FROM MW_EOD.dbo.UpdatedTransHeaders 
                WHERE ProcessingDate >= '{start_date_time_str}' AND ProcessingDate <= '{end_date_time_str}'
                AND Branch = '{selected_branch}' AND Station = '{selected_station}'
            """
                cursor = connection.cursor()
                cursor.execute(check_query)
                count = cursor.fetchone()[0]

                # If count is greater than zero, fetch from UpdatedTransHeaders
                if count > 0:
                    data_found_in_mw_new = True
                    report_query_mw_new = f"""
                        SELECT PaymentMethod, ActualAmount, ReportedAmount, TotalVariance
                        FROM MW_EOD.dbo.UpdatedTransHeaders
                        WHERE ProcessingDate >= '{start_date_time_str}' AND ProcessingDate <= '{end_date_time_str}'
                        AND Branch = '{selected_branch}' AND Station = '{selected_station}'
                        GROUP BY PaymentMethod, ActualAmount, ReportedAmount, TotalVariance;
                    """
                    df = pd.read_sql_query(report_query_mw_new, connection)
                    if not df.empty:
                        print("Appending data from MW_EOD")
                        results.append(df)

            elif db.strip() == "AKPOS" and not data_found_in_mw_new:
                report_query_akpos = """
                    SELECT
                        CASE
                            WHEN TP.MediaName = 'Cash' THEN 'Cash'
                            WHEN TP.MediaName = 'Extra Cash' THEN 'Extra Cash'
                            WHEN TP.MediaName = 'Account' THEN 'Account'
                            WHEN TP.MediaName = 'EFTPOS' THEN 'EFTPOS'
                            WHEN TP.MediaName = 'Credit Card' THEN 'Credit Card'
                            WHEN TP.MediaName = 'CLICK AND COLLECT' THEN 'CLICK AND COLLECT'
                            WHEN TP.MediaName = 'CC EFTPOS' THEN 'EFTPOS'
                            WHEN TP.MediaName = 'FSG CASH' THEN 'Cash'
                        END AS PaymentMethod,
                        SUM(TP.Value) AS ActualAmount,
                        SUM(TP.Value) AS ReportedAmount,
                        SUM(TP.Change) AS TotalChange
                    FROM AKPOS.dbo.TransHeaders TH
                    INNER JOIN AKPOS.dbo.TransPayments TP ON TH.TransNo = TP.TransNo
                    WHERE TH.Logged >= ? AND TH.Logged <= ?
                    AND TH.Branch = ? AND TH.Station = ?
                    GROUP BY
                        CASE
                            WHEN TP.MediaName = 'Cash' THEN 'Cash'
                            WHEN TP.MediaName = 'Extra Cash' THEN 'Extra Cash'
                            WHEN TP.MediaName = 'Account' THEN 'Account'
                            WHEN TP.MediaName = 'EFTPOS' THEN 'EFTPOS'
                            WHEN TP.MediaName = 'Credit Card' THEN 'Credit Card'
                            WHEN TP.MediaName = 'CLICK AND COLLECT' THEN 'CLICK AND COLLECT'
                            WHEN TP.MediaName = 'CC EFTPOS' THEN 'EFTPOS'
                            WHEN TP.MediaName = 'FSG CASH' THEN 'Cash'
                        END;
                """
                branch_num = int(selected_branch.split(' ')[-1])  # This will convert 'Branch 1' to 1

                df = pd.read_sql_query(report_query_akpos, connection, params=(start_date_time_str, end_date_time_str, branch_num, selected_station))

                if "TotalChange" in df.columns:
                    df.rename(columns={'TotalChange': 'TotalVariance'}, inplace=True)
                if not df.empty:
                    print("Appending data from AKPOS")
                    results.append(df)

                    

            connection.close()

         # If the results are empty, generate a DataFrame with default values.
        if not results:
            expected_payment_methods = ['Cash', 'Account', 'EFTPOS', 'Credit Card', 'CLICK AND COLLECT']
            default_data = {
                'PaymentMethod': expected_payment_methods,
                'ActualAmount': [0.0] * len(expected_payment_methods),
                'ReportedAmount': [0.0] * len(expected_payment_methods),
                'TotalVariance': [0.0] * len(expected_payment_methods)
            }
            final_df = pd.DataFrame(default_data)
        else:
            # Ensure only one dataframe is present
            assert len(results) == 1, "Multiple data sources found. This shouldn't happen."
            final_df = results[0]
            
            # Step 1: Create a list of all expected PaymentMethod fields
            expected_payment_methods = ['Cash', 'Account', 'EFTPOS', 'Credit Card', 'CLICK AND COLLECT']
            
            # Step 2: Check if each expected PaymentMethod exists in final_df
            for method in expected_payment_methods:
                if method not in final_df['PaymentMethod'].values:
                    new_row = pd.Series({'PaymentMethod': method, 'ActualAmount': 0.0, 'ReportedAmount': 0.0, 'TotalVariance': 0.0})
                    final_df = pd.concat([final_df, pd.DataFrame([new_row])], ignore_index=True)

        # Step 3: Append the total row to final_df
        total_row = pd.DataFrame(final_df.sum(numeric_only=True)).transpose()
        total_row["PaymentMethod"] = "Total"
        final_df = pd.concat([final_df, total_row], ignore_index=True)

        return final_df
    except Exception as e:
        print(f"An error occurred: {e}")


# # Create a Treeview for data display
# columns = ["PaymentMethod", "TotalAmount", "ReportedAmount","TotalVariance"]
# report_tree = ttk.Treeview(window, columns=columns, show="headings")
# for col in columns:
#     report_tree.heading(col, text=col)
# report_tree.pack(pady=20)



def generate_both_reports(
    start_date_str,
    start_time_str,
    end_date_str,
    end_time_str,
    current_date_time_str,
    previous_date_time_str,
    selected_branch,
    selected_station,
):
    start_date_time_str = f"{start_date_str} {start_time_str}"
    end_date_time_str = f"{end_date_str} {end_time_str}"

    generate_report_2(start_date_str, selected_branch, selected_station)



def populate_branch_dropdown():
    try:
        # Get DB credentials from config
        config = ConfigParser()
        config.read("config.ini")
        server = base64.b64decode(config.get("DATABASE", "server").encode()).decode()
        databases = base64.b64decode(config.get("DATABASE", "database").encode()).decode().split(',')
        print("Decoded Databases:", databases)

        username = base64.b64decode(
            config.get("DATABASE", "username").encode()
        ).decode()
        password = base64.b64decode(
            config.get("DATABASE", "password").encode()
        ).decode()

        branches = []
        for db in databases:
            # Establish DB connection
            if username and password:
                connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={db};UID={username};PWD={password}"
            else:
                connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={db};Trusted_Connection=yes"
            
            connection = pyodbc.connect(connection_string)

            # Query to get all branch names
            branches_query = "SELECT DISTINCT Name FROM AKPOS.dbo.Branches;"
            branches_df = pd.read_sql_query(branches_query, connection)
            branches.extend(branches_df['Name'].tolist())

            connection.close()

        # Update dropdown values (remove duplicates)
        branch_dropdown['values'] = list(set(branches))

    except Exception as e:
        print(f"An error occurred: {e}")
        showerror(title="Error", message=f"An error occurred: {e}")





def open_config_window():
    global server_entry, database_entry, username_entry, password_entry
    global smtp_server_entry, smtp_username_entry, smtp_password_entry
    global smtp_from_entry, to_email_entry, time_entry

    config_window = tk.Toplevel(window)
    config_window.title("Update Configuration")

    # All your Labels and Entries come here

    # Server Label and Entry
    server_label = tk.Label(config_window, text="Server:")
    server_label.pack()
    server_entry = tk.Entry(config_window)
    server_entry.pack()

    # Database Label and Entry
    database_label = tk.Label(config_window, text="Databases (Separate with comma if more than one, e.g., AKPOS,MW_EOD):")
    database_label.pack()
    database_entry = tk.Entry(config_window)
    database_entry.pack()


    # Username Label and Entry
    username_label = tk.Label(
        config_window, text="Username (leave blank for Windows Authentication):"
    )
    username_label.pack()
    username_entry = tk.Entry(config_window)
    username_entry.pack()

    # Password Label and Entry
    password_label = tk.Label(
        config_window, text="Password (leave blank for Windows Authentication):"
    )
    password_label.pack()
    password_entry = tk.Entry(config_window, show="*")
    password_entry.pack()

    # # SMTP Server Label and Entry
    # smtp_server_label = tk.Label(config_window, text="SMTP Server:")
    # smtp_server_label.pack()
    # smtp_server_entry = tk.Entry(config_window)
    # smtp_server_entry.pack()

    # # SMTP Username Label and Entry
    # smtp_username_label = tk.Label(config_window, text="SMTP Username:")
    # smtp_username_label.pack()
    # smtp_username_entry = tk.Entry(config_window)
    # smtp_username_entry.pack()

    # # SMTP Password Label and Entry
    # smtp_password_label = tk.Label(config_window, text="SMTP Password:")
    # smtp_password_label.pack()
    # smtp_password_entry = tk.Entry(config_window, show="*")
    # smtp_password_entry.pack()

    # # 'From' Email Address Label and Entry
    # smtp_from_label = tk.Label(config_window, text="'From' Email Address:")
    # smtp_from_label.pack()
    # smtp_from_entry = tk.Entry(config_window)
    # smtp_from_entry.pack()

    # # 'To' Email Address Label and Entry
    # to_email_label = tk.Label(config_window, text="'To' Email Address:")
    # to_email_label.pack()
    # to_email_entry = tk.Entry(config_window)
    # to_email_entry.pack()

    # # Time to Send Report Label and Entry
    # time_entry_label = tk.Label(config_window, text="Time to Send Report (HH:MM):")
    # time_entry_label.pack()
    # time_entry = tk.Entry(config_window)
    # time_entry.pack()


    
    # Save SMTP Config Button
    # Pass the config_window to the save_config function
    save_config_button = tk.Button(
        config_window, text="Save Config", command=lambda: save_config(config_window)
    )
    save_config_button.pack()



# Create the main application window
window = tk.Tk()
window.title("Moore Wilsons End of Day Report")
window.geometry("1300x800")

# Use a more general layout manager
window.grid_rowconfigure(0, weight=1)
window.grid_columnconfigure(0, weight=1)

# Create a main frame to hold everything
main_frame = ttk.Frame(window, padding="20")
main_frame.grid(row=0, column=0, sticky="nsew")

# Frame for static input elements
static_frame = ttk.Frame(main_frame, padding="20")
static_frame.grid(row=0, column=0, sticky="ew")

dynamic_frame = tk.Frame(main_frame)
dynamic_frame.grid(row=1, column=0, pady=0, padx=20, sticky="nsew")

# Title Label
title_label = tk.Label(static_frame, text="Moore Wilsons End of Day Report", font=("Helvetica", 18, "bold"))
title_label.grid(row=0, column=0, columnspan=6, pady=(10, 20), sticky="n")
static_frame.columnconfigure(0, weight=1)  # Make the first column expand


# Branch Selection
branch_label = tk.Label(static_frame, text="Select Branch:", font=("Helvetica", 12))
branch_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
branch_dropdown = ttk.Combobox(static_frame, font=("Helvetica", 12))
branch_dropdown.grid(row=1, column=1, pady=10, padx=10, sticky="w")
populate_branch_dropdown()

# Date Range Selection
start_date_label = tk.Label(static_frame, text="Processing Date:", font=("Helvetica", 12))
start_date_label.grid(row=1, column=2, pady=10, padx=10, sticky="w")
start_date_entry = DateEntry(static_frame, font=("Helvetica", 12), date_pattern='dd/mm/yy')
start_date_entry.grid(row=1, column=3, pady=10, padx=10, sticky="w")

# Show Lanes Button
generate_report_button = ttk.Button(
    static_frame,
    text="Show Lanes",
    command=show_stations_for_selected_branch,
    style="Cool.TButton"
)
generate_report_button.grid(row=1, column=4, pady=10, padx=10, sticky="w")

# Update Configuration Button
update_config_button = ttk.Button(
    static_frame,
    text="Update Configuration",
    command=open_config_window,
    style="Cool.TButton"
)
update_config_button.grid(row=1, column=5, pady=10, padx=10, sticky="w")

# Status Label for Feedback
status_label = ttk.Label(static_frame)
status_label.grid(row=2, column=0, columnspan=6, pady=(20, 0), padx=10)

# Style for the "Cool" buttons
style = ttk.Style()
style.configure("Cool.TButton", font=("Helvetica", 12), foreground="black", background="#3498db", padding=10)

# Ensure main_frame expands to fill window
main_frame.columnconfigure(0, weight=1)
main_frame.rowconfigure(1, weight=1)

# Start the GUI event loop
window.mainloop()
