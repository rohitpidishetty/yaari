from django.apps import AppConfig
from datetime import datetime
import threading
import time
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import firebase_admin
from firebase_admin import credentials, db, messaging  
import os
import hashlib
import json
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.cloud import storage


path = json.loads(os.getenv("FIREBASE"))
cred = credentials.Certificate(path)

if not firebase_admin._apps:
  firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://yaari-jud-default-rtdb.firebaseio.com/'
  })

credentials_gcs = service_account.Credentials.from_service_account_info(path)
client = storage.Client(project='yaari-jud', credentials=credentials_gcs)

ref = db.reference('convos/')


def auto_deletion():
    while True:
        now = datetime.now()
        if now.hour == 23 and now.minute == 59:
            entries = ref.get()
            for bucket in (list(entries.keys())):
                ref.child(f"{bucket}/").update({"chat":"{}"})
            bucket_name = "yaari-jud.firebasestorage.app"
            try:
                bucket = client.get_bucket(bucket_name)
                blobs = bucket.list_blobs()
                for b in blobs:
                    if(b.name.startswith('YaariChatUploads') and b.name != 'YaariChatUploads/'):
                        b.delete()
            except Exception as e:
                print(f"Error accessing storage bucket: {e}")
                time.sleep(60)
        else:
            time.sleep(10)  
    

class ResolverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'resolver'

    def ready(self):
        thread = threading.Thread(target=auto_deletion)
        thread.daemon = True 
        thread.start()
        
        
