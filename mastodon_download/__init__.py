from argparse import ArgumentParser
from datetime import datetime
from json import dump, dumps
from os import environ, mkdir, remove
from os.path import exists, join
from typing import Optional
from zipfile import ZipFile

from platformdirs import user_cache_dir

from mastodon_download.mastodon import Mastodon, RateLimitExceededException

parser = ArgumentParser("mastodon-download-toots")
parser.add_argument("domain", type=str, help="Domain, e.g. mastodon.social")
parser.add_argument(
    "-o",
    "--output",
    type=str,
    required=False,
    help="Output file, e.g. statuses.json. By default the output file is <USERNAME>_<INSTANCE_DOMAIN>_<DATE>.json when zip is not enabled, otherwise it's <USERNAME>_<INSTANCE_DOMAIN>_<DATE>.zip.",
)
parser.add_argument(
    "-z",
    "--zip",
    action="store_true",
    help="Instead of having one json file and a media directory download everything into a zip file.",
)
parser.add_argument(
    "-m",
    "--media-output",
    type=str,
    help="Enable media downloading by supplying a directory where media files should be downloaded. For zip mode it's always enabled.",
)
parser.add_argument(
    "-c",
    "--cache-dir",
    type=str,
    default=environ.get(
        "CACHE_DIR", user_cache_dir("mastodon-download-toots", "AdriDevelopsThings")
    ),
)


def main() -> None:
    args = parser.parse_args()
    mastodon = Mastodon.from_instance_domain(args.domain, args.cache_dir)
    if not mastodon.authorized:
        print(
            "Open the following url in the browser, authorize and than paste the shown authorize code here."
        )
        print(f"URL:   {mastodon.authorize_url}")
        print("")
        code = input("Authorize code: ")
        mastodon.create_token(code)
    me = mastodon.get_me()

    output = args.output
    if not output:
        date = datetime.now().strftime("%Y-%m-%d")
        output = (
            f"{me['username']}_{args.domain}_{date}.{'zip' if args.zip else 'json'}"
        )

    if exists(output):
        if input("Output file already exists, overwriting? [y/n] ").lower() != "y":
            return
        remove(output)

    if not args.zip and args.media_output and not exists(args.media_output):
        mkdir(args.media_output)

    media_output = args.media_output
    if args.zip:
        media_output = "media"

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
            statuses = mastodon.get_user_statuses(me["id"], limit=40, max_id=max_id)
        except RateLimitExceededException as e:
            e.wait()
            statuses = mastodon.get_user_statuses(me["id"], limit=40, max_id=max_id)

        if len(statuses) == 0:
            break
        all_statuses.extend(statuses)

        if media_output:
            for status in statuses:
                for attachment in status["media_attachments"]:
                    url = attachment["url"]
                    file_suffix = url.split(".")[-1]
                    filename = attachment["id"] + "." + file_suffix
                    path = join(media_output, filename)
                    if not zipfile and exists(path):
                        continue
                    print(
                        f"\033[KDownloading attachment {path}...", end="\r", flush=True
                    )
                    attachment = mastodon.download_attachment(url)
                    if zipfile:
                        zipfile.writestr(path, attachment)
                    else:
                        with open(path, "wb") as file:
                            file.write(attachment)

        max_id = statuses[-1]["id"]
        page += 1

    s = dumps(all_statuses)
    if zipfile:
        zipfile.writestr("statuses.json", s)
        zipfile.close()
    else:
        with open(output, "w") as file:
            file.write(s)
