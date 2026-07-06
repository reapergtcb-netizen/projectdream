import json
import random
import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

TITLE_ID = "ECCFF"
SECRET_KEY = "AHB8OCJMJA6D4XXXRNO1I5FGO4KHXZWCP6IGKSN4RJOZYC7WCO"
API_KEY = "OC|1179071591961775|4ab0641ca9afc14d61a7f49fb84ffd3a"
PHOTON_WEBHOOK_URL = "https://ECCFF.playfablogic.com/webhook/1/prod/SMTDDXYTXHB7BC93J3RC7K6E7FS9ZF8TJXBBB7E6DBQHB3DSH4"

def get_auth_headers():
    return {"Content-Type": "application/json", "X-SecretKey": SECRET_KEY}

polls = [
    {
        "pollId": 2,
        "question": "ARE YOU SIGMA ???????",
        "voteOptions": [
            "YES",
            "NO"
        ],
        "voteCount": [],
        "predictionCount": [],
        "startTime": "2025-03-11T18:00:00",
        "endTime": "2025-03-20T17:00:00",
        "isActive": True
    }
]

def generate_active_quests(quest_type="DailyQuests"):
    selected_categories = []
    for category in QuestThing["AllActiveQuests"][quest_type]:
        pool = [q for q in category["quests"] if not q.get("disable", False)]
        count_to_pick = min(category["selectCount"], len(pool))
        chosen_quests = random.sample(pool, count_to_pick) if pool else []
        selected_categories.append({
            "selectCount": category["selectCount"],
            "name": category["name"],
            "quests": chosen_quests
        })
    return {"ActiveQuests": selected_categories}

@app.route('/api/TD', methods=['POST'])
def titled_data():
    rjson = request.json
    print("JSON Received:", rjson)
    
    payload = {"Keys": []}

    try:
        response = requests.post(
            f"https://{TITLE_ID}.playfabapi.com/Server/GetTitleData", 
            json=payload, 
            headers=get_auth_headers()
        )
        
        if response.status_code != 200:
            return jsonify({"error": f"PlayFab API error: {response.text}"}), response.status_code
            
        pf_json = response.json()
        
        if "data" not in pf_json or "Data" not in pf_json["data"]:
            return jsonify({"error": "Unexpected PlayFab response structure", "details": pf_json}), 500
            
        raw_data = pf_json["data"]["Data"]
        processed_data = {}

        for key, value in raw_data.items():
            try:
                processed_data[key] = json.loads(value)
            except (ValueError, TypeError):
                processed_data[key] = value

        print("JSON Outputted:", processed_data)
        return jsonify(processed_data)

    except Exception as e:
        print(f"Server Error: {str(e)}")
        return jsonify({"error": "Internal server error occurred"}), 500
        
@app.route("/api/FetchPoll", methods=["GET", "POST"])
def fetch_poll():
    return jsonify(polls), 200

@app.route("/api/GetDailyQuests", methods=["GET", "POST", "PUT"])
def GetDailyQuests():
    return jsonify(generate_active_quests("DailyQuests")), 200

@app.route("/api/GetQuestStatus", methods=["GET", "POST", "PUT"])
def GetQuestStatus():
    return jsonify(generate_active_quests("WeeklyQuests")), 200

@app.route("/api/Vote", methods=["POST"])
def vote():
    data = request.json
    if not data:
        return "", 400
        
    poll_id = int(data.get("PollId", -1))
    playfab_id = data.get("PlayFabId")
    option_index = data.get("OptionIndex")
    is_prediction = data.get("IsPrediction")
    
    poll = next((p for p in polls if p["pollId"] == poll_id), None)
    
    if not poll or not poll["isActive"]:
        return "", 404

    if option_index < 0 or option_index >= len(poll["voteOptions"]):
        return "", 404
    
    embed = {
        "embeds": [
            {
                "title": "✅ - Vote success",
                "description": f"**PlayFab ID**: {playfab_id}\n**Prediction**: {is_prediction}\n**Question**: {poll['question']}\n**Voting for**: {poll['voteOptions'][option_index]}\n**Search Thing**: {is_prediction}-{poll['voteOptions'][option_index]}",
                "color": 3447003
            }
        ]
    }
    requests.post("https://discordapp.com/api/webhooks/1349180410793300028/jjrJoyWo5Jm8v9vA4I3Q4zvBTgQ1pCTIBFQmXapMV2GrESw9gsUMR88rPaMJ5Qm79eY_", json=embed)
    
    return jsonify({"success": True}), 200

@app.route("/api/PlayFabAuthentication", methods=["POST"])
def playfab_authentication():
    data = request.get_json()
    oculus_id = data.get("OculusId", "Null")
    nonce = data.get("Nonce", "Null")
    platform = data.get("Platform", "Null")

    login_req = requests.post(
        url=f"https://{TITLE_ID}.playfabapi.com/Server/LoginWithServerCustomId",
        json={
            "ServerCustomId": f"OCULUS{oculus_id}",
            "CreateAccount": True
        },
        headers=get_auth_headers()
    )

    if login_req.status_code == 200:
        rjson = login_req.json().get('data', {})
        session_ticket = rjson.get('SessionTicket')
        playfab_id = rjson.get('PlayFabId')
        entity = rjson.get('EntityToken', {})
        entity_token = entity.get('EntityToken')
        entity_id = entity.get('Entity', {}).get('Id')
        entity_type = entity.get('Entity', {}).get('Type')
        
        requests.post(
            url=f"https://{TITLE_ID}.playfabapi.com/Client/LinkCustomID",
            json={"CustomID": f"OCULUS{oculus_id}", "ForceLink": True},
            headers={
                "content-type": "application/json",
                "x-authorization": session_ticket
            }
        )

        return jsonify({
            "PlayFabId": playfab_id,
            "SessionTicket": session_ticket,
            "EntityToken": entity_token,
            "EntityId": entity_id,
            "EntityType": entity_type,
            "Nonce": nonce,
            "OculusId": oculus_id,
            "Platform": platform
        }), 200
    else:
        ban_info = login_req.json()
        if ban_info.get("errorCode") == 1002:
            details = ban_info.get("errorDetails", {})
            ban_reason = next(iter(details.keys()), "Banned")
            ban_time = details.get(ban_reason, ["Indefinite"])[0]
            return jsonify({
                "BanMessage": ban_reason,
                "BanExpirationTime": ban_time,
                "ResultCode": 1,
                "StatusCode": 403
            }), 403
        return jsonify({"Message": "Login failed"}), 403
        
@app.route("/api/GetFriendsV2", methods=["POST", "GET"])
def get_friends():
    data = request.get_json(silent=True) or {}
    pID = data.get("PlayFabId")
    
    if not pID:
        return jsonify({"error": "Missing PlayFabId parameters"}), 400

    url = f"https://{TITLE_ID}.playfabapi.com/Server/GetFriendsList"
    headers = {
        "X-SecretKey": SECRET_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "PlayFabId": pID,
        "IncludeSteamFriends": False,
        "IncludeFacebookFriends": False
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        res_json = res.json()
        
        if res.status_code == 200:
            playfab_data = res_json.get("data", {})
            friends_list = playfab_data.get("Friends", [])
            
            formatted_friends = []
            for friend in friends_list:
                formatted_friends.append({
                    "FriendPlayFabId": friend.get("FriendPlayFabId"),
                    "Username": friend.get("Username", "Unknown Tagger"),
                    "TitleDisplayName": friend.get("TitleDisplayName", "No Name Set"),
                    "Tags": friend.get("Tags", [])
                })
                
            return jsonify({
                "status": "success",
                "PlayFabId": pID,
                "FriendCount": len(formatted_friends),
                "Friends": formatted_friends
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "PlayFab rejected the friends list request",
                "details": res_json
            }), res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/RequestFriend", methods=["POST"])
def request_friend():
    data = request.get_json(silent=True) or {}
    playfab_id = data.get("PlayFabId")
    friend_id = data.get("FriendPlayFabId")

    if not playfab_id or not friend_id:
        return jsonify({"error": "Missing PlayFabId or FriendPlayFabId"}), 400

    url = f"https://{TITLE_ID}.playfabapi.com/Server/AddFriend"
    headers = {
        "X-SecretKey": SECRET_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "PlayFabId": playfab_id,
        "FriendPlayFabId": friend_id
    }

    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            return jsonify({
                "status": "success",
                "message": "Friend added successfully"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "PlayFab rejected the add friend request",
                "details": res.json()
            }), res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/RemoveFriend", methods=["POST"])
def remove_friend():
    data = request.get_json(silent=True) or {}
    playfab_id = data.get("PlayFabId")
    friend_id = data.get("FriendPlayFabId")

    if not playfab_id or not friend_id:
        return jsonify({"error": "Missing PlayFabId or FriendPlayFabId"}), 400

    url = f"https://{TITLE_ID}.playfabapi.com/Server/RemoveFriend"
    headers = {
        "X-SecretKey": SECRET_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "PlayFabId": playfab_id,
        "FriendPlayFabId": friend_id
    }

    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            return jsonify({
                "status": "success",
                "message": "Friend removed successfully"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "PlayFab rejected the remove friend request",
                "details": res.json()
            }), res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/SetPrivacyState", methods=["POST"])
def set_privacy_state():
    data = request.get_json(silent=True) or {}
    playfab_id = data.get("PlayFabId")
    privacy_state = data.get("PrivacyState")  # Expected input string matching room display setup

    if not playfab_id or privacy_state is None:
        return jsonify({"error": "Missing PlayFabId or PrivacyState"}), 400

    url = f"https://{TITLE_ID}.playfabapi.com/Server/UpdateUserInternalData"
    headers = {
        "X-SecretKey": SECRET_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "PlayFabId": playfab_id,
        "Data": {
            "PrivacyState": str(privacy_state)
        }
    }

    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            return jsonify({
                "status": "success",
                "message": "Privacy state updated successfully",
                "PrivacyState": privacy_state
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "PlayFab rejected the privacy update",
                "details": res.json()
            }), res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/CheckForBadName", methods=["POST", "GET"])
def check_for_bad_name():
    bad_names = ["KKK", "PENIS", "NIGG", "NEG", "NIGA", "MONKEYSLAVE", "SLAVE", "FAG",
                 "NAGGI", "TRANNY", "QUEER", "KYS", "DICK", "PUSSY", "VAGINA", "BIGBLACKCOCK",
                 "DILDO", "HITLER", "KKX", "XKK", "NIGE", "NIG", "NI6", "PORN",
                 "JEW", "JAXX", "TTTPIG", "SEX", "COCK", "CUM", "FUCK", "ELLIOT", "JMAN", "K9", "NIGGA", 
                 "NICKER", "NICKA", "REEL", "NII", "@here", "!", " ", "PPPTIG", "CLEANINGBOT", "JANITOR", 
                 "H4PKY", "MOSA", "NIGGER", "IHATENIGGERS", "@everyone", "TTT"]

    if not request.is_json:
        list_items = "".join([f"<li style='margin: 5px 0;'>{name}</li>" for name in bad_names])
        return f"""
        <html>
            <body style="background-color: #111; color: #fff; font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                <h1 style="color: #ff3333;">🚫 Blocked Names</h1>
                <ul style="background: #1a1a1a; padding: 20px 40px; border-radius: 8px; column-count: 2;">
                    {list_items}
                </ul>
            </body>
        </html>
        """, 200

    try:
        content = request.get_json(silent=True) or {}
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if "name" in content:
        name = str(content.get("name", "")).upper()
    else:
        rjson = content.get("FunctionResult", {})
        if isinstance(rjson, dict) and "name" in rjson:
            name = str(rjson.get("name", "")).upper()
        else:
            return jsonify({"error": "Missing 'name' field parameter"}), 400

    return jsonify({"result": 2 if name in bad_names else 0})

@app.route("/api/CachePlayFabId", methods=["POST"])
def cache_playfab_id():
    data = request.get_json()
    session_ticket = data.get("SessionTicket")
    if session_ticket:
        playfab_id = session_ticket.split("-")[0]
        return jsonify({"Message": "Authed", "PlayFabId": playfab_id}), 200
    return jsonify({"Message": "Try Again Later."}), 404

@app.route("/api/ConsumeOculusIAP", methods=["POST"])
def consume_oculus_iap():
    data = request.get_json()
    user_id = data.get("userID")
    nonce = data.get("nonce")
    sku = data.get("sku")

    response = requests.post(
        url=f"https://graph.oculus.com/consume_entitlement?nonce={nonce}&user_id={user_id}&sku={sku}&access_token={API_KEY}",
        headers={"content-type": "application/json"}
    )

    if response.json().get("success"):
        return jsonify({"result": True})
    return jsonify({"error": True})


@app.route("/api/photon", methods=["POST"])
def photonauth():
    AA = request.get_json()
    PlayFabId = AA.get("PlayFabId")
    OrgScopedID = AA.get("OrgScopedId")
    CustomId = AA.get("CustomID")
    Platform = AA.get("Platform")
    Nonce = AA.get("Nonce")
    UserId = AA.get("UserId")
    MasterPlayer = AA.get("Master")
    GorillaTagger = AA.get("GorillaTagger")
    CosmeticsInRoom = AA.get("CosmeticsInRoom")
    SharedGroupData = AA.get("SharedGroupData")
    UpdatePlayerCosmetics = AA.get("UpdatePlayerCosmetics")
    MasterClient = AA.get("MasterClient")
    ItemIds = AA.get("ItemIds")
    PlayerCount = AA.get("PlayerCount")
    CosmeticAuthenticationV2 = AA.get("CosmeticAuthenticationV2")
    RPCS = AA.get("RPCS")
    BroadcastMyRoomV2 = AA.get("BroadcastMyRoomV2")
    DLCOwnerShipV2 = AA.get("DLCOwnerShipV2")
    GorillaCorpCurrencyV1 = AA.get("GorillaCorpCurrencyV1")
    DeadMonke = AA.get("DeadMonke")
    GhostCounter = AA.get("GhostCounter")
    DirtyCosmeticSpawnnerV2 = AA.get("DirtyCosmeticSpawnnerV2")
    RoomJoined = AA.get("RoomJoined")
    VirtualStump = AA.get("VirtualStump")
    PlayerRoomCount = AA.get("PlayerRoomCount")
    AppVersion = AA.get("AppVersion")
    AppId = AA.get("AppId")
    TaggedDistance = AA.get("TaggedDistance")
    TaggedClient = AA.get("TaggedClient")
    OculusId = AA.get("OCULUSId")
    TitleId = AA.get("TITLE_ID")

    return jsonify({
        "ResultCode": 1,
        "StatusCode": 200,
        "Message": "authed with photon",
        "Result": 0,
        "UserId": UserId,
        "AppId": AppId,
        "AppVersion": AppVersion,
        "Ticket": AA.get("Ticket"),
        "Token": AA.get("Token"),
        "Nonce": Nonce,
        "Platform": Platform,
        "Username": AA.get("Username"),
        "PlayerRoomCount": PlayerRoomCount,
        "GorillaTagger": GorillaTagger,
        "CosmeticAuthentication": CosmeticAuthenticationV2,
        "CosmeticsInRoom": CosmeticsInRoom,
        "UpdatePlayerCosmetics": UpdatePlayerCosmetics,
        "DLCOwnerShip": DLCOwnerShipV2,
        "Currency": GorillaCorpCurrencyV1,
        "RoomJoined": RoomJoined,     
        "VirtualStump": VirtualStump,
        "DeadMonke": DeadMonke,
        "GhostCounter": GhostCounter,
        "BroadcastRoom": BroadcastMyRoomV2,
        "TaggedClient": TaggedClient,
        "TaggedDistance": TaggedDistance,
        "RPCS": RPCS
    }), 200


@app.route("/iap", methods=["POST"])
def consume_oculus_iap_alt():
    rjson = request.get_json()
    user_id = rjson.get("userID")
    nonce = rjson.get("nonce")
    sku = rjson.get("sku")

    response = requests.post(
        url=f"https://graph.oculus.com/consume_entitlement?nonce={nonce}&user_id={user_id}&sku={sku}&access_token={API_KEY}",
        headers={"content-type": "application/json"}
    )

    if response.json().get("success"):
        return jsonify({"result": True})
    else:
        return jsonify({"error": True})

@app.route("/api/GetAcceptedAgreements", methods=['POST'])
def GetAcceptedAgreements():
    received_data = request.get_json()
    return jsonify({
        "ResultCode": 1,
        "StatusCode": 200,
        "Message": '',
        "result": 0,
        "CallerEntityProfile": received_data.get('CallerEntityProfile'),
        "TitleAuthenticationContext": received_data.get('TitleAuthenticationContext')
    })

@app.route("/api/SubmitAcceptedAgreements", methods=['POST'])
def SubmitAcceptedAgreements():
    received_data = request.get_json()
    return jsonify({
        "ResultCode": 1,
        "StatusCode": 200,
        "Message": '',
        "result": 0,
        "CallerEntityProfile": received_data.get('CallerEntityProfile'),
        "TitleAuthenticationContext": received_data.get('TitleAuthenticationContext'),
        "FunctionArgument": received_data.get('FunctionArgument')
    })

def save_accepted_agreements(agreements):
    with open('accepted_agreements.json', 'w') as file:
        json.dump(agreements, file)

@app.route("/api/K-ID", methods=["POST"])
def k_id():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    required_fields = ["Age", "Permissions", "GetSubmittedAge", "VoiceChat", "CustomNames", "PhotonPermission"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    response = {
        "status": "success",
        "UserAge": data.get("Age"),
        "Permissions": data.get("Permissions"),
        "GetSubmittedAge": data.get("GetSubmittedAge"),
        "VoiceChat": data.get("VoiceChat"),
        "CustomNames": data.get("CustomNames"),
        "PhotonPermission": data.get("PhotonPermission"),
        "AnnouncementData": {
            "ShowAnnouncement": "false",
            "AnnouncementID": "kID_Prelaunch",
            "AnnouncementTitle": "IMPORTANT NEWS",
            "Message": "We're working to make Gorilla Tag a better, more age-appropriate experience in our next update. To learn more, please check out our Discord."
        }
    }
    return jsonify(response), 200

@app.route("/", methods=["GET"])
def main():
    image_url = "https://i.postimg.cc/SKVKRBMz/image.png"
    return f"""
    <html>
      <head>
        <title>Server Dashboard</title>
        <style>
          body {{
            background-color: #111;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
          }}
          img {{
            max-width: 90vw;
            max-height: 90vh;
            border-radius: 12px;
            box-shadow: 0 0 20px rgba(255,255,255,0.2);
          }}
        </style>
      </head>
      <body>
        <img src="{image_url}" alt="Clean Image" />
      </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)
