import cv2
import numpy as np
from sklearn.cluster import KMeans

class ColorDetector:
    def __init__(self):
        # Base color ranges (day conditions)
        self.day_ranges = {
            'white': ([0, 0, 200], [180, 30, 255]),
            'black': ([0, 0, 0], [180, 30, 50]),
            'red': ([0, 50, 50], [10, 255, 255], [170, 50, 50], [180, 255, 255]),
            'blue': ([100, 50, 50], [130, 255, 255]),
            'silver': ([0, 0, 140], [180, 30, 200]),
            'gray': ([0, 0, 70], [180, 30, 140]),
            'metallic_blue': ([100, 30, 70], [130, 150, 255]),
            'dark_metallic_blue': ([100, 30, 50], [130, 150, 200]),
            'light_metallic_blue': ([100, 20, 100], [130, 120, 255]),
            'pearl_white': ([0, 0, 180], [180, 20, 255]),
            'metallic_gray': ([0, 0, 100], [180, 30, 180]),
            'metallic_silver': ([0, 0, 160], [180, 25, 220]),
            'metallic_black': ([0, 0, 20], [180, 30, 80]),
            'burgundy': ([0, 50, 20], [10, 255, 150], [170, 50, 20], [180, 255, 150]),
            'brown': ([10, 30, 20], [20, 255, 200]),
            'beige': ([20, 10, 170], [30, 50, 255]),
            'gold': ([20, 30, 100], [30, 150, 255]),
            'green': ([40, 50, 50], [80, 255, 255]),
            'yellow': ([20, 50, 50], [35, 255, 255])
        }

        # Night-specific ranges (more strict)
        self.night_ranges = {
            'white': ([0, 0, 180], [180, 40, 255]),
            'black': ([0, 0, 0], [180, 45, 40]),
            'red': ([0, 60, 40], [10, 255, 255], [170, 60, 40], [180, 255, 255]),
            'blue': ([100, 60, 40], [130, 255, 255]),
            'silver': ([0, 0, 130], [180, 40, 200]),
            'gray': ([0, 0, 60], [180, 40, 130]),
            'metallic_blue': ([100, 40, 60], [130, 160, 255]),
            'dark_metallic_blue': ([100, 40, 40], [130, 160, 200]),
            'light_metallic_blue': ([100, 30, 90], [130, 130, 255]),
            'pearl_white': ([0, 0, 170], [180, 30, 255]),
            'metallic_gray': ([0, 0, 90], [180, 40, 170]),
            'metallic_silver': ([0, 0, 150], [180, 35, 220]),
            'metallic_black': ([0, 0, 10], [180, 40, 70]),
            'burgundy': ([0, 60, 20], [10, 255, 140], [170, 60, 20], [180, 255, 140]),
            'brown': ([10, 40, 20], [20, 255, 180]),
            'beige': ([20, 20, 160], [30, 60, 255]),
            'gold': ([20, 50, 120], [30, 150, 255]),
            'green': ([40, 60, 40], [80, 255, 255]),
            'yellow': ([20, 70, 70], [35, 255, 255])
        }

        # Define metallic colors for special handling
        self.metallic_colors = {
            'metallic_blue', 'dark_metallic_blue', 'light_metallic_blue',
            'metallic_gray', 'metallic_silver', 'metallic_black', 'pearl_white'
        }

        # Night detection penalties
        self.night_penalties = {
            'yellow': 0.8,
            'gold': 0.85,
            'brown': 0.7,
            'beige': 0.6,
            'white': 0.2,
            'silver': 0.3
        }

        # Color weights for better discrimination
        self.color_weights = {
            'black': 1.4,
            'gray': 0.8,
            'metallic_gray': 0.85,
            'yellow': 0.5
        }

        # Weights
        self.segmentation_weight = 0.6
        self.histogram_weight = 0.4
        
        # Debug flags
        self.debug_mode = True
        self.save_debug_images = False

    def detect_lighting_condition(self, img):
        """Detect if image was taken in day or night conditions"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray)
        
        # Calculate brightness histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        dark_pixels = np.sum(hist[:70]) / np.sum(hist)  # Percentage of dark pixels
        
        # Calculate brightness variance (for detecting reflections)
        brightness_std = np.std(gray)
        
        # Calculate high intensity pixels (for detecting light sources)
        _, bright_spots = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        bright_pixel_ratio = np.sum(bright_spots) / (img.shape[0] * img.shape[1])
        
        # Night conditions (more comprehensive):
        # 1. Either low average brightness or high dark pixel ratio
        # 2. High brightness variance from reflections/lights
        # 3. Presence of bright spots (typical in night scenes)
        is_night = (
            (avg_brightness < 85 or dark_pixels > 0.6) and  # Basic darkness check
            brightness_std > 40 and                         # Reflection check
            bright_pixel_ratio > 0.01                      # Light sources present
        )
        
        if self.debug_mode:
            print("\n=== Lighting Analysis ===")
            print(f"Average brightness: {avg_brightness:.2f}")
            print(f"Dark pixel ratio: {dark_pixels:.2f}")
            print(f"Brightness variance: {brightness_std:.2f}")
            print(f"Bright pixel ratio: {bright_pixel_ratio:.4f}")
            print(f"Detected lighting: {'night' if is_night else 'day'}")
            print("========================\n")
            
        return "night" if is_night else "day"

    def detect_light_sources(self, img):
        """Detect bright light sources that might affect color detection"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, bright_spots = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        return np.sum(bright_spots) > (img.shape[0] * img.shape[1] * 0.1)  # 10% threshold

    def is_two_tone(self, img):
        """Detect if vehicle might be two-tone by analyzing top and bottom halves"""
        height = img.shape[0]
        top_half = img[0:height//2, :]
        bottom_half = img[height//2:, :]
        
        top_color = self.get_dominant_color(top_half)
        bottom_color = self.get_dominant_color(bottom_half)
        
        return top_color != bottom_color, (top_color, bottom_color)

    def get_color_ranges(self, lighting):
        """Get appropriate color ranges based on lighting condition"""
        return self.night_ranges if lighting == "night" else self.day_ranges

    def adjust_scores_for_lighting(self, scores, lighting, img):
        """Apply penalties to scores based on lighting conditions"""
        if lighting == "night":
            adjusted_scores = scores.copy()
            
            # Calculate reflection intensity
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness_std = np.std(gray)
            
            # Calculate bright spots
            _, bright_spots = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            bright_pixel_ratio = np.sum(bright_spots) / (img.shape[0] * img.shape[1])
            
            # Apply standard night penalties
            for color, penalty in self.night_penalties.items():
                if color in adjusted_scores:
                    adjusted_scores[color] *= (1 - penalty)
            
            # Sanity check for gold/yellow at night
            if bright_pixel_ratio < 0.05:  # If there aren't many bright spots
                for color in ['yellow', 'gold']:
                    if color in adjusted_scores and adjusted_scores[color] > 0.3:
                        adjusted_scores[color] *= 0.1  # Severe penalty
                        if self.debug_mode:
                            print(f"Applied severe penalty to {color} due to low bright spots")
            
            return adjusted_scores
        return scores

    def get_dominant_color(self, img):
        try:
            # Detect lighting condition
            lighting = self.detect_lighting_condition(img)
            color_ranges = self.get_color_ranges(lighting)
            
            # Preprocess image
            img = self.preprocess_image(img)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            if self.debug_mode:
                print("\n=== Starting color detection ===")
                print(f"Lighting condition: {lighting}")
                print(f"Image shape: {img.shape}")

            # Get segmentation scores
            color_scores = {}
            for color, ranges in color_ranges.items():
                if color == 'red':  # Special case for red
                    mask1 = cv2.inRange(hsv, np.array(ranges[0]), np.array(ranges[1]))
                    mask2 = cv2.inRange(hsv, np.array(ranges[2]), np.array(ranges[3]))
                    mask = cv2.bitwise_or(mask1, mask2)
                else:
                    mask = cv2.inRange(hsv, np.array(ranges[0]), np.array(ranges[1]))
                
                color_scores[color] = np.sum(mask) / (hsv.shape[0] * hsv.shape[1] * 255)

            # Get histogram scores
            hist_scores = self.get_histogram_scores(hsv)

            # Combine scores
            final_scores = {}
            for color in color_ranges.keys():
                seg_score = color_scores[color] / max(color_scores.values()) if color_scores.values() else 0
                hist_score = hist_scores[color] / max(hist_scores.values()) if hist_scores.values() else 0
                
                final_scores[color] = (self.segmentation_weight * seg_score + 
                                     self.histogram_weight * hist_score)

            # Apply lighting-based adjustments
            final_scores = self.adjust_scores_for_lighting(final_scores, lighting, img)

            # Apply color-specific weights
            for color, weight in self.color_weights.items():
                if color in final_scores:
                    final_scores[color] *= weight

            # Sort scores
            top_colors = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Check for two-tone possibility
            top_two_colors = top_colors[:2]
            if (top_two_colors[0][1] - top_two_colors[1][1]) < 0.3:  # Close scores
                if {'black', 'white'}.intersection({c[0] for c in top_two_colors}):
                    if self.debug_mode:
                        print("Detected possible two-tone vehicle")
                    return f"{top_two_colors[0][0]}/{top_two_colors[1][0]}"
            
            # Metallic color handling
            metallic_detected = False
            metallic_score = 0
            metallic_color = None
            
            for color, score in top_colors[:3]:
                if color in self.metallic_colors and score > 0.6:
                    metallic_detected = True
                    if score > metallic_score:
                        metallic_score = score
                        metallic_color = color

            # Adjust black score if metallic color is detected
            if metallic_detected and 'black' in final_scores:
                if final_scores['black'] > metallic_score:
                    reduction = metallic_score * 0.5
                    final_scores['black'] *= (1 - reduction)
                    
                    if self.debug_mode:
                        print(f"Reduced black score due to {metallic_color} detection")
                        print(f"Original black score: {final_scores['black']:.4f}")

            # Get final results
            top_colors = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
            
            if self.debug_mode:
                print("\n=== Final Results ===")
                print(f"Final color scores: {final_scores}")
                print(f"Top color predictions: {top_colors[:2]}")
            
            predicted_color = top_colors[0][0]
            confidence = top_colors[0][1]
            
            print(f"Detected color: {predicted_color}")
            print(f"Confidence: {confidence:.4f}")
            
            return predicted_color

        except Exception as e:
            print(f"Error in color detection: {str(e)}")
            return "unknown"

    def preprocess_image(self, img):
        """Preprocess image for better color detection"""
        img = cv2.resize(img, (300, 300))
        img = cv2.GaussianBlur(img, (5, 5), 0)
        return img

    def get_histogram_scores(self, hsv):
        """Get scores based on histogram analysis"""
        hist_scores = {}
        color_ranges = self.day_ranges  # Use day ranges for histogram analysis
        
        for color, ranges in color_ranges.items():
            if color == 'red':
                mask1 = cv2.inRange(hsv, np.array(ranges[0]), np.array(ranges[1]))
                mask2 = cv2.inRange(hsv, np.array(ranges[2]), np.array(ranges[3]))
                mask = cv2.bitwise_or(mask1, mask2)
            else:
                mask = cv2.inRange(hsv, np.array(ranges[0]), np.array(ranges[1]))
            
            hist = cv2.calcHist([hsv], [0], mask, [180], [0, 180])
            hist_scores[color] = np.sum(hist)
        
        return hist_scores

    def download_weights(self):
        """Placeholder for compatibility with existing code"""
        pass