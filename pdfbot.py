# -*- coding: utf-8 -*-

"""
Simple Bot to reply to Telegram messages.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import os
import logging
import uuid
import shutil

import img2pdf
from PyPDF2 import PdfFileMerger
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

SENDING = range(1)


def conv_image(file_name, args):
    """Convert an image to pdf."""
    a4inpt = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
    if args == "A4":
        layout_fun = img2pdf.get_layout_fun(a4inpt)
    else:
        layout_fun = img2pdf.get_layout_fun()

    with open(file_name + ".pdf", "wb") as f:
        f.write(img2pdf.convert(file_name, layout_fun=layout_fun))

    return True


def cleanup(file_name):
    """Cleanup files"""
    os.remove(file_name)
    os.remove(file_name + ".pdf")
    print("File removed")


def get_image(update, context, mode="Single"):
    file_id = update.message.document.file_id
    file_name = update.message.document.file_name
    file_desc = update.message.caption
    new_file = context.bot.get_file(file_id)
    if mode == "Folder":
        temp_name = os.path.join("/mnt/ramdisk", context.chat_data["idd"], file_id + file_name)
    else:
        temp_name = os.path.join("/mnt/ramdisk", file_id + file_name)
    new_file.download(custom_path=temp_name)
    print("File saved")
    return file_name, file_desc, temp_name


def join_pdfs(pdfs, idd):
    merger = PdfFileMerger()
    for pdf in pdfs:
        merger.append(pdf)
    merger.write(os.path.join("/mnt/ramdisk", idd, "result.pdf"))
    merger.close()


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text(
        'Hi! You can send me images and I will convert them to pdf and send them back to you. '
        'Please send the images as files (photos get compressed). '
        'If you want the output to be A4 format use the caption "A4".')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def convert_image(update, context):
    """Convert the sent image to pdf and send it back."""
    file_name, file_desc, temp_name = get_image(update, context)
    conv_image(temp_name, file_desc)

    context.bot.send_document(
        chat_id=update.effective_chat.id, document=open(temp_name + ".pdf", 'rb'), filename=file_name + ".pdf")
    print("File send")

    cleanup(temp_name)


def info_photo(update, context):
    """Send info that one should send images as files."""
    update.message.reply_text("Please send images as files.")
    return SENDING


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def join(update, context):
    context.chat_data["idd"] = str(uuid.uuid4())
    folder_name = os.path.join("/mnt/ramdisk", context.chat_data["idd"])
    os.mkdir(folder_name)
    context.chat_data["images"] = []
    context.chat_data["folder"] = folder_name
    context.chat_data["name"] = "result"
    update.message.reply_text("Send images and /done when finished")
    return SENDING


def add_image(update, context):
    # Do something
    file_name, file_desc, temp_name = get_image(update, context, mode="Folder")
    conv_image(temp_name, file_desc)
    os.remove(temp_name)
    context.chat_data["images"].append(temp_name + ".pdf")
    return SENDING


def add_pdf(update, context):
    # Do something
    file_name, file_desc, temp_name = get_image(update, context, mode="Folder")
    context.chat_data["images"].append(temp_name)
    return SENDING


def set_title(update, context):
    if len(context.args) != 0:
        context.chat_data["name"] = context.args[0]
    else:
        update.message.reply_text("Please enter a name for the document.")
    return SENDING


def done(update, context):
    chat_data = context.chat_data
    if chat_data is None:
        chat_data = next(iter(context.job.context.dispatcher.chat_data.values()))
        print("timeout")
    print(chat_data)

    if len(chat_data["images"]) != 0:
        join_pdfs(chat_data["images"], chat_data["idd"])
        context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(os.path.join("/mnt/ramdisk", chat_data["idd"], "result.pdf"), 'rb'),
            filename=chat_data["name"] + ".pdf")
        print("File send")

    try:
        shutil.rmtree(chat_data["folder"])
    except OSError as e:
        print("Error: %s : %s" % (chat_data["folder"], e.strerror))

    update.message.reply_text("Finished")
    chat_data.clear()
    return ConversationHandler.END


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("join", join)],
        states={
            SENDING: [MessageHandler(Filters.document.category("image"), add_image),
                      MessageHandler(Filters.document.mime_type("application/pdf"), add_pdf),
                      CommandHandler("title", set_title),
                      ],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, done)],
        },
        fallbacks=[CommandHandler("done", done)],
        conversation_timeout=60,
    )

    dp.add_handler(conv_handler)

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))
    dp.add_handler(MessageHandler(Filters.document.category("image"), convert_image))
    dp.add_handler(MessageHandler(Filters.photo, info_photo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()