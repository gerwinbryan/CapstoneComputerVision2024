from ultralytics import YOLO
from ultralytics.utils import LOGGER
LOGGER.info = lambda x: None  # Suppress info messages
LOGGER.warning = lambda x: None  # Suppress warnings too if needed

import cv2
import numpy as np
import threading
import queue
import time
from collections import defaultdict
import tkinter as tk
from region_selector import select_region
from parking_monitor import handle_stationary_car, finalize_stationary_car, ViolationLogGUI, start_ocr_thread
from input_gui import InputConfigGUI, confirm_region_selection
from config import *
import tkinter.messagebox as messagebox

# Load YOLOv8 models
car_model = YOLO('models/yolov8n.pt')
plate_model = YOLO('models/license_plate_detection.pt')

# Get input configuration
input_gui = InputConfigGUI()
setup_complete, input_path, cap = input_gui.run()

if not setup_complete:
    print("Setup cancelled. Exiting.")
    exit()

# Get video dimensions
video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Select region of interest before starting threads
region = select_region(input_path, video_width, video_height, confirm_callback=confirm_region_selection)
if region is None:
    print("Region selection failed. Exiting.")
    cap.release()
    exit()

# Create a mask for the selected region
mask = np.zeros((video_height, video_width), dtype=np.uint8)
cv2.fillPoly(mask, [region], 255)

# Shared queue and control flags
frame_queue = queue.Queue(maxsize=QUEUE_SIZE)
ocr_queue = queue.Queue()
program_running = True

# Tracking data
track_history = defaultdict(lambda: [])
car_statuses = defaultdict(lambda: "Unknown")
stationary_cars = {}
stationary_frame_counts = defaultdict(int)  # Track how long each car has been stationary


def read_frames():
    global program_running
    frame_count = 0
    while program_running:
        ret, frame = cap.read()
        if not ret:
            program_running = False
            break

        frame_count += 1

        if frame_queue.full():
            frame_queue.get()
        frame_queue.put((frame, frame_count, time.time()))

        time.sleep(1 / TARGET_FPS)


def process_and_display():
    global program_running, track_history
    start_time = time.time()
    frame_count = 0

    # Create named window
    cv2.namedWindow('Car and License Plate Detection')

    while program_running:
        if frame_queue.empty():
            time.sleep(0.01)
            continue

        try:
            frame, frame_count, frame_time = frame_queue.get()
        except:
            continue

        # Check if window was closed
        if cv2.getWindowProperty('Car and License Plate Detection', cv2.WND_PROP_VISIBLE) < 1:
            if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the program?"):
                program_running = False
                break
            else:
                # Recreate window if user cancels
                cv2.namedWindow('Car and License Plate Detection')

        # Resize frame to match the mask size
        frame = cv2.resize(frame, (video_width, video_height))
        masked_frame = cv2.bitwise_and(frame, frame, mask=mask)

        car_results = car_model.track(masked_frame, persist=True)[0]

        for car_box in car_results.boxes:
            if car_box.cls == 2:  # Assuming class 2 is for cars
                x1, y1, x2, y2 = map(int, car_box.xyxy[0])

                if mask[int((y1 + y2) / 2), int((x1 + x2) / 2)] == 0:
                    continue

                # Expand the crop area by 50 pixels in each direction
                crop_x1 = max(0, x1 - 50)
                crop_y1 = max(0, y1 - 50)
                crop_x2 = min(frame.shape[1], x2 + 50)
                crop_y2 = min(frame.shape[0], y2 + 50)

                # Get the original image crop without bounding boxes
                car_img = frame.copy()[crop_y1:crop_y2, crop_x1:crop_x2]
                
                # Draw car bounding box on the main display frame
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Get the display crop with bounding boxes
                display_car_img = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                display_car_img = cv2.resize(display_car_img, (DISPLAY_WIDTH, DISPLAY_HEIGHT))

                # Detect license plate on the clean crop
                plate_results = plate_model(car_img)[0]

                if len(plate_results.boxes) > 0:
                    plate_box = plate_results.boxes[0]
                    px1, py1, px2, py2 = map(int, plate_box.xyxy[0])
                    
                    # Draw plate box on main frame
                    cv2.rectangle(frame, 
                                (crop_x1 + px1, crop_y1 + py1), 
                                (crop_x1 + px2, crop_y1 + py2), 
                                (255, 0, 0), 2)

                track_id = int(car_box.id) if car_box.id is not None else -1
                if track_id != -1:
                    car_center = ((x1 + x2) // 2, (y1 + y2) // 2)
                    track = track_history[track_id]
                    track.append((frame_time, car_center))

                    if len(track) > STATIONARY_FRAMES:
                        track.pop(0)

                        start_pos = np.array(track[0][1])
                        end_pos = np.array(track[-1][1])
                        total_distance = np.linalg.norm(end_pos - start_pos)
                        time_diff = track[-1][0] - track[0][0]

                        if time_diff > 0:
                            speed = total_distance / time_diff
                            if speed < MOVEMENT_THRESHOLD:
                                car_statuses[track_id] = "Stationary"
                                if track_id not in stationary_frame_counts:
                                    stationary_frame_counts[track_id] = frame_count

                                if (frame_count - stationary_frame_counts[track_id]) >= ILLEGAL_PARKING_FRAMES:
                                    handle_stationary_car(car_img, track_id, stationary_cars, ocr_queue)
                            else:
                                car_statuses[track_id] = "Moving"
                                if track_id in stationary_frame_counts:
                                    del stationary_frame_counts[track_id]
                                if track_id in stationary_cars:
                                    finalize_stationary_car(track_id, stationary_cars)

                    # Convert track IDs to a set of integers
                    current_tracks = {int(box.id) for box in car_results.boxes if box.id is not None}
                    old_tracks = set(track_history.keys()) - current_tracks
                    for old_id in old_tracks:
                        if old_id in track_history:
                            del track_history[old_id]
                        if old_id in car_statuses:
                            del car_statuses[old_id]
                        if old_id in stationary_frame_counts:
                            del stationary_frame_counts[old_id]

                    status = car_statuses[track_id]
                    cv2.putText(frame, status, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                                (0, 0, 255) if status == "Stationary" else (255, 0, 0), 2)

        cv2.polylines(frame, [region], True, (0, 255, 255), 2)

        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Frame: {frame_count}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Car and License Plate Detection', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the program?"):
                program_running = False
                break

    # Finalize all stationary cars when the program ends
    for track_id in list(stationary_cars.keys()):
        finalize_stationary_car(track_id, stationary_cars)

    # Cleanup
    cv2.destroyAllWindows()


def run_gui():
    root = tk.Tk()
    gui = ViolationLogGUI(root)
    root.mainloop()


if __name__ == "__main__":
    # Start threads
    read_thread = threading.Thread(target=read_frames)
    process_thread = threading.Thread(target=process_and_display)
    gui_thread = threading.Thread(target=run_gui, daemon=True)
    ocr_thread = threading.Thread(target=start_ocr_thread, args=(ocr_queue, stationary_cars), daemon=True)

    read_thread.start()
    process_thread.start()
    gui_thread.start()
    ocr_thread.start()

    # Wait for threads to finish
    read_thread.join()
    process_thread.join()

    # Cleanup
    ocr_queue.put(None)  # Signal OCR thread to exit

    cap.release()
    cv2.destroyAllWindows()

    print("Video processing completed")
