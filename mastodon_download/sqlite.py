import sqlite3
from json import dumps, loads
from typing import Optional

from mastodon_download.mastodon import Account


class SqliteDatabase:
    def __init__(self, path: str) -> None:
        self.__con = sqlite3.connect(path)
        self.__cur = self.__con.cursor()
        self.__run_table_create()

    def close(self) -> None:
        self.__cur.close()
        self.__con.close()

    def __run_table_create(self) -> None:
        self.__cur.execute(
            "CREATE TABLE IF NOT EXISTS status(id TEXT NOT NULL PRIMARY KEY, status TEXT)"
        )
        self.__cur.execute(
            "CREATE TABLE IF NOT EXISTS account(id TEXT NOT NULL PRIMARY KEY, account TEXT)"
        )
        self.__cur.execute(
            "CREATE TABLE IF NOT EXISTS newest_status(id TEXT NOT NULL PRIMARY KEY)"
        )
        self.__con.commit()

    def set_account(self, account: Account) -> None:
        self.__cur.execute("SELECT id, account FROM account")
        accounts = self.__cur.fetchall()
        if len(accounts) > 1:
            raise Exception(
                "Database contains multiple accounts, only one account per database is allowed"
            )

        if len(accounts) == 1:
            acc = accounts[0]
            if acc[0] != account["id"]:
                a = loads(acc[1])
                raise Exception(
                    f"Database contains account {a['username']} ({acc[0]}) but currently running for account {account['username']} ({account['id']})"
                )

        self.__cur.execute(
            "INSERT INTO account(id, account) VALUES(?, ?) ON CONFLICT DO UPDATE SET account=EXCLUDED.account",
            (account["id"], dumps(account)),
        )
        self.__con.commit()

    def get_newest_status(self) -> Optional[str]:
        self.__cur.execute("SELECT id FROM newest_status")
        statuses = self.__cur.fetchall()
        if len(statuses) > 1:
            raise Exception("Database has multiple newest statuses")
        if len(statuses) == 0:
            return None
        return statuses[0][0]

    def set_newest_status(self, status_id: str) -> None:
        self.__cur.execute("DELETE FROM newest_status")
        self.__cur.execute("INSERT INTO newest_status(id) VALUES(?)", (status_id,))
        self.__con.commit()

    def has_status(self, status_id: str) -> bool:
        self.__cur.execute("SELECT id FROM status WHERE id=?", (status_id,))
        return self.__cur.fetchone() is not None

    def add_status(self, status: dict) -> None:
        self.__cur.execute(
            "INSERT INTO status(id, status) VALUES(?,?) ON CONFLICT DO UPDATE SET status=EXCLUDED.status",
            (status["id"], dumps(status)),
        )
        self.__con.commit()
