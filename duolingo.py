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

DUOLINGO_SETTING_URL = "https://www.duolingo.com/api/1/version_info"
HEADERS = {
    "Accept": "*/*",
    "User-Agent": "request",
}

PROMPT = "Please write a short story in {language} which is less than 300 words, the story should use simple words and these special words must be included: ${words}."
PROMPT_TRANS = "Translate the given text to {language}. Be faithful or accurate in translation. Make the translation readable or intelligible. Be elegant or natural in translation. f the text cannot be translated, return the original text as is. Do not translate person's name. Do not add any additional text in the translation. The text to be translated is:\n{text}"

EDGE_TTS_DICT = {
    "af": ["af-ZA-AdriNeural", "af-ZA-WillemNeural"],
    "am": ["am-ET-AmehaNeural", "am-ET-MekdesNeural"],
    "ar": [
        "ar-AE-FatimaNeural",
        "ar-AE-HamdanNeural",
        "ar-BH-AliNeural",
        "ar-BH-LailaNeural",
        "ar-DZ-AminaNeural",
        "ar-DZ-IsmaelNeural",
        "ar-EG-SalmaNeural",
        "ar-EG-ShakirNeural",
        "ar-IQ-BasselNeural",
        "ar-IQ-RanaNeural",
        "ar-JO-SanaNeural",
        "ar-JO-TaimNeural",
        "ar-KW-FahedNeural",
        "ar-KW-NouraNeural",
        "ar-LB-LaylaNeural",
        "ar-LB-RamiNeural",
        "ar-LY-ImanNeural",
        "ar-LY-OmarNeural",
        "ar-MA-JamalNeural",
        "ar-MA-MounaNeural",
        "ar-OM-AbdullahNeural",
        "ar-OM-AyshaNeural",
        "ar-QA-AmalNeural",
        "ar-QA-MoazNeural",
        "ar-SA-HamedNeural",
        "ar-SA-ZariyahNeural",
        "ar-SY-AmanyNeural",
        "ar-SY-LaithNeural",
        "ar-TN-HediNeural",
        "ar-TN-ReemNeural",
        "ar-YE-MaryamNeural",
        "ar-YE-SalehNeural",
    ],
    "az": ["az-AZ-BabekNeural", "az-AZ-BanuNeural"],
    "bg": ["bg-BG-BorislavNeural", "bg-BG-KalinaNeural"],
    "bn": [
        "bn-BD-NabanitaNeural",
        "bn-BD-PradeepNeural",
        "bn-IN-BashkarNeural",
        "bn-IN-TanishaaNeural",
    ],
    "bs": ["bs-BA-GoranNeural", "bs-BA-VesnaNeural"],
    "ca": ["ca-ES-EnricNeural", "ca-ES-JoanaNeural"],
    "cs": ["cs-CZ-AntoninNeural", "cs-CZ-VlastaNeural"],
    "cy": ["cy-GB-AledNeural", "cy-GB-NiaNeural"],
    "da": ["da-DK-ChristelNeural", "da-DK-JeppeNeural"],
    "de": [
        "de-AT-IngridNeural",
        "de-AT-JonasNeural",
        "de-CH-JanNeural",
        "de-CH-LeniNeural",
        "de-DE-AmalaNeural",
        "de-DE-ConradNeural",
        "de-DE-KatjaNeural",
        "de-DE-KillianNeural",
    ],
    "el": ["el-GR-AthinaNeural", "el-GR-NestorasNeural"],
    "en": [
        "en-AU-NatashaNeural",
        "en-AU-WilliamNeural",
        "en-CA-ClaraNeural",
        "en-CA-LiamNeural",
        "en-GB-LibbyNeural",
        "en-GB-MaisieNeural",
        "en-GB-RyanNeural",
        "en-GB-SoniaNeural",
        "en-GB-ThomasNeural",
        "en-HK-SamNeural",
        "en-HK-YanNeural",
        "en-IE-ConnorNeural",
        "en-IE-EmilyNeural",
        "en-IN-NeerjaExpressiveNeural",
        "en-IN-NeerjaNeural",
        "en-IN-PrabhatNeural",
        "en-KE-AsiliaNeural",
        "en-KE-ChilembaNeural",
        "en-NG-AbeoNeural",
        "en-NG-EzinneNeural",
        "en-NZ-MitchellNeural",
        "en-NZ-MollyNeural",
        "en-PH-JamesNeural",
        "en-PH-RosaNeural",
        "en-SG-LunaNeural",
        "en-SG-WayneNeural",
        "en-TZ-ElimuNeural",
        "en-TZ-ImaniNeural",
        "en-US-AnaNeural",
        "en-US-AriaNeural",
        "en-US-ChristopherNeural",
        "en-US-EricNeural",
        "en-US-GuyNeural",
        "en-US-JennyNeural",
        "en-US-MichelleNeural",
        "en-US-RogerNeural",
        "en-US-SteffanNeural",
        "en-ZA-LeahNeural",
        "en-ZA-LukeNeural",
    ],
    "es": [
        "es-AR-ElenaNeural",
        "es-AR-TomasNeural",
        "es-BO-MarceloNeural",
        "es-BO-SofiaNeural",
        "es-CL-CatalinaNeural",
        "es-CL-LorenzoNeural",
        "es-CO-GonzaloNeural",
        "es-CO-SalomeNeural",
        "es-CR-JuanNeural",
        "es-CR-MariaNeural",
        "es-CU-BelkysNeural",
        "es-CU-ManuelNeural",
        "es-DO-EmilioNeural",
        "es-DO-RamonaNeural",
        "es-EC-AndreaNeural",
        "es-EC-LuisNeural",
        "es-ES-AlvaroNeural",
        "es-ES-ElviraNeural",
        "es-GQ-JavierNeural",
        "es-GQ-TeresaNeural",
        "es-GT-AndresNeural",
        "es-GT-MartaNeural",
        "es-HN-CarlosNeural",
        "es-HN-KarlaNeural",
        "es-MX-DaliaNeural",
        "es-MX-JorgeNeural",
        "es-NI-FedericoNeural",
        "es-NI-YolandaNeural",
        "es-PA-MargaritaNeural",
        "es-PA-RobertoNeural",
        "es-PE-AlexNeural",
        "es-PE-CamilaNeural",
        "es-PR-KarinaNeural",
        "es-PR-VictorNeural",
        "es-PY-MarioNeural",
        "es-PY-TaniaNeural",
        "es-SV-LorenaNeural",
        "es-SV-RodrigoNeural",
        "es-US-AlonsoNeural",
        "es-US-PalomaNeural",
        "es-UY-MateoNeural",
        "es-UY-ValentinaNeural",
        "es-VE-PaolaNeural",
        "es-VE-SebastianNeural",
    ],
    "et": ["et-EE-AnuNeural", "et-EE-KertNeural"],
    "fa": ["fa-IR-DilaraNeural", "fa-IR-FaridNeural"],
    "fi": ["fi-FI-HarriNeural", "fi-FI-NooraNeural"],
    "fil": ["fil-PH-AngeloNeural", "fil-PH-BlessicaNeural"],
    "fr": [
        "fr-BE-CharlineNeural",
        "fr-BE-GerardNeural",
        "fr-CA-AntoineNeural",
        "fr-CA-JeanNeural",
        "fr-CA-SylvieNeural",
        "fr-CH-ArianeNeural",
        "fr-CH-FabriceNeural",
        "fr-FR-DeniseNeural",
        "fr-FR-EloiseNeural",
        "fr-FR-HenriNeural",
    ],
    "ga": ["ga-IE-ColmNeural", "ga-IE-OrlaNeural"],
    "gl": ["gl-ES-RoiNeural", "gl-ES-SabelaNeural"],
    "gu": ["gu-IN-DhwaniNeural", "gu-IN-NiranjanNeural"],
    "he": ["he-IL-AvriNeural", "he-IL-HilaNeural"],
    "hi": ["hi-IN-MadhurNeural", "hi-IN-SwaraNeural"],
    "hr": ["hr-HR-GabrijelaNeural", "hr-HR-SreckoNeural"],
    "hu": ["hu-HU-NoemiNeural", "hu-HU-TamasNeural"],
    "id": ["id-ID-ArdiNeural", "id-ID-GadisNeural"],
    "is": ["is-IS-GudrunNeural", "is-IS-GunnarNeural"],
    "it": ["it-IT-DiegoNeural", "it-IT-ElsaNeural", "it-IT-IsabellaNeural"],
    "ja": ["ja-JP-KeitaNeural", "ja-JP-NanamiNeural"],
    "jv": ["jv-ID-DimasNeural", "jv-ID-SitiNeural"],
    "ka": ["ka-GE-EkaNeural", "ka-GE-GiorgiNeural"],
    "kk": ["kk-KZ-AigulNeural", "kk-KZ-DauletNeural"],
    "km": ["km-KH-PisethNeural", "km-KH-SreymomNeural"],
    "kn": ["kn-IN-GaganNeural", "kn-IN-SapnaNeural"],
    "ko": ["ko-KR-InJoonNeural", "ko-KR-SunHiNeural"],
    "lo": ["lo-LA-ChanthavongNeural", "lo-LA-KeomanyNeural"],
    "lt": ["lt-LT-LeonasNeural", "lt-LT-OnaNeural"],
    "lv": ["lv-LV-EveritaNeural", "lv-LV-NilsNeural"],
    "mk": ["mk-MK-AleksandarNeural", "mk-MK-MarijaNeural"],
    "ml": ["ml-IN-MidhunNeural", "ml-IN-SobhanaNeural"],
    "mn": ["mn-MN-BataaNeural", "mn-MN-YesuiNeural"],
    "mr": ["mr-IN-AarohiNeural", "mr-IN-ManoharNeural"],
    "ms": ["ms-MY-OsmanNeural", "ms-MY-YasminNeural"],
    "mt": ["mt-MT-GraceNeural", "mt-MT-JosephNeural"],
    "my": ["my-MM-NilarNeural", "my-MM-ThihaNeural"],
    "nb": ["nb-NO-FinnNeural", "nb-NO-PernilleNeural"],
    "ne": ["ne-NP-HemkalaNeural", "ne-NP-SagarNeural"],
    "nl": [
        "nl-BE-ArnaudNeural",
        "nl-BE-DenaNeural",
        "nl-NL-ColetteNeural",
        "nl-NL-FennaNeural",
        "nl-NL-MaartenNeural",
    ],
    "pl": ["pl-PL-MarekNeural", "pl-PL-ZofiaNeural"],
    "ps": ["ps-AF-GulNawazNeural", "ps-AF-LatifaNeural"],
    "pt": [
        "pt-BR-AntonioNeural",
        "pt-BR-FranciscaNeural",
        "pt-PT-DuarteNeural",
        "pt-PT-RaquelNeural",
    ],
    "ro": ["ro-RO-AlinaNeural", "ro-RO-EmilNeural"],
    "ru": ["ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural"],
    "si": ["si-LK-SameeraNeural", "si-LK-ThiliniNeural"],
    "sk": ["sk-SK-LukasNeural", "sk-SK-ViktoriaNeural"],
    "sl": ["sl-SI-PetraNeural", "sl-SI-RokNeural"],
    "so": ["so-SO-MuuseNeural", "so-SO-UbaxNeural"],
    "sq": ["sq-AL-AnilaNeural", "sq-AL-IlirNeural"],
    "sr": ["sr-RS-NicholasNeural", "sr-RS-SophieNeural"],
    "su": ["su-ID-JajangNeural", "su-ID-TutiNeural"],
    "sv": ["sv-SE-MattiasNeural", "sv-SE-SofieNeural"],
    "sw": [
        "sw-KE-RafikiNeural",
        "sw-KE-ZuriNeural",
        "sw-TZ-DaudiNeural",
        "sw-TZ-RehemaNeural",
    ],
    "ta": [
        "ta-IN-PallaviNeural",
        "ta-IN-ValluvarNeural",
        "ta-LK-KumarNeural",
        "ta-LK-SaranyaNeural",
        "ta-MY-KaniNeural",
        "ta-MY-SuryaNeural",
        "ta-SG-AnbuNeural",
        "ta-SG-VenbaNeural",
    ],
    "te": ["te-IN-MohanNeural", "te-IN-ShrutiNeural"],
    "th": ["th-TH-NiwatNeural", "th-TH-PremwadeeNeural"],
    "tr": ["tr-TR-AhmetNeural", "tr-TR-EmelNeural"],
    "uk": ["uk-UA-OstapNeural", "uk-UA-PolinaNeural"],
    "ur": [
        "ur-IN-GulNeural",
        "ur-IN-SalmanNeural",
        "ur-PK-AsadNeural",
        "ur-PK-UzmaNeural",
    ],
    "uz": ["uz-UZ-MadinaNeural", "uz-UZ-SardorNeural"],
    "vi": ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"],
    "zh": [
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-XiaoyiNeural",
        "zh-CN-YunjianNeural",
        "zh-CN-YunxiNeural",
        "zh-CN-YunxiaNeural",
        "zh-CN-YunyangNeural",
        "zh-CN-liaoning-XiaobeiNeural",
        "zh-CN-shaanxi-XiaoniNeural",
        "zh-HK-HiuGaaiNeural",
        "zh-HK-HiuMaanNeural",
        "zh-HK-WanLungNeural",
        "zh-TW-HsiaoChenNeural",
        "zh-TW-HsiaoYuNeural",
        "zh-TW-YunJheNeural",
    ],
    "zu": ["zu-ZA-ThandoNeural", "zu-ZA-ThembaNeural"],
}


def call_openai_to_make_article(words, language):
    prompt = PROMPT.format(language=language, words=words)
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion["choices"][0]["message"]["content"].encode("utf8").decode()


def call_openai_to_make_trans(text, language="Simplified Chinese"):
    prompt = PROMPT_TRANS.format(text=text, language=language)
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion["choices"][0]["message"]["content"].encode("utf8").decode()


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


def make_edge_tts_mp3(text, language_short):
    """
    TODO Refactor this shit
    """
    language = random.choice(EDGE_TTS_DICT.get(language_short, "zh"))

    communicate = edge_tts.Communicate(text, language)
    return asyncio.run(communicate.save("new_article.mp3"))


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
    i = 1
    my_new_words = words[:latest_num]

    def download_word_to_mp3(i, word_string, tts_url=tts_url):
        print(i)
        mp3_content = requests.get(f"{tts_url}{word_string}")
        with open(os.path.join("MP3_NEW", str(i) + ".mp3"), "wb") as f:
            f.write(mp3_content.content)

    for w in my_new_words:
        if w["normalized_string"] == "<*sf>":
            continue
        word_string = w["word_string"]
        words_list.append(word_string)

    for index, w in enumerate(words_list):
        threading.Thread(target=download_word_to_mp3, args=(i, w))

    words_str = ",".join(words_list)
    article = call_openai_to_make_article(words_str, language)
    article_trans = call_openai_to_make_trans(article)
    # call edge-tts to generate mp3
    make_edge_tts_mp3(article, language_short)

    if words_list:
        return "\n".join(words_list), article, article_trans


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
    duolingo_words, article, article_trans = get_duolingo_words_and_save_mp3(
        tts_url, latest_num=latest_num
    )
    print(duolingo_words, article, article_trans)
    if duolingo_words:
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
