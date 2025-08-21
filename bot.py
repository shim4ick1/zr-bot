import os
import random
import time
import threading
import re
import telebot
import pymorphy2

# =========================
# 🔑 СЕКРЕТЫ И НАСТРОЙКИ
# =========================
TOKEN = os.getenv("TOKEN", "8435949737:AAFOoiJe1pbduW0fQK3S92q04XbKFqCXWD8")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@zalesskayarepublic")

if not TOKEN or not CHANNEL_ID or "YOUR_TELEGRAM_BOT_TOKEN" in TOKEN:
    raise RuntimeError("Укажи переменные окружения TOKEN и CHANNEL_ID!")

bot = telebot.TeleBot(TOKEN, parse_mode=None)
morph = pymorphy2.MorphAnalyzer()

# =========================
# 📍 ЛОКАЦИИ
# =========================
zr_regions = {
    "Орловская": [
        "Орёл","Ливны","Мценск","Болхов","Кромы","Хотынец","Новосиль","Покровское","Дмитровск",
        "Колпна","Тросна","Нарышкино","Залегощь","Верховье","Малоархангельск","Глазуновка","Шаблыкино",
        "Сосково","Урицкое","Долгое","Плещеево","Становой Колодезь","Хомутово","Красная Заря",
        "Нарышкинский округ","Кромской район","Покровский район","Знаменское","Сосковский район",
        "Мценский район","Ливенский район"
    ],
    "Курская": [
        "Курск","Льгов","Рыльск","Обоянь","Железногорск","Фатеж","Касторное","Глушково","Коренево",
        "Курчатов","Мантурово","Медвенка","Суджа","Золотухино","Щигры","Поныри","Хомутовка","Солнцево",
        "Пристень","Большое Солдатское","Тим","Горшечное","Советский","Беловский","Конышевка",
        "Черемисиново","Ольговка","Марьино","Кочка","Свобода","Беседино"
    ],
    "Брянская": [
        "Брянск","Севск","Клинцы","Стародуб","Унеча","Дятьково","Жуковка","Новозыбков","Трубчевск",
        "Суземка","Почеп","Навля","Комаричи","Карачев","Сельцо","Фокино","Клетня","Мглин",
        "Погар","Злынка","Красная Гора","Сураж","Гордеевка","Выгоничи","Дубровка",
        "Рогнедино","Брасово","Жирятино","Локоть","Белая Берёзка","Старое Село","Климово"
    ]
}

enemy_regions = {
    "Белгородская": ["Белгород","Шебекино","Валуйки","Губкин","Старый Оскол","Грайворон","Алексеевка","Ракитное","Прохоровка","Новый Оскол"],
    "Смоленская":   ["Смоленск","Ярцево","Рославль","Сафоново","Десногорск","Дорогобуж","Вязьма","Рудня"],
    "Калужская":    ["Калуга","Обнинск","Малоярославец","Балабаново","Таруса","Козельск","Людиново","Мосальск"],
    "Тульская":     ["Тула","Новомосковск","Ефремов","Узловая","Суворов","Щёкино","Донской","Богородицк"],
    "Липецкая":     ["Липецк","Елец","Грязи","Данков","Задонск","Чаплыгин","Усмань"],
    "Воронежская":  ["Воронеж","Семилуки","Острогожск","Лиски","Россошь","Калач","Бутурлиновка","Павловск"],
    "Тамбовская":   ["Тамбов","Мичуринск","Котовск","Моршанск","Рассказово","Уварово","Жердевка"],
    "Московская":   ["Москва","Подмосковье","Химки","Мытищи","Балашиха","Одинцово","Щёлково","Коломна","Орехово-Зуево","Клин","Сергиев Посад","Домодедово","Жуковский"],
    "Рязанская":    ["Рязань","Касимов","Скопин","Сасово","Ряжск","Кораблино"],
    "Тверская":     ["Тверь","Ржев","Вышний Волочёк","Торжок","Кимры","Бежецк"],
    "Ярославская":  ["Ярославль","Рыбинск","Переславль-Залесский","Углич","Тутаев"],
    "Прочие":       ["граница РФ (Белгород)","Смоленское направление","Рязанское направление","Калужское направление","Подмосковное направление"]
}

our_locations = [c for cities in zr_regions.values() for c in cities]
enemy_locations = [c for cities in enemy_regions.values() for c in cities]

# =========================
# 📜 СЦЕНАРИИ
# =========================
patterns = [
    "❗️❗️ {loc1} — удары с территории {enemy}",
    "⚡ Прилёты по {loc1}, источник огня — {enemy}",
    "❗️❗️ Пролёт ракет над {loc1}, курс на {loc2}",
    "⚡ Мощный взрыв в районе {loc1}, направление удара — {enemy}",
    "❗️❗️ Артобстрел по {loc1} с позиций {enemy}",
    "⚡ Ракета стартовала из {enemy}, цель — {loc2}",
    "❗️❗️ БПЛА замечен у {loc1}, курс с {enemy}",
    "⚡ Массовый залп из {enemy} по {loc1}",
    "❗️❗️ Прорыв ПВО, удар по {loc1}, направление {enemy}",
    "⚡ Серия взрывов у {loc1}, прилёты со стороны {enemy}"
]

# =========================
# ⚙️ РЕЖИМЫ СКОРОСТИ
# =========================
modes = {
    "затишье": (900, 1500),
    "разведка": (300, 600),
    "обстрел": (90, 180),
    "массированный удар": (20, 60),
    "хаос": (3, 20),
    "спад": (600, 1200)
}
current_mode = "обстрел"

# =========================
# 🛠 УТИЛИТЫ
# =========================
def decline(word: str, case: str) -> str:
    parsed = morph.parse(word.split()[0])[0]  # берём только первое слово (город)
    form = parsed.inflect({case})
    return form.word if form else word

def format_text(text: str) -> str:
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    if not text.endswith("Радар Залесской Республики"):
        text += "\n\n📡 Радар Залесской Республики"
    return text

def pick_two_different(seq):
    a = random.choice(seq)
    b = random.choice(seq)
    while b == a:
        b = random.choice(seq)
    return a, b

def generate_message() -> str:
    pattern = random.choice(patterns)
    loc1, loc2 = pick_two_different(our_locations)
    enemy = random.choice(enemy_locations)

    # аккуратное склонение
    if "по {loc1}" in pattern:
        loc1 = decline(loc1, "dat")  # дательный
    if "с {enemy}" in pattern or "из {enemy}" in pattern:
        enemy = decline(enemy, "gen")  # родительный
    if "в {loc1}" in pattern or "у {loc1}" in pattern:
        loc1 = decline(loc1, "loc")  # предложный

    text = pattern.format(loc1=loc1, loc2=loc2, enemy=enemy)
    return format_text(text)

def switch_mode():
    global current_mode
    if random.random() < 0.2:
        current_mode = random.choice(list(modes.keys()))
        print(f"[MODE] → {current_mode}")

def safe_send(text: str):
    delay = 1
    while True:
        try:
            bot.send_message(CHANNEL_ID, text)
            print("[SENT]", text)
            return
        except Exception as e:
            s = str(e)
            print("[ERROR]", s)
            m = re.search(r"Too Many Requests: retry after (\d+)", s)
            if m:
                wait = int(m.group(1)) + random.randint(1, 3)
            else:
                wait = delay
                delay = min(delay * 2, 60)
            time.sleep(wait)

def sender():
    global current_mode
    while True:
        msg = generate_message()
        safe_send(msg)
        low, high = modes[current_mode]
        time.sleep(random.randint(low, high))
        switch_mode()

# =========================
# 🚀 ЗАПУСК
# =========================
if __name__ == "__main__":
    threading.Thread(target=sender, daemon=True).start()
    print("✅ Бот запущен")
    bot.polling(none_stop=True, interval=1, timeout=20)
