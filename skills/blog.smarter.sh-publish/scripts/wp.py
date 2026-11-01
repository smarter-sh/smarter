#!/usr/bin/env python3
"""
Read and publish blog.smarter.sh posts through the WordPress REST API.

The blog has no Application Passwords (Wordfence turns them off, and the REST index
lists no authentication methods), so this logs in through wp-login.php like a browser,
keeps the session cookies, and sends the REST nonce that wp-admin issues with each
request. Credentials come from WP_URL, WP_USERNAME and WP_PASSWORD in the environment,
or from the repository's git-ignored .env. They are never printed.

Usage:
  wp.py whoami
  wp.py categories
  wp.py list [--search TEXT] [--status publish|draft|any]
  wp.py get ID [--raw FILE]
  wp.py publish POST.md --slug SLUG [--title TITLE] [--category ID] [--status draft|publish]
                [--excerpt TEXT] [--id ID] [--date YYYY-MM-DDTHH:MM:SS]
                [--featured-media MEDIA_ID]
  wp.py upload IMAGE [--alt TEXT]
  wp.py clear-cache
  wp.py slack ID [--dry-run]

publish converts POST.md with md2wp.py, which leaves out the post's # H1 and date
line (the theme prints the title and date), and uses the H1 as the title unless
--title is given. With --id it updates that post instead of
creating one. It prints the post's id, status and link. upload adds a file to the
media library and prints its id and url, for a ``![alt](url)`` line in a post.
--date sets the publication date (blog time), for a post the user wants
backdated. --featured-media sets the featured image in the same request as the
content, which makes Yoast SEO rebuild the post's og:image; publish checks it
and saves once more if Yoast has not caught up. clear-cache deletes WP Super
Cache's whole page cache. slack announces a published post in Slack, as the bot
whose token is SLACK_BOT_TOKEN: a release announcement (category 4) in
SLACK_ANNOUNCEMENTS_CHANNEL, any other post in SLACK_BLOG_CHANNEL.
"""

import argparse
import html
import http.cookiejar
import json
import mimetypes
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from md2wp import convert, split_header  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
ANNOUNCEMENTS_CATEGORY = 4  # release announcements


def settings(*keys: str) -> dict[str, str]:
    """Return these settings from the environment, or from the repository's .env."""
    values = {k: os.environ.get(k, "") for k in keys}
    env_file = REPO / ".env"
    if not all(values.values()) and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() in values and not values[key.strip()]:
                values[key.strip()] = value.strip().strip("'\"")
    missing = [k for k, v in values.items() if not v]
    if missing:
        sys.exit(f"missing {', '.join(missing)}: set them in the environment or in {env_file}")
    return values


def credentials() -> tuple[str, str, str]:
    """Return the blog's base url, username and password."""
    values = settings("WP_URL", "WP_USERNAME", "WP_PASSWORD")
    parts = urllib.parse.urlsplit(values["WP_URL"])
    return f"{parts.scheme}://{parts.netloc}", values["WP_USERNAME"], values["WP_PASSWORD"]


def slack_escape(text: str) -> str:
    """Escape the three characters that Slack's mrkdwn treats as control characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def announce(post: dict, dry_run: bool = False) -> None:
    """Post a published post's title, link and description to Slack.

    Release announcements (category 4) go to SLACK_ANNOUNCEMENTS_CHANNEL, every
    other post to SLACK_BLOG_CHANNEL.

    Slack unfurls the link into a card from the page's Yoast og:title, og:description
    and og:image, so the message itself stays short.
    """
    if post["status"] != "publish":
        sys.exit(f"slack: post {post['id']} is {post['status']}, not published. Announce only live posts.")
    title = html.unescape(post["title"]["rendered"])
    yoast = post.get("yoast_head_json") or {}
    description = yoast.get("og_description") or re.sub(r"<[^>]+>", "", post["excerpt"]["rendered"])
    description = html.unescape(description).strip()
    text = f"New on the blog: *<{post['link']}|{slack_escape(title)}>*"
    if description:
        text += f"\n{slack_escape(description)}"
    if dry_run:
        print(text)
        return
    channel = "SLACK_ANNOUNCEMENTS_CHANNEL" if ANNOUNCEMENTS_CATEGORY in post["categories"] else "SLACK_BLOG_CHANNEL"
    values = settings("SLACK_BOT_TOKEN", channel)
    sys.path.insert(0, str(REPO / "scripts"))
    from slack_post import post as slack_post  # pylint: disable=import-outside-toplevel

    try:
        result = slack_post(values[channel], text, values["SLACK_BOT_TOKEN"], unfurl=True)
    except RuntimeError as error:
        sys.exit(f"slack: {error}")
    print(json.dumps({"channel": result["channel"], "ts": result["ts"]}))


class Blog:
    """A logged-in session on the blog's REST API."""

    def __init__(self) -> None:
        self.base, username, password = credentials()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.opener.addheaders = [("User-Agent", "smarter-blog-publisher")]
        login = f"{self.base}/wp-login.php"
        self.opener.open(login).read()  # sets wordpress_test_cookie
        form = urllib.parse.urlencode(
            {
                "log": username,
                "pwd": password,
                "wp-submit": "Log In",
                "testcookie": "1",
                "redirect_to": f"{self.base}/wp-admin/",
            }
        ).encode()
        self.opener.open(login, form).read()
        nonce = self.opener.open(f"{self.base}/wp-admin/admin-ajax.php?action=rest-nonce").read().decode().strip()
        if not nonce or nonce == "0" or len(nonce) > 20:
            sys.exit("login failed: wp-admin issued no REST nonce. Check WP_USERNAME and WP_PASSWORD.")
        self.nonce = nonce

    def request(self, method: str, route: str, body: dict | None = None, **query: str) -> dict | list:
        url = f"{self.base}/wp-json/wp/v2/{route}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("X-WP-Nonce", self.nonce)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(req) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            sys.exit(f"{method} {route}: HTTP {error.code}: {error.read().decode()[:500]}")

    def upload(self, path: pathlib.Path, alt: str = "") -> dict:
        """Upload a file to the media library, and set its alt text."""
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        req = urllib.request.Request(f"{self.base}/wp-json/wp/v2/media", data=path.read_bytes(), method="POST")
        req.add_header("X-WP-Nonce", self.nonce)
        req.add_header("Content-Type", content_type)
        req.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
        try:
            with self.opener.open(req) as response:
                media = json.loads(response.read())
        except urllib.error.HTTPError as error:
            sys.exit(f"POST media: HTTP {error.code}: {error.read().decode()[:500]}")
        if alt:
            media = self.request("POST", f"media/{media['id']}", {"alt_text": alt})
        return media

    def clear_cache(self) -> None:
        """Delete WP Super Cache's whole page cache, as its settings page does."""
        page = self.opener.open(f"{self.base}/wp-admin/options-general.php?page=wpsupercache").read().decode()
        match = re.search(r"var wpsc_ajax = (\{.*?\});", page)
        if not match:
            sys.exit("clear-cache: no wpsc_ajax settings on the WP Super Cache page")
        nonce = json.loads(match.group(1))["nonce"]
        form = urllib.parse.urlencode(
            {"action": "ajax-delete-cache", "path": "/", "admin": "1", "nonce": nonce}
        ).encode()
        # WP Super Cache answers "0" when it has deleted the cache.
        self.opener.open(f"{self.base}/wp-admin/admin-ajax.php", form).read()
        print("page cache cleared")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("whoami")
    sub.add_parser("categories")
    listing = sub.add_parser("list")
    listing.add_argument("--search", default="")
    listing.add_argument("--status", default="publish")
    get = sub.add_parser("get")
    get.add_argument("id")
    get.add_argument("--raw", help="write the post's block markup to this file")
    publish = sub.add_parser("publish")
    publish.add_argument("markdown")
    publish.add_argument("--title", help="the post's title; defaults to the Markdown's # H1")
    publish.add_argument("--slug", required=True)
    publish.add_argument("--category", type=int, action="append", default=[])
    publish.add_argument("--status", choices=("draft", "publish"), default="draft")
    publish.add_argument("--excerpt", default="")
    publish.add_argument("--id", help="update this post instead of creating one")
    publish.add_argument("--date", help="publication date in blog time, e.g. 2026-04-21T09:00:00")
    publish.add_argument("--featured-media", type=int, help="media id of the featured image")
    upload = sub.add_parser("upload")
    upload.add_argument("file")
    upload.add_argument("--alt", default="", help="the image's alt text")
    sub.add_parser("clear-cache")
    slack = sub.add_parser("slack")
    slack.add_argument("id")
    slack.add_argument("--dry-run", action="store_true", help="print the message instead of posting it")
    args = parser.parse_args()

    blog = Blog()
    if args.command == "whoami":
        me = blog.request("GET", "users/me", context="edit")
        print(json.dumps({k: me.get(k) for k in ("id", "name", "roles")}))
    elif args.command == "categories":
        for c in blog.request("GET", "categories", per_page="100"):
            print(c["id"], c["slug"], c["name"], c["count"])
    elif args.command == "list":
        query = {"per_page": "50", "context": "edit", "status": args.status}
        if args.search:
            query["search"] = args.search
        for p in blog.request("GET", "posts", **query):
            print(p["id"], p["date"][:10], p["status"], p["slug"], p["categories"], p["title"]["raw"])
    elif args.command == "get":
        post = blog.request("GET", f"posts/{args.id}", context="edit")
        if args.raw:
            pathlib.Path(args.raw).write_text(post["content"]["raw"], encoding="utf-8")
        print(json.dumps({k: post[k] for k in ("id", "date", "status", "slug", "link", "categories")}))
        print(post["title"]["raw"])
    elif args.command == "clear-cache":
        blog.clear_cache()
    elif args.command == "slack":
        announce(blog.request("GET", f"posts/{args.id}", context="edit"), args.dry_run)
    elif args.command == "upload":
        media = blog.upload(pathlib.Path(args.file), args.alt)
        print(json.dumps({k: media[k] for k in ("id", "source_url", "alt_text")}))
    else:
        markdown = pathlib.Path(args.markdown).read_text(encoding="utf-8")
        title = args.title or split_header(markdown)[0]
        if not title:
            sys.exit("publish: the Markdown has no # H1, so pass --title")
        body = {
            "title": title,
            "slug": args.slug,
            "content": convert(markdown),
            "status": args.status,
            "comment_status": "closed",
            "format": "standard",
        }
        if args.category:
            body["categories"] = args.category
        if args.excerpt:
            body["excerpt"] = args.excerpt
        if args.date:
            body["date"] = args.date
        if args.featured_media:
            body["featured_media"] = args.featured_media
        route = f"posts/{args.id}" if args.id else "posts"
        post = blog.request("POST", route, body)
        if args.featured_media:
            # Yoast can miss the new image when the same request also changes the status.
            route = f"posts/{post['id']}"
            if not blog.request("GET", route, context="edit").get("yoast_head_json", {}).get("og_image"):
                blog.request("POST", route, {"featured_media": args.featured_media, "content": body["content"]})
        print(json.dumps({k: post[k] for k in ("id", "status", "slug", "link")}))


if __name__ == "__main__":
    main()
