# Hosting story content on GitHub Pages

The specification and setup runbook for the **content repository** that
serves stories to the Photo Jigsaw Android app over the network.

**This document is written to be executed by Claude Code** in a fresh
session, with no access to the Android source. Everything needed is in here.
A person can follow it too; the steps are the same.

To start that session, open an empty folder (or a clone of the content
repository), put this file in it as `content-hosting.md`, run Claude Code
there, and paste the prompt in section 11.

---

## 0. Instructions for Claude — read this first

### Your task

1. Stand up a **public GitHub repository** whose root is served by **GitHub
   Pages**, and which publishes only content that passes `validate.py`.
2. Optionally seed it with the story the Android app already bundles.
3. After that, act as the maintainer of the content: every change you make
   is validated before it is published, and follows the rules in section 6.

### How this document is organised

| Section | What it is | How to treat it |
|---|---|---|
| 0 | these instructions | binding |
| 1 | what the repository is, and why | background |
| 2 | the setup runbook | **do the steps in order** |
| 3–7 | layout, JSON schemas, permanent rules, validator, workflow | **normative specification** |
| 8 | how to add or change a story later | procedure for later requests |
| 9 | troubleshooting | look up errors here before improvising |
| 10 | what the app will do with this | background |
| 11 | the prompt that starts a session | for the user |
| 12 | release checklist | report against it at the end |

Every step in section 2 has a **Do**, a **Check**, and where it matters an
**If it fails**. Do not start a step until the previous step's Check has
passed. If a Check keeps failing and section 9 does not cover it, stop and
report to the user; do not work around it.

### Hard rules

1. **Copy, never retype.** Files marked `<!-- file: … -->` in this document
   are extracted verbatim with the script in step 2.3. Do not reformat,
   modernise or "improve" them.
2. **Never edit `validate.py` or the workflow to make content pass.** If
   content fails validation, fix the content, or stop and ask.
3. **Never rename or renumber a story id or event id** once it has been
   pushed (section 6). Titles may change freely.
4. **Never invent image rights.** `credit`, `source` and `licence` must come
   from the image's real source. If you do not know them, ask the user. Never
   write `Public domain` or `CC0` just to get past the allowlist.
5. **Never reuse an image filename for a different picture**, and increase
   `contentVersion` on every edit to a published story.
6. **All file and folder names lower case; `/` in every JSON path.**
7. **Never** force-push, rewrite `main`'s history, delete the repository,
   make it private, or switch the Pages source away from GitHub Actions.

### When to ask the user

- **Once, before creating anything:** confirm the inputs in step 2.1. That
  confirmation covers every action in section 2: creating the public repo,
  enabling Pages, pushing the skeleton, and pushing the seed content if they
  asked for it.
- Before pushing anything that is **not** part of section 2 or a change the
  user asked for.
- Whenever a step says **Ask**.

### Things only the user can do

Ask for these and wait. Do not try to work around them.

- **Interactive logins:** `gh auth login` and `gh auth refresh`. Ask the user
  to type the command with a `!` in front (e.g. `! gh auth login`) so it runs
  in this session.
- **DNS records** for a custom domain.
- Anything the API refuses with `403` because of account permissions. Give
  them the website click path from the step instead.

### Definition of done

- Every machine-checkable Check in section 2 has passed.
- The final report in step 2.11 has been given to the user, including the
  section 12 items only a person can confirm.

---

## 1. What this repository is

A **static folder of JSON and JPEGs**, served over HTTPS. Nothing else. No
application server, no database, no build step, no SDK.

The app fetches three kinds of URL and nothing more:

```
<baseUrl>/index.json          the catalogue of stories
<baseUrl>/<storyId>.json      one story: all of its text
<baseUrl>/<path>.jpg          a picture, at the path an image ref names
```

That layout is **identical** to `app/src/main/assets/story/` inside the app,
which is the whole trick: the bundled copy and the hosted copy are the same
shape, the same parser reads both, and the same rules validate both.

**Why not Firestore.** A story is mostly paintings, which is a CDN problem,
not a database problem. Firestore would still need Storage or a CDN for the
images, so you would run two services to deliver what one static folder
delivers. Firestore's real strengths — realtime listeners, per-user documents
— are worth nothing for content that is identical for every player and
changes monthly.

---

## 2. Setup runbook

Do these in order. Commands are given for **bash** (Git Bash, macOS, Linux);
where PowerShell differs, both are shown. Work out which shell you are in
before starting. Replace `<user>` and `<repo>` with the values from 2.1.

### 2.1 Preflight and inputs

**Do** — check the tools:

| Tool | Check | If missing, tell the user to install |
|---|---|---|
| Git | `git --version` | `winget install Git.Git` / git-scm.com |
| GitHub CLI | `gh --version` | `winget install GitHub.cli` / `brew install gh` |
| Python 3.8+ | `python --version` (or `python3`) | `winget install Python.Python.3.12` / python.org |

Then check the login and its scopes:

```bash
gh auth status
```

- Not logged in → ask the user to run `! gh auth login` (GitHub.com, HTTPS,
  authenticate Git with credentials: Yes, log in with a web browser), then
  re-check.
- `Token scopes` does not include `workflow` → pushing
  `.github/workflows/deploy.yml` will be refused. Ask the user to run
  `! gh auth refresh -h github.com -s workflow`, then re-check.

**Do** — establish the inputs. Detect what you can and ask the user for the
rest, **in one message**, as a table with your proposed values:

| Input | How to get it | Default |
|---|---|---|
| `<user>` — GitHub account | `gh api user -q .login` | — |
| `<repo>` — repository name | ask | `photo-jigsaw-content` |
| Seed with the bundled story? | ask; if yes, the path to the Android project root | no |
| Protect `main`? | ask: *basic* (block force pushes and deletion) or *strict* (also require the `validate` check, so every change goes by pull request) | basic |
| Custom domain | ask | none |

Tell the user, in that same message, what the name commits them to:

- The base URL is `https://<user>.github.io/<repo>`, or
  `https://<custom domain>` if they give one.
- **The base URL is effectively permanent.** It will be compiled into the app.
  If the repo is later renamed or moved, installed copies keep asking the old
  address. They will not break, because they fall back to their cache and the
  bundled story, but they will never see a new story until the player
  updates the app. GitHub does **not** redirect an old Pages URL after a
  rename. A custom domain (2.9) is the way to keep the freedom to move.
- Do not use `<user>.github.io` as `<repo>`. That is the account's single
  user-site slot.

**Check:** the user has confirmed every input. Do not continue without it.
This confirmation authorises everything else in section 2.

### 2.2 Create the repository, or adopt an existing one

**Do:** first see where you are:

```bash
git rev-parse --is-inside-work-tree 2>/dev/null && git remote -v
```

- **Already inside a clone of `<user>/<repo>`:** skip creation.
- **Otherwise:** check that the name is free, then create and clone:

  ```bash
  gh repo view <user>/<repo> >/dev/null 2>&1 && echo "EXISTS - stop and ask"
  gh repo create <repo> --public --clone \
    --description "Story content for the Photo Jigsaw app, served by GitHub Pages"
  ```

  Then make the new folder your working directory, and copy this document
  into it as `content-hosting.md`. It travels with the content, and step 2.3
  reads it.

**Check:** `gh repo view <user>/<repo> --json visibility -q .visibility`
prints `PUBLIC`, and `git remote -v` points at `github.com/<user>/<repo>`.

**If it fails:** if the repo already exists and is not the one you are in,
stop and ask. Do not reuse or overwrite somebody else's repository.

*Why public:* Pages on a private repo needs a paid plan, and the content is
public anyway the moment it ships inside an app.

### 2.3 Extract the skeleton files

The repository needs exactly these files to start:

| File | Source in this document |
|---|---|
| `content-hosting.md` | this document (2.2) |
| `.nojekyll` | empty file |
| `.gitattributes` | below |
| `index.json` | below (the empty catalogue) |
| `validate.py` | section 7 |
| `.github/workflows/deploy.yml` | section 7 |

Starter catalogue, so the site has something valid to serve before any story
exists:

<!-- file: index.json -->
```json
{
  "formatVersion": 1,
  "stories": []
}
```

Line-ending and binary rules, so Git on Windows never rewrites the JSON and
never "fixes" an image:

<!-- file: .gitattributes -->
```
*.json  text eol=lf
*.py    text eol=lf
*.yml   text eol=lf
*.md    text eol=lf
*.jpg   binary
*.jpeg  binary
*.png   binary
```

**Do:** extract every `<!-- file: … -->` block verbatim. Save this script
**outside the repository**, for example in your scratch directory, and run it
with the repository root as the working directory:

```python
# extract_files.py - writes each "<!-- file: PATH -->" block of content-hosting.md
import pathlib, re, sys

doc = pathlib.Path("content-hosting.md").read_text(encoding="utf-8")
blocks = re.findall(r"<!-- file: (\S+) -->\s*```[^\n]*\n(.*?)\n```", doc, re.S)
expected = {"index.json", ".gitattributes", "validate.py", ".github/workflows/deploy.yml"}
found = {path for path, _ in blocks}
if found != expected:
    sys.exit("expected %s, found %s" % (sorted(expected), sorted(found)))
for path, body in blocks:
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(body + "\n")
    print("wrote", path)
```

Then create the empty `.nojekyll`:

```bash
touch .nojekyll                    # bash
New-Item .nojekyll -ItemType File  # PowerShell
```

*Why `.nojekyll`:* with the Actions deploy, Jekyll never runs. But if the
Pages source is ever switched back to a branch, Jekyll silently drops every
file and folder whose name starts with `_`. The empty file costs nothing and
prevents that.

**Check:** the script printed four `wrote` lines, and `.nojekyll` exists.

### 2.4 Validate locally and commit

**Do:**

```bash
python validate.py        # expect: OK - 0 story/stories validated
git add -A
git commit -m "Content repository skeleton"
git branch -M main
```

**Check:** `git status` is clean. `git ls-files` lists exactly the six files
from 2.3, plus `README.md` if GitHub created one.

### 2.5 Turn Pages on, publishing from GitHub Actions

Pages can publish in two ways, and only one is acceptable here:

| Source | On a push to `main` |
|---|---|
| Deploy from a branch | publishes the files as they are. A failing check runs alongside, but the broken content is **already live**. |
| **GitHub Actions** | runs `validate.py` first, and publishes **only if it passes**. A bad push leaves the previous good version live. |

**Do:**

```bash
gh api -X POST "repos/<user>/<repo>/pages" -f build_type=workflow
```

**If it fails:**

- `409 ... already exists`: Pages is already on. Switch its source:
  `gh api -X PUT "repos/<user>/<repo>/pages" -f build_type=workflow`
- Any error that mentions the repository being empty: do 2.6 first, then come
  back and run this, then start a deploy with `gh workflow run deploy.yml`.
- `403`: ask the user to open **repo → Settings → Pages → Build and
  deployment → Source: GitHub Actions**. Choosing it is enough; there is no
  Save button. They should **not** pick one of the suggested starter
  workflows.

**Check:** `gh api "repos/<user>/<repo>/pages" -q .build_type` prints
`workflow`.

### 2.6 Push, and watch the deploy

**Do:**

```bash
git push -u origin main
```

Then find the run and wait for it. `gh run watch` with no id opens an
interactive picker, so always pass the id:

```bash
gh run list --workflow deploy.yml --branch main --limit 1 \
  --json databaseId,status,conclusion
gh run watch <databaseId> --exit-status
```

The run can take a few seconds to appear after the push. If the list is
empty, run it again.

**Check:** the watch exits 0, and both jobs, `validate` and `deploy`,
succeeded. The first deploy usually takes one to three minutes.

**If it fails:** `gh run view <databaseId> --log-failed`, then look up the
message in section 9. The common first-run failure is *"Branch "main" is not
allowed to deploy to github-pages due to environment protection rules"*. Ask
the user to allow `main` under **Settings → Environments → github-pages →
Deployment branches and tags**, then run `gh run rerun <databaseId>`.

### 2.7 Verify from outside

**Do:**

```bash
curl -sI https://<user>.github.io/<repo>/index.json
curl -s  https://<user>.github.io/<repo>/index.json
```

In PowerShell, use `curl.exe`, not `curl`. Plain `curl` there is an alias
for `Invoke-WebRequest`.

**Check:**

- `HTTP/2 200`
- `content-type: application/json; charset=utf-8`
- the body matches the committed `index.json`

**If it fails:** a `404` shortly after a green deploy is usually propagation.
Retry for up to five minutes, then go to section 9.

**Optional gate test** (**Ask** first; it creates and then closes a pull
request). This proves validation really blocks bad content:

```bash
git switch -c gate-test
# break index.json, e.g. set "formatVersion": 2
git commit -am "Gate test: deliberately invalid"
git push -u origin gate-test
gh pr create --draft --title "Gate test" --body "Deliberately invalid; will be closed."
gh pr checks --watch          # expect: validate fails
gh pr close --delete-branch
git switch main && git branch -D gate-test
```

### 2.8 Protect `main`

**Do:** write the ruleset for the level the user chose in 2.1 to a JSON file
**outside the repository**, then apply it.

*Basic* (default): blocks force pushes and deleting `main`.

```json
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" }
  ]
}
```

*Strict*: the same, plus one more entry in `rules`. From then on, **every**
change, including yours, must go through a pull request whose `validate`
check has passed:

```json
{
  "type": "required_status_checks",
  "parameters": {
    "strict_required_status_checks_policy": false,
    "required_status_checks": [ { "context": "validate" } ]
  }
}
```

```bash
gh api -X POST "repos/<user>/<repo>/rulesets" --input <path-to-ruleset.json>
```

**Check:** `gh api "repos/<user>/<repo>/rulesets" -q '.[].name'` lists
`main`.

**If it fails with 403 or 422:** give the user the click path instead:
**Settings → Rules → Rulesets → New ruleset → New branch ruleset →** name
`main`, enforcement *Active*, target *Include default branch*, tick *Restrict
deletions* and *Block force pushes* (and, for strict, *Require status checks
to pass* with the check `validate`) **→ Create**.

Even without the strict level, the Actions gate from 2.5 already keeps
failing content off the live site.

### 2.9 Custom domain (only if the user gave one)

1. **User:** at their DNS provider, add a `CNAME` record
   `<domain> → <user>.github.io`. Ask them to tell you when it is done.
2. **Do:** `gh api -X PUT "repos/<user>/<repo>/pages" -f cname=<domain>`
3. **Check:** `gh api "repos/<user>/<repo>/pages" -q .cname` prints the domain.
   Then wait for the certificate, which can take up to an hour.
   `gh api "repos/<user>/<repo>/pages" -q .https_certificate.state` should
   reach `approved`.
4. **Do:** `gh api -X PUT "repos/<user>/<repo>/pages" -F https_enforced=true`
5. **User:** verify the domain under **their account → Settings → Pages → Add
   a domain**, so nobody else can claim it if the repo is ever deleted.

The base URL becomes `https://<domain>`, with no repo name in the path. With
the Actions deploy, the domain lives in the Pages settings, not in a `CNAME`
file. Repeat 2.7 against the new URL.

### 2.10 Seed with the bundled story (only if the user asked)

The app's bundled folder has exactly this repository's layout, so the first
real content is a straight copy of `<android>/app/src/main/assets/story/`.

**Do:** check that the source is there (`index.json` inside that folder),
then copy its **contents** into the repository root:

```bash
cp -r "<android>/app/src/main/assets/story/." .
```

```powershell
Copy-Item -Recurse -Force "<android>\app\src\main\assets\story\*" .
```

This replaces the empty `index.json` with the real catalogue (one story,
`shakuntala`), and adds `shakuntala.json` and the `shakuntala/` image folder.

```bash
python validate.py          # expect: OK - 1 story/stories validated
git add -A
git commit -m "Seed with Shakuntala, as bundled in the app"
git push
```

Watch the run as in 2.6, then check as in 2.7. Also check an image:
`curl -sI https://<user>.github.io/<repo>/shakuntala/e1.jpg` should give
`200` with `content-type: image/jpeg`.

**Note for the report:** the bundled pictures are still generated
placeholders that say so on their face. That is fine for proving the
pipeline. They must be replaced by real, rights-checked paintings before the
app is pointed at this site (section 12).

### 2.11 Report to the user

**Do:** finish with one message in this shape:

```
Base URL:        https://...
Repository:      https://github.com/<user>/<repo>
Pages source:    GitHub Actions (verified via API)
Last deploy:     <run URL> - success
Verified live:   index.json 200 application/json; [shakuntala.json, e1.jpg ...]
Seeded:          yes (Shakuntala, 5 events, placeholder art) / no
Protection:      basic | strict | not applied (why)
Custom domain:   <domain>, HTTPS enforced | none
Gate test:       validate failed on PR #n as expected | not run

Needs you:
- <anything in section 12 that only a person can confirm>
- <anything that failed or was skipped, and why>
```

Report failures and skipped steps plainly. Do not describe a step as done
unless its Check passed.

---

### Background: things worth knowing about Pages

- **HTTPS is automatic and enforced.** This matters: Android blocks cleartext
  HTTP by default at this targetSdk, so a plain-HTTP host would need a network
  security config. Pages needs none.
- **No directory listing.** `index.json` is the only catalogue there is, which
  is exactly why the app reads it first.
- **`Cache-Control: max-age=600`.** Edits go live in about ten minutes. Do not
  chase that with cache-busting query strings — `contentVersion` is the
  mechanism for telling the app something changed.
- **Soft limits:** 1 GB published site, 100 GB/month bandwidth, 10 builds an
  hour. A story is a few MB, so you are nowhere near any of them.
- **CORS is irrelevant** to the Android client — it is a browser rule. Pages
  sends `Access-Control-Allow-Origin: *` anyway, so a web preview would work.
- **Optional CDN:** `https://cdn.jsdelivr.net/gh/<user>/<repo>@<tag>/` fronts
  the same repo with immutable tagged URLs if you ever want versioned
  delivery. Not needed to start.

---

## 3. Layout

```
.nojekyll
index.json                    the catalogue
shakuntala.json               one file per story, named <storyId>.json
shakuntala/                   one folder per story, named <storyId>/
  cover.jpg
  intro.jpg
  e1.jpg  e2.jpg  e3.jpg  e4.jpg  e5.jpg
  finale.jpg
  char_shakuntala.jpg         optional character portraits
content-hosting.md            this document
validate.py                   section 7
.gitattributes                section 2.3
.github/workflows/deploy.yml  section 7
```

**File and folder names are case-sensitive on Pages** even though they are not
on Windows or macOS. `shakuntala/E1.jpg` on disk and `"shakuntala/e1.jpg"` in
the JSON will work on your machine and 404 for every player. Keep every name
lower case, and use `/`, never `\`, inside the JSON. The validator checks both.

Image paths inside the JSON are **relative to the repository root and include
the story folder** — `"shakuntala/e1.jpg"`, never `"e1.jpg"`.

---

## 4. `index.json`

```json
{
  "formatVersion": 1,
  "stories": [
    {
      "id": "shakuntala",
      "title": "Shakuntala",
      "subtitle": "From the Adi Parva of the Mahabharata",
      "contentVersion": 1,
      "cover": "shakuntala/cover.jpg",
      "eventCount": 5
    }
  ]
}
```

| Field | Required | Rule |
|---|---|---|
| `formatVersion` | yes | must be exactly `1`; anything else is refused outright |
| `stories` | yes | array; may be empty |
| `stories[].id` | yes | `^[a-z0-9_]+$`, and **permanent** — see section 6 |
| `stories[].title` | yes | non-blank after trimming |
| `stories[].subtitle` | no | defaults to `""` |
| `stories[].contentVersion` | no | integer, defaults to `1`; bump on every edit |
| `stories[].cover` | no | path to the library card image |
| `stories[].eventCount` | no | defaults to `0`; must equal the story's real event count |

**Two version numbers, deliberately.** `formatVersion` is the shape of the
JSON and governs parser compatibility. `contentVersion` is this story's
revision and drives refetch and cache invalidation. Collapsing them would mean
either refetching on every schema change or failing to refetch on a typo fix.

**`eventCount` duplicates what the story file knows**, so it can drift. That
is deliberate: the library screen renders from the index alone, without
downloading every story, which matters little locally and a great deal over a
network. The validator holds the two to each other so drift fails CI. At
runtime a missing or stale count degrades to showing no progress rather than a
wrong one.

---

## 5. `<storyId>.json`

```json
{
  "formatVersion": 1,
  "id": "shakuntala",
  "title": "Shakuntala",
  "subtitle": "From the Adi Parva of the Mahabharata",

  "intro": {
    "title": "A girl raised by the forest",
    "body": "First paragraph.\n\nSecond paragraph.",
    "image": {
      "file": "shakuntala/intro.jpg",
      "caption": "Shakuntala",
      "credit": "Raja Ravi Varma (1848-1906)",
      "source": "Wikimedia Commons",
      "licence": "Public domain"
    }
  },

  "characters": [
    {
      "id": "shakuntala",
      "name": "Shakuntala",
      "epithet": "Daughter of a sage and an apsara",
      "blurb": "Two or three sentences.",
      "image": null
    }
  ],

  "events": [
    {
      "id": "e1_the_hermitage",
      "title": "The Hermitage",
      "setup": "One line shown above the board, 160 characters at most.",
      "characters": ["shakuntala", "dushyanta"],
      "image": {
        "file": "shakuntala/e1.jpg",
        "caption": "Shakuntala looking back",
        "credit": "Raja Ravi Varma (1848-1906)",
        "source": "Wikimedia Commons",
        "licence": "Public domain"
      },
      "payoff": {
        "title": "Two worlds meet",
        "body": "What the scene meant.\n\nA second paragraph if you like."
      }
    }
  ],

  "finale": {
    "title": "Why this story survived",
    "body": "Closing words."
  }
}
```

### Rules the parser enforces

Every failure names its path, e.g. `shakuntala.events[2].payoff.body`.

**Top level**

| Field | Required | Rule |
|---|---|---|
| `formatVersion` | yes | exactly `1` |
| `id` | yes | `^[a-z0-9_]+$`; must match the filename and the index entry |
| `title` | yes | non-blank |
| `subtitle` | no | defaults to `""` |
| `intro` | yes | a **card** (below) |
| `characters` | no | array; ids must be unique |
| `events` | yes | array, **at least one**; ids must be unique |
| `finale` | no | a card |

**A card** — `intro`, `finale`, and each `events[].payoff`

| Field | Required |
|---|---|
| `title` | yes, non-blank |
| `body` | yes, non-blank — split into paragraphs on `\n\n` |
| `image` | no |

**A character**

| Field | Required |
|---|---|
| `id` | yes, `^[a-z0-9_]+$`, unique within the story |
| `name` | yes, non-blank |
| `epithet` | no |
| `blurb` | yes, non-blank |
| `image` | no |

**An event**

| Field | Required |
|---|---|
| `id` | yes, `^[a-z0-9_]+$`, unique, **permanent** |
| `title` | yes, non-blank |
| `setup` | yes, non-blank, **160 characters at most** |
| `characters` | array of character ids; every one must resolve |
| `image` | **yes** — this is the puzzle picture |
| `payoff` | **yes** — a card |
| `dialogue` | no — comic-style lines drawn over the revealed picture (below) |

**A dialogue line** — one entry of `events[].dialogue`, shown in order as
comic speech bubbles, thought bubbles and caption boxes once the puzzle is
solved:

```json
{ "speaker": "dushyanta", "kind": "speech", "text": "Wear my signet ring.", "anchor": "top_left" }
```

| Field | Rule |
|---|---|
| `speaker` | a character id listed in this event's `characters`, or `null` for a caption |
| `kind` | `speech`, `thought`, or `caption`; a caption has `speaker: null`, and nothing else does |
| `text` | non-blank, 120 characters at most, so it fits a bubble on a phone |
| `anchor` | where the bubble sits: `top`, `bottom`, `top_left`, `top_right`, `bottom_left`, `bottom_right`; place it off the faces |

The field is optional and additive, so it does not change `formatVersion`: an
app that does not know it ignores it. `validate.py` does not check it; check
it by eye, or with a quick script, before pushing.

**An image reference** — all five fields required and non-blank:

| Field | Meaning |
|---|---|
| `file` | path from the repo root, including the story folder |
| `caption` | what the picture shows |
| `credit` | who made it, e.g. `Raja Ravi Varma (1848-1906)` |
| `source` | where it came from, e.g. `Wikimedia Commons` |
| `licence` | **must be one of** `Public domain`, `CC0`, `CC BY 4.0`, `CC BY-SA 4.0` |

The licence allowlist is the point of the whole block: an image whose rights
were never actually checked cannot pass validation, so it cannot ship.

### Extra rules the validator enforces

The parser does not check these, but the app's own test suite does, so the
hosted copy should meet them too:

1. `index.eventCount` equals the story's real number of events.
2. Every `image.file` referenced anywhere **exists**. This is the single
   likeliest authoring slip — a renamed jpg.
3. **No event reuses another event's image.** Usually a copy-paste.
4. Every event image's aspect ratio is between **0.4 and 2.5**. Outside that
   the app centre-crops, which quietly cuts the subject out of a painting.
5. Every event names **at least one character** — an event's first screen
   introduces the people you need, and an empty one is a blank card.
6. Every declared character is referenced by **at least one** event.

---

## 6. Rules that must never be broken

**Story ids and event ids are a contract.** The app keys player progress on
`(story_id, event_id)` in its local database. Renaming or renumbering an id
silently erases that player's progress on that chapter, with no error and no
way to recover it. Ids are permanent once published. Titles are free to change
at any time.

**Bump `contentVersion` whenever text or art changes.** It is how the app
knows to refetch, and how a cached copy is invalidated. Re-publishing a
painting under the same filename without bumping it leaves players on the old
one.

**Never point two different pictures at one filename.** The app folds image
identity into the key that decides whether a half-finished board is still
valid. Reusing a name is how someone ends up solving a board made of a
painting that is no longer there.

**A refused fetch is not an error state.** Unknown `formatVersion`, malformed
JSON and a 404 should all degrade to the previously cached copy, and then to
the story bundled in the APK. A library that breaks when the CDN hiccups is
worse than one that updates a day late.

---

## 7. Validate before you push

Authoring mistakes should surface in a two-second local run, not in front of a
player. `validate.py` has **no dependencies** — it reads JPEG and PNG
dimensions itself rather than pulling in Pillow.

```bash
python validate.py        # exits non-zero and names the path that failed
```

It has been run against this app's real content: it passes the shipped story,
and it was checked against thirteen deliberately broken variants — a listed
story with no file, a stale `eventCount`, a licence off the allowlist, a
renamed jpg, an over-long `setup`, a duplicate event id, a dangling character
reference, an event naming nobody, two events sharing art, a bad id, a card
missing its body, a future `formatVersion`, and malformed JSON. Each is caught
and named by path. The dimension reader was checked against both JPEG and PNG.
It was later tightened to catch two mistakes that pass on Windows and 404 on
Pages — a file whose name differs from the JSON only in case (`E1.jpg`), and a
path written with a backslash — and both were checked on Windows.

<details>
<summary><code>validate.py</code></summary>

<!-- file: validate.py -->
```python
#!/usr/bin/env python3
"""Validates the story content in this repository. No dependencies."""
import json
import os
import re
import struct
import sys

ID = re.compile(r"^[a-z0-9_]+$")
LICENCES = {"Public domain", "CC0", "CC BY 4.0", "CC BY-SA 4.0"}
FORMAT_VERSION = 1
MAX_SETUP = 160
MIN_ASPECT, MAX_ASPECT = 0.4, 2.5
SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}

errors = []


def fail(path, message):
    errors.append("%s: %s" % (path, message))


def text(obj, path, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        fail("%s.%s" % (path, key), "missing or blank")
        return ""
    return value.strip()


def ident(obj, path, key):
    value = text(obj, path, key)
    if value and not ID.match(value):
        fail("%s.%s" % (path, key),
             "'%s' must be lower case letters, digits or underscore" % value)
    return value


def exists_exactly(name):
    """True only if the file exists with this exact spelling, case included.

    Windows and macOS would find 'shakuntala/E1.jpg' when asked for
    'shakuntala/e1.jpg'; GitHub Pages would not, so every player gets a 404.
    """
    if not os.path.isfile(name):
        return False
    folder = "."
    for part in name.split("/"):
        if part not in os.listdir(folder):
            return False
        folder = os.path.join(folder, part)
    return True


def image_size(path):
    """(width, height) for a JPEG or PNG, or None."""
    with open(path, "rb") as f:
        head = f.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        if head[:2] != b"\xff\xd8":
            return None
        f.seek(2)
        while True:
            byte = f.read(1)
            while byte and byte != b"\xff":
                byte = f.read(1)
            marker = f.read(1)
            while marker == b"\xff":
                marker = f.read(1)
            if not marker:
                return None
            code = marker[0]
            if code == 0x01 or 0xD0 <= code <= 0xD9:
                continue
            length_bytes = f.read(2)
            if len(length_bytes) < 2:
                return None
            length = struct.unpack(">H", length_bytes)[0]
            if code in SOF:
                body = f.read(5)
                if len(body) < 5:
                    return None
                height, width = struct.unpack(">HH", body[1:5])
                return width, height
            f.seek(length - 2, 1)


def check_image(obj, path, seen):
    if obj is None:
        return None
    if not isinstance(obj, dict):
        fail(path, "not an object")
        return None
    for key in ("file", "caption", "credit", "source"):
        text(obj, path, key)
    licence = text(obj, path, "licence")
    if licence and licence not in LICENCES:
        fail("%s.licence" % path,
             "'%s' is not an allowed licence - check the rights first" % licence)
    name = obj.get("file") if isinstance(obj.get("file"), str) else ""
    if name:
        if not exists_exactly(name):
            fail("%s.file" % path,
                 "no such file '%s' (names are case-sensitive, separators are /)"
                 % name)
        seen.add(name)
    return name


def check_card(obj, path, seen):
    if not isinstance(obj, dict):
        fail(path, "missing")
        return
    text(obj, path, "title")
    text(obj, path, "body")
    check_image(obj.get("image"), path + ".image", seen)


def check_story(story_id, expected_events):
    filename = "%s.json" % story_id
    if not exists_exactly(filename):
        fail(filename, "the index lists this story but the file does not exist")
        return
    try:
        with open(filename, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        fail(filename, "not valid JSON (%s)" % e)
        return
    if not isinstance(data, dict):
        fail(filename, "not an object")
        return

    if data.get("formatVersion") != FORMAT_VERSION:
        fail("%s.formatVersion" % story_id, "expected %d" % FORMAT_VERSION)
    if ident(data, story_id, "id") != story_id:
        fail("%s.id" % story_id, "does not match the filename or the index")
    text(data, story_id, "title")

    seen = set()
    check_card(data.get("intro"), "%s.intro" % story_id, seen)
    if data.get("finale") is not None:
        check_card(data["finale"], "%s.finale" % story_id, seen)

    characters = data.get("characters") or []
    ids = []
    for i, character in enumerate(characters):
        path = "%s.characters[%d]" % (story_id, i)
        if not isinstance(character, dict):
            fail(path, "not an object")
            continue
        ids.append(ident(character, path, "id"))
        text(character, path, "name")
        text(character, path, "blurb")
        check_image(character.get("image"), path + ".image", seen)
    for cid in set(ids):
        if cid and ids.count(cid) > 1:
            fail("%s.characters" % story_id, "duplicate character id '%s'" % cid)

    events = data.get("events")
    if not isinstance(events, list) or not events:
        fail("%s.events" % story_id, "a story needs at least one event")
        return

    if expected_events is not None and expected_events != len(events):
        fail("index.eventCount for %s" % story_id,
             "says %d but the story has %d" % (expected_events, len(events)))

    event_ids, event_images, referenced = [], [], set()
    for i, event in enumerate(events):
        path = "%s.events[%d]" % (story_id, i)
        if not isinstance(event, dict):
            fail(path, "not an object")
            continue
        event_ids.append(ident(event, path, "id"))
        text(event, path, "title")
        setup = text(event, path, "setup")
        if len(setup) > MAX_SETUP:
            fail("%s.setup" % path, "longer than %d characters" % MAX_SETUP)

        names = event.get("characters") or []
        if not names:
            fail("%s.characters" % path,
                 "an event must introduce at least one character")
        for j, ref in enumerate(names):
            if ref not in ids:
                fail("%s.characters[%d]" % (path, j),
                     "no character with id '%s'" % ref)
            referenced.add(ref)

        image = event.get("image")
        if not isinstance(image, dict):
            fail("%s.image" % path, "missing")
        else:
            name = check_image(image, path + ".image", seen)
            if name:
                event_images.append(name)
                if os.path.isfile(name):
                    size = image_size(name)
                    if size is None:
                        fail("%s.image.file" % path,
                             "cannot read the dimensions of '%s'" % name)
                    else:
                        aspect = size[0] / float(size[1])
                        if not MIN_ASPECT <= aspect <= MAX_ASPECT:
                            fail("%s.image.file" % path,
                                 "aspect %.2f is outside %.1f-%.1f and would be cropped"
                                 % (aspect, MIN_ASPECT, MAX_ASPECT))
        check_card(event.get("payoff"), path + ".payoff", seen)

    for eid in set(event_ids):
        if eid and event_ids.count(eid) > 1:
            fail("%s.events" % story_id, "duplicate event id '%s'" % eid)
    for name in set(event_images):
        if event_images.count(name) > 1:
            fail("%s.events" % story_id, "two events share the image '%s'" % name)

    unused = set(i for i in ids if i) - referenced
    if unused:
        fail("%s.characters" % story_id,
             "declared but never used: %s" % sorted(unused))


def main():
    if not os.path.isfile("index.json"):
        print("index.json not found - run this from the repository root")
        return 1
    try:
        with open("index.json", encoding="utf-8") as f:
            index = json.load(f)
    except ValueError as e:
        print("index.json: not valid JSON (%s)" % e)
        return 1

    if index.get("formatVersion") != FORMAT_VERSION:
        fail("index.formatVersion", "expected %d" % FORMAT_VERSION)

    stories = index.get("stories")
    if not isinstance(stories, list):
        fail("index.stories", "missing")
        stories = []

    seen = []
    for i, entry in enumerate(stories):
        path = "index.stories[%d]" % i
        if not isinstance(entry, dict):
            fail(path, "not an object")
            continue
        story_id = ident(entry, path, "id")
        text(entry, path, "title")
        cover = entry.get("cover")
        if cover and not exists_exactly(cover):
            fail("%s.cover" % path, "no such file '%s'" % cover)
        if story_id:
            seen.append(story_id)
            check_story(story_id, entry.get("eventCount") or None)
    for sid in set(seen):
        if seen.count(sid) > 1:
            fail("index.stories", "duplicate story id '%s'" % sid)

    if errors:
        print("%d problem(s):\n" % len(errors))
        for line in errors:
            print("  " + line)
        return 1
    print("OK - %d story/stories validated" % len(seen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

</details>

### Run it on every push — and deploy only if it passes

`.github/workflows/deploy.yml`:

<!-- file: .github/workflows/deploy.yml -->
```yaml
name: Validate and deploy

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:        # a "Run workflow" button, for redeploying by hand

permissions:
  contents: read
  pages: write
  id-token: write

# One deploy at a time; a newer push supersedes a queued one, but a deploy
# already running is allowed to finish.
concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  validate:
    runs-on: ubuntu-latest   # Linux, so file names are checked case-sensitively
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - run: python validate.py

  deploy:
    needs: validate          # never runs if validation failed
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: .            # the repo root is the site; .git and .github are left out
      - id: deployment
        uses: actions/deploy-pages@v4
```

Newer major versions of these actions are fine; the shape does not change.

What this buys you:

- A push to `main` that fails validation **publishes nothing**. The site keeps
  serving the last good version, and the Actions tab shows which path failed.
- A pull request runs `validate` only, so you see the verdict before merging.
- `validate.py`, `README.md` and this guide are published too. That is
  harmless — the app never asks for them — and keeping the repo root as the
  site root is what makes the layout identical to the app's assets folder.

The gate only works because Pages publishes from this workflow (2.5). With
the source set to "Deploy from a branch", a bad push would be live before the
check finished, so never switch it.

---

## 8. Publishing a change

Follow this when the user asks you to add or change content after setup. The
hard rules in section 0 still apply. In particular, the **pictures and their
rights come from the user.** If you are asked to find paintings yourself,
take `credit`, `source` and `licence` from each file's own page (for example
its Wikimedia Commons page). List every image whose rights you could not
confirm, and do not push those until the user has decided.

If `main` has the *strict* ruleset (2.8), do every change below on a branch
and open a pull request with `gh pr create`. Merge only after
`gh pr checks --watch` passes, and only if the user has said you may merge.

### Adding a new story

1. Pick the id — lower case, digits, underscores — and accept that it is
   permanent (section 6). Say `savitri`.
2. Create `savitri/` and put the pictures in it: `cover.jpg`, `intro.jpg`,
   one per event, `finale.jpg` if the finale has one. Lower-case names.
   Resize first — around 1600 px on the long side and a few hundred KB each is
   plenty for a phone.
3. Write `savitri.json` following section 5. Easiest is to copy
   `shakuntala.json` and replace everything, *including every id*.
4. Add an entry to `index.json` with `contentVersion: 1` and the right
   `eventCount`.
5. `python validate.py` until it says OK.
6. Commit and push (or open a pull request), then watch the run as in 2.6:

   ```bash
   git add -A
   git commit -m "Add Savitri"
   git push
   ```

7. Check that `savitri.json` and every new image answer 200 (2.7). Players
   see the story within about ten minutes of the deploy finishing, the next
   time the app checks.
8. Report what you published, with its URLs and the run link.

### Editing a published story

1. Change the text or replace the picture. A changed picture gets a **new
   filename** (`e3.jpg` → `e3_v2.jpg`), never the old name (section 6).
2. In `index.json`, **increase that story's `contentVersion` by one**. This is
   the only signal the app gets that something changed.
3. Do **not** touch story or event ids. Titles are free to change.
4. Validate, commit, push, watch and check, as above. Say in the report which
   story's `contentVersion` changed, and what it changed from and to.

### Undoing a bad publish

The site is whatever `main` says, so undoing is a Git operation:

```bash
git log --oneline            # find the commit that broke it
git revert <commit>          # makes a new commit that undoes it
git push                     # redeploys the previous content
```

Then bump `contentVersion` again, so apps that fetched the bad version fetch
the fixed one. **Ask** before reverting anything you did not publish in this
session. Revert rather than `git reset --hard` + force-push: history
stays intact and the ruleset in 2.8 blocks force pushes anyway.

To redeploy without changing anything — say the last deploy failed for a
reason on GitHub's side — use **Actions → Validate and deploy → Run
workflow**, or `gh workflow run deploy.yml`.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `404` for every URL, even `index.json` | Pages not on yet, or first deploy still running | wait 2–3 minutes; check **Settings → Pages** shows "Your site is live"; check the Actions run is green |
| `404` for one image, fine locally | case mismatch or `\` in the JSON path | rename to match exactly with `git mv Old.jpg old.jpg`; note Windows Git may not notice a case-only rename without `git mv` |
| Actions run red at `validate` | content breaks a rule | read the log: every line names the path, e.g. `shakuntala.events[2].setup: longer than 160 characters` |
| Red at `deploy`: *not allowed to deploy to github-pages* | environment branch rule | **Settings → Environments → github-pages** → allow `main` |
| Red at `deploy`: *Get Pages site failed* / *Not Found* | Pages source is not "GitHub Actions" | section 2.5 |
| Deploy green, old content still served | Pages caches for 10 minutes | wait; check with `curl -sI` and look at `age:` and `last-modified:` |
| Deploy green, app still shows old content | `contentVersion` not bumped | bump it, push |
| `content-type: text/plain` or `application/octet-stream` | wrong extension (`.JSON`, `.jpeg` where the JSON says `.jpg`) | lower-case `.json` / `.jpg` |
| A folder starting with `_` is missing online | Jekyll ran (branch deploy without `.nojekyll`) | add `.nojekyll`, or switch to the Actions deploy |
| `validate.py`: *run this from the repository root* | run from the wrong folder | `cd` to the repo root |
| `gh: command not found` / not logged in | CLI missing or unauthenticated | 2.1 |
| `git push` rejected: *protected branch* | the strict ruleset in 2.8 | push a branch and open a pull request: `git switch -c my-change`, push, `gh pr create` |

---

## 10. What the app will do with this

Not built yet, but this is the contract the layout is designed for, so it is
worth knowing what you are serving.

One new class in the app, and no changes above the data layer:

```kotlin
class RemoteStoryCatalog(
    private val baseUrl: String,
    private val cacheDir: File,
    private val fallback: StoryCatalog,   // the stories bundled in the APK
) : StoryCatalog
```

Resolution order for every read is **cache → bundled → network**, with
anything fetched written into `filesDir/story/` in the same layout as this
repository. So the app keeps working offline and on a first run with no
connection, and the bundled story is the permanent floor.

Networking will use `HttpURLConnection` from the platform. This project has no
third-party dependencies and adding one for three GET requests would be a poor
trade.

**Player data never comes here.** Progress and saved boards live in the app's
local SQLite and are the app's business. This repository is read-only content,
identical for every player.

---

## 11. Paste this into Claude Code to start

Put this file in the folder as `content-hosting.md`, open Claude Code there,
and paste:

> Read `content-hosting.md` in full. It is both the specification and your
> instructions. Follow section 0, then carry out the setup runbook in
> section 2, step by step. Ask me for the inputs in 2.1 before you create
> anything. When you are done, give me the report described in 2.11.

For later sessions in the same repository:

> Read `content-hosting.md`, sections 0, 5, 6 and 8. Then <add the story in
> folder X / fix the typo in Y / replace picture Z>.

---

## 12. Checklist before the first real publish

Claude checks and reports these:

- [ ] Repository is public and Pages is serving `index.json` over HTTPS
- [ ] Pages source is **GitHub Actions** (`build_type: workflow`)
- [ ] The gate test in 2.7 showed `validate` failing on bad content (if run)
- [ ] `.nojekyll` and `.gitattributes` exist at the root
- [ ] `validate.py` passes locally and in CI
- [ ] Every file name is lower case, and every live image URL returns 200
- [ ] `eventCount` in the index matches each story

Only the user can confirm these. List them under *Needs you* in the report:

- [ ] The base URL is final (2.1) — it is about to be compiled into the app
- [ ] Every image has a real `credit` and a `licence` from the allowlist,
      checked per file rather than assumed
- [ ] Every painting comes from a file tagged `PD-Art` or equivalent — a
      photograph of a public-domain painting can carry its own copyright in
      some jurisdictions
- [ ] Story ids and event ids are ones you are willing to keep for ever
- [ ] No placeholder art remains
- [ ] Images are a few hundred KB each, not multi-megabyte originals
- [ ] No subject sits dead centre — the middle of the 4x3 grid is a seam, not
      a tile
