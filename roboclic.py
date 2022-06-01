import logging
import random
import json
import re
from unittest import result
import pytz
from datetime import datetime
from bs4 import BeautifulSoup as bs
import os

from telegram import Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler


def open_utf8_r(filename, mode='r'):
    return open(filename, mode, encoding='utf-8')


LIMIT = 10
POLL = 0
JUL = 'jul.txt'
RAYAN = 'rayan.txt'
ARTHUR = 'arthur.txt'
HELPER_TEXTS = "helper_texts.txt"
NORMAL_COMMANDS = {
    'jul', 'hugo', 'reuf', 'noel', 'arthur', 'rayan',
    'birthday', 'bureau', 'year', 'stats', 'cafe'
}
SPECIAL_COMMANDS = {'poll', 'help'}

EXPLANATIONS = {}
for line in open_utf8_r(HELPER_TEXTS):
    (fname, help_text) = line.split(' ', 1)
    EXPLANATIONS[fname] = help_text

KEYS = json.load(open('.keys'))
OPTIONS = json.load(open('options.json'))
BIRTHDAYS = json.load(open('birthday.json'))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

REQUEST_TIMER = {
    "launched":datetime.now()
}
# Helper functions


def quote(file):
    """
    Selects random line from file
    """
    quotes = open_utf8_r(file).read().splitlines()
    return random.choice(quotes)


def countdown(*time):
    """
    Returns time left until given time, as (days, hours, minutes)
    """
    r = datetime(*time) - datetime.now()
    return r.days, r.seconds // 3600, r.seconds % 3600 // 60


def get_time(timedelta):
    """
    Number of seconds in a time interval
    """
    return timedelta.days * 24 * 60 * 60 + timedelta.seconds


def progression_bar(percent):
    """
    ASCII progress bar given a percentage
    """
    total = 25
    tiles = min(total, int(round(percent / 4)))
    return '[' + '#' * tiles + '-' * (total - tiles) + ']'


def error(update, context):
    """
    Error handler
    """
    logger.warning(f'Update "{update}" caused error "{context.error}"')


# Commands
def rayan(update, context):
    update.message.reply_text(quote(RAYAN).capitalize(), quote=False)


def arthur(update, context):
    update.message.reply_text(quote(ARTHUR), quote=False)


def qalf(update, context):
    w = countdown(2021, 4, 26)
    update.message.reply_text('{}j {}h {}m'.format(*w), quote=False)


def kaamelott(update, context):
    w = countdown(2021, 7, 21)
    update.message.reply_text('{}j {}h {}m'.format(*w), quote=False)


def year(update, contact):
    timezone = pytz.timezone('Europe/Zurich')
    today = datetime.now(timezone)
    start = datetime(today.year, 1, 1, 0, 0).astimezone(timezone)
    end = datetime(today.year, 12, 31, 23, 59).astimezone(timezone)

    passed = today - start
    total = end - start

    percent = max(0, get_time(passed) / get_time(total) * 100)
    display = progression_bar(percent)

    update.message.reply_text(
        '{:.2f}%\n{}'.format(percent, display), quote=False)


def oss(update, context):
    w = countdown(2021, 4, 14)
    update.message.reply_text('{}j {}h {}m'.format(*w), quote=False)


def jul(update, context):
    regex = r'\[Couplet \d : (.*?)\]'
    song = open_utf8_r(JUL).read().split('\n\n')
    choices = re.findall(regex, '$'.join(song))

    block = random.choice(song)
    artist = re.search(regex, block).groups()[0]
    lyrics = block.splitlines()[1:]
    punchline = random.choice(lyrics)
    answer_id = choices.index(artist)

    question = f"Qui est l'auteur de la punchline qui suit ?\n\"{punchline}\""

    context.bot.send_poll(chat_id=update.effective_chat.id,
                          question=question,
                          options=choices,
                          type=Poll.QUIZ,
                          correct_option_id=answer_id,
                          is_anonymous=False,
                          allows_multiple_answers=False)


def increment_stats(updated_user, stats_file):
    if not updated_user in OPTIONS:
        return
    stats = json.load(open(stats_file))
    stats.update({updated_user: stats.get(updated_user, 0) + 1})
    json.dump(stats, open(stats_file, 'w'))


def soup(update, context):
    """
    Uses bs4 and a curl script to scrape FLEP's daily menus and output all meals fitting the criterion.
    As of know, only supports price threshold (/soup 10 returns all meal under 10 chf)
    """
    text = ""
    if (datetime.now()-REQUEST_TIMER.get("soup", "1700-01-01T00:00:00Z GMT")).total_seconds()>=3600:
        # Fetches the daily menu
        os.system("sh script.sh {}".format(
            datetime.datetime.today().strftime("%Y-%m-%d")))
    f = open("menu.html", "r")

    soup = bs(f, "html.parser")
    menu = soup.find_all("tr", {"class": "menuPage"})

    # Removes non-Lausanne results
    excluded = set(["La Ruch", "Microci", "Hodler"])

    inputs = context.args.split(" ")
    results = []

    if len(inputs) > 1:
        price_thrsh = float(inputs[0])
    else:
        price_thrsh = 10  # Default budget is 10 CHF

    for item in menu:
        price_list = [
            float(price.text[2:-4])
            # Gne gneu Marahja doesn't know how to fill their menus in
            if len(item.findAll("span", {"class": "price"})) > 1 or "E" in price.text
            else
            float(price.text[:-3])  # All prices are xx CHF, we only want xx
            for price in item.findAll("span", {"class": "price"})
            if "g" not in price.text and float(price.text[2:-4]) > 0]  # removes prix au gramme prices as they're scam and meals with prices=0 due to restaurateur not being honnetes and cheating the price filters
        if len(price_list):
            if min(price_list) <= price_thrsh:  # Assuming the user is a student
                resto = item.findAll("td", {"class": "restaurant"})[
                    0].text.strip()[:7]
                if resto not in excluded:
                    results.append(
                        "{} pour {} CHF : {}".format(
                            resto,
                            min(price_list),
                            item
                            # desc is the description of the meal
                            .findAll("div", {"class": "descr"})[0]
                            .findAll("b")[0]
                            .text.replace("\n", " ")
                        ))
    if not len(results):
        text = "Pas de résultat correspondant aux filtres, c'est régime"
    else :
        text="\n".join(results)
    update.message.reply_text(text, quote=False)


def cafe(update, context):
    text = ''
    if len(context.args) > 0:
        if 'vide' in context.args or 'plus' in context.args:
            context.bot_data['empty'] = True
            text = "Il faut remplir le stock de café !!!"
        elif 'plein' in context.args or 'rempli' in context.args:
            context.bot_data['empty'] = False
            text = "Le stock de café a été rempli !"
    elif context.bot_data.get('empty', False):
        text = "Il n'y a plus de café !!!"
    else:
        text = "Pas de panique, il y a encore du café"
    update.message.reply_text(text, quote=False)


def stats(update, context):
    stats = json.load(open('stats.json'))
    if not len(context.args):
        text = ''
        for user, score in sorted(stats.items(), key=lambda t: t[1], reverse=True):
            text += (f'{OPTIONS[user]}: {score}\n')
        if not text:
            text += 'No stat available'
        update.message.reply_text(text, quote=False)
    else:
        # cumbersome formatting
        query_user = context.args[0].lower().replace(
            'é', 'e').replace('ï', 'i').replace('ë', 'e')
        user = OPTIONS.get(query_user, query_user.title())
        score = stats.get(query_user, 0)
        update.message.reply_text(f'{user}: {score}', quote=False)


def poll(update, context):
    logger.info(f'Poll started by:\n{update}')
    context.user_data.update({'user': update.message.from_user.username})

    keyboard = [
        [
            InlineKeyboardButton(option, callback_data=data)
            for data, option in list(OPTIONS.items())[4*row:4*(row+1)]
        ]
        for row in range(len(OPTIONS))
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Qui l'a dit ?", reply_markup=reply_markup, quote=False)
    try:
        update.message.delete()
    except:
        logger.info(f'Could not delete message {update.message.message_id}')

    return POLL


def keyboard_handler(update, context):
    query = update.callback_query
    query.answer()
    answer = query.data
    context.user_data.update({'answer': answer})
    context.user_data.update({'callback_message': query.message})
    logger.info(f'Selected {OPTIONS[answer]}')
    query.edit_message_text(text=f"Qu'est-ce qui a été dit ?")


def create_poll(update, context):
    chat_id = update.message.chat.id
    previous_message = context.user_data['callback_message']
    try:
        context.bot.delete_message(chat_id, previous_message.message_id)
    except:
        logger.info(f'Could not delete message {previous_message.message_id}')

    answer = context.user_data['answer']
    logger.info(f'{OPTIONS[answer]} said "{update.message.text}"')
    question = f'Qui a dit ça : "{update.message.text}"'

    try:
        update.message.delete()
    except:
        logger.info(f'Could not delete message {update.message.message_id}')

    answer_name = OPTIONS[answer]
    options = list(OPTIONS.values())
    if len(OPTIONS) > LIMIT:
        options.remove(answer_name)
        choices = random.sample(options, LIMIT - 1)
        answer_id = random.randint(0, LIMIT - 1)
        choices.insert(answer_id, answer_name)
    else:
        choices = OPTIONS.values()[:]
        random.shuffle(choices)
        answer_id = choices.index(answer_name)

    context.bot.send_poll(chat_id=update.effective_chat.id,
                          question=question,
                          options=choices,
                          type=Poll.QUIZ,
                          correct_option_id=answer_id,
                          is_anonymous=False,
                          allows_multiple_answers=False)

    if chat_id in KEYS.get('groups', {chat_id}):
        increment_stats(answer, 'stats.json')

    if 'admin' in KEYS:
        try:
            author = context.user_data['user']
            target = OPTIONS[context.user_data['answer']]
            context.bot.send_message(
                KEYS['admin'], f'Poll started by @{author}\nThe answer is "{target}"')
        except:
            pass

    return ConversationHandler.END


def birthday(update, context):
    options = list(OPTIONS.values())
    user_id = random.sample(list(OPTIONS), 1)[0]

    username = OPTIONS[user_id]
    date = BIRTHDAYS[user_id]

    question = f"Qui est né le {date} ?"

    if len(OPTIONS) > LIMIT:
        options.remove(username)
        choices = random.sample(options, LIMIT - 1)
        answer_id = random.randint(0, LIMIT - 1)
        choices.insert(answer_id, username)
    else:
        choices = random.sample(OPTIONS.values(), LIMIT)
        answer_id = choices.index(username)

    context.bot.send_poll(chat_id=update.effective_chat.id,
                          question=question,
                          options=choices,
                          type=Poll.QUIZ,
                          correct_option_id=answer_id,
                          is_anonymous=False,
                          allows_multiple_answers=False)


def telephone_du(reuf='reuf'):
    return f"{KEYS.get('phone', '3630')} le téléphone du {reuf} !"


def noel(update, context):
    update.message.reply_text(telephone_du('Père Noël'), quote=False)


def reuf(update, context):
    update.message.reply_text(telephone_du(), quote=False)


def hugo(update, context):
    update.message.reply_text("???", quote=False)


def bureau(update, context):
    question = "Qui est au bureau ?"
    choices = [
        "Je suis actuellement au bureau",
        "Je suis à proximité du bureau",
        "Je compte m'y rendre bientôt",
        "J'y suis pas",
        "Je suis pas en Suisse"
    ]
    context.bot.send_poll(chat_id=update.effective_chat.id,
                          question=question,
                          options=choices,
                          type=Poll.REGULAR,
                          is_anonymous=False,
                          allows_multiple_answers=False)


def help(update, context):
    if len(context.args) > 0:
        update.message.reply_text(EXPLANATIONS.get(
            context.args[0], 'Not a command'))
    else:
        def display(commands):
            return '\n'.join(('/' + command) for command in commands)
        commands = display(NORMAL_COMMANDS.union(SPECIAL_COMMANDS))
        update.message.reply_text(
            "Available commands:\n{}\nUse help 'command_name' for more info"
            .format(commands)
        )


logger.info(f'Keys: {KEYS}')
updater = Updater(token=KEYS['token'], use_context=True)
dp = updater.dispatcher

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('poll', poll)],
    states={POLL: [MessageHandler(
        filters=Filters.text, callback=create_poll)]},
    fallbacks=[]
)

dp.add_handler(conv_handler)
dp.add_handler(CallbackQueryHandler(keyboard_handler))
dp.add_error_handler(error)
dp.add_handler(CommandHandler('help', help, pass_args=True))

for fname in NORMAL_COMMANDS:
    dp.add_handler(CommandHandler(fname, globals().get(fname)))
updater.start_polling()
updater.idle()
