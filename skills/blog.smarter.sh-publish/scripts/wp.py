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
                [--excerpt TEXT] [--id ID]
  wp.py upload IMAGE [--alt TEXT]

publish converts POST.md with md2wp.py, which leaves out the post's # H1 and date
line (the theme prints the title and date), and uses the H1 as the title unless
--title is given. With --id it updates that post instead of
creating one. It prints the post's id, status and link. upload adds a file to the
media library and prints its id and url, for a ``![alt](url)`` line in a post.
"""

import argparse
import http.cookiejar
import json
import mimetypes
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from md2wp import convert, split_header  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]


def credentials() -> tuple[str, str, str]:
    """Return the blog's base url, username and password, from the environment or .env."""
    values = {k: os.environ.get(k, "") for k in ("WP_URL", "WP_USERNAME", "WP_PASSWORD")}
    env_file = REPO / ".env"
    if not all(values.values()) and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() in values and not values[key.strip()]:
                values[key.strip()] = value.strip().strip("'\"")
    missing = [k for k, v in values.items() if not v]
    if missing:
        sys.exit(f"missing {', '.join(missing)}: set them in the environment or in {env_file}")
    parts = urllib.parse.urlsplit(values["WP_URL"])
    return f"{parts.scheme}://{parts.netloc}", values["WP_USERNAME"], values["WP_PASSWORD"]


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
    upload = sub.add_parser("upload")
    upload.add_argument("file")
    upload.add_argument("--alt", default="", help="the image's alt text")
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
        route = f"posts/{args.id}" if args.id else "posts"
        post = blog.request("POST", route, body)
        print(json.dumps({k: post[k] for k in ("id", "status", "slug", "link")}))


if __name__ == "__main__":
    main()
