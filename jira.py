#!/usr/bin/env python3

import time
import os

import requests
import json
from datetime import date
import dateutil.parser as iso

from my_auth import *

project = "<PROJECT>"
my_user_name = "<USERNAME>"
jira_url = "<URL>"
min_key = 1
max_key = 100
skip_dates = {
    date(2006, 12, 18),
}
JIRA_DEBUG = False

missing_file_path = "missing-tickets.txt"
try:
    with open(missing_file_path, 'r') as f:
        missing_tickets = set(f.read().split("\n"))
except OSError:
    print("Could not read " + missing_file_path)
    missing_tickets = set()
print("Missing tickets count = ", len(missing_tickets))
print("Missing tickets: ", ", ".join(sorted(missing_tickets)))


def get_issue_url(issue_key: str) -> str:
    return jira_url + '/rest/api/2/issue/' + issue_key


def json_path(title: str) -> str:
    return "json_dump/" + title + ".json"


def load_json(title: str):
    file = json_path(title)
    try:
        print("Loading json: ", file)
        print("Size of file: ", os.stat(file).st_size)
        with open(file, 'r') as jf:
            return json.load(jf)
    except FileNotFoundError:
        print("No file: " + file)
    except OSError:
        print("OSError while reading file: " + file)
    return None


def download_issue(issue_key: str):
    result = None
    issue_url = get_issue_url(issue_key)
    params = {
        "fields": "key,summary",
        "expand": "changelog"
    }
    if issue_key in missing_tickets:
        print("Skipping missing ticket ", issue_key)
        return None
    print("Downloading: ", issue_key)
    while True:
        try:
            r = requests.get(issue_url,
                             params=params,
                             auth=get_auth(my_login=my_user_name, prompt_line="jira pass:"),
                             verify=False)
            if r.status_code != 200:
                print(r)
                print("Download failed for ticket ", issue_key)
                if r.status_code == 401:
                    print("Wrong password")
                    reset_auth()
                    # go into while True again, ask for password one more time
                    continue
                if r.status_code == 403:
                    print("Need to enter CAPTCHA in the web JIRA interface")
                    reset_auth()
                    continue
                if r.status_code == 404:
                    print("No issue ", issue_key)
                    missing_tickets.add(issue_key)
                break
            else:
                if JIRA_DEBUG:
                    print("url: ", issue_url)
                print("Request successful")
                result = r.json()
                if JIRA_DEBUG:
                    print(str(json.dumps(r.json(), indent=4, separators=(',', ': '))))
                break  # whatever, still can return the json
        except requests.exceptions.ConnectionError as ce:
            clear_key(key)
            print("Connection error: ", ce)
            print("Waiting for {0} seconds...".format(NETWORK_ERROR_WAIT_DELAY))
            time.sleep(NETWORK_ERROR_WAIT_DELAY)
            # print("Trying again...")
            # might be useless to try again, return None
            break
    return result


def pretty_print(json_obj):
    print(str(json.dumps(json_obj, indent=4, separators=(',', ': '))))


def get_history(issue_json_obj):
    return issue_json_obj['changelog']['histories']


tickets_title = project + '-tickets'
tickets_json = load_json(tickets_title)
if tickets_json is None:
    tickets_json = {}

print("Already saved: {0} tickets".format(len(tickets_json)))
NETWORK_ERROR_WAIT_DELAY = 5  # five seconds


def clear_key(k):
    if k in tickets_json:
        if 'downloaded' not in tickets_json[k]:
            tickets_json.pop(k, None)


def get_history_or(issue_json_obj, default_value="Empty history") -> str:
    history_json = get_history(issue_json_obj)
    if len(history_json) == 0:
        return default_value
    return history_json[0]['created']


for i in range(min_key, max_key):
    key = project + '-' + str(i)
    try:
        if key not in tickets_json:
            issue_json = download_issue(key)
            if issue_json is None:
                # could not download issue
                continue
            # store the ticket. Use 'JIRA' as key for the json part of the JIRA's response
            tickets_json[key] = {}
            tickets_json[key]['JIRA'] = issue_json
            # show the first item in the history to the user
            pretty_print(get_history_or(issue_json))
            tickets_json[key]['downloaded'] = True
    except KeyboardInterrupt:
        clear_key(key)
        print("Interrupted by the user")
        break
    except Exception as e:
        clear_key(key)
        print("Unexpected exception: ", e)
        print("Key: ", key)
        print("Bailing out")
        break
    if key not in tickets_json:
        continue
    issue_json = tickets_json[key]['JIRA']
    issue_history = get_history(issue_json)
    toRemove = []
    for changelog_entry in issue_history:
        timestamp = changelog_entry['created']
        iso_date = iso.parse(timestamp).date()
        if JIRA_DEBUG:
            print(iso_date)
        if iso_date in skip_dates:
            toRemove.append(changelog_entry)
    for x in toRemove:
        issue_history.remove(x)


def save_json(title: str, json_obj):
    with open(json_path(title), 'w') as f:
        json.dump(json_obj, f)


# store all the tickets
print("Total number of tickets: {0}".format(len(tickets_json)))
print("Saving " + json_path(tickets_title))
save_json(tickets_title, tickets_json)
print("Saved!")

print("Saving " + missing_file_path)
with open(missing_file_path, "w") as f:
    f.write("\n".join(sorted(missing_tickets)))
print("Saved!")

tickets_to_process = []
for i in range(min_key, max_key):
    key = project + '-' + str(i)
    if key not in tickets_json:
        continue
    ticket_json = tickets_json[key]['JIRA']
    if JIRA_DEBUG:
        print("Ticket : " + key)
        pretty_print(ticket_json)
    # jira.pretty_print(jira.get_history(ticket_json))
    tickets_to_process.append(key)

changes = {}
for key in tickets_to_process:
    ticket_json = tickets_json[key]['JIRA']
    history = get_history(ticket_json)
    for h in history:
        timestamp = h['created']
        h['ticket'] = key
        changes[timestamp + key] = h

