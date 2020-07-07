#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 16:28:56 2020

@author: gustavolibotte
"""

import json
import sys
from time import sleep

from helium import S, click, kill_browser, start_chrome, wait_until
from selenium import webdriver
from selenium.common.exceptions import TimeoutException

opts = webdriver.ChromeOptions()
opts.set_capability("loggingPrefs", {"performance": "ALL"})
driver = start_chrome("https://covid.saude.gov.br/", options=opts)
wait_until(S("ion-button").exists)
sleep(3)
click("Arquivo CSV")

global URL
URL = None

def process_browser_log_entry(entry):
    response = json.loads(entry["message"])["message"]
    return response

def fetch_download_url():
    global URL

    browser_log = driver.get_log("performance")
    events = [process_browser_log_entry(entry) for entry in browser_log]
    responses = [event for event in events if "Network.response" in event["method"]]

    for r in responses:
        if "params" not in r:
            continue
        params = r["params"]
        if "response" not in params:
            continue
        if "url" not in params["response"]:
            continue
        url = params["response"]["url"]
        if "HIST_PAINEL_COVIDBR" in url:
            URL = url
            return True

    return False

def run_url_catcher():
    try:
        wait_until(fetch_download_url, timeout_secs=15)
    except TimeoutException as e:
        print("Failed!")
        print(e)
    else:
        return URL
    finally:
        kill_browser()
        
    
    if URL is None:
        sys.exit(1)