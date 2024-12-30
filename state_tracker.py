from collections import deque, defaultdict
import time
import numpy as np

class StateHistory:
    def __init__(self, queue_size=30):
        self.state_queue = deque(maxlen=queue_size)
        self.timestamp_queue = deque(maxlen=queue_size)
        self.position_queue = deque(maxlen=queue_size)
        self.last_known_state = "Unknown"
        self.last_confident_state = "Unknown"
        self.confidence_threshold = 0.4  # Reduced from 0.6 to 0.4

    def add_state(self, state, position, timestamp):
        self.state_queue.append(state)
        self.position_queue.append(position)
        self.timestamp_queue.append(timestamp)
        self._update_state()

    def _update_state(self):
        if not self.state_queue:
            return "Unknown"

        # Count states in recent history
        state_counts = defaultdict(float)  # Changed to float for better precision
        total_states = len(self.state_queue)
        
        # Enhanced weighting system
        for idx, state in enumerate(self.state_queue):
            # Exponential weighting - more recent states have much higher weight
            weight = 2 ** (idx / (total_states/2))  # Modified weight calculation
            state_counts[state] += weight
            
        # Ignore "Unknown" state in decision making if we have other states
        valid_states = {k: v for k, v in state_counts.items() if k != "Unknown"}
        if valid_states:
            state_counts = valid_states

        # Get most common state
        if state_counts:
            max_count = max(state_counts.values())
            total_weights = sum(state_counts.values())
            confidence = max_count / total_weights

            most_common = max(state_counts.items(), key=lambda x: x[1])[0]

            # More lenient state updating
            if confidence >= self.confidence_threshold:
                self.last_confident_state = most_common
                self.last_known_state = most_common
            elif self.last_confident_state != "Unknown":
                # Keep last confident state if we had one
                self.last_known_state = self.last_confident_state

        return self.last_known_state

    def get_current_state(self):
        return self.last_known_state

class StateTracker:
    def __init__(self, queue_size=30):
        self.state_histories = {}
        self.queue_size = queue_size
        self.track_history = defaultdict(lambda: [])
        self.stationary_frame_counts = defaultdict(int)

    def update_state(self, track_id, position, current_time, movement_detected):
        # Initialize state history if needed
        if track_id not in self.state_histories:
            self.state_histories[track_id] = StateHistory(self.queue_size)

        # More sensitive movement detection
        current_state = "Moving" if movement_detected else "Stationary"
        
        # Store position history for movement calculation
        self.track_history[track_id].append((current_time, position))
        
        # Calculate movement from recent positions
        if len(self.track_history[track_id]) >= 2:
            recent_positions = [pos for _, pos in self.track_history[track_id][-2:]]
            movement = np.linalg.norm(np.array(recent_positions[1]) - np.array(recent_positions[0]))
            if movement > 5:  # Adjust this threshold as needed
                current_state = "Moving"
        
        # Update state history
        self.state_histories[track_id].add_state(current_state, position, current_time)
        
        # Cleanup old track history
        while len(self.track_history[track_id]) > self.queue_size:
            self.track_history[track_id].pop(0)

        return self.state_histories[track_id].get_current_state()

    def clean_old_tracks(self, current_tracks):
        """Remove tracks that are no longer active"""
        for track_id in list(self.state_histories.keys()):
            if track_id not in current_tracks:
                # Increased retention time for occlusions
                last_timestamp = self.state_histories[track_id].timestamp_queue[-1] if self.state_histories[track_id].timestamp_queue else 0
                if time.time() - last_timestamp > 10:  # Increased from 5 to 10 seconds
                    del self.state_histories[track_id]
                    if track_id in self.track_history:
                        del self.track_history[track_id]

    def get_state(self, track_id):
        """Get current state for a track"""
        if track_id in self.state_histories:
            return self.state_histories[track_id].get_current_state()
        return "Unknown"
