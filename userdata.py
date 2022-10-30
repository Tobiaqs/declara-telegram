import json
import os
import re

import schwifty

email_regex = r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"


class UserData:
    user_data = None

    def __init__(self, file_path):
        self.file_path = file_path
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.file_path):
            with open(self.file_path) as json_file:
                self.user_data = json.loads(json_file.read())
                for key, value in list(self.user_data.items()):
                    self.user_data[int(key)] = value
                    del self.user_data[key]
        else:
            self.user_data = {}
            self._store_data()

    def _store_data(self):
        with open(self.file_path, "w") as json_file:
            json.dump(self.user_data, json_file, indent=4)

    def _is_valid(self, user_id):
        data = self.user_data[user_id]
        return (
            data["email"]
            and data["name"]
            and data["iban"]
            and data["rows"]
            and data["attachments"]
            and data["approved"]
        )

    def reset_user(self, user_id):
        self._init_user_if_not_exist(user_id)
        self.user_data[user_id]["rows"] = []
        self.user_data[user_id]["attachments"] = []
        self.user_data[user_id]["send_to_board"] = True
        self._store_data()

    def _init_user_if_not_exist(self, user_id):
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "name": "",
                "email": "",
                "iban": "",
                "rows": [],
                "attachments": [],
                "send_to_board": True,
                "approved": False,
            }
            self._store_data()

    def add_row(self, user_id, text):
        splits = text.split(";")
        message = splits[0]
        amount = splits[-1]

        try:
            amount = round(float(amount.replace(",", ".")), 2)
        except ValueError:
            return False

        self._init_user_if_not_exist(user_id)
        line = dict(message=message, amount=amount)
        self.user_data[user_id]["rows"].append(line)
        self._store_data()
        return True

    def add_attachment(self, user_id, url):
        self._init_user_if_not_exist(user_id)
        self.user_data[user_id]["attachments"].append(url)
        self._store_data()

    def approve(self, user_id):
        self._init_user_if_not_exist(user_id)
        self.user_data[user_id]["approved"] = True
        self._store_data()

    def update_iban(self, user_id, iban):
        try:
            ib = schwifty.IBAN(iban)
            ib.validate()
        except:
            return False
        self._init_user_if_not_exist(user_id)
        self.user_data[user_id]["iban"] = iban
        self._store_data()
        return True

    def update_name(self, user_id, name):
        self._init_user_if_not_exist(user_id)
        self.user_data[user_id]["name"] = name
        self._store_data()

    def update_board(self, user_id, send_to_board):
        self._init_user_if_not_exist(user_id)
        self.user_data[user_id]["send_to_board"] = send_to_board
        self._store_data()

    def update_email(self, user_id, email):
        if not re.fullmatch(email_regex, email):
            return False
        self._init_user_if_not_exist(user_id)
        self.user_data[user_id]["email"] = email
        self._store_data()
        return True

    def get(self, user_id, human_readable=False):
        self._init_user_if_not_exist(user_id)
        data = self.user_data[user_id]
        if human_readable:
            return (
                f'name: {data["name"]}\n'
                f'email: {data["email"]}\n'
                f'IBAN: {data["iban"]}\n'
                f'send to board: {str(data["send_to_board"]).lower()}\n'
                f'approved: {str(data["approved"]).lower()}\n'
            )
        else:
            return self.user_data[user_id]
