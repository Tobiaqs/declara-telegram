from collections import namedtuple
from io import BytesIO
from os import environ
from signal import SIGTERM, signal

from declara import Declara
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from userdata import UserData


# handle docker's SIGTERM
def handle_sigterm(*args):
    raise KeyboardInterrupt()


signal(SIGTERM, handle_sigterm)


updater = Updater(token=environ["TELEGRAM_BOT_TOKEN"])
dispatcher = updater.dispatcher


user_data = UserData("data.json")


def help(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Stel eerst je parameters in met de /name, /email, /iban commando's. Voeg dan regels toe aan de declaratie door iets te typen als:\n\nBoodschappen; 12.34\n\nJe kunt foto's en PDF's toevoegen door ze op te sturen.\n\nMet /board stel je in of de PDF alleen naar jouw e-mailadres gestuurd moet worden of ook meteen naar het bestuur.\n\nMet /reset begin je opnieuw aan je declaratie (let op. De send to board instelling wordt hierdoor weer op true gezet).\n\nMet /show zie je wat je tot nu toe hebt ingevuld.\n\n Met /send verstuur je de declaratie.\n\nMet /profile zie je jouw parameters.",
    )


def show(update: Update, context: CallbackContext):
    profile = user_data.get(update.message.from_user.id)
    total = sum(map(lambda msg: msg["amount"], profile["rows"]))
    summary = "\n".join(
        map(
            lambda row: f"- {row['message']} => " + f"€{row['amount']:.2f}".replace(".", ","),
            profile["rows"],
        )
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{summary}\n\nTotaalbedrag is €{total:.2f}".replace(".", ",")
        + f"\n\nEr zijn {len(profile['attachments'])} bijlage(n).",
    )


def profile(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=user_data.get(update.message.from_user.id, human_readable=True)
    )


def board(update: Update, context: CallbackContext):
    s = update.message.text.split(" ", maxsplit=1)
    if len(s) == 1:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Dit commando verwacht een waarde (true of false)."
        )
        return

    if s[1].lower() == "true":
        user_data.update_board(update.message.from_user.id, True)
        context.bot.send_message(chat_id=update.effective_chat.id, text="✅ E-mail sturen naar bestuur staat nu aan.")
    elif s[1].lower() == "false":
        user_data.update_board(update.message.from_user.id, False)
        context.bot.send_message(chat_id=update.effective_chat.id, text="✅ E-mail sturen naar bestuur staat nu uit.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Ongeldige waarde. Gebruik true of false.")
        return


def iban(update: Update, context: CallbackContext):
    s = update.message.text.split(" ", maxsplit=1)
    if len(s) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Dit commando verwacht een waarde (IBAN).")
        return

    if user_data.update_iban(update.message.from_user.id, s[1]):
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ IBAN veranderd naar {s[1]}.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Ongeldige IBAN.")


def name(update: Update, context: CallbackContext):
    s = update.message.text.split(" ", maxsplit=1)
    if len(s) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Dit commando verwacht een waarde (naam).")
        return

    user_data.update_name(update.message.from_user.id, s[1])
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Naam veranderd naar {s[1]}.")


def reset(update: Update, context: CallbackContext):
    user_data.reset_user(update.message.from_user.id)
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Gereset.")
    profile(update, context)


def email(update: Update, context: CallbackContext):
    s = update.message.text.split(" ", maxsplit=1)
    if len(s) == 1:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Dit commando verwacht een waarde (e-mailadres)."
        )
        return

    user_data.update_email(update.message.from_user.id, s[1])
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ E-mailadres veranderd naar {s[1]}.")


def send(update: Update, context: CallbackContext):
    if not user_data._is_valid(update.message.from_user.id):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Declaratie is niet geldig.")
        return
    profile = user_data.get(update.message.from_user.id)
    declara = Declara()
    for att in profile["attachments"]:
        buf = BytesIO()
        context.bot.get_file(att["file_id"]).download(out=buf)
        buf.seek(0)
        declara.attachments.append(
            Declara.Attachment(buf, "is_image" in att and att["is_image"], "is_pdf" in att and att["is_pdf"])
        )

    declara.rows = list(map(lambda row: Declara.Row(row["message"], row["amount"]), profile["rows"]))

    declara.name = profile["name"]
    declara.iban = profile["iban"]

    declara.send_email(
        extra_addresses=[profile["email"]] if profile["email"] else [],
        only_extra_addresses=not profile["send_to_board"],
    )

    user_data.reset_user(update.message.from_user.id)

    context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ E-mail verzonden.")


dispatcher.add_handler(CommandHandler("help", help))
dispatcher.add_handler(CommandHandler("show", show))
dispatcher.add_handler(CommandHandler("profile", profile))
dispatcher.add_handler(CommandHandler("board", board))
dispatcher.add_handler(CommandHandler("name", name))
dispatcher.add_handler(CommandHandler("email", email))
dispatcher.add_handler(CommandHandler("reset", reset))
dispatcher.add_handler(CommandHandler("iban", iban))
dispatcher.add_handler(CommandHandler("send", send))


def text(update: Update, context: CallbackContext):
    s = update.message.text.split(";")
    if len(s) != 2:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Voer een regel in als volgt: \n\n<Omschrijving>; <Bedrag>\n\nVoorbeeld:\n\nBoodschappen weekend; 14.22",
        )
        return

    user_data.add_row(update.message.from_user.id, update.message.text)
    profile = user_data.get(update.message.from_user.id)
    total = sum(map(lambda row: row["amount"], profile["rows"]))
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"✅ Regel toegevoegd. Totaalbedrag is nu €{total:.2f}".replace(".", ",")
    )


dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), text))


def image(update: Update, context: CallbackContext):
    photo = update.message.photo[-1]
    profile = user_data.get(update.message.from_user.id)
    profile["attachments"].append(dict(file_id=photo.file_id, is_image=True))
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Foto toegevoegd. Je hebt nu {len(profile['attachments'])} bijlage(n) klaarstaan.",
    )


def document(update: Update, context: CallbackContext):
    document = update.message.document
    if document.mime_type != "application/pdf":
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="❌ Je mag alleen gecomprimeerde afbeeldingen of PDF's opsturen."
        )
        return

    if document.file_size > 10 * 1024 * 1024:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="❌ PDF's groter dan 10 MB zijn niet ondersteund."
        )
        return

    profile = user_data.get(update.message.from_user.id)
    profile["attachments"].append(dict(file_id=document.file_id, is_pdf=True))
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ PDF toegevoegd. Je hebt nu {len(profile['attachments'])} bijlage(n) klaarstaan.",
    )


dispatcher.add_handler(MessageHandler(Filters.photo, image))
dispatcher.add_handler(MessageHandler(Filters.document, document))

updater.start_polling()
