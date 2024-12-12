# Configuration parameters
QUEUE_SIZE = 30
DISPLAY_WIDTH = 960
DISPLAY_HEIGHT = 540
TARGET_FPS = 79
MOVEMENT_THRESHOLD = 50  # Increased threshold for movement detection
STATIONARY_FRAMES = 60  # Number of frames to consider a car stationary (now easily adjustable)
MAX_TRACKING_AGE = 5  # Maximum number of seconds to keep tracking data
ILLEGAL_PARKING_FRAMES = 900 # Number of frames before logging violation (5 seconds at 60 FPS)
# Add other configuration parameters here
