
import sys
import os
import shutil
import requests as req
import time
import datetime
import threading
import itertools

def getConfig(keyvals) -> dict:
  config = {}
  expectedKeys = {"session","year","day"}
  for keyval in keyvals:
    (key, val) = keyval.split('=')
    expectedKeys.remove(key.strip())      
    config[key.strip()] = val.strip()
  if len(expectedKeys) != 0:
    raise KeyError(f'Missing {[field for field in expectedKeys]} fields in settings.ini')
  return config

def increaseConfigDayValue(config):
  with open('settings.ini', 'w') as f:
    for key, val in config.items():
      if (key == "day"):
        val = int(val)+1
      f.write(key+"="+str(val)+'\n')

def buildNewFolder(day, input):
  os.chdir("..")
  os.mkdir(day)
  obj = os.scandir("./AdventOfCodeUtils/dummy")
  for entry in obj :
    if entry.is_file() or entry.is_dir():
      shutil.copy(entry, os.curdir+"/"+day)
  with open(f'{day}/input.txt','w') as f:
    f.write(input)
  os.chdir("./AdventOfCodeUtils")

def estimateSecondsUntilDrop():
  utc = datetime.datetime.utctimetuple(datetime.datetime.now().utcnow())
  currentSecondsInDay = utc.tm_sec + 60 * (utc.tm_min + 60 * ((utc.tm_hour-5)%24))
  return (24*3600-currentSecondsInDay+30) ## pad ~30 seconds because AoC's clock seems to be roughly 30sec fast

def getSecondsUntilDrop(HTTPsession):
  r = HTTPsession.get("https://adventofcode.com/")
  if not r.ok:
    return estimateSecondsUntilDrop()
  else:
    eta_start = r.text.find("var server_eta = ")+17
    eta_end = r.text.find(";", eta_start)
    return int(r.text[eta_start:eta_end])
  
def getStartTime(HTTPsession):
  secondsUntil = getSecondsUntilDrop(HTTPsession)
  return time.time() + secondsUntil

def printCountDownMessage(c, totalSecondsLeft):
  hoursLeft = int(totalSecondsLeft / 3600)
  minutesLeft = int((totalSecondsLeft-(hoursLeft*3600)) / 60)
  secLeft = totalSecondsLeft % 60
  if (totalSecondsLeft > 3600):
    sys.stdout.write(f'\r{c} Waiting {hoursLeft} hours {minutesLeft} minutes {secLeft} seconds {c}')
  elif(totalSecondsLeft > 60):
    sys.stdout.write(f'\r{c} Waiting {minutesLeft} minutes {secLeft} seconds {c}                ')
  else:
    sys.stdout.write(f'\r{c} Waiting {totalSecondsLeft} seconds {c}                            ')

def waitTillDrop(HTTPsession):
  startTime = getStartTime(HTTPsession)
  done = False
  interrupted = False
  
  def animate():
    for c in itertools.cycle(["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]):
        totalSecondsLeft = int(startTime - time.time())
        printCountDownMessage(c, totalSecondsLeft)
        sys.stdout.flush()
        time.sleep(0.1)

        if done or interrupted or totalSecondsLeft < 0:
            break
        
    if not interrupted:
      sys.stdout.write('\rDone!                                        \n')

  t = threading.Thread(target=animate)
  t.start()
  
  #Blocking wait, still catches Ctrl-C keyboard interrupts quickly
  try:
    while(time.time() < startTime):
      time.sleep(0.5)
  except KeyboardInterrupt:
    interrupted = True
    raise KeyboardInterrupt("User Escape Sequence")
  done = True


def main() -> int:
  s = req.session()
  my_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}
  s.headers.update(my_headers)
  config = {}
  status_code = 404
  retryCodes = [404]
  retryWarningSent = False
  with open('settings.ini', 'r') as c:
    try:
      config = getConfig(c.readlines())
    except KeyError:
      sys.stdout.write("[KeyError] settings.ini seems misconfigured. See README.md for example format.")
    except ValueError:
      sys.stdout.write("[ValueError] settings.ini seems misconfigured. See README.md for example format.")

    s.cookies.set("session",config["session"],domain="adventofcode.com")
    attempts = 1
    while (status_code in retryCodes):
      r = s.get("https://adventofcode.com/2021/day/"+config["day"]+"/input")
      status_code = r.status_code
      time.sleep(0.2*attempts) # to prevent spamming AoC servers w/ requests
      if not retryWarningSent:
        if not r.ok and status_code in retryCodes:
          retryWarningSent = True
          print("Couldn't retrieve input. Waiting until 12:00 EST to attempt a new request.")
          try:
            waitTillDrop(s)
          except KeyboardInterrupt:
            sys.stdout.write("\rLet's try again later                           ")
            return 0
      attempts += 1
    input = r.text.rstrip()
  



  if (r.ok):
    buildNewFolder(config["day"], input)
    increaseConfigDayValue(config)
    print("Success! Happy Coding!")
  else:
    print("[ERROR] GET Response Code: " + str(r.status_code))
    print("[ERROR] " + r.reason)
    print("Couldn't retrieve today's input. Try updating your session key in settings.ini")

  return 0


if __name__ == '__main__':
  sys.exit(main())