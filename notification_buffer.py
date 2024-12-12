import json
import os
from datetime import datetime, timedelta
import threading
import time

class NotificationBuffer:
    BUFFER_FILE = 'notification_buffer.json'
    
    # Constants for notification rules
    LOW_ACTIVITY_THRESHOLD = 10  # logs per hour
    HIGH_ACTIVITY_THRESHOLD = 50  # logs per hour
    IMMEDIATE_NOTIFY_THRESHOLD = 100  # instant notification if reached
    
    def __init__(self, telegram_bot=None, chat_id=None):
        print("Initializing NotificationBuffer")
        self.lock = threading.Lock()
        self.telegram_bot = telegram_bot
        self.chat_id = chat_id
        
        # Load or create buffer data
        self.buffer_data = self._load_buffer()
        
        self.notification_thread = threading.Thread(target=self._check_buffer, daemon=True)
        self.notification_thread.start()
        print("NotificationBuffer initialized successfully")

    def _load_buffer(self):
        try:
            if os.path.exists(self.BUFFER_FILE):
                with open(self.BUFFER_FILE, 'r') as f:
                    return json.load(f)
            else:
                # Enhanced default buffer structure
                default_buffer = {
                    'count': 0,
                    'last_notification': datetime.now().isoformat(),
                    'last_termination': datetime.now().isoformat(),  # New field
                    'pending_logs': [],
                    'notification_settings': {
                        'low_activity_hours': 3,    # wait longer if few violations
                        'normal_activity_hours': 1,  # standard wait time
                        'high_activity_minutes': 30  # quick notification for high activity
                    }
                }
                self._save_buffer(default_buffer)
                return default_buffer
        except Exception as e:
            print(f"Error loading buffer: {e}")
            return {
                'count': 0, 
                'last_notification': datetime.now().isoformat(),
                'last_termination': datetime.now().isoformat(),
                'pending_logs': [],
                'notification_settings': {
                    'low_activity_hours': 3,
                    'normal_activity_hours': 1,
                    'high_activity_minutes': 30
                }
            }

    def _save_buffer(self, data):
        with self.lock:  # Added lock for thread safety
            with open(self.BUFFER_FILE, 'w') as f:
                json.dump(data, f, indent=2)

    def update_termination_time(self):
        """Update termination time when program exits"""
        current_time = datetime.now()
        self.buffer_data['last_termination'] = current_time.isoformat()
        print(f"\nSaving termination time: {current_time}")
        self._save_buffer(self.buffer_data)
        print(f"Termination time saved to buffer file: {self.BUFFER_FILE}")

    def _calculate_activity_rate(self):
        """Calculate violations per hour based on pending logs"""
        if not self.buffer_data['pending_logs']:
            return 0
            
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # Count logs in the last hour
        recent_logs = [log for log in self.buffer_data['pending_logs'] 
                      if datetime.fromisoformat(log['timestamp']) > one_hour_ago]
        
        return len(recent_logs)

    def _should_send_notification(self):
        """Determine if notification should be sent based on various rules"""
        if not self.buffer_data['count']:
            return False
            
        current_time = datetime.now()
        last_notification = datetime.fromisoformat(self.buffer_data['last_notification'])
        last_termination = datetime.fromisoformat(self.buffer_data['last_termination'])
        
        # Calculate time differences
        time_since_notification = (current_time - last_notification).total_seconds()
        time_since_termination = (current_time - last_termination).total_seconds()
        total_wait_time = time_since_notification + time_since_termination
        
        hourly_rate = self._calculate_activity_rate()
        print(f"\nChecking notification conditions:")
        print(f"Current time: {current_time}")
        print(f"Last notification: {last_notification}")
        print(f"Last termination: {last_termination}")
        print(f"Time since notification: {time_since_notification/3600:.2f} hours")
        print(f"Time since termination: {time_since_termination/3600:.2f} hours")
        print(f"Total wait time: {total_wait_time/3600:.2f} hours")
        print(f"Current log count: {self.buffer_data['count']}")
        
        # Rule 1: Send immediately if count exceeds threshold
        if self.buffer_data['count'] >= self.IMMEDIATE_NOTIFY_THRESHOLD:
            print(f"Sending notification: Count ({self.buffer_data['count']}) exceeded immediate threshold")
            return True
            
        # Rule 2: Consider program termination time
        if total_wait_time > 5 * 3600:  # 5 hours total wait
            print(f"Sending notification: Total wait time ({total_wait_time/3600:.2f} hours) exceeded 5 hours")
            return True
            
        # Get activity rate
        hourly_rate = self._calculate_activity_rate()
        print(f"Current hourly violation rate: {hourly_rate}")
        
        # Rule 3: Activity-based rules
        if hourly_rate >= self.HIGH_ACTIVITY_THRESHOLD:
            if time_since_notification > self.buffer_data['notification_settings']['high_activity_minutes'] * 60:
                print(f"Sending notification: High activity ({hourly_rate} violations/hour)")
                return True
        elif hourly_rate <= self.LOW_ACTIVITY_THRESHOLD:
            if time_since_notification > self.buffer_data['notification_settings']['low_activity_hours'] * 3600:
                print(f"Sending notification: Low activity period completed ({hourly_rate} violations/hour)")
                return True
        else:
            if time_since_notification > self.buffer_data['notification_settings']['normal_activity_hours'] * 3600:
                print(f"Sending notification: Normal activity period completed ({hourly_rate} violations/hour)")
                return True
                
        print("No notification conditions met yet")
        return False

    def add_log(self, log_entry):
        print(f"Attempting to add log: {log_entry}")
        with self.lock:
            self.buffer_data['count'] += 1
            self.buffer_data['pending_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'data': log_entry
            })
            self._save_buffer(self.buffer_data)
            print(f"Log added successfully. New count: {self.buffer_data['count']}")

    def force_send_notification(self):
        print("Force send notification requested")
        with self.lock:
            if self.buffer_data['count'] > 0:
                print(f"Sending notification for {self.buffer_data['count']} logs")
                current_time = datetime.now()
                notification_message = self._create_message(current_time)
                self._send_notification(notification_message)
                
                # Reset buffer
                self.buffer_data['count'] = 0
                self.buffer_data['last_notification'] = current_time.isoformat()
                self.buffer_data['pending_logs'] = []
                self._save_buffer(self.buffer_data)
                
                print("Notification sent and buffer cleared")
                return True
            print("No logs in buffer to send")
            return False

    def _create_message(self, current_time):
        # You can now include details from pending_logs if needed
        logs = self.buffer_data['pending_logs']
        message = f"🚨 New Parking Violations Alert!\n\n"
        message += f"Number of violations: {self.buffer_data['count']}\n"
        
        # Optionally add details of each violation
        for log in logs:
            plate = log['data'].get('plate_number', 'Unknown')
            color = log['data'].get('car_color', 'Unknown')
            message += f"\n• {plate} ({color})"
            
        return message

    def _send_notification(self, message):
        if self.telegram_bot and self.chat_id:
            try:
                self.telegram_bot.send_message(self.chat_id, message)
            except Exception as e:
                print(f"Error sending notification: {str(e)}")

    def set_telegram_bot(self, bot, chat_id):
        self.telegram_bot = bot
        self.chat_id = chat_id

    def _check_buffer(self):
        """Periodically check buffer and send notifications if needed"""
        while True:
            try:
                if self._should_send_notification():
                    self.force_send_notification()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                print(f"Error in buffer check: {e}")
                time.sleep(10)
