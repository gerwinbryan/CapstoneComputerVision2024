import firebase_admin
from firebase_admin import firestore
from datetime import datetime
import sqlite3
import time

class FirebaseSync:
    def __init__(self, local_db_path='parking_violations.db'):
        self.local_db_path = local_db_path
        # Initialize Firestore
        self.db = firestore.client()
        self.violations_ref = self.db.collection('violations')

    def sync_to_firebase(self):
        """Sync local DB to Firebase, overwriting Firebase data"""
        try:
            # Get all local violations
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, license_plate, location, 
                       parking_duration, image_path, car_color 
                FROM violations
                ORDER BY timestamp DESC
            """)
            violations = cursor.fetchall()
            conn.close()

            # Clear existing Firebase collection
            self._clear_firebase_collection()

            # Upload all violations
            batch = self.db.batch()
            for violation in violations:
                doc_ref = self.violations_ref.document(str(violation[0]))  # Use ID as document ID
                batch.set(doc_ref, {
                    'id': violation[0],
                    'timestamp': violation[1],
                    'license_plate': violation[2],
                    'location': violation[3],
                    'parking_duration': violation[4],
                    'image_path': violation[5],
                    'car_color': violation[6],
                    'last_synced': datetime.now().isoformat()
                })
            
            # Commit the batch
            batch.commit()
            print(f"Successfully synced {len(violations)} violations to Firebase")

        except Exception as e:
            print(f"Error syncing to Firebase: {e}")

    def _clear_firebase_collection(self):
        """Clear all documents in the violations collection"""
        batch = self.db.batch()
        docs = self.violations_ref.limit(500).stream()  # Firestore limits batches to 500
        deleted = 0

        for doc in docs:
            batch.delete(doc.reference)
            deleted += 1

        if deleted > 0:
            batch.commit()
            print(f"Cleared {deleted} documents from Firebase")

    def start_periodic_sync(self, interval_seconds=300):  # 5 minutes default
        """Start periodic sync in the background"""
        while True:
            self.sync_to_firebase()
            time.sleep(interval_seconds)
