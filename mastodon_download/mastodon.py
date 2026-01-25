from datetime import datetime, timezone
from hashlib import blake2b
from json import dump, load
from os import mkdir
from os.path import exists, join
from time import sleep, time
from typing import Optional, TypedDict
from urllib.parse import urlencode

import requests

CLIENT_NAME = "Mastodon Toots Downloader"

WEBFINGER_PATH = "/.well-known/webfinger"
NODEINFO_PATH = "/.well-known/nodeinfo"
APP_CREATE_PATH = "/api/v1/apps"
AUTHORIZE_PATH = "/oauth/authorize"
TOKEN_PATH = "/oauth/token"
VERIFIY_CREDENTIALS_PATH = "/api/v1/accounts/verify_credentials"
ACCOUNTS_STATUSES_PATH = "/api/v1/accounts/{ACCOUNT_ID}/statuses"

REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
SCOPES = "read:statuses profile"
WEBSITE = "https://github.com/adridevelopsthings/mastodon-download-toots"


class RateLimitExceededException(Exception):
    def __init__(self, reset: datetime) -> None:
        self.reset = reset

    def wait(self) -> None:
        """Wait until rate limit shouldn't be exceeded anymore."""
        waiting_time = (self.reset - datetime.now(timezone.utc)).total_seconds() + 0.1
        if waiting_time <= 0:
            return
        print(f"Waiting until rate limit is over for {round(waiting_time)} seconds...")
        sleep(waiting_time)


class ClientCredentials(TypedDict):
    client_id: str
    client_secret: str


class Token(TypedDict):
    access_token: str
    token_type: str


class Me(TypedDict):
    id: str
    username: str


class Mastodon:
    @staticmethod
    def __get_nodeinfo(instance_url: str) -> dict:
        response = requests.get(instance_url + NODEINFO_PATH)
        response.raise_for_status()
        j = response.json()
        assert len(j["links"]) > 0
        link = j["links"][0]
        href = link["href"]
        response = requests.get(href)
        response.raise_for_status()
        j = response.json()
        return j

    @classmethod
    def from_instance_domain(cls, domain: str, cache_dir: str) -> "Mastodon":
        response = requests.get(f"https://{domain}{WEBFINGER_PATH}")
        if not response.url.endswith(WEBFINGER_PATH):
            raise Exception(
                f"Invalid mastodon url: Webfinger request redirects to an url that is not a webfinger url: '{response.url}'"
            )
        instance_url: str = response.url[: -len(WEBFINGER_PATH)]
        requests.head(instance_url).raise_for_status()
        if Mastodon.__get_nodeinfo(instance_url)["software"]["name"] != "mastodon":
            raise Exception(f"Instance '{instance_url}' is not a mastodon instance")
        return cls(instance_url, cache_dir)

    def __init__(self, instance_url: str, cache_dir: str) -> None:
        self.__instance_url = instance_url
        self.__cached_client_credentials: Optional[ClientCredentials] = None
        self.__cached_user_credentials: Optional[Token] = None
        self.__cache_dir = cache_dir
        if not exists(self.__cache_dir):
            mkdir(self.__cache_dir)
        self.__instance_hash = blake2b(self.__instance_url.encode("utf-8")).hexdigest()

    def create_token(self, code: str) -> Token:
        response = requests.post(
            self.__instance_url + TOKEN_PATH,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.__client_credentials["client_id"],
                "client_secret": self.__client_credentials["client_secret"],
                "redirect_uri": REDIRECT_URI,
            },
        )
        response.raise_for_status()
        j = response.json()
        self.__cached_user_credentials = j
        with open(self.__user_credentials_path, "w") as file:
            dump(j, file)
        return j

    def get_user_statuses(
        self, account_id: str, max_id: Optional[str] = None, limit: Optional[int] = None
    ) -> list[dict]:
        params: dict[str, str] = {}
        if max_id:
            params["max_id"] = max_id
        if limit:
            params["limit"] = str(limit)

        response = requests.get(
            self.__instance_url
            + ACCOUNTS_STATUSES_PATH.replace("{ACCOUNT_ID}", account_id),
            params=params,
            headers=self.__auth_headers,
        )
        if response.status_code == 429:
            raise RateLimitExceededException(
                datetime.fromisoformat(response.headers["X-RateLimit-Reset"])
            )
        response.raise_for_status()
        j = response.json()
        return j

    def download_attachment(self, url: str) -> bytes:
        response = requests.get(url, headers=self.__auth_headers)
        response.raise_for_status()
        return response.content

    def get_me(self) -> Me:
        response = requests.get(
            self.__instance_url + VERIFIY_CREDENTIALS_PATH, headers=self.__auth_headers
        )
        response.raise_for_status()
        return response.json()

    @property
    def authorize_url(self) -> str:
        return (
            self.__instance_url
            + AUTHORIZE_PATH
            + "?"
            + urlencode(
                {
                    "response_type": "code",
                    "client_id": self.__client_credentials["client_id"],
                    "redirect_uri": REDIRECT_URI,
                    "scope": SCOPES,
                }
            )
        )

    @property
    def authorized(self) -> bool:
        return self.__token is not None

    @property
    def __auth_headers(self) -> dict[str, str]:
        assert self.__token, "Not Authorized"
        return {
            "Authorization": self.__token["token_type"]
            + " "
            + self.__token["access_token"]
        }

    @property
    def __token(self) -> Optional[Token]:
        if self.__cached_user_credentials:
            return self.__cached_user_credentials

        cache_file = self.__user_credentials_path
        if not exists(cache_file):
            return None

        with open(cache_file) as file:
            return load(file)

    @property
    def __client_credentials(self) -> ClientCredentials:
        if self.__cached_client_credentials:
            return self.__cached_client_credentials

        cache_file = self.__client_credentials_path
        if exists(cache_file):
            with open(cache_file) as file:
                credentials = load(file)
        else:
            response = requests.post(
                self.__instance_url + APP_CREATE_PATH,
                json={
                    "client_name": CLIENT_NAME,
                    "redirect_uris": REDIRECT_URI,
                    "scopes": SCOPES,
                    "website": WEBSITE,
                },
            )
            response.raise_for_status()
            credentials = response.json()
            with open(cache_file, "w") as file:
                dump(credentials, file)
        self.__cached_client_credentials = credentials
        return credentials

    @property
    def __client_credentials_path(self) -> str:
        return join(self.__cache_dir, f"{self.__instance_hash}_client.json")

    @property
    def __user_credentials_path(self) -> str:
        return join(self.__cache_dir, f"{self.__instance_hash}_user.json")
