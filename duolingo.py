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
HEADERS = {"Accept": "*/*", "User-Agent": "request"}

PROMPT = "Please write a short story in {language} which is less than 300 words, the story should use simple words and these special words must be included: {words}."
PROMPT_EDGE_GPT = "Please write a short story in {language} which is less than 300 words, please tell the story only without anything else, the story should use simple words and these special words must be included: {words}."
PROMPT_TRANS = "Translate the given text to {language}. Be faithful or accurate in translation. Make the translation readable or intelligible. Be elegant or natural in translation. If the text cannot be translated, return the original text as is. Do not translate person's name. Do not add any additional text in the translation. The text to be translated is:\n{text}"
PROMPT_CONVERSATION = "Can you expand these words `{words}` into an {language} conversation that contains these words? The conversation is between two people, male and female, male is A, female is B. Just return the conversation between these two people"
PROMPT_EDGE_GPT_CONVERSATION = "Can you expand these words `{words}` into an {language} conversation that contains these words? The conversation is between two people, male and female, male is A, female is B. Just return the conversation content between these two people. Please don't translate the conversation or return anything else."
EDGE_TTS_DICT = {}

GENDER_LIST = ["Male", "Female"]

with open("edge_voice_list.json") as f:
    EDGE_TTS_DICT = json.loads(f.read())


def call_openai_to_make_article(
    words, language, engine="gpt-3.5-turbo", use_azure=False
):
    prompt = PROMPT.format(language=language, words=words)
    if use_azure:
        completion = openai.ChatCompletion.create(
            engine=engine, messages=[{"role": "user", "content": prompt}]
        )
    else:
        completion = openai.ChatCompletion.create(
            model=engine, messages=[{"role": "user", "content": prompt}]
        )
    return completion["choices"][0]["message"]["content"].encode("utf8").decode()


def call_openai_to_make_conversation(
    words, language, engine="gpt-3.5-turbo", use_azure=False
):
    prompt = PROMPT_CONVERSATION.format(language=language, words=words)
    if use_azure:
        completion = openai.ChatCompletion.create(
            engine=engine, messages=[{"role": "user", "content": prompt}]
        )
    else:
        completion = openai.ChatCompletion.create(
            model=engine, messages=[{"role": "user", "content": prompt}]
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
    if respond.startswith("markdown:\n"):
        respond = respond[9:]
    return respond


def call_openai_to_make_trans(
    text, language="Simplified Chinese", engine="gpt-3.5-turbo", use_azure=False
):
    prompt = PROMPT_TRANS.format(text=text, language=language)
    if use_azure:
        completion = openai.ChatCompletion.create(
            engine=engine, messages=[{"role": "user", "content": prompt}]
        )
    else:
        completion = openai.ChatCompletion.create(
            model=engine, messages=[{"role": "user", "content": prompt}]
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


def call_edge_gpt_to_make_conversation(words, language):
    cookies = json.loads(os.environ.get("EDGE_GPT_COOKIE"))
    bot = Chatbot(cookies=cookies)
    prompt = PROMPT_EDGE_GPT_CONVERSATION.format(words=words, language=language)
    respond = asyncio.run(bot.ask(prompt))["item"]["messages"]
    respond = next(
        x
        for x in respond
        if x.get("messageType", None) is None and x.get("author") == "bot"
    )
    respond = respond["text"]
    respond = respond[respond.find("A:") :]
    respond = respond.strip("`")
    return respond


class Duolingo:
    def __init__(self, duolingo_name, duolingo_jwt, latest_number=50):
        self.duolingo_name = duolingo_name
        self.duolingo_jwt = duolingo_jwt
        self.s = requests.session()
        self.lauguage = None
        self.tts_url = ""
        self.latest_number = latest_number
        self.duolingo_data = None

    def _make_duolingo_setting(self):
        try:
            r = self.s.get(DUOLINGO_SETTING_URL, headers=HEADERS)
        except Exception as e:
            print(f"Something is wrong to get the setting error: {str(e)}")
            exit(1)
        setting_data = r.json()
        tts_base_url = setting_data.get("tts_base_url")
        if not tts_base_url:
            raise Exception("Something wrong get the tts url")
        # request data
        HEADERS["Authorization"] = "Bearer " + self.duolingo_jwt
        r = self.s.get(
            f"https://www.duolingo.com/users/{self.duolingo_name}", headers=HEADERS
        )
        if r.status_code != 200:
            raise Exception("Get profile failed")
        self.duolingo_data = r.json()
        self.lauguage = self.duolingo_data["learning_language"]

        lauguage_tts_dict = setting_data.get("tts_voice_configuration", {}).get(
            "voices"
        )
        lauguage_path = json.loads(lauguage_tts_dict).get(self.lauguage)
        self.tts_url = f"{tts_base_url}tts/{lauguage_path}/token/"

    def get_duolingo_daily(self):
        if not self.duolingo_data:
            self._make_duolingo_setting()
        is_today_check = self.duolingo_data["streak_extended_today"]
        streak = self.duolingo_data["site_streak"]
        level_progress = (
            self.duolingo_data["language_data"]
            .get(self.lauguage, {})
            .get("level_progress", 0)
        )
        return level_progress, streak, is_today_check

    def get_duolingo_words_and_save_mp3(self):
        if not self.tts_url:
            self._make_duolingo_setting()
        r = self.s.get("https://www.duolingo.com/vocabulary/overview", headers=HEADERS)
        if not r.ok:
            raise Exception("get duolingo words failed")
        res_json = r.json()
        words = res_json["vocab_overview"]
        language_short = res_json["learning_language"]
        language = res_json["language_string"]

        words.sort(key=lambda v: v.get("last_practiced_ms", 0), reverse=True)
        words_list = []
        my_new_words = words[: self.latest_number]

        def download_word_to_mp3(i, word_string):
            mp3_content = requests.get(f"{self.tts_url}{word_string}")
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
        use_azure = False
        if os.environ.get("OPENAI_API_KEY"):
            if os.environ.get("API_TYPE") == "azure":
                use_azure = True
                openai.api_type = "azure"
                openai.api_base = os.environ.get("OPENAI_API_BASE")
                if openai.api_base is None:
                    raise Exception("Please provide OPENAI_API_BASE in env")
                engine = os.environ.get("OPENAI_ENGINE")
                if engine is None:
                    raise Exception("Please provide OPENAI_ENGINE in env")
                api_version = os.environ.get("OPENAI_API_VERSION")
                openai.api_version = (
                    api_version if api_version else "2023-03-15-preview"
                )
                print(f"Using Azure API with engine {engine}")
            else:
                engine = "gpt-3.5-turbo"
                print(f"Using OpenAI API with engine {engine}")
            article = call_openai_to_make_article(
                words_str, language, engine, use_azure=use_azure
            )
            article_trans = call_openai_to_make_trans(
                text=article, engine=engine, use_azure=use_azure
            )
            # conversation
            conversion = call_openai_to_make_conversation(
                words_str, language, engine, use_azure=use_azure
            )
            conversion_trans = call_openai_to_make_trans(
                text=conversion, engine=engine, use_azure=use_azure
            )

        elif os.environ.get("EDGE_GPT_COOKIE"):
            print("Using Edge GPT API")
            article = call_edge_gpt_to_make_article(words_str, language)
            article_trans = call_edge_gpt_to_make_trans(article)
            conversion = call_edge_gpt_to_make_conversation(words_str, language)
            conversion_trans = call_edge_gpt_to_make_trans(conversion)
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


def main(duolingo_user_name, duolingo_jwt, tele_token, tele_chat_id, latest_num):
    try:
        latest_num = int(latest_num)
    except Exception as e:
        print(str(e))
        # default
        latest_num = 20
    duolingo = Duolingo(duolingo_user_name, duolingo_jwt, latest_number=latest_num)
    duolingo._make_duolingo_setting()
    _, duolingo_streak, duolingo_today_check = duolingo.get_duolingo_daily()
    (
        duolingo_words,
        article,
        article_trans,
        conversion,
        conversion_trans,
    ) = duolingo.get_duolingo_words_and_save_mp3()
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
