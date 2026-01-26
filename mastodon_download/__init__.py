from datetime import datetime
from json import dump, dumps
from os import mkdir, remove
from os.path import exists, join
from typing import Any, Optional
from zipfile import ZipFile

from requests import HTTPError

from mastodon_download.args import parser
from mastodon_download.mastodon import Mastodon, RateLimitExceededException


def main() -> None:
    args = parser.parse_args()
    mastodon = Mastodon.from_instance_domain(
        args.domain, args.cache_dir, account_profile=args.account_profile
    )
    if args.purge_cache:
        mastodon.purge_cache()
    if not mastodon.authorized or args.force_login:
        print(
            "Open the following url in the browser, authorize and than paste the shown authorize code here."
        )
        print(f"URL:   {mastodon.authorize_url}")
        print("")
        code = input("Authorize code: ")
        mastodon.create_token(code)

    if args.user:
        accounts = mastodon.search_accounts(args.user, limit=1, resolve=True)
        account = accounts[0]
        if account["acct"] != args.user:
            raise Exception(
                f"User was not found: Searched for {args.user} but got {account['acct']}"
            )
        acct = account["acct"].split("@")
        instance_domain = args.domain if len(acct) == 1 else acct[1]
    else:
        account = mastodon.get_me()
        instance_domain = args.domain

    output = args.output
    if not output:
        date = datetime.now().strftime("%Y-%m-%d")
        output = f"{account['username']}_{instance_domain}_{date}.{'zip' if args.zip else 'json'}"

    if exists(output):
        if input("Output file already exists, overwriting? [y/n] ").lower() != "y":
            return
        remove(output)

    media_output = args.media_output
    if args.media and not media_output:
        media_output = f"{account['username']}_{instance_domain}_media"
    if args.zip:
        media_output = "media"

    if not args.zip and media_output and not exists(media_output):
        mkdir(media_output)
    
    zipfile = None
    if args.zip:
        zipfile = ZipFile(output, "x")

    all_statuses: list[dict] = []
    max_id: Optional[str] = None
    page = 1

    print("Fetching statuses...")
    while True:
        print(
            f"\033[KPage {page} (already fetched: {len(all_statuses)})",
            end="\r",
            flush=True,
        )
        try:
            statuses = mastodon.get_user_statuses(
                account["id"], limit=40, max_id=max_id
            )
        except RateLimitExceededException as e:
            e.wait()
            statuses = mastodon.get_user_statuses(
                account["id"], limit=40, max_id=max_id
            )

        if len(statuses) == 0:
            break
        all_statuses.extend(statuses)

        if media_output:
            for status in statuses:
                for attachment in status["media_attachments"]:
                    url = attachment["url"]
                    remote_url = attachment["remote_url"]
                    file_suffix = (
                        (remote_url if remote_url else url)
                        .split("/")[-1]
                        .split(".")[-1]
                    )
                    filename = attachment["id"] + "." + file_suffix
                    path = join(media_output, filename)
                    if not zipfile and exists(path):
                        continue

                    print(
                        f"\033[KDownloading attachment {path}...", end="\r", flush=True
                    )
                    url_first_try = remote_url if remote_url else url
                    url_second_try = url if remote_url else None

                    try:
                        attachment = mastodon.download_attachment(url_first_try)
                    except RateLimitExceededException as e:
                        e.wait()
                        attachment = mastodon.download_attachment(url_first_try)
                    if not attachment and url_second_try:
                        try:
                            attachment = mastodon.download_attachment(url_second_try)
                        except RateLimitExceededException as e:
                            e.wait()
                            attachment = mastodon.download_attachment(url_second_try)

                    if not attachment:
                        print(
                            f"Warning: Skipping attachment {url} because it was not found"
                        )
                        continue

                    if zipfile:
                        zipfile.writestr(path, attachment)
                    else:
                        with open(path, "wb") as file:
                            file.write(attachment)

        max_id = statuses[-1]["id"]
        page += 1

    j: Any
    if args.optimize_json:
        ac = all_statuses[0]["account"] if len(all_statuses) > 0 else None
        for status in all_statuses:
            del status["account"]
        j = {"account": ac, "statuses": all_statuses}
    else:
        j = all_statuses

    s = dumps(j)
    if zipfile:
        zipfile.writestr("statuses.json", s)
        zipfile.close()
    else:
        with open(output, "w") as file:
            file.write(s)
