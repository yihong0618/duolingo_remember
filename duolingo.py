import argparse
import os
import random
import json
import threading

from rich import print
import requests
import openai
import edge_tts
import asyncio
from EdgeGPT import Chatbot

DUOLINGO_SETTING_URL = "https://www.duolingo.com/api/1/version_info"
HEADERS = {
    "Accept": "*/*",
    "User-Agent": "request",
}

PROMPT = "Please write a short story in {language} which is less than 300 words, the story should use simple words and these special words must be included: {words}."
PROMPT_EDGE_GPT = "Please write a short story in {language} which is less than 300 words, please tell the story only without anything else, the story should use simple words and these special words must be included: {words}."
PROMPT_TRANS = "Translate the given text to {language}. Be faithful or accurate in translation. Make the translation readable or intelligible. Be elegant or natural in translation. If the text cannot be translated, return the original text as is. Do not translate person's name. Do not add any additional text in the translation. The text to be translated is:\n{text}"
PROMPT_CONVERSATION = "Can you expand these words `{words}` into an {language} conversation that contains these words? The conversation is between two people, male and female, male is A, female is B. Just return the conversation between these two people"

EDGE_TTS_DICT = {}

GENDER_LIST = ["Male", "Female"]

with open("edge_voice_list.json") as f:
    EDGE_TTS_DICT = json.loads(f.read())


def call_openai_to_make_article(words, language):
    prompt = PROMPT.format(language=language, words=words)
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion["choices"][0]["message"]["content"].encode("utf8").decode()


def call_openai_to_make_conversation(words, language):
    prompt = PROMPT_CONVERSATION.format(language=language, words=words)
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion["choices"][0]["message"]["content"].encode("utf8").decode()


def call_edge_gpt_to_make_article(words, language):
    cookies = json.loads(os.environ.get("EDGE_GPT_COOKIE"))
    bot = Chatbot(cookies=cookies)
    prompt = PROMPT_EDGE_GPT.format(language=language, words=words)
    respond = asyncio.run(bot.ask(prompt))["item"]["messages"]
    respond = next(
        x
        for x in respond
        if x.get("messageType", None) is None and x.get("author") == "bot"
    )
    respond = respond["text"].strip("`")
    if respond.startswith("md\n"):
        respond = respond[3:]
    return respond


def call_openai_to_make_trans(text, language="Simplified Chinese"):
    prompt = PROMPT_TRANS.format(text=text, language=language)
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion["choices"][0]["message"]["content"].encode("utf8").decode()


def call_edge_gpt_to_make_trans(text, language="Simplified Chinese"):
    cookies = json.loads(os.environ.get("EDGE_GPT_COOKIE"))
    bot = Chatbot(cookies=cookies)
    prompt = PROMPT_TRANS.format(text=text, language=language)
    respond = asyncio.run(bot.ask(prompt))["item"]["messages"]
    respond = next(
        x
        for x in respond
        if x.get("messageType", None) is None and x.get("author") == "bot"
    )
    return respond["text"]


class Duolingo:
    """
    TODO refactor
    """

    def __init__(self):
        pass


def get_duolingo_setting():
    try:
        r = requests.get(DUOLINGO_SETTING_URL, headers=HEADERS)
    except Exception as e:
        print(f"Something is wrong to get the setting error: {str(e)}")
        exit(1)
    setting_data = r.json()
    tts_base_url = setting_data.get("tts_base_url")
    if not tts_base_url:
        raise Exception("Something wrong get the tts url")
    lauguage_tts_dict = setting_data.get("tts_voice_configuration", {}).get("voices")
    return tts_base_url, json.loads(lauguage_tts_dict)


def get_duolingo_daily(name, jwt):
    HEADERS["Authorization"] = "Bearer " + jwt
    r = requests.get(f"https://www.duolingo.com/users/{name}", headers=HEADERS)
    if r.status_code != 200:
        raise Exception("Get profile failed")
    data = r.json()
    is_today_check = data["streak_extended_today"]
    streak = data["site_streak"]
    lauguage = data["learning_language"]
    level_progress = data["language_data"].get(lauguage, {}).get("level_progress", 0)
    return level_progress, lauguage, streak, is_today_check


def make_edge_article_tts_mp3(text, language_short):
    """
    TODO Refactor this shit
    """
    gender = random.choice(GENDER_LIST)
    language = random.choice(EDGE_TTS_DICT[language_short][gender])
    communicate = edge_tts.Communicate(text, language)
    asyncio.run(communicate.save("new_article.mp3"))


def make_edge_conversation_tts_mp3(text, language_short):
    """
    A, B two roles in coversation
    we make mp3 then use ffmpeg to combine them
    TODO refactor
    """
    male_voice = random.choice(EDGE_TTS_DICT[language_short]["Male"])
    female_voice = random.choice(EDGE_TTS_DICT[language_short]["Female"])
    lines_list = text.splitlines()
    i = 1
    for line in lines_list:
        if line.startswith("A: "):
            line = line[3:]
            print(line)
            communicate = edge_tts.Communicate(line, male_voice)
            asyncio.run(communicate.save(os.path.join("CONVERSATION_NEW", f"{i}.mp3")))
            i += 1
        elif line.startswith("B: "):
            line = line[3:]
            print(line)
            communicate = edge_tts.Communicate(line, female_voice)
            asyncio.run(communicate.save(os.path.join("CONVERSATION_NEW", f"{i}.mp3")))
            i += 1


def get_duolingo_words_and_save_mp3(tts_url, latest_num=100):
    r = requests.get("https://www.duolingo.com/vocabulary/overview", headers=HEADERS)
    if not r.ok:
        raise Exception("get duolingo words failed")
    res_json = r.json()
    words = res_json["vocab_overview"]
    language_short = res_json["learning_language"]
    language = res_json["language_string"]

    words.sort(key=lambda v: v.get("last_practiced_ms", 0), reverse=True)
    words_list = []
    my_new_words = words[:latest_num]

    def download_word_to_mp3(i, word_string, tts_url=tts_url):
        mp3_content = requests.get(f"{tts_url}{word_string}")
        with open(os.path.join("MP3_NEW", str(i) + ".mp3"), "wb") as f:
            f.write(mp3_content.content)

    for w in my_new_words:
        if w["normalized_string"] == "<*sf>":
            continue
        word_string = w["word_string"]
        words_list.append(word_string)

    for index, w in enumerate(words_list):
        t = threading.Thread(target=download_word_to_mp3, args=(index, w))
        t.start()
        t.join()

    words_str = ",".join(words_list)
    conversion = ""
    conversion_trans = ""
    if os.environ.get("OPENAI_API_KEY"):
        article = call_openai_to_make_article(words_str, language)
        article_trans = call_openai_to_make_trans(article)
        # conversation
        conversion = call_openai_to_make_conversation(words_str, language)
        conversion_trans = call_openai_to_make_trans(conversion)

    elif os.environ.get("EDGE_GPT_COOKIE"):
        article = call_edge_gpt_to_make_article(words_str, language)
        article_trans = call_edge_gpt_to_make_trans(article)
    else:
        raise Exception("Please provide OPENAI_API_KEY or EDGE_GPT_COOKIE in env")

    # call edge-tts to generate mp3
    make_edge_article_tts_mp3(article, language_short)
    make_edge_conversation_tts_mp3(conversion, language_short)

    if words_list:
        return (
            "\n".join(words_list),
            article,
            article_trans,
            conversion,
            conversion_trans,
        )


def main(duolingo_user_name, duolingo_jwt, tele_token, tele_chat_id, latest_num):
    _, lauguage, duolingo_streak, duolingo_today_check = get_duolingo_daily(
        duolingo_user_name, duolingo_jwt
    )
    tts_url_base, lauguage_setting_dict = get_duolingo_setting()
    lauguage_path = lauguage_setting_dict.get(lauguage)
    tts_url = f"{tts_url_base}tts/{lauguage_path}/token/"
    try:
        latest_num = int(latest_num)
    except Exception as e:
        print(str(e))
        # default
        latest_num = 20
    (
        duolingo_words,
        article,
        article_trans,
        conversion,
        conversion_trans,
    ) = get_duolingo_words_and_save_mp3(tts_url, latest_num=latest_num)
    print(duolingo_words, article, article_trans, conversion, conversion_trans)
    if duolingo_words and tele_token and tele_chat_id:
        duolingo_words = (
            f"Your streak: {duolingo_streak}\n" "New words\n" + duolingo_words
        )
        requests.post(
            url="https://api.telegram.org/bot{0}/{1}".format(tele_token, "sendMessage"),
            data={"chat_id": tele_chat_id, "text": duolingo_words},
        )
        requests.post(
            url="https://api.telegram.org/bot{0}/{1}".format(tele_token, "sendMessage"),
            data={"chat_id": tele_chat_id, "text": f"New Article:\n{article}"},
        )
        requests.post(
            url="https://api.telegram.org/bot{0}/{1}".format(tele_token, "sendMessage"),
            data={
                "chat_id": tele_chat_id,
                "text": f"New Article Trans:\n{article_trans}",
            },
        )
        if conversion:
            requests.post(
                url="https://api.telegram.org/bot{0}/{1}".format(
                    tele_token, "sendMessage"
                ),
                data={
                    "chat_id": tele_chat_id,
                    "text": f"New Conversation:\n{conversion}",
                },
            )
        if conversion_trans:
            requests.post(
                url="https://api.telegram.org/bot{0}/{1}".format(
                    tele_token, "sendMessage"
                ),
                data={
                    "chat_id": tele_chat_id,
                    "text": f"New Conversation Trans:\n{conversion_trans}",
                },
            )

    if not duolingo_today_check and tele_chat_id and tele_token:
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
    parser.add_argument("duolingo_jwt", help="duolingo jwt ")
    parser.add_argument(
        "--tele_token", help="tele_token", nargs="?", default="", const=""
    )
    parser.add_argument(
        "--tele_chat_id", help="tele_chat_id", nargs="?", default="", const=""
    )
    parser.add_argument("--latest_number", help="latest_number", default=20)
    options = parser.parse_args()
    main(
        options.duolingo_user_name,
        options.duolingo_jwt,
        options.tele_token,
        options.tele_chat_id,
        options.latest_number,
    )
