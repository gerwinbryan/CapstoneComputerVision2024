import cv2
import numpy as np
import threading
import time
import sqlite3
from datetime import datetime
from paddleocr import PaddleOCR
import re
import os
import queue
import tkinter as tk
from tkinter import ttk, messagebox  # Add messagebox here
from PIL import Image, ImageTk
from config import DISPLAY_WIDTH, DISPLAY_HEIGHT  # Add this import
from collections import Counter
import requests
import firebase_admin
from firebase_admin import credentials, messaging

# At the top of the file, add:
DATABASE_PATH = 'parking_violations.db'

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')

# Initialize Firebase Admin SDK once
cred = credentials.Certificate("firebase-adminsdk.json")
firebase_admin.initialize_app(cred)

# Database setup
conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS violations
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp TEXT,
                   license_plate TEXT,
                   location TEXT,
                   parking_duration INTEGER,
                   image_path TEXT)''')
conn.commit()

# Add near the other CREATE TABLE statements
cursor.execute('''CREATE TABLE IF NOT EXISTS fcm_tokens
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   token TEXT UNIQUE NOT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

# Philippine license plate patterns
PLATE_PATTERNS = [
    r'^[A-Z]{3}\s?\d{3,4}$',  # Standard format
    r'^\d{3,4}\s?[A-Z]{3}$',  # Reversed format
    r'^[A-Z]{2}\s?\d{4,5}$',  # Older format
    r'^\d{4,5}\s?[A-Z]{2}$',  # Older reversed format
    r'^[A-Z]{3}\s?\d{4}$',  # New format (like NHJ 6964)
]


def is_valid_plate(text):
    return any(re.match(pattern, text.replace(" ", "")) for pattern in PLATE_PATTERNS)


def process_stationary_car(car_image, start_time):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = f"violations/car_{timestamp}.jpg"
    os.makedirs("violations", exist_ok=True)
    cv2.imwrite(image_path, car_image)
    return image_path, start_time


def perform_ocr(image_path):
    # Read and upscale image
    img = cv2.imread(image_path)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    result = ocr.ocr(img, cls=True)
    if result and result[0]:
        print(f"OCR Result structure: {result}")

        best_match = None
        highest_confidence = 0

        for line in result:
            for item in line:
                text, confidence = item[1]
                if isinstance(confidence, tuple):
                    confidence = confidence[0]

                print(f"Detected text: {text}, Confidence: {confidence}")

                if is_valid_plate(text) and confidence > highest_confidence:
                    best_match = (text, confidence)
                    highest_confidence = confidence

        if best_match:
            return best_match

    print("No valid license plate detected")
    return "", 0


def log_violation(plate_text, start_time, image_path):
    violation_id = int(time.time() * 1000)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not plate_text:
        plate_text = "Unknown"

    full_image_path = os.path.abspath(image_path)

    # Calculate parking duration
    duration = int(time.time() - start_time)

    # Log to local database
    cursor.execute('''INSERT INTO violations 
                      (id, timestamp, license_plate, location, parking_duration, image_path)
                      VALUES (?, ?, ?, ?, ?, ?)''',
                   (violation_id, timestamp, plate_text, "Manila", duration, full_image_path))
    conn.commit()

    # Send FCM notification directly
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title='New Parking Violation',
                body=f'Vehicle with plate {plate_text} detected'
            ),
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='ic_launcher',
                    color='#7B1FA2',
                    channel_id='parking_violations'
                )
            ),
            # Send to topic instead of specific tokens
            topic='parking_violations'  # All devices will subscribe to this topic
        )

        response = messaging.send(message)
        print(f"Successfully sent notification: {response}")

    except Exception as e:
        print(f"Error sending notification: {e}")

    return violation_id


def update_parking_duration(violation_id, duration):
    cursor.execute('''UPDATE violations SET parking_duration = ? WHERE id = ?''',
                   (duration, violation_id))
    conn.commit()


def handle_stationary_car(car_image, track_id, stationary_cars, ocr_queue):
    if track_id not in stationary_cars:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = f"violations/car_{timestamp}_{track_id}.jpg"
        os.makedirs("violations", exist_ok=True)
        cv2.imwrite(image_path, car_image)
        start_time = time.time()
        stationary_cars[track_id] = (None, start_time, image_path)
        ocr_queue.put((track_id, image_path))
        print(
            f"Car with track_id {track_id} detected as potentially illegally parked at {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")


def finalize_stationary_car(track_id, stationary_cars):
    if track_id in stationary_cars:
        violation_id, start_time, image_path = stationary_cars.pop(track_id)
        if violation_id:
            end_time = time.time()
            duration = int(end_time - start_time)
            update_parking_duration(violation_id, duration)
        # Remove this line:
        # if os.path.exists(image_path):
        #     os.remove(image_path)
        print(f"Stationary car data for track_id {track_id} has been finalized.")


def start_ocr_thread(ocr_queue, stationary_cars):
    ocr_attempts = {}
    max_attempts = 20  # Maximum number of OCR attempts per car

    while True:
        try:
            car_data = ocr_queue.get(timeout=1)
            if car_data is None:
                break

            track_id, image_path = car_data
            print(f"Processing OCR for track_id {track_id}, image: {image_path}")

            if track_id not in ocr_attempts:
                ocr_attempts[track_id] = {'attempts': 0, 'results': []}

            if ocr_attempts[track_id]['attempts'] < max_attempts:
                plate_text, confidence = perform_ocr(image_path)
                ocr_attempts[track_id]['attempts'] += 1
                ocr_attempts[track_id]['results'].append((plate_text, confidence))

                if ocr_attempts[track_id]['attempts'] >= max_attempts:
                    results = ocr_attempts[track_id]['results']
                    if results:
                        plate_counts = Counter(result[0] for result in results)
                        most_common_plate, count = plate_counts.most_common(1)[0]
                        avg_confidence = sum(result[1] for result in results if result[0] == most_common_plate) / count

                        if is_valid_plate(most_common_plate) and avg_confidence > 0.7:
                            plate_text = most_common_plate
                        else:
                            plate_text = "Unknown"
                    else:
                        plate_text = "Unknown"

                    violation_id = log_violation(plate_text, stationary_cars[track_id][1], image_path)
                    stationary_cars[track_id] = (violation_id, stationary_cars[track_id][1], image_path)
                    print(f"Illegal parking logged for car with track_id {track_id}. License plate: {plate_text}")
                    print(f"Violation logged with ID: {violation_id}")

                    del ocr_attempts[track_id]
                    print(f"OCR data for car with track_id {track_id} has been deleted.")
                else:
                    ocr_queue.put((track_id, image_path))

        except queue.Empty:
            continue
        except Exception as e:
            print(f"Unexpected error in OCR thread: {str(e)}")

    print("OCR thread exiting.")


class ViolationLogGUI:
    def __init__(self, master):
        self.master = master
        master.title("Parking Violation Logs")

        self.tree = ttk.Treeview(master, columns=('ID', 'Timestamp', 'License Plate', 'Location', 'Duration', 'Image'),
                                 show='headings', height=20)
        self.tree.heading('ID', text='ID')
        self.tree.heading('Timestamp', text='Timestamp')
        self.tree.heading('License Plate', text='License Plate')
        self.tree.heading('Location', text='Location')
        self.tree.heading('Duration', text='Duration (s)')
        self.tree.heading('Image', text='Image')

        self.tree.column('ID', width=100)
        self.tree.column('Timestamp', width=150)
        self.tree.column('License Plate', width=100)
        self.tree.column('Location', width=100)
        self.tree.column('Duration', width=100)
        self.tree.column('Image', width=200)

        self.tree.pack(fill=tk.BOTH, expand=1)

        # Add buttons frame
        button_frame = tk.Frame(master)
        button_frame.pack()

        self.remove_button = tk.Button(button_frame, text="Remove Selected", command=self.remove_selected)
        self.remove_button.pack(side=tk.LEFT, padx=5)

        self.notify_button = tk.Button(button_frame, text="Send Test Notification", command=self.send_test_notification)
        self.notify_button.pack(side=tk.LEFT, padx=5)

        self.tree.bind("<Double-1>", self.on_double_click)

        self.image_refs = {}  # Store references to images
        self.update_logs()

    def update_logs(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        cursor.execute(
            "SELECT id, timestamp, license_plate, location, parking_duration, image_path FROM violations ORDER BY timestamp DESC")
        for row in cursor.fetchall():
            self.tree.insert('', 'end', values=row)

        self.master.after(5000, self.update_logs)  # Update every 5 seconds

    def on_double_click(self, event):
        item = self.tree.selection()[0]
        image_path = self.tree.item(item, "values")[5]  # Assuming image_path is the 6th column
        self.show_full_image(image_path)

    def show_full_image(self, image_path):
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.thumbnail((1280, 720))  # Resize image if it's too large
                photo = ImageTk.PhotoImage(img)

                top = tk.Toplevel(self.master)
                top.title("Vehicle Image")
                label = tk.Label(top, image=photo)
                label.image = photo  # Keep a reference
                label.pack()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open image: {str(e)}")
        else:
            messagebox.showerror("Error", f"Image not found: {image_path}")

    def remove_selected(self):
        selected_items = self.tree.selection()
        if selected_items:
            if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the selected violation(s)?"):
                for item in selected_items:
                    violation_id = self.tree.item(item, "values")[0]
                    self.remove_violation(violation_id)
                    self.tree.delete(item)
                    if item in self.image_refs:
                        del self.image_refs[item]

    def remove_violation(self, violation_id):
        cursor.execute("SELECT image_path FROM violations WHERE id = ?", (violation_id,))
        result = cursor.fetchone()
        if result:
            image_path = result[0]

        cursor.execute("DELETE FROM violations WHERE id = ?", (violation_id,))
        conn.commit()
        print(f"Violation with ID {violation_id} has been removed from the database.")

    def send_test_notification(self):
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title='Test Notification',
                    body='This is a test notification from the parking violation system'
                ),
                topic='parking_violations'  # Send to all subscribed devices
            )

            response = messaging.send(message)
            messagebox.showinfo("Success", "Test notification sent!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to send notification: {str(e)}")


# Start the GUI in a separate thread
# gui_thread = threading.Thread(target=run_gui, daemon=True)
# gui_thread.start()

# In your main processing loop, you would call:
# handle_stationary_car(car_image, track_id, stationary_cars)
# When a car leaves or the program ends:
# finalize_stationary_car(track_id, stationary_cars)

# Don't forget to close the database connection when your program ends
# conn.close()

# Start the OCR thread
stationary_cars = {}
ocr_queue = queue.Queue()
ocr_thread = threading.Thread(target=start_ocr_thread, args=(ocr_queue, stationary_cars), daemon=True)
ocr_thread.start()

