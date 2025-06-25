from django.apps import AppConfig
from datetime import datetime
import threading
import time
import json
import os
import firebase_admin
from firebase_admin import credentials, db
from google.oauth2 import service_account
from google.cloud import storage


raw_env = os.getenv("FIREBASE_SERVICE_ACCOUNT")
service_account_info = json.loads(raw_env.encode('utf-8').decode('unicode_escape'))

cred = credentials.Certificate(service_account_info)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://yaari-jud-default-rtdb.firebaseio.com/'
    })

credentials_gcs = service_account.Credentials.from_service_account_info(service_account_info)
client = storage.Client(project='yaari-jud', credentials=credentials_gcs)

ref = db.reference('convos/')

def auto_deletion():
    while True:
        now = datetime.now()
        if now.hour == 9 and now.minute >= 47:
            try:
                entries = ref.get() or {}
                for bucket in entries.keys():
                    ref.child(f"{bucket}/").update({"chat": "{}"})
                bucket_name = "yaari-jud.firebasestorage.app"
                bucket = client.get_bucket(bucket_name)
                blobs = bucket.list_blobs()
                for b in blobs:
                    if b.name.startswith('YaariChatUploads') and b.name != 'YaariChatUploads/':
                        b.delete()
            except Exception as e:
                print(f"Error during auto deletion: {e}")
            time.sleep(60)  # Sleep to avoid multiple deletes in the same minute
        else:
            time.sleep(10)

class ResolverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'resolver'

    def ready(self):
        # Prevent starting multiple threads if ready() called multiple times
        if not hasattr(self, 'auto_deletion_thread'):
            thread = threading.Thread(target=auto_deletion, daemon=True)
            thread.start()
            self.auto_deletion_thread = thread
