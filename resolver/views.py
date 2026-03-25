from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import firebase_admin
from firebase_admin import credentials, db
import os
import hashlib
import requests
import re, math
import numpy as np
from google.oauth2 import service_account
import sys
import uuid
from google.auth.transport.requests import Request
from urllib.parse import urlparse
from django.views.decorators.http import require_http_methods

raw_env = os.getenv("FIREBASE_SERVICE_ACCOUNT")
service_account_info = json.loads(raw_env.encode('utf-8').decode('unicode_escape'))


# Testing
# file = open("./service_acc.json", "r")
# service_account_info = json.load(file)

cred = credentials.Certificate(service_account_info)

if not firebase_admin._apps:
    firebase_admin.initialize_app(
        cred, {"databaseURL": "https://yaari-jud-default-rtdb.firebaseio.com/"}
    )

ref = db.reference("users/")


def get_access_token():
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )
    credentials.refresh(Request())
    return credentials.token


def notify(token, title, body):
    access_token = get_access_token()
    url = f"https://fcm.googleapis.com/v1/projects/yaari-jud/messages:send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }
    payload = {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": body,
            },
            "webpush": {
                "notification": {"icon": "https://yaari-jud.web.app/assets/logo.png"}
            },
        }
    }

    return requests.post(url, headers=headers, data=json.dumps(payload))


@csrf_exempt
def yaari_assoc(req):
    if req.method == "POST":
        try:
            payload = req.body.decode("utf-8")
            json_req = json.loads(payload)
            friend_name = json_req["union"]["friend"]["name"]
            friend_dp = json_req["union"]["friend"]["dp"]
            friend_req_id = json_req["union"]["friend"]["req_id"]
            friend_name_id = hashlib.md5(friend_name.encode()).hexdigest()
            with_name = json_req["union"]["with"]["name"]
            with_dp = json_req["union"]["with"]["dp"]
            with_device_id = json_req["union"]["with"]["deviceId"]
            with_name_id = hashlib.md5(with_name.encode()).hexdigest()

            with_payload = {
                with_name_id: {
                    "name": with_name,
                    "dp": with_dp,
                    "friendId": with_name_id,
                }
            }
            friend_payload = {
                friend_name_id: {
                    "name": friend_name,
                    "dp": friend_dp,
                    "friendId": friend_name_id,
                }
            }

            ref.child(f"{with_name}/friends").update(friend_payload)
            ref.child(f"{friend_name}/friends").update(with_payload)

            res = notify(
                with_device_id,
                "Hey Yaari",
                f"{friend_name} has accepted your friend request",
            )

            data = ref.child(f"{friend_name}/notifications/").get() or {}
            mag = len(data)
            if mag > 1:
                ref.child(f"{friend_name}/notifications/{friend_req_id}").delete()
            else:
                ref.child(f"{friend_name}/").update({"notifications": "{}"})

            return JsonResponse({"status": 200, "res": res.json()})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})
    return JsonResponse({"status": 500})


@csrf_exempt
def yaari_assoc_req(req):
    if req.method == "POST":
        try:
            payload = req.body.decode("utf-8")
            json_req = json.loads(payload)
            _from_ = json_req["from"]
            _to_ = json_req["to"]
            req_id = hashlib.md5(_from_["name"].encode()).hexdigest()
            ref.child(f"{_to_['name']}/notifications").update(
                {
                    req_id: {
                        "from": _from_["name"],
                        "deviceId": _from_["deviceId"],
                        "profile_picture": _from_["dp"],
                        "req_id": req_id,
                    }
                }
            )
            user_data = ref.child(f"{_to_['name']}").get() or {}
            count = user_data.get("new_notifications_count", 0)
            ref.child(f"{_to_['name']}").update({"new_notifications_count": count + 1})

            res = notify(
                _to_["deviceId"],
                "Hey Yaari",
                f"{_from_['name']} has sent you a friend request",
            )

            return JsonResponse({"status": 200, "notification": res.json()})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})
    return JsonResponse({"status": 500})


@csrf_exempt
def yaari_de_assoc(req):
    if req.method == "POST":
        try:
            payload = req.body.decode("utf-8")
            json_req = json.loads(payload)
            friend_name_1 = json_req["from"]["name"]
            friend_id_1 = hashlib.md5(friend_name_1.encode()).hexdigest()
            friend_name_2 = json_req["to"]["name"]
            friend_id_2 = hashlib.md5(friend_name_2.encode()).hexdigest()

            friend1 = ref.child(f"{friend_name_1}/friends").get() or {}
            if len(friend1) > 1:
                ref.child(f"{friend_name_1}/friends/{friend_id_2}").delete()
            else:
                ref.child(f"{friend_name_1}/").update({"friends": "{}"})

            friend2 = ref.child(f"{friend_name_2}/friends").get() or {}
            if len(friend2) > 1:
                ref.child(f"{friend_name_2}/friends/{friend_id_1}").delete()
            else:
                ref.child(f"{friend_name_2}/").update({"friends": "{}"})

            return JsonResponse({"status": 200})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})
    return JsonResponse({"status": 500})


@csrf_exempt
def yaari_assoc_chat_id(req):
    if req.method == "POST":
        try:
            body = req.body.decode("utf-8")
            jsonified = json.loads(body)
            chat_id = jsonified["chatId"]
            yaari1 = jsonified["convInitiator1"]
            yaari2 = jsonified["convInitiator2"]
            ref.child(f"{yaari1}/messages/").update({chat_id: chat_id})
            ref.child(f"{yaari2}/messages/").update({chat_id: chat_id})
            return JsonResponse({"status": 200})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})
    return JsonResponse({"status": 500})


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def yaari_notify(req):
    if req.method == "OPTIONS":
        # Reply to preflight with 200 OK and empty body
        return JsonResponse({}, status=200)

    if req.method == "POST":
        try:
            body = req.body.decode("utf-8")
            jsonified = json.loads(body)
            device_id = jsonified["deviceId"]
            user_message = jsonified["user_message"]
            author = jsonified["author"]
            res = notify(
                device_id, f"Yaari, {author} has sent you a message", user_message
            )
            return JsonResponse({"status": 200, "res": res.json()})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})

    # Fallback for other methods
    return JsonResponse({"status": 405, "error": "Method not allowed"})


@csrf_exempt
def yaari_action_notify(req):
    if req.method == "POST":
        try:
            body = req.body.decode("utf-8")
            data = json.loads(body)
            by = data["by"]
            deviceId = data["deviceId"]
            type_ = data["type"]
            comment = data["comment"]
            if type_ == "comment":
                notify(deviceId, f"Yaari, {by} has commented on your post", comment)
            else:
                notify(deviceId, f"Yaari", f"{by} has liked your post")
            return JsonResponse({"status": 200})
        except Exception as e:
            return JsonResponse({"status": 500, "error": str(e)})
    return JsonResponse({"status": 500})


@csrf_exempt
def yaari_two_step_verify(req):
    if req.method == "POST":
        try:
            body = req.body.decode("utf-8")
            data = json.loads(body)
            otp = str(data["otp"])
            user = data["username"]
            sent_otp = str(ref.child(f"{user}/otp").get())
            if otp == sent_otp:
                return JsonResponse({"status": 200})
            else:
                return JsonResponse({"status": 300})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})
    return JsonResponse({"status": 500})


import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_KEY")


@csrf_exempt
def yaari_two_step_verification(req):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8"))
        verify = body["verify_email"]
        username = body["username"]
        try:
            code = random.randint(10000, 99999)
            msg = MIMEMultipart()
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = verify
            msg["Subject"] = "Yaari, 2 step email verification"
            ref.child(f"{username}/").update({"otp": code})
            message = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', 'Roboto', sans-serif;
                        background: linear-gradient(135deg, rgba(18, 104, 202, 0.08), rgba(3, 167, 167, 0.08));
                        margin: 0;
                        padding: 20px;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: auto;
                        padding: 2rem;
                        border-radius: 20px;
                        background: linear-gradient(135deg, rgba(18, 104, 202, 0.15), rgba(3, 167, 167, 0.15));
                        backdrop-filter: blur(12px);
                        -webkit-backdrop-filter: blur(12px);
                        border: 1px solid rgba(35, 103, 126, 0.3);
                        box-shadow: 0 4px 12px rgba(0, 128, 128, 0.2);
                        text-align: center;
                    }}
                    h2 {{
                        color: #00b3b3;
                        font-size: 1.8rem;
                        margin-bottom: 10px;
                    }}
                    .code-box {{
                        display: inline-block;
                        background-color: #e0f7f7;
                        color: #333;
                        font-size: 28px;
                        letter-spacing: 4px;
                        padding: 12px 24px;
                        border-radius: 12px;
                        margin-top: 10px;
                        font-weight: bold;
                        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
                    }}
                    .footer {{
                        margin-top: 30px;
                        font-size: 12px;
                        color: #777;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>YAARI Email Verification</h2>
                    <div class="code-box">{code}</div>
                    <div class="footer">
                        This is an auto-generated email from <strong>YAARI</strong>. Please do not reply.
                    </div>
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(message, "html"))

            # Send email
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, verify, msg.as_string())
            server.quit()

            return JsonResponse({"status": 200})

        except Exception as e:
            return JsonResponse({"status": 400, "err": str(e)})

    return JsonResponse({"status": 500})


def haversine_formula(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    # Returning distance in KM
    return distance


@csrf_exempt
def yaari_suggestions(req):
    if req.method == "GET":
        coords = req.GET
        lat = coords.get("lat")
        lon = coords.get("lon")
        snapshot = ref.get()
        users = list(snapshot.keys())
        curr_lat = float(lat)
        curr_lon = float(lon)
        nearby = {}
        for user in users:
            coords = snapshot.get(user).get("location")
            lat = float(coords.get("lat"))
            lon = float(coords.get("lon"))
            dist = haversine_formula(curr_lat, curr_lon, lat, lon)
            if dist < 4:
                payload = {
                    "username": snapshot.get(user).get("username"),
                    "profile_picture": snapshot.get(user).get("profile_picture"),
                    "name": snapshot.get(user).get("name"),
                    "bio_status": snapshot.get(user).get("bio_status"),
                }
                nearby.update({user: payload})
        return JsonResponse({"suggestion": nearby})
    return JsonResponse({"status": 500})


import boto3
from botocore.config import Config
import uuid
import mimetypes
from django.conf import settings


@csrf_exempt
def yaari_image_upload(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": 405, "message": "Method not allowed"}, status=405
        )
    try:
        image = request.FILES.get("image")
        if not image:
            return JsonResponse(
                {"status": 400, "message": "No file uploaded"}, status=400
            )
        file_ext = str(image.name).split(".")[-1].lower()
        content_type = "application/octet-stream"
        if content_type is None:
            content_type = "application/octet-stream"
        print("POST =>", request.POST)
        print("FILES =>", request.FILES)
        
        file_name = f"{request.POST.get('folder')}/{uuid.uuid4()}.{file_ext}"
        print("DEBUG bucket =", settings.AWS_STORAGE_BUCKET_NAME)
        print("DEBUG key =", file_name)
        print("DEBUG content_type =", content_type)
        print("DEBUG access_key =", settings.AWS_ACCESS_KEY_ID)
        print("DEBUG secret_key =", settings.AWS_SECRET_ACCESS_KEY)
        print("DEBUG region =", settings.AWS_S3_REGION_NAME)
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            endpoint_url="https://s3.us-east-2.amazonaws.com",
            config=Config(signature_version="s3v4"),
        )
        s3.upload_fileobj(
            Fileobj=image,
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_name,
            ExtraArgs={"ACL": "public-read", "ContentType": content_type},
        )
        public_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.us-east-2.amazonaws.com/{file_name}"
        return JsonResponse({"status": 200, "url": public_url})

    except Exception as e:
        return JsonResponse({"status": 400, "message": str(e)})

@csrf_exempt
def generate_presigned_url(request):
    file_name = request.GET.get("filename")
    if not file_name:
        return JsonResponse({"status": 400, "message": "No filename provided"}, status=400)

    file_content_type = request.GET.get("content_type", "image/jpeg")
    key = f"YaariUploads/{uuid.uuid4()}_{file_name}"

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version="s3v4"),
    )

    url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": key,       
            "ContentType": file_content_type
        },
        ExpiresIn=3600
    )

    public_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"

    return JsonResponse({"uploadUrl": url, "publicUrl": public_url})


from getstream import Stream
@csrf_exempt
def generate_token(req):
    if req.method == "GET":
        try:
            name = req.GET.get("username")
            apiKey = os.getenv("STREAM_API_KEY")
            apiSecret = os.getenv("STREAM_API_SECRET")
            client = Stream(api_key=apiKey, api_secret=apiSecret, timeout=3.0)
            token = client.create_token(user_id=f"{name}")
            return JsonResponse({"token":token})
        except Exception as e:
            return JsonResponse({"message": str(e)})
    return JsonResponse({"message":0})


@csrf_exempt
def get_signed_url(request):
    full_url = request.GET.get("url")  
    parsed = urlparse(full_url)
    key = parsed.path.lstrip("/")  
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version="s3v4"),
    )
    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": key
        },
        ExpiresIn=3600
    )
    return JsonResponse({"signedUrl": url})
