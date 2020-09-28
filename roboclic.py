import logging
import random
import json
from datetime import datetime

from telegram import Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler


LIMIT = 10
POLL = 0

KEYS = dict(line.strip().split('=') for line in open('.keys'))
OPTIONS = json.loads(open('options.json').read())

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def countdown(*time):
    r = datetime(*time) - datetime.now()
    return r.days, r.seconds // 3600, r.seconds % 3600 // 60


def qalf(update, context):
    w = countdown(2021, 4, 26)
    update.message.reply_text('{}j {}h {}m'.format(*w), quote=False)


def kaamelott(update, context):
    w = countdown(2020, 11, 25)
    update.message.reply_text('{}j {}h {}m'.format(*w), quote=False)


def oss(update, context):
        w = countdown(2021, 2, 3)
        update.message.reply_text('{}j {}h {}m'.format(*w), quote=False)


def poll(update, context):
    logger.info(f'Bot started by {update.message.from_user}')

    keyboard = [
                    [
                        InlineKeyboardButton(option, callback_data=data)
                        for data, option in list(OPTIONS.items())[4*row:4*(row+1)]
                    ]
                    for row in range(len(OPTIONS))
                ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Qui l'a dit ?", reply_markup=reply_markup, quote=False)

    return POLL


def keyboard_handler(update, context):
    query = update.callback_query
    query.answer()
    answer = query.data
    context.user_data['answer'] = answer
    logger.info(f'Selected {OPTIONS[answer]}')
    query.edit_message_text(text=f"Qu'est-ce qui a été dit ?")


def create_poll(update, context):
    answer = context.user_data['answer']
    logger.info(f'{OPTIONS[answer]} said "{update.message.text}"')
    question = f'Qui a dit ça : "{update.message.text}"'

    options = list(OPTIONS.values())
    if len(OPTIONS) > LIMIT:
        options.remove(OPTIONS[answer])
        choices = random.sample(options, LIMIT - 1)
        answer_id = random.randint(0, LIMIT - 1)
        choices.insert(answer_id, OPTIONS[answer])
    else:
        choices = random.sample(OPTIONS.values(), LIMIT)
        answer_id = choices.index(OPTIONS[answer])

    context.bot.send_poll(chat_id=update.effective_chat.id,
                          question=question,
                          options=choices,
                          type=Poll.QUIZ,
                          correct_option_id=answer_id,
                          is_anonymous=False,
                          allows_multiple_answers=False)

    return ConversationHandler.END


def error(update, context):
    logger.warning(f'Update "{update}" caused error "{context.error}"')


def help(update, context):
    update.message.reply_text("Type /poll to use me.")


if __name__ == '__main__':
    logger.info(f'Keys: {KEYS}')
    updater = Updater(token=KEYS['token'], use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('poll', poll)],
        states={POLL: [MessageHandler(filters=Filters.text, callback=create_poll)]},
        fallbacks=[]
    )

    dp.add_handler(CommandHandler('qalf', qalf))
    dp.add_handler(CommandHandler('kaamelott', kaamelott))
    dp.add_handler(CommandHandler('oss', oss))
    dp.add_handler(conv_handler)
    dp.add_handler(CallbackQueryHandler(keyboard_handler))
    dp.add_handler(CommandHandler('help', help))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()