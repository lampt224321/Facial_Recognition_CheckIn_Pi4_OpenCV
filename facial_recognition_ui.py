# facial_recognition_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import csv
import pandas as pd
import sys
from PIL import Image, ImageTk
import importlib.util

# Import our face recognition module
spec = importlib.util.spec_from_file_location("facial_recognition", "facial_recognition.py")
facial_recognition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(facial_recognition)

# Configuration
LOG_FILE = "checkin_log.csv"
IMG_FOLDER = "checkin_images"

class CheckinApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Recognition Check-in UI")
        self.root.geometry("950x700")
        self.face_rec = None
        
        # Create required directories and files
        if not os.path.exists(IMG_FOLDER):
            os.makedirs(IMG_FOLDER)
        
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Name", "Timestamp"])

        self.create_widgets()
        
        # Set up closing handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        title = tk.Label(self.root, text="HỆ THỐNG CHECK-IN KHUÔN MẶT", font=("Arial", 12, "bold"))
        title.pack(pady=10)

        # Status indicator
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, font=("Arial", 10))
        self.status_label.pack(pady=5)

        # Video display area
        self.video_frame = tk.Frame(self.root, bg="black", width=400, height=300)
        self.video_frame.pack(pady=5, padx=10)
        
        # Make sure the frame maintains its size
        self.video_frame.pack_propagate(False)
        
        # Create a label inside the frame where the video will be displayed
        self.video_label = tk.Label(self.video_frame, bg="black")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.checkin_btn = tk.Button(btn_frame, text="Check-in", font=("Arial", 12), width=15, 
                                     command=self.start_checkin, bg="#f3f3f3", fg="black")
        self.checkin_btn.grid(row=0, column=0, padx=10)

        self.cancel_btn = tk.Button(btn_frame, text="Stop", font=("Arial", 12), width=15, 
                                    command=self.cancel_checkin, bg="#f3f3f3", fg="black", state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=10)

        self.open_pictures_btn = tk.Button(btn_frame, text="Pictures", font=("Arial", 12), width=15, 
                                          command=self.open_pictures, bg="#f3f3f3", fg="black")
        self.open_pictures_btn.grid(row=1, column=0, padx=10, pady=10)

        self.info_btn = tk.Button(btn_frame, text="Information", font=("Arial", 12), width=15, 
                                 command=self.open_log_file, bg="#f3f3f3", fg="black")
        self.info_btn.grid(row=1, column=1, padx=10, pady=10)

        # Add a horizontal separator
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', pady=5)

        self.filter_frame = tk.LabelFrame(self.root, text="Lọc dữ liệu check-in", padx=10, pady=10)
        self.filter_frame.pack(pady=5, fill="x", padx=20)

        tk.Label(self.filter_frame, text="Tên:").grid(row=0, column=0)
        self.name_entry = tk.Entry(self.filter_frame)
        self.name_entry.grid(row=0, column=1, padx=5)

        tk.Label(self.filter_frame, text="Ngày (YYYY-MM-DD):").grid(row=0, column=2)
        self.date_entry = tk.Entry(self.filter_frame)
        self.date_entry.grid(row=0, column=3, padx=5)

        self.filter_btn = tk.Button(self.filter_frame, text="Lọc", command=self.filter_log)
        self.filter_btn.grid(row=0, column=4, padx=10)
        
        # Reset filter button
        self.reset_btn = tk.Button(self.filter_frame, text="Reset", command=self.reset_filter)
        self.reset_btn.grid(row=0, column=5, padx=10)

        # Create a frame for the treeview and scrollbar
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(expand=True, fill="both", padx=20, pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side="right", fill="y")

        # Configure treeview with scrollbar
        self.tree = ttk.Treeview(tree_frame, columns=("name", "time"), show="headings", yscrollcommand=scrollbar.set)
        self.tree.heading("name", text="Tên")
        self.tree.heading("time", text="Thời gian check-in")
        self.tree.column("name", width=150)
        self.tree.column("time", width=150)
        self.tree.pack(expand=True, fill="both")
        
        scrollbar.config(command=self.tree.yview)
        
        # Load initial logs
        self.show_logs()
        
        # Place "Không có video" text initially
        self.no_video_text = tk.Label(self.video_label, text="Không có video", font=("Arial", 16), bg="black", fg="white")
        self.no_video_text.place(relx=0.5, rely=0.5, anchor="center")

    def update_status(self, message):
        """Callback for the face recognition module to update status"""
        self.status_var.set(message)
        # If it's a check-in message, refresh the log
        if "Check-in successful" in message:
            self.root.after(500, self.show_logs)

    def start_checkin(self):
        # Check if encodings file exists
        if not os.path.exists("encodings.pickle"):
            messagebox.showerror("Error", "encodings.pickle not found. Please create face encodings first.")
            return
        
        # Remove "no video" text
        self.no_video_text.place_forget()
            
        # Initialize face recognition if not already done
        if self.face_rec is None:
            self.face_rec = facial_recognition.FaceRecognition(
                video_label=self.video_label,
                status_callback=self.update_status
            )
        
        # Start the face recognition
        if self.face_rec.start():
            self.status_var.set("Check-in process running...")
            self.checkin_btn.config(state="disabled")
            self.cancel_btn.config(state="normal")
        else:
            messagebox.showerror("Error", "Failed to start face recognition")

    def cancel_checkin(self):
        if self.face_rec:
            self.face_rec.stop()
            self.face_rec = None
            self.status_var.set("Check-in stopped")
            self.checkin_btn.config(state="normal")
            self.cancel_btn.config(state="disabled")
            
            # Show "No video" text again
            self.no_video_text.place(relx=0.5, rely=0.5, anchor="center")
            
            # Clear the video label
            self.video_label.config(image="")

    def open_log_file(self):
        """Open the check-in log CSV file"""
        if os.path.exists(LOG_FILE):
            try:
                # Use appropriate system command to open the CSV file
                if sys.platform == "win32":
                    os.startfile(LOG_FILE)
                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.run(["open", LOG_FILE])
                else:
                    import subprocess
                    subprocess.run(["xdg-open", LOG_FILE])
            except Exception as e:
                messagebox.showerror("Error", f"Cannot open log file: {str(e)}")
        else:
            messagebox.showwarning("Thông báo", "Chưa có file log check-in.")

    def open_pictures(self):
        if os.path.exists(IMG_FOLDER) and os.listdir(IMG_FOLDER):
            # Use appropriate system command to open folder
            if sys.platform == "win32":
                os.startfile(IMG_FOLDER)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", IMG_FOLDER])
            else:
                try:
                    import subprocess
                    subprocess.run(["xdg-open", IMG_FOLDER])
                except FileNotFoundError:
                    messagebox.showerror("Error", "Cannot open folder - xdg-open not found")
        else:
            messagebox.showwarning("Thông báo", "Chưa có ảnh nào được lưu.")

    def show_logs(self):
        # Clear existing data
        self.tree.delete(*self.tree.get_children())
        
        if not os.path.exists(LOG_FILE):
            return
            
        try:
            # Read and display all log entries
            with open(LOG_FILE, "r") as file:
                reader = csv.reader(file)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 2:
                        self.tree.insert("", "end", values=(row[0], row[1]))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi đọc file CSV: {str(e)}")

    def filter_log(self):
        if not os.path.exists(LOG_FILE):
            messagebox.showwarning("Không có dữ liệu", "Chưa có log check-in.")
            return
            
        try:
            name = self.name_entry.get().strip().lower()
            date = self.date_entry.get().strip()
            
            df = pd.read_csv(LOG_FILE)
            filtered_df = df.copy()
            
            # Apply filters
            if name:
                filtered_df = filtered_df[filtered_df["Name"].str.lower().str.contains(name)]
            if date:
                filtered_df = filtered_df[filtered_df["Timestamp"].str.startswith(date)]
            
            # Update treeview
            self.tree.delete(*self.tree.get_children())
            for _, row in filtered_df.iterrows():
                self.tree.insert("", "end", values=(row["Name"], row["Timestamp"]))
                
            # Show count of filtered records
            if len(filtered_df) == 0:
                self.status_var.set(f"No records match your filter")
            else:
                self.status_var.set(f"Found {len(filtered_df)} matching records")
                
        except Exception as e:
            messagebox.showerror("Error", f"Filter error: {str(e)}")
    
    def reset_filter(self):
        self.name_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.show_logs()
        self.status_var.set("Filter reset")
        
    def on_closing(self):
        """Handle window closing event"""
        if self.face_rec:
            self.face_rec.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CheckinApp(root)
    root.mainloop()