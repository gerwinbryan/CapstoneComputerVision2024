import PyInstaller.__main__
import os
import sys
import paddle
import paddleocr
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Get the current directory and paths
current_dir = os.path.dirname(os.path.abspath(__file__))
paddle_path = os.path.dirname(paddle.__file__)
paddleocr_path = os.path.dirname(paddleocr.__file__)

# Additional data paths
models_dir = os.path.join(current_dir, "models")
firebase_config = os.path.join(current_dir, "firebase-adminsdk.json")

# Verify required files exist
required_files = [
    (models_dir, "models directory"),
    (firebase_config, "Firebase admin SDK config")
]

for file_path, description in required_files:
    if not os.path.exists(file_path):
        print(f"ERROR: Required {description} not found at {file_path}")
        sys.exit(1)

PyInstaller.__main__.run([
    'main.py',
    '--name=ParkingViolationDetector',
    '--onedir',
    '--windowed',
    '--noconfirm',
    '--clean',  # Clean PyInstaller cache
    
    # Add data files
    f'--add-data={models_dir};models',
    f'--add-data={os.path.join(paddleocr_path, "tools")};tools',
    f'--add-data={os.path.join(paddle_path, "libs")};paddle/libs',
    f'--add-data={os.path.join(paddleocr_path, "ppocr")};ppocr',
    f'--add-data={firebase_config};.',
    
    # Additional data files
    '--add-data=config.py;.',
    
    # Hidden imports
    '--hidden-import=paddleocr',
    '--hidden-import=paddle',
    '--hidden-import=paddle.base.proto',
    '--hidden-import=ultralytics',
    '--hidden-import=cv2',
    '--hidden-import=numpy',
    '--hidden-import=PIL',
    '--hidden-import=skimage',
    '--hidden-import=shapely',
    '--hidden-import=pyclipper',
    '--hidden-import=lanms',
    '--hidden-import=sklearn',
    '--hidden-import=sklearn.cluster',
    '--hidden-import=sklearn.cluster._kmeans',
    '--hidden-import=sklearn.utils',
    '--hidden-import=sklearn.preprocessing',
    '--hidden-import=firebase_admin',
    '--hidden-import=firebase_admin.credentials',
    '--hidden-import=firebase_admin.messaging',
    '--hidden-import=firebase_admin.firestore',
    '--hidden-import=tkinter',
    '--hidden-import=queue',
    '--hidden-import=threading',
    '--hidden-import=json',
    '--hidden-import=datetime',
    '--hidden-import=openpyxl',
    '--hidden-import=torch',
    '--hidden-import=paddle.fluid.proto',
    '--hidden-import=paddle.fluid.proto.framework_pb2',
    '--hidden-import=collections',
    '--hidden-import=collections.defaultdict',
    '--hidden-import=deque',
    
    # Collect all required packages
    '--collect-all=paddleocr',
    '--collect-all=paddle',
    '--collect-all=ultralytics',
    '--collect-all=firebase_admin',
    '--collect-all=sklearn',
    '--collect-all=torch',
    
    # Exclude unnecessary modules
    '--exclude-module=tensorboard',
    '--exclude-module=tensorflow',
    '--exclude-module=torch.utils.tensorboard',
    
    # Additional options
    '--log-level=WARN',  # Reduce log verbosity
])

print("Build completed successfully!") 