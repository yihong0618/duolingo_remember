# duolingo_remember
Automatically send new words from duolingo to telegram

## steps

- Login duolingo.com to get jwt, open webbrowser run `document.cookie.match(new RegExp('(^| )jwt_token=([^;]+)'))[0].slice(11)`
- Get your telegram token and chatid (please google how to)
- Change the secrets to your own
- Change your own config file in [yml](./.github/workflows/run_duolingo.yml)
- If you fork this repo run the actions, please trigger the action first (by mannual).

## Run local

```
pip install -r requirements.txt
python duolingo.py ${duolingo_name} ${duolingo_jwt}
```

![image](https://user-images.githubusercontent.com/15976103/104862648-8eae6300-596e-11eb-8881-d29845649af2.png)

## TODO
- [ ] Support auto buy streak freeze
- [x] Support sentence mp3
- [x] Make action a little simple
- [ ] Support Multi lauguages
- [ ] Support send to other bots like dingding


# Contribution

- Any issues or PRs are welcome.
- Please run `black .` before submitting the code.

## Appreciation

Thank you, that's enough.
