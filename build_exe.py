import PyInstaller.__main__
import os
import sys
import paddle
import paddleocr

# Get the current directory and paths
current_dir = os.path.dirname(os.path.abspath(__file__))
paddle_path = os.path.dirname(paddle.__file__)
paddleocr_path = os.path.dirname(paddleocr.__file__)

PyInstaller.__main__.run([
    'main.py',
    '--name=ParkingViolationDetector',
    '--onedir',
    '--windowed',
    '--noconfirm',
    # Add data files
    f'--add-data={os.path.join(current_dir, "models")};models',
    f'--add-data={os.path.join(paddleocr_path, "tools")};tools',
    f'--add-data={os.path.join(paddle_path, "libs")};paddle/libs',
    f'--add-data={os.path.join(paddleocr_path, "ppocr")};ppocr',
    # Hidden imports
    '--hidden-import=paddleocr',
    '--hidden-import=paddle',
    '--hidden-import=ultralytics',
    '--hidden-import=cv2',
    '--hidden-import=numpy',
    '--hidden-import=PIL',
    '--hidden-import=skimage',
    '--hidden-import=shapely',
    '--hidden-import=pyclipper',
    '--hidden-import=lanms',
    # Collect all data
    '--collect-all=paddleocr',
    '--collect-all=paddle',
    '--collect-all=ultralytics',
]) 