import cv2
import numpy as np
from ultralytics import YOLO
import threading
import queue
import time
from collections import defaultdict
import tkinter as tk
from region_selector import select_region
from parking_monitor import handle_stationary_car, finalize_stationary_car, ViolationLogGUI, start_ocr_thread
from input_gui import InputConfigGUI, confirm_region_selection
from config import *

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

    while program_running:
        if frame_queue.empty():
            time.sleep(0.01)
            continue

        frame, frame_count, frame_time = frame_queue.get()

        # Resize frame to match the mask size
        frame = cv2.resize(frame, (video_width, video_height))
        masked_frame = cv2.bitwise_and(frame, frame, mask=mask)

        car_results = car_model.track(masked_frame, persist=True)[0]

        for car_box in car_results.boxes:
            if car_box.cls == 2:  # Assuming class 2 is for cars
                x1, y1, x2, y2 = map(int, car_box.xyxy[0])

                if mask[int((y1 + y2) / 2), int((x1 + x2) / 2)] == 0:
                    continue

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                car_img = frame[y1:y2, x1:x2]
                display_car_img = cv2.resize(car_img, (DISPLAY_WIDTH, DISPLAY_HEIGHT))

                plate_results = plate_model(car_img)[0]

                if len(plate_results.boxes) > 0:
                    plate_box = plate_results.boxes[0]
                    px1, py1, px2, py2 = map(int, plate_box.xyxy[0])
                    cv2.rectangle(frame, (x1 + px1, y1 + py1), (x1 + px2, y1 + py2), (255, 0, 0), 2)

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
                                handle_stationary_car(display_car_img, track_id, stationary_cars, ocr_queue)
                            else:
                                car_statuses[track_id] = "Moving"
                                if track_id in stationary_cars:
                                    finalize_stationary_car(track_id, stationary_cars)

                    status = car_statuses[track_id]
                    cv2.putText(frame, status, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                                (0, 0, 255) if status == "Stationary" else (255, 0, 0), 2)

        cv2.polylines(frame, [region], True, (0, 255, 255), 2)

        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Frame: {frame_count}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Car and License Plate Detection', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            program_running = False
            break

    # Finalize all stationary cars when the program ends
    for track_id in list(stationary_cars.keys()):
        finalize_stationary_car(track_id, stationary_cars)


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
