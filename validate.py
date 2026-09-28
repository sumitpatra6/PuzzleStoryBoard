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
