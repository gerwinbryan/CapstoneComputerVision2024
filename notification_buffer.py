import json
import os
import time
from datetime import datetime
from firebase_admin import messaging

class NotificationBuffer:
    _instance = None  # Singleton instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationBuffer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.buffer_file = "notification_buffer.json"
        self.default_buffer = {
            "pending_notifications": [],
            "last_notification_time": time.time(),
            "notification_settings": {
                "thresholds": [
                    {
                        "count": 1,
                        "time": 10800    # 3 hours 
                    },
                    {
                        "count": 5,
                        "time": 7200  # 2 hours
                    },
                    {
                        "count": 10,
                        "time": 3600  # 1 hour
                    },
                    {
                        "count": 20,
                        "time": 1800  # 30 minutes
                    }
                ]
            }
        }
        self.load_buffer()
        self._initialized = True
        print("NotificationBuffer initialized")

    def load_buffer(self):
        """Load or create buffer file"""
        if os.path.exists(self.buffer_file):
            with open(self.buffer_file, 'r') as f:
                self.buffer = json.load(f)
        else:
            self.buffer = self.default_buffer
            self.save_buffer()

    def save_buffer(self):
        """Save current buffer to file"""
        with open(self.buffer_file, 'w') as f:
            json.dump(self.buffer, f, indent=2)

    def add_notification(self, license_plate, color):
        """Add new notification to buffer"""
        notification = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "license_plate": license_plate,
            "color": color,
            "status": "pending"
        }
        self.buffer["pending_notifications"].append(notification)
        self.save_buffer()
        self.check_and_send()

    def check_and_send(self):
        """Check if conditions are met to send notifications"""
        pending = self.buffer["pending_notifications"]
        if not pending:
            return

        current_time = time.time()
        last_time = self.buffer["last_notification_time"]
        
        if last_time is None:
            self.buffer["last_notification_time"] = current_time
            self.save_buffer()
            return  # Don't send yet, just start the timer
        
        pending_count = len(pending)
        elapsed_time = current_time - last_time
        
        # Check thresholds from highest count to lowest
        thresholds = sorted(
            self.buffer["notification_settings"]["thresholds"],
            key=lambda x: x["count"],
            reverse=True
        )
        
        for threshold in thresholds:
            if pending_count >= threshold["count"]:
                if elapsed_time >= threshold["time"]:
                    self.send_notifications()
                    return  # Only return after sending
                break  # Exit loop after finding matching count threshold

    def send_notifications(self):
        """Send all pending notifications"""
        if not self.buffer["pending_notifications"]:
            return

        # Prepare message
        notifications = self.buffer["pending_notifications"]
        message_text = "New Illegal Parking:\n"
        for notif in notifications:
            message_text += f"- {notif['license_plate']} ({notif['color']})\n"

        # Send FCM message
        message = messaging.Message(
            notification=messaging.Notification(
                title="Illegal Parking Update",
                body=message_text
            ),
            topic="Illegal_Parking"
        )

        try:
            response = messaging.send(message)
            print(f"Successfully sent notification batch: {response}")
            
            # Clear sent notifications
            self.buffer["pending_notifications"] = []
            self.buffer["last_notification_time"] = time.time()
            self.save_buffer()
        except Exception as e:
            print(f"Error sending notification: {e}")

    def force_send(self):
        """Manually trigger sending of all pending notifications"""
        self.send_notifications()

    def update_notifications(self):
        # Check every X seconds (e.g., 30 seconds)
        self.master.after(30000, self.update_notifications)
