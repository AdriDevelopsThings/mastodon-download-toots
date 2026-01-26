from argparse import ArgumentParser
from os import environ

from platformdirs import user_cache_dir

parser = ArgumentParser("mastodon-download-toots")
parser.add_argument("domain", type=str, help="Domain, e.g. mastodon.social")
parser.add_argument(
    "-a",
    "--account-profile",
    type=str,
    help="If you want to manage multiple accounts on one instance you should set an account profile name that is used for caching the access token",
)
parser.add_argument(
    "--force-login",
    action="store_true",
    help="Force a new login even if a cached access token exists",
)
parser.add_argument("--purge-cache", action="store_true")
parser.add_argument(
    "-u",
    "--user",
    type=str,
    help="Download data for another user than you, must be an exact address like 'adridoesthings@chaos.social'",
)
parser.add_argument(
    "--optimize-json",
    action="store_true",
    help="Store the account once in the json and remove it from every status for smaller json",
)
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
