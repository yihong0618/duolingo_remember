import argparse
import os
import json

import requests

DUOLINGO_SETTING_URL = "https://www.duolingo.com/api/1/version_info"


def get_duolingo_setting():
    try:
        r = requests.get(DUOLINGO_SETTING_URL)
    except Exception as e:
        print(f"Something is wrong to get the setting error: {str(e)}")
        exit(1)
    setting_data = r.json()
    tts_base_url = setting_data.get("tts_base_url")
    if not tts_base_url:
        raise Exception("Something wrong get the tts url")
    lauguage_tts_dict = setting_data.get("tts_voice_configuration", {}).get("voices")
    return tts_base_url, json.loads(lauguage_tts_dict)

def get_duolingo_session_and_name(user_name, password):
    headers = {
        "Accept": "*/*",
        "User-Agent": "request",
    }
    s = requests.Session()
    r = s.post(
        "https://www.duolingo.com/login",
        params={"login": user_name, "password": password},
        headers=headers
    )
    if r.status_code != 200:
        raise Exception("Login failed")
    name = r.json()["username"]
    return s, name


def get_duolingo_daily(session, name):
    r = session.get(f"https://www.duolingo.com/users/{name}")
    if r.status_code != 200:
        raise Exception("Get profile failed")
    data = r.json()
    is_today_check = data["streak_extended_today"]
    streak = data["site_streak"]
    lauguage = data["learning_language"]
    level_progress = data["language_data"].get(lauguage, {}).get("level_progress", 0)
    return level_progress, lauguage, streak, is_today_check


def get_duolingo_words_and_save_mp3(session, tts_url, latest_num=100):
    r = session.get("https://www.duolingo.com/vocabulary/overview")
    if not r.ok:
        raise Exception("get duolingo words failed")
    
    words = r.json()["vocab_overview"]
    words.sort(key=lambda v: v.get("last_practiced_ms", 0), reverse=True)
    words_list = []
    i = 1
    my_new_words = words[:latest_num]
    for w in my_new_words:
        if w["normalized_string"] == "<*sf>":
            continue
        word_string = w["word_string"] 
        words_list.append(word_string)
        try:
            mp3_content = requests.get(f"{tts_url}{word_string}")
            with open(os.path.join("MP3_NEW", str(i) + ".mp3"), "wb") as f:
                f.write(mp3_content.content)
            i += 1
        except:
            pass
    if words_list:
        return "\n".join(words_list)


def main(duolingo_user_name, duolingo_password, tele_token, tele_chat_id, latest_num):
    s, duolingo_name = get_duolingo_session_and_name(
        duolingo_user_name, duolingo_password
    )
    _, lauguage, duolingo_streak, duolingo_today_check = get_duolingo_daily(s, duolingo_name)
    tts_url_base, lauguage_setting_dict = get_duolingo_setting()
    lauguage_path = lauguage_setting_dict.get(lauguage) 
    tts_url = f"{tts_url_base}tts/{lauguage_path}/token/"
    try:
        latest_num = int(latest_num)
    except Exception as e:
        print(str(e))
        # default
        latest_num = 50
    duolingo_words = get_duolingo_words_and_save_mp3(s, tts_url, latest_num=latest_num)
    if duolingo_words:
        duolingo_words = (
            f"Your streak: {duolingo_streak}\n" "New words\n" + duolingo_words
        )
        requests.post(
            url="https://api.telegram.org/bot{0}/{1}".format(tele_token, "sendMessage"),
            data={"chat_id": tele_chat_id, "text": duolingo_words},
        )
    if not duolingo_today_check:
        requests.post(
            url="https://api.telegram.org/bot{0}/{1}".format(tele_token, "sendMessage"),
            data={
                "chat_id": tele_chat_id,
                "text": "You are not streak today, please note",
            },
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("duolingo_user_name", help="duolingo_user_name")
    parser.add_argument("duolingo_password", help="duolingo_password")
    parser.add_argument("tele_token", help="tele_token")
    parser.add_argument("tele_chat_id", help="tele_chat_id")
    parser.add_argument("latest_number", help="latest_number")
    options = parser.parse_args()
    main(
        options.duolingo_user_name,
        options.duolingo_password,
        options.tele_token,
        options.tele_chat_id,
        options.latest_number,
    )
