from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import firebase_admin
from firebase_admin import credentials, db
import os
import hashlib
import requests
import re
import numpy as np
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# ML imports commented out — uncomment if you add tensorflow and keras dependencies
# import tensorflow as tf
# from tensorflow.keras.preprocessing.text import Tokenizer
# from tensorflow.keras.preprocessing import sequence

raw_env = os.getenv("FIREBASE_SERVICE_ACCOUNT")
service_account_info = json.loads(raw_env.encode('utf-8').decode('unicode_escape'))



cred = credentials.Certificate(service_account_info)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://yaari-jud-default-rtdb.firebaseio.com/'
    })

ref = db.reference('users/')

def get_access_token():
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=['https://www.googleapis.com/auth/firebase.messaging']
    )
    credentials.refresh(Request())
    return credentials.token

from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def yaari_notify(req):
    if req.method == "OPTIONS":
        # Reply to preflight with 200 OK and empty body
        return JsonResponse({}, status=200)
    
    if req.method == "POST":
        try:
            body = req.body.decode('utf-8')
            jsonified = json.loads(body)
            device_id = jsonified['deviceId']
            user_message = jsonified['user_message']
            author = jsonified['author']
            res = notify(device_id, f"Yaari, {author} has sent you a message", user_message)
            return JsonResponse({"status": 200, "res": res.json()})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})

    # Fallback for other methods
    return JsonResponse({"status": 405, "error": "Method not allowed"})

@csrf_exempt
def yaari_assoc(req):
    if req.method == "POST":
        try:
            payload = req.body.decode('utf-8')
            json_req = json.loads(payload)
            friend_name = json_req['union']['friend']['name']
            friend_dp = json_req['union']['friend']['dp']
            friend_req_id = json_req['union']['friend']['req_id']
            friend_name_id = hashlib.md5(friend_name.encode()).hexdigest()
            with_name = json_req['union']['with']['name']
            with_dp = json_req['union']['with']['dp']
            with_device_id = json_req['union']['with']['deviceId']
            with_name_id = hashlib.md5(with_name.encode()).hexdigest()

            with_payload = {
                with_name_id: {
                    "name": with_name,
                    "dp": with_dp,
                    "friendId": with_name_id
                }
            }
            friend_payload = {
                friend_name_id: {
                    "name": friend_name,
                    "dp": friend_dp,
                    "friendId": friend_name_id
                }
            }

            ref.child(f"{with_name}/friends").update(friend_payload)
            ref.child(f"{friend_name}/friends").update(with_payload)

            res = notify(with_device_id, 'Hey Yaari', f"{friend_name} has accepted your friend request")

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
            payload = req.body.decode('utf-8')
            json_req = json.loads(payload)
            _from_ = json_req['from']
            _to_ = json_req['to']
            req_id = hashlib.md5(_from_['name'].encode()).hexdigest()
            ref.child(f"{_to_['name']}/notifications").update({
                req_id: {
                    "from": _from_['name'],
                    "deviceId": _from_['deviceId'],
                    "profile_picture": _from_['dp'],
                    "req_id": req_id,
                }
            })
            user_data = ref.child(f"{_to_['name']}").get() or {}
            count = user_data.get("new_notifications_count", 0)
            ref.child(f"{_to_['name']}").update({"new_notifications_count": count + 1})

            res = notify(_to_['deviceId'], 'Hey Yaari', f"{_from_['name']} has sent you a friend request")

            return JsonResponse({"status": 200, "notification": res.json()})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})
    return JsonResponse({"status": 500})

@csrf_exempt
def yaari_de_assoc(req):
    if req.method == "POST":
        try:
            payload = req.body.decode('utf-8')
            json_req = json.loads(payload)
            friend_name_1 = json_req['from']['name']
            friend_id_1 = hashlib.md5(friend_name_1.encode()).hexdigest()
            friend_name_2 = json_req['to']['name']
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
            body = req.body.decode('utf-8')
            jsonified = json.loads(body)
            chat_id = jsonified['chatId']
            yaari1 = jsonified['convInitiator1']
            yaari2 = jsonified['convInitiator2']
            ref.child(f"{yaari1}/messages/").update({chat_id: chat_id})
            ref.child(f"{yaari2}/messages/").update({chat_id: chat_id})
            return JsonResponse({"status": 200})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})
    return JsonResponse({"status": 500})

@csrf_exempt
def yaari_notify(req):
    if req.method == "POST":
        try:
            body = req.body.decode('utf-8')
            jsonified = json.loads(body)
            device_id = jsonified['deviceId']
            user_message = jsonified['user_message']
            author = jsonified['author']
            res = notify(device_id, f"Yaari, {author} has sent you a message", user_message)
            return JsonResponse({"status": 200, "res": res.json()})
        except Exception as e:
            return JsonResponse({"status": 400, "error": str(e)})
    return JsonResponse({"status": 500})

@csrf_exempt
def yaari_action_notify(req):
    if req.method == "POST":
        try:
            body = req.body.decode('utf-8')
            data = json.loads(body)
            by = data['by']
            deviceId = data['deviceId']
            type_ = data['type']
            comment = data['comment']
            if type_ == "comment":
                notify(deviceId, f"Yaari, {by} has commented on your post", comment)
            else:
                notify(deviceId, f"Yaari", f"{by} has liked your post")
            return JsonResponse({"status": 200})
        except Exception as e:
            return JsonResponse({"status": 500, "error": str(e)})
    return JsonResponse({"status": 500})

def textProcessor(data):
    # Removes URLs, lowercases, removes whitespace and non-alphanumeric chars except spaces
    url_filtered = re.sub(r'(?:(https|http)\s?:\/\/)(\s)*(www\.)?(\s)*((\w|\s)+\.)*([\w\-\s]+\/)*([\w\-]+)((\?)?[\w\s]*=\s*[\w\%&]*)*', '', data, flags=re.MULTILINE)
    lowercased = url_filtered.lower()
    no_newlines = lowercased.replace('\n', '')
    processedData = ''.join(letter for letter in no_newlines if letter.isalnum() or letter == ' ')
    return processedData

# Uncomment and fix when tensorflow is installed and model available
# def predict(news):
#     news = textProcessor(news)
#     news = news.lower()
#     tokenizer = Tokenizer(num_words=50, filters='!"#$%&()*+,-./:;<=>?@[\\]^_{|}~\t\n-', split=' ', char_level=False, oov_token=None, document_count=0)
#     tokenizer.fit_on_texts([news])
#     _dir_ = os.path.join(BASE_DIR, 'CNNBiLSTM_Model.h5')
#     CNN_BiLSTM = tf.keras.models.load_model(_dir_)
#     sequences = tokenizer.texts_to_sequences([news])
#     padded_seq = sequence.pad_sequences(sequences, value=0.0, padding='post', maxlen=50)
#     prediction = CNN_BiLSTM.predict(padded_seq)
#     return 'real' if np.argmax(prediction, axis=-1) == 0 else 'fake'

@csrf_exempt
def yaari_hoax_auditor(req):
    if req.method == "POST":
        try:
            body = req.body.decode('utf-8')
            data = json.loads(body)
            text = data['text']
            # For now, just echo the text since ML model is commented out
            # prediction = predict(text) + " news"
            return JsonResponse({"status": text})
        except Exception as e:
            return JsonResponse({"status": 500, "error": str(e)})
    return JsonResponse({"status": 500})
