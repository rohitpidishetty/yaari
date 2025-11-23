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


class ResolverConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"

