#!/usr/bin/env python3
import requests
import argparse
import json
import random
import time
import sys
import urllib

reqHeaders = {
  "Accept":	"*/*",
  "Accept-Encoding": "gzip, deflate, br",
  "Accept-Language": "en-US,en;q=0.5",
  "Connection":	"close",
  "Origin":	"https://myteam.mail.ru",
  "Referer":	"https://myteam.mail.ru/",
  "Sec-Fetch-Dest": "empty",
  "Sec-Fetch-Mode":	"cors",
  "Sec-Fetch-Site":	"same-site",
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0"
}

def getLoginData(login):
    ret = None
    loginParams = { 
      "tokenType": "otp_via_email",
      "clientName": "webVKTeams",
      "clientVersion": "VKTeams Web ic1zmlWFTdkiTnkL 22.10.1(2022/11/16 11:27 release) unknown desktop",
      "idType": "ICQ",
      "s": login,
      "k": "ic1zmlWFTdkiTnkL",
    }
    loginPostData = {
      "pwd": "1"
    }
    
    r = requests.request(method = "POST", url = "https://u.internal.myteam.mail.ru/api/v92/wim/auth/clientLogin", headers = reqHeaders, params = loginParams, data = loginPostData)
    if (r.status_code == 200):
      passwd = input("Enter one time password from your email:")
      loginParams["tokenType"] = "longTerm"
      loginPostData = {
        "pwd": passwd
      }
      r = requests.request(method = "POST", url = "https://u.internal.myteam.mail.ru/api/v92/wim/auth/clientLogin", headers = reqHeaders, params = loginParams, data = loginPostData)
      if (r.status_code == 200):
        loginData = r.json()
        if (loginData["response"]["statusCode"] == 200):
          ret = {
            "token": loginData["response"]["data"]["token"],
            "sessionSecret": loginData["response"]["data"]["sessionSecret"],
            "loginId": loginData["response"]["data"]["loginId"]
          }
          print("Successfully logged in")
      else:
        print("{} - {} - {}".format(r.status_code, r.headers, r.text))
    else:
      print("{} - {} - {}".format(r.status_code, r.headers, r.text))

    return ret
    
def startSession(ldf):
  sessionStartParams = {
    "clientName": "webVKTeams",
    "clientVersion": "VKTeams Web ic1zmlWFTdkiTnkL 22.10.1(2022/11/16 11:27 release) unknown desktop",
    "idType": "ICQ",
    "k": "ic1zmlWFTdkiTnkL",
    "ts": int(time.time()),
    "a": ldf["token"]["a"],
    "userSn": ldf["loginId"],
    "view": "online",
    "language": "en-US",
    "deviceId": "993328-2330-611e-512d-a6a63c9bb7dc",
    "sessionTimeout": 2592000,
    "assertCaps": "094613584C7F11D18222444553540000,0946135C4C7F11D18222444553540000,0946135b4c7f11d18222444553540000,0946135E4C7F11D18222444553540000,AABC2A1AF270424598B36993C6231952,1f99494e76cbc880215d6aeab8e42268,A20C362CD4944B6EA3D1E77642201FD8,094613504c7f11d18222444553540000,094613514c7f11d18222444553540000,094613564c7f11d18222444553540000,094613503c7f11d18222444553540000",
    "interestCaps": "8eec67ce70d041009409a7c1602a5c84,094613504c7f11d18222444553540000,094613514c7f11d18222444553540000,094613564c7f11d18222444553540000",
    "events": "myInfo,buddylist,hiddenChat,hist,mchat,sentIM,imState,dataIM,offlineIM,userAddedToBuddyList,service,lifestream,apps,permitDeny,diff,webrtcMsg",
    "includePresenceFields": "aimId,displayId,friendly,friendlyName,state,userType,statusMsg,statusTime,lastseen,ssl,mute,abContactName,abPhoneNumber,abPhones,official,quiet,autoAddition,largeIconId,nick,userState"
  }
  r = requests.request(method = "POST", url = "https://u.internal.myteam.mail.ru/api/v92/wim/aim/startSession", headers = reqHeaders, params = sessionStartParams)
  if (r.status_code == 200):
    sessionData = r.json()
    ldf.update({"aimsid": sessionData["response"]["data"]["aimsid"], "fetchBaseURL": sessionData["response"]["data"]["fetchBaseURL"]})
    print("Successfully started new session")
    print("{}".format(sessionData["response"]["data"]["myInfo"]))
    
  else:
    print("{} - {} - {}".format(r.status_code, r.headers, r.text))
  return ldf

def fetchInitialEvents(ldf):
  ret = None
  fdb = urllib.parse.urlparse(ldf["fetchBaseURL"])
  feUrl = "{}://{}{}".format(fdb.scheme, fdb.netloc, fdb.path)
  feQ = urllib.parse.parse_qs(fdb.query)
  feParams = {
    "aimsid": feQ["aimsid"],
    "first": 1,
    "rnd": time.time()
  }
  events = []
  r = requests.request(method = "GET", url = feUrl, headers = reqHeaders, params = feParams)
  while r.status_code == 200:
    resp = r.json()
    if not "response" in resp:
      print("{} - {} - {}".format(r.status_code, r.headers, r.text))
      break
    resp = resp["response"]
    if ("fetchBaseURL" in resp["data"]):
      ldf["fetchBaseURL"] = resp["data"]["fetchBaseURL"]
    if ("events" in resp["data"]) and (len(resp["data"]["events"]) > 0):
      events = events + resp["data"]["events"]
    else:
      break
    fdb = urllib.parse.urlparse(ldf["fetchBaseURL"])
    feUrl = "{}://{}{}".format(fdb.scheme, fdb.netloc, fdb.path)
    feQ = urllib.parse.parse_qs(fdb.query)
    feParams = {
      "timeout": 500,
      "supportedSuggestTypes": "",
      "rnd": time.time()
    }
    feParams.update(feQ)
    r = requests.request(method = "GET", url = feUrl, headers = reqHeaders, params = feParams)
  print("Fetched initial data")
  return ( ldf, events )
  
def listChats(initialData):
  ret = []
  for rec in initialData:
    if ("type" in rec) and (rec["type"] == "buddylist"):
      for blr in rec["eventData"]["groups"]: # buddy list records
        rbl = { "name": blr["name"], "buddies": [] } # ret buddylist
        for c in blr["buddies"]:
          rbl["buddies"].append({"friendly": c["friendly"], "aimId": c["aimId"]})
        ret.append(rbl)
  return ret

def dumpMsg(msg):
  if "class" in msg: # not an ordinary msg, could skip
    return
  text = ""
  if "text" in msg:
    text = msg["text"]
  if "parts" in msg:
    for p in msg["parts"]:
      if p["mediaType"] == "text":
        text = text + " " + p["text"]
  sender = msg["chat"]["sender"]
  print("{} - {} - {} - {}".format(msg["msgId"], time.strftime("%H:%M:%S %m-%d-%y", time.gmtime(msg["time"])), sender, text))
  
def dumpChat(ldf, chatId):
  getHistoryPostData = {
    "aimsid":	ldf["aimsid"],
    "params": {
      "count": 50,
      "fromMsgId": "1",
      "lang": "en",
      "mentions": {
        "resolve": "false"
      },
      "patchVersion":	"init",
      "sn":	chatId
    },
    "reqId": "{}-{}".format(random.randint(10000,99999), int(time.time()))
  }
  fromMsgId = 1
  lastMsgId = 0
  patchVersion = 0
  alsoDump = []
  try:
    cfF = open(chatId, 'w', encoding="utf-8")
  except Exception as e:
    print("Unable to open {} for writing".format(chatId))
    return []
  cfF.write("[ ")
  r = requests.post(url = "https://u.internal.myteam.mail.ru/api/v92/rapi/getHistory", headers = reqHeaders, json = getHistoryPostData)
  done = False
  while not done:
    if r.status_code == 200:
      resp = r.json()
      if not "results" in resp:
        print("{} - {} - {}".format(r.status_code, r.headers, r.text))
        break
      results = resp["results"]
      if "lastMsgId" in results and int(results["lastMsgId"]) > lastMsgId:
        lastMsgId = int(results["lastMsgId"])
      if "patchVersion" in results:
        patchVersion = results["patchVersion"]
      if "newerMsgId" in results:
        fromMsgId = int(results["newerMsgId"])
      if "messages" in results:
        if (len(results["messages"]) > 0 ):
          for m in results["messages"]:
            json.dump(m, cfF, ensure_ascii=False)
            dumpMsg(m)
            if int(m["msgId"]) > fromMsgId:
              fromMsgId = int(m["msgId"])
            if "thread" in m:
              alsoDump.append(m["thread"]["threadId"])
            if int(m["msgId"]) >= lastMsgId:
              done = True
              break
            else:
              cfF.write(",\n")

        else:
          done = True
    else:
      print("{} - {} - {}".format(r.status_code, r.headers, r.text))
      break
    if not done:
      getHistoryPostData["reqId"] = "{}-{}".format(random.randint(10000,99999), int(time.time()))
      getHistoryPostData["params"]["patchVersion"] = patchVersion
      getHistoryPostData["params"]["fromMsgId"] = fromMsgId
      r = requests.post(url = "https://u.internal.myteam.mail.ru/api/v92/rapi/getHistory", headers = reqHeaders, json = getHistoryPostData)

  cfF.write(" ]\n")
  cfF.close()
  print("Dumped {}".format(chatId))
  return alsoDump

def main(args):
    ap = argparse.ArgumentParser(description = 'Dump your chat history')
    ap.add_argument('--login', action = 'store')
    ap.add_argument('--ldf', action = 'store')
    ap.add_argument('--list-chats', action = 'store_true')
    ap.add_argument('--dump-chat', action = 'store', nargs = 1)

    args = ap.parse_args()
    ldf = None
    if (args.ldf != None):
      try:
        ldfF = open(args.ldf, 'r', encoding="utf-8")
      except Exception as e:
        ldfF = None
      if ldfF != None:
        try:
          ldf = json.load(ldfF)
        except Exception as e:
          ldf = None
    if ldf == None:
      print("Empty or invalid login data file {}, trying to log in".format(args.ldf) if args.ldf != None else "login data file not specified, trying to log in")
      if args.login:
        ldf = getLoginData(args.login)
      else:
        print("No login specified on command line, can't continue")
        return -1
      if ldf == None:
        print("Unable to log in, can't continue")
        return -2
      ldfF = open(args.ldf, 'w')
      json.dump(ldf, ldfF)
      ldfF.close()
      
    ldf = startSession(ldf)
    (ldf, initialData) = fetchInitialEvents(ldf)
    dumpChatId = None
    dumpChatName = next(iter(args.dump_chat)) if args.dump_chat != None else None
    chatList = listChats(initialData)
    for bl in chatList:
      if args.list_chats == True:
        print("{}:".format(bl["name"]))
      for b in bl["buddies"]:
        if args.list_chats == True:
          print("\t{}:{}".format(b["friendly"], b["aimId"]))
        if (dumpChatName != None) and (b["friendly"] == dumpChatName):
          dumpChatId = b["aimId"]
          print("{} has chat id {}".format(dumpChatName, dumpChatId))

    if (args.dump_chat != None):
      if dumpChatId != None:
        alsoDump = dumpChat(ldf, dumpChatId)
        
        for cId in alsoDump: #threads
          print("Going to dump thread {}".format(cId))
          dumpChat(ldf, cId)
      else:
        print("Unable to find aimId for chat {}".format(dumpChatName))
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
