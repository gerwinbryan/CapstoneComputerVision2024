import cv2
import numpy as np
import json
import os
import time

def select_region(image_path, width, height, json_path='region.json'):
    print(f"Attempting to connect to RTSP stream: {image_path}")

    try:
        # Create VideoCapture object
        cap = cv2.VideoCapture(image_path)

        # Check if camera opened successfully
        if not cap.isOpened():
            raise ValueError("Unable to open video source")

        print("Successfully connected to RTSP stream.")

        # Read frames until we get a valid frame
        while True:
            ret, frame = cap.read()
            if ret:
                break
            elif cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
                raise ValueError("End of video reached without getting a frame")

        print("Successfully read the first frame of the video.")

        # Resize frame to match the video dimensions
        frame = cv2.resize(frame, (width, height))

        # Release the capture object
        cap.release()

        # Check if region file exists
        if os.path.exists(json_path):
            use_existing = input("Existing region found. Use it? (y/n): ").lower() == 'y'
            if use_existing:
                with open(json_path, 'r') as f:
                    return np.array(json.load(f), dtype=np.int32)

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

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

if __name__ == "__main__":
    # Test the function
    image_path = "rtsp://admin:admin123@192.168.1.108:554/cam/realmonitor?channel=3&subtype=0"
    width = 1280
    height = 720
    
    try:
        region = select_region(image_path, width, height)
        if region is not None:
            print("Selected region:", region)
    except Exception as e:
        print(f"Failed to read video stream: {str(e)}")