---
name: blog.smarter.sh-publish
description: Use when asked to publish, upload, post, update or draft a post on blog.smarter.sh (WordPress) yourself, e.g. "publish the release announcements to the blog", "post this to the WordPress blog", "fix the typo in the v0.21 post", or when asked which release announcement was published last. Covers the credentials in .env, why the scripts log in with a cookie and REST nonce instead of Application Passwords, converting a Markdown post to the Gutenberg blocks the blog uses (md2wp.py), wp.py's whoami/list/get/publish/upload commands, adding screenshots and images, titles, slugs and categories, the draft-check-publish routine, verifying the public page, and choosing which releases to group into one announcement.
---

# Publishing to blog.smarter.sh

[blog.smarter.sh](https://blog.smarter.sh) is a WordPress site. You can read and
publish its posts yourself through the WordPress REST API, with the two scripts
in [scripts/](scripts/). Write the post first, with
`blog.smarter.sh-release-announcement` or `blog.smarter.sh-blog-post`. This
skill only takes a finished Markdown file to a published post.

Publishing is public. A post can be cached, indexed and syndicated before you
take it down. Publish only when the user has asked you to publish. Otherwise
upload a draft and give them the draft's id.

## Credentials

The scripts read `WP_URL`, `WP_USERNAME` and `WP_PASSWORD` from the environment,
or, when they are not set there, from the repository's git-ignored `.env`. The
user keeps them in `.env`, so a fresh shell usually has none of them set, and
that is fine. `WP_URL` is the login page (`https://blog.smarter.sh/wp-login.php`).
The scripts use only its scheme and host.

- Never print, echo or log the password, and never copy it into a file, a
  command line or the conversation. To check that it's set, print its length.
- The account is an administrator. Don't change users, plugins, settings or
  other people's posts.

## Why cookie login, not Application Passwords

The REST index (`https://blog.smarter.sh/wp-json/`) lists no authentication
methods. Wordfence turns Application Passwords off, so HTTP Basic auth with
the login password answers `rest_not_logged_in`. `wp.py` logs in the way a
browser does instead:

1. GET `wp-login.php`, which sets the test cookie.
2. POST `log`, `pwd`, `testcookie=1` and `redirect_to=/wp-admin/` to
   `wp-login.php`. A 302 to `/wp-admin/` means success.
3. GET `/wp-admin/admin-ajax.php?action=rest-nonce`, which returns a
   10-character nonce (or `0` when the login failed).
4. Send the session cookies and an `X-WP-Nonce` header on every REST request.

If Wordfence ever adds a CAPTCHA or two-factor login, step 2 will fail.
`wp.py` stops with "login failed". Tell the user. Don't try to get around it.

## How the posts are stored

The posts are Gutenberg block markup, not Markdown or classic HTML:
`wp:heading`, `wp:paragraph`, `wp:list`/`wp:list-item`, `wp:table`,
`wp:quote`, `wp:separator`, and the SyntaxHighlighter plugin's
`wp:syntaxhighlighter/code` for code. [scripts/md2wp.py](scripts/md2wp.py)
converts the Markdown that the release announcements use into exactly those
blocks. Run on `blog.smarter.sh-release-announcement/references/example-v0.16.md`,
it gives the same blocks as the published v0.16 post. So a converted post
opens cleanly in the block editor, and the user can edit it there.

- Supported: ATX headings, paragraphs, one level of `-` or `1.` lists (an
  indented line continues the item), pipe tables, `>` quotes, `---`, fenced
  code, and inline `**bold**`, `*italics*`, `` `code` `` and `[links](url)`.
  An image is `![alt](url "caption")` on a line of its own, and becomes an
  image block linked to the full-size file. Nested lists, inline images and
  raw HTML are not supported. Keep the post within that.
- Code fences need a language that SyntaxHighlighter has a brush for: `bash`,
  `yaml`, `python`, `jscript`, `sql`, `xml`, `css`, `diff` or `plain`. An
  unknown language, such as `typescript` or `toml`, renders as unhighlighted
  text with curly quotes. md2wp maps `ts`, `typescript`, `js` and `json` to
  `jscript`, `console`, `sh` and `zsh` to `bash`, and `toml`, `ini`, `text`
  and a fence with no language to `plain`. To check that a brush exists, look
  for a 200 from
  `https://blog.smarter.sh/wp-content/plugins/syntaxhighlighter/syntaxhighlighter3/scripts/shBrush<Name>.js`,
  then add it to the map.
- The post's first line, `# vX.Y Release: <theme>`, stays in the content as an
  H1, as in every earlier post. The WordPress title is separate (see below).

## The commands

```bash
S=skills/blog.smarter.sh-publish/scripts
$S/wp.py whoami                    # {"id": 1, "name": "smarter_blog", "roles": ["administrator"]}
$S/wp.py categories                # 4 announcements Announcements ...
$S/wp.py list --status any         # id, date, status, slug, categories, title
$S/wp.py get 132 --raw /tmp/x.html # a post's metadata, and its block markup
$S/wp.py publish ~/desktop/blog-v0.21-v0.23.md --title "Release v0.21 – v0.23" \
  --slug release-v0-21-v0-23 --category 4 --status draft
$S/wp.py publish ... --status publish --id 319   # update post 319, here to publish it
$S/wp.py upload ~/desktop/shot.png --alt "What the image shows"  # id and source_url
```

To add a screenshot, `upload` it and put its `source_url` in an image line.
Resize it to 1680 px wide first (`sips --resampleWidth 1680 in.png --out
<scratchpad>/out.png`). A larger image, such as a 3000 px Retina screenshot,
makes WordPress answer 500 while it builds the resized copies. The file is
saved anyway, but without its large sizes and never moved to
`cdn.blog.smarter.sh`. If that happens, delete the broken media item
(`DELETE media/<id>` with `force=true`) and upload the resized file. Read an
image before uploading it. It is public too, so check it shows no keys,
hostnames, account numbers or customer data.

`publish` without `--id` creates a new post every time. To change a post, pass
its `--id`, or you'll publish a duplicate. It closes comments, like the earlier
posts.

**Never create a second post for an article that already exists**, not even a
draft "for review". Two posts with one title in wp-admin confuse the user, who
can't tell which one is live. An agent once copied a published post into a
"REVISION of post 376" draft for review, then published the edits to the
original and left the draft behind. The user had it deleted and said never to
do that again. To change an existing post, edit that post by its `--id`. If the
user wants to review edits before they go live, show the changed passages in
the conversation and update the post once they approve.

## Conventions

| Field     | Release announcement                                           | Example                                  |
| --------- | -------------------------------------------------------------- | ---------------------------------------- |
| Title     | `Release vX.Y`, or `Release vX.Y – vX.Z` (en dash) for a group | `Release v0.21 – v0.23`                  |
| Slug      | `release-vX-Y`, or `release-vX-Y-vX-Z`                         | `release-v0-21-v0-23`                    |
| Category  | 4, Announcements                                               |                                          |
| H1        | `vX.Y – vX.Z Release: <theme>`                                 |                                          |
| Date line | the day you publish                                            | `October 17, 2026 · The Smarter Project` |

Other articles use category 6 (Artificial Intelligence), 5 (How To) or 9
(System Management). Run `categories` for the current list. The home page
leaves out category 4 (a Code Snippets snippet, "Home page: hide
Announcements", in wp-admin > Snippets). Announcements are listed in the Main
Sidebar's "Announcements" widget instead. So put release announcements and other
administrative posts in category 4, and never add 4 to an article. Leave the
publication date to WordPress (now), and keep the Markdown source at
`~/desktop/blog-<slug>.md`.

Post cards show no excerpt. That is snippet 6, "Post cards: hide excerpts", a
front-end PHP snippet that prints `.entry-card .entry-excerpt { display: none; }`
in `wp_head`. Its CSS goes through PHP because the blog does not serve Code
Snippets' `site-css` snippets. The Code Snippets REST API
(`/wp-json/code-snippets/v1/snippets`) accepts the same login and nonce as
`wp.py`.

WP Super Cache serves pages to visitors, and saving a snippet or theme setting
does not clear it. After such a change, delete the whole cache: read the
`wpsc_ajax` nonce from `wp-admin/options-general.php?page=wpsupercache`, then
POST `action=ajax-delete-cache&path=/&admin=1&nonce=<nonce>` to
`wp-admin/admin-ajax.php`. Verify with the plain url, not a `?query` url,
which bypasses the cache and shows you a page that visitors don't get.

## Routine

1. **Find where the announcements stopped.** `wp.py list` shows the latest
   `Release` post in category 4. The release after it is where you start.
   Confirm the current version from `changelogs/CHANGELOG.md` and
   `gh release list`.
2. **Group the releases.** Not every minor version deserves a post. Read
   each changelog from there to now (`changelogs/CHANGELOG-vX.Y.md`, then
   `CHANGELOG.md`). Group versions until a post has at least one headline
   feature that a reader would upgrade for. For example, v0.31 only added
   Brazilian Portuguese to the console that v0.30 made multilingual, so they
   belong in one post. Use themes that hold together: a contract and the SDK
   built on it, or a feature and the fixes that finished it. Ending a group at a
   theme change is better than making every post the same size. Publish the
   groups oldest first, so the newest post is on top of the blog.
3. **Write each post** with `blog.smarter.sh-release-announcement`. List
   every version in the group in its changelog links. Its "What's next" can
   name what the next post covers, which is a fact, not a guess.
4. **Upload a draft**, then check the rendered HTML, which `wp.py` can read
   while the post is a draft:

   ```bash
   cd skills/blog.smarter.sh-publish/scripts && python3 -c '
   import re
   from wp import Blog
   r = Blog().request("GET", "posts/<id>", context="edit")["content"]["rendered"]
   print(re.findall(r"<pre class=\"brush: \w+", r))   # one per code fence
   text = re.sub(r"<[^>]+>", "", re.sub(r"<pre.*?</pre>", "", r, flags=re.S))
   print(re.findall(r"\*\*|`|\]\(", text))           # leftover Markdown: should be []
   '
   ```

   Every code fence must appear as a `brush:`. A code block that renders as a
   plain `<div>` has an unknown language.

5. **Publish** with `--status publish --id <id>`, if the user asked you to.
6. **Verify the public page.** `curl -sL -o /dev/null -w '%{http_code}' <link>`
   gives 200, and the page's `<title>` is the post's title.
7. **Report** each post's link, which releases it covers, and the claims to
   review (see the release announcement skill's last section).

## Pitfalls

- The host shell is zsh. `${(P)name}` reads a variable by name, and an unquoted
  `--include=*.py` is a glob error. Pass arguments to the scripts quoted.
- `.env` is git-ignored. Make sure it stays that way (`git check-ignore .env`),
  and never add the credentials to a skill, a script or a commit.
- A post on the blog is not the source. If the user edits a post in WordPress
  and you republish the Markdown with `--id`, their edit is lost. First compare
  with `wp.py get <id> --raw`.
