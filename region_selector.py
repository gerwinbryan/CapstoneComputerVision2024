import cv2
import numpy as np
import json
import os


def select_region(image_path, width, height, json_path='region.json'):
    # Check if region file exists
    if os.path.exists(json_path):
        use_existing = input("Existing region found. Use it? (y/n): ").lower() == 'y'
        if use_existing:
            with open(json_path, 'r') as f:
                return np.array(json.load(f), dtype=np.int32)

    # Read the first frame of the video
    cap = cv2.VideoCapture(image_path)
    ret, frame = cap.read()
    if not ret:
        print("Failed to read the video file.")
        return None
    cap.release()

    # Resize frame to match the video dimensions
    frame = cv2.resize(frame, (width, height))

    # Create a window and set mouse callback
    cv2.namedWindow("Select Region")
    points = []
    current_point = 0

    def mouse_callback(event, x, y, flags, param):
        nonlocal points, current_point
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) < 4:
                points.append((x, y))
            else:
                points[current_point] = (x, y)
                current_point = (current_point + 1) % 4

            # Redraw the frame and points
            frame_copy = frame.copy()
            for i, pt in enumerate(points):
                color = (0, 0, 255) if i == current_point else (0, 255, 0)
                cv2.circle(frame_copy, pt, 5, color, -1)
            if len(points) > 1:
                pts = np.array(points + [points[0]], np.int32)
                cv2.polylines(frame_copy, [pts], True, (0, 255, 0), 2)
            cv2.imshow("Select Region", frame_copy)

    cv2.setMouseCallback("Select Region", mouse_callback)

    # Main loop for region selection
    while True:
        frame_copy = frame.copy()
        for i, pt in enumerate(points):
            color = (0, 0, 255) if i == current_point else (0, 255, 0)
            cv2.circle(frame_copy, pt, 5, color, -1)
        if len(points) > 1:
            pts = np.array(points + [points[0]], np.int32)
            cv2.polylines(frame_copy, [pts], True, (0, 255, 0), 2)
        cv2.imshow("Select Region", frame_copy)

        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # Enter key
            break
        elif key == 27:  # Esc key
            points = []
            break

    cv2.destroyAllWindows()

    if len(points) < 4:
        print("Not enough points selected. Please select exactly 4 points.")
        return None

    # Save the region to JSON file
    with open(json_path, 'w') as f:
        json.dump(points, f)

    # Convert points to numpy array
    region = np.array(points, dtype=np.int32)
    return region


if __name__ == "__main__":
    # Test the function
    region = select_region("front.MP4", 1280, 720)  # Example dimensions
    if region is not None:
        print("Selected region:", region)
