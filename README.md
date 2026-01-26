# mastodon-download-toots
Download mastodon toots as json including media.

## Installation
Install mastodon-download-toots using `pipx`:
```
git clone https://github.com/adridevelopsthings/mastodon-download-toots
pipx install .
```

## Usage

### Authorization
The program will show the following prompt:
```
Open the following url in the browser, authorize and than paste the shown authorize code here.
URL:   https://social.adridoesthings.com/oauth/authorize?response_type=code&client_id=oXdoUcfBRjqXYPLg8tWEpIFYiOGViKmmkv_HbPPM8v0&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob&scope=read%3Astatuses+profile

Authorize code: <TYPE IN THE AUTHORIZE CODE SHOWN ON THE SITE HERE>
```
so you just have to click Yes on the site and then copy and paste the code. The access token will be stored on your device in a cache directory.

### JSON output
Run
```
mastodon-download-toots <DOMAIN>
```
and it will put all statuses to `<USERNAME>_<INSTANCE_DOMAIN>_<DATE>.json`. The JSON file contains a list of all statuses. Take a look to the [Mastodon API Documenation: Topic Status](https://docs.joinmastodon.org/entities/Status) to see how these objects look like.

### JSON output and media download
If you also want to download all media attachments pass the option `-m <MEDIA DIRECTORY>` and all attachments will be stored there. Every media object has this filename structure: `<ATTACHMENT ID>.<FILE SUFFIX>`.
```
mastodon-download-toots -m media <DOMAIN>
```

### ZIP file output
If you want to archive your output it might be useful to backup everything into a zip file. This could be done by using the option `-z`. Downloading media attachments is always enabled so you don't have to pass the option `-m`. The `-z` option will download everything into a zipfile (see `--output` option for default zip file output name) by creating the following files inside the zip file:
- `statuses.json`: A JSON list of all statuses
- `media/<ATTACHMENT ID>.<FILE SUFFIX>`: A media attachment

```
mastodon-download-toots -z <DOMAIN>
```
and it will put everyting to `<USERNAME>_<INSTANCE_DOMAIN>_<DATE>.zip`.

### Detailed usage
This is the output of `mastodon-download-toots --help`:
```
usage: mastodon-download-toots [-h] [-a ACCOUNT_PROFILE] [--force-login] [-o OUTPUT] [-z] [-m MEDIA_OUTPUT] [-c CACHE_DIR] domain

positional arguments:
  domain                Domain, e.g. mastodon.social

options:
  -h, --help            show this help message and exit
  -a, --account-profile ACCOUNT_PROFILE
                        If you want to manage multiple accounts on one instance you should set an account profile name that is used for caching the access token
  --force-login         Force a new login even if a cached access token exists
  -o, --output OUTPUT   Output file, e.g. statuses.json. By default the output file is <USERNAME>_<INSTANCE_DOMAIN>_<DATE>.json when zip is not enabled, otherwise it's <USERNAME>_<INSTANCE_DOMAIN>_<DATE>.zip.
  -z, --zip             Instead of having one json file and a media directory download everything into a zip file.
  -m, --media-output MEDIA_OUTPUT
                        Enable media downloading by supplying a directory where media files should be downloaded. For zip mode it's always enabled.
  -c, --cache-dir CACHE_DIR
```