#!/usr/bin/env python3

"""
GZCTF Game and Challenge Cloner

Author: l4rm4nd (https://github.com/l4rm4nd)
License: MIT

Description:
    This script allows duplicating existing games and challenges on a GZCTF instance.
    It supports three modes:
      - Clone an existing game and all/some of its challenges.
      - Create a new empty game and populate it with challenges selected from any game.
      - Export an existing game onto disk for later re-import

    Supports cross-instance cloning if --dst-url and --dst-token are supplied.
    The script preserves flags, hints, metadata, and attachments.
    All duplicated games are hidden and challenges disabled by default.
"""

import requests
import argparse
import time
import secrets
import sys
import os
import io
import json
from urllib.parse import urlparse
from datetime import datetime

def generate_invite_code(length=24):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def session_with_token(base_url, token):
    session = requests.Session()
    domain = base_url.split("//")[-1].split("/")[0]
    session.cookies.set("GZCTF_Token", token, domain=domain)
    return session

def fetch_games(session, base_url):
    try:
        r = session.get(f"{base_url}/api/game?count=50&skip=0")
        r.raise_for_status()
        return r.json()["data"]
    except Exception as e:
        print(f"❌ Failed to fetch games: {e}")
        sys.exit(1)

def fetch_challenges(session, base_url, game_id):
    try:
        r = session.get(f"{base_url}/api/edit/games/{game_id}/challenges")
        r.raise_for_status()
        chs = r.json()
        for ch in chs:
            ch["game_id"] = game_id
        return chs
    except Exception as e:
        print(f"❌ Failed to fetch challenges for game {game_id}: {e}")
        return []

def fetch_challenge_config(session, base_url, game_id, challenge_id):
    r = session.get(f"{base_url}/api/edit/games/{game_id}/challenges/{challenge_id}")
    r.raise_for_status()
    return r.json()

def create_game(session, base_url, title, invite_code=None):
    now = int(time.time()) + 600
    data = {
        "title": title,
        "summary": f"Cloned: {title}",
        "hidden": True,
        "acceptWithoutReview": False,
        "writeupRequired": False,
        "inviteCodeRequired": True,
        "inviteCode": invite_code or generate_invite_code(),
        "practiceMode": True,
        "start": now * 1000,
        "end": (now + 3600) * 1000
    }
    r = session.post(f"{base_url}/api/edit/games", json=data)
    r.raise_for_status()
    return r.json()

def create_challenge_minimal(session, base_url, game_id, ch_full, ch_meta):
    score = ch_meta.get("originalScore", ch_meta.get("score", 100))
    data = {
        "title": ch_full.get("title", ch_meta["title"]),
        "category": ch_full.get("category", ch_meta.get("category", "Misc")),
        "type": ch_full.get("type", "StaticAttachment"),
        "isEnabled": False,
        "score": score,
        "minScore": score,
        "originalScore": score
    }
    r = session.post(f"{base_url}/api/edit/games/{game_id}/challenges", json=data)
    r.raise_for_status()
    return r.json()

def update_challenge(session, base_url, game_id, challenge_id, ch):
    patch_fields = {
        "title": ch.get("title"),
        "content": ch.get("content"),
        "flagTemplate": ch.get("flagTemplate"),
        "category": ch.get("category"),
        "hints": ch.get("hints", []),
        "fileName": ch.get("fileName"),
        "containerImage": ch.get("containerImage"),
        "memoryLimit": ch.get("memoryLimit"),
        "cpuCount": ch.get("cpuCount"),
        "storageLimit": ch.get("storageLimit"),
        "containerExposePort": ch.get("containerExposePort"),
        "enableTrafficCapture": ch.get("enableTrafficCapture"),
        "disableBloodBonus": ch.get("disableBloodBonus"),
        "originalScore": ch.get("originalScore"),
        "minScoreRate": ch.get("minScoreRate"),
        "difficulty": ch.get("difficulty")
    }
    patch_fields = {k: v for k, v in patch_fields.items() if v is not None}
    r = session.put(f"{base_url}/api/edit/games/{game_id}/challenges/{challenge_id}", json=patch_fields)
    r.raise_for_status()

def duplicate_flags(session, base_url, game_id, cid, flags):
    flag_data = [{"flag": f["flag"]} for f in flags]
    r = session.post(f"{base_url}/api/edit/games/{game_id}/challenges/{cid}/flags", json=flag_data)
    r.raise_for_status()

def duplicate_attachment(session, base_url, full_url_base, game_id, cid, attachment):
    if not attachment or not attachment.get("url"):
        return

    if attachment.get("type") == "Remote":
        remote_url = attachment["url"]
        data = {"attachmentType": "Remote", "remoteUrl": remote_url}
        r = session.post(f"{base_url}/api/edit/games/{game_id}/challenges/{cid}/attachment", json=data)
        r.raise_for_status()
        return

    elif attachment.get("type") == "Local":
        download_url = full_url_base + attachment["url"]
        try:
            # Download the file
            res = session.get(download_url)
            res.raise_for_status()
            file_data = res.content
            file_name = attachment["url"].split("/")[-1]

            # Upload to /api/assets
            files = {'files': (file_name, io.BytesIO(file_data), 'application/octet-stream')}
            upload_res = session.post(f"{base_url}/api/assets", files=files)
            upload_res.raise_for_status()
            assets = upload_res.json()

            if not assets or "hash" not in assets[0]:
                raise ValueError("Invalid upload response: missing hash")

            file_hash = assets[0]["hash"]

            # Link the uploaded asset to the challenge
            link_payload = {"attachmentType": "Local", "fileHash": file_hash}
            r = session.post(f"{base_url}/api/edit/games/{game_id}/challenges/{cid}/attachment", json=link_payload)
            r.raise_for_status()
        except Exception as e:
            print(f"❌ Failed to duplicate Local attachment for challenge {cid}: {e}")

def duplicate_selected_challenges(src_sess, dst_sess, src_base, dst_base, full_url_base, challenges, new_game_id):
    for ch in challenges:
        try:
            full = fetch_challenge_config(src_sess, src_base, ch["game_id"], ch["id"])
            created = create_challenge_minimal(dst_sess, dst_base, new_game_id, full, ch)
            update_challenge(dst_sess, dst_base, new_game_id, created["id"], full)
            if full.get("flags"):
                duplicate_flags(dst_sess, dst_base, new_game_id, created["id"], full["flags"])
            if full.get("attachment"):
                duplicate_attachment(dst_sess, dst_base, full_url_base, new_game_id, created["id"], full["attachment"])
            print(f"✅ Cloned: {created['title']}")
        except Exception as e:
            print(f"❌ Failed to clone challenge {ch['id']}: {e}")


def sanitize_filename(name):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())

def export_game_prompt(session, base_url):
    games = fetch_games(session, base_url)
    if not games:
        print("❌ No games available.")
        return

    print("\n📚 Available Games:")
    games.sort(key=lambda g: g["id"])
    for g in games:
        print(f"{g['id']:>3} | {g['title']}")
    
    gid = input("\n🎯 Enter game ID to export: ").strip()
    game = next((g for g in games if str(g["id"]) == gid), None)
    if not game:
        print("❌ Invalid game ID")
        return

    chs_raw = fetch_challenges(session, base_url, game["id"])
    challenges = []
    for ch in chs_raw:
        try:
            full = fetch_challenge_config(session, base_url, game["id"], ch["id"])
            full["originalScore"] = full.get("originalScore", ch.get("score", 0))
            full["game_id"] = game["id"]
            challenges.append(full)
        except Exception as e:
            print(f"⚠️ Failed to fetch full config for challenge {ch['id']}: {e}")

    if not challenges:
        print("⚠️ No challenges found.")
        return

    print("\n📦 Available Challenges:")
    for ch in challenges:
        print(f"{ch['id']:>3} | [{ch.get('category', '-')}] {ch['title']} ({ch.get('originalScore', 0)} pts)")

    ids = input("\n🔢 Enter challenge IDs to export (comma-separated), or press Enter to export all: ").strip()

    if not ids:
        selected = challenges
    else:
        id_list = [s.strip() for s in ids.split(",")]
        selected = [ch for ch in challenges if str(ch["id"]) in id_list]
        if not selected:
            print("❌ No valid challenges selected.")
            return

    # Generate output paths
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    host = urlparse(base_url).netloc.replace(":", "-")
    safe_title = sanitize_filename(game["title"])[:40]
    base_folder = f"gzctf-backup-{timestamp}-{host}-{safe_title}"
    os.makedirs(os.path.join(base_folder, "attachments"), exist_ok=True)

    backup = {
        "game": {
            "title": game["title"],
            "summary": game.get("summary", ""),
            "inviteCode": generate_invite_code()
        },
        "challenges": []
    }

    for ch in selected:
        backup_ch = {
            k: ch.get(k) for k in [
                "title", "category", "type", "content", "flagTemplate",
                "originalScore", "minScoreRate", "difficulty", "containerImage",
                "memoryLimit", "cpuCount", "storageLimit", "containerExposePort",
                "enableTrafficCapture", "disableBloodBonus", "hints"
            ]
        }
        backup_ch["flags"] = ch.get("flags", [])

        att = ch.get("attachment")
        if att and att.get("url"):
            if att.get("type") == "Local":
                filename = att["url"].split("/")[-1]
                download_url = base_url + att["url"]
                try:
                    res = session.get(download_url)
                    res.raise_for_status()
                    with open(os.path.join(base_folder, "attachments", filename), "wb") as f:
                        f.write(res.content)
                    backup_ch["attachment"] = {"type": "Local", "filename": filename}
                    print(f"📎 Saved attachment: {filename}")
                except Exception as e:
                    print(f"⚠️ Failed to download attachment for {ch['title']}: {e}")
            elif att.get("type") == "Remote":
                backup_ch["attachment"] = {"type": "Remote", "url": att["url"]}

        backup["challenges"].append(backup_ch)

    backup_path = os.path.join(base_folder, "backup.json")
    with open(backup_path, "w") as f:
        json.dump(backup, f, indent=2)
    
    print(f"\n✅ Exported backup to {backup_path}")

def import_game_from_backup(session, base_url, backup_path):
    import json

    if not os.path.exists(backup_path):
        print(f"❌ Backup file not found: {backup_path}")
        return

    backup_dir = os.path.dirname(backup_path)
    with open(backup_path, "r") as f:
        backup = json.load(f)

    game_meta = backup.get("game", {})
    title = game_meta.get("title", "Restored Game")
    invite_code = game_meta.get("inviteCode")

    print(f"\n📥 Importing game: {title}")
    new_game = create_game(session, base_url, title + " (Imported)", invite_code)
    print(f"✅ Created game: {new_game['title']} (ID: {new_game['id']})")

    for ch in backup.get("challenges", []):
        try:
            score = ch.get("originalScore", 100)
            ch_minimal = {
                "title": ch.get("title"),
                "category": ch.get("category", "Misc"),
                "type": ch.get("type", "StaticAttachment"),
                "isEnabled": False,
                "score": score,
                "minScore": score,
                "originalScore": score
            }

            created = session.post(
                f"{base_url}/api/edit/games/{new_game['id']}/challenges", json=ch_minimal
            )
            created.raise_for_status()
            ch_id = created.json()["id"]

            # Update challenge with full metadata
            patch_fields = {
                k: ch.get(k) for k in [
                    "title", "content", "flagTemplate", "category", "hints", "fileName",
                    "containerImage", "memoryLimit", "cpuCount", "storageLimit",
                    "containerExposePort", "enableTrafficCapture", "disableBloodBonus",
                    "originalScore", "minScoreRate", "difficulty"
                ] if ch.get(k) is not None
            }

            session.put(f"{base_url}/api/edit/games/{new_game['id']}/challenges/{ch_id}", json=patch_fields)

            # Restore flags
            if ch.get("flags"):
                flags = [{"flag": f["flag"]} for f in ch["flags"]]
                session.post(
                    f"{base_url}/api/edit/games/{new_game['id']}/challenges/{ch_id}/flags",
                    json=flags
                )

            # Restore attachment
            att = ch.get("attachment")
            if att:
                if att.get("type") == "Remote":
                    session.post(
                        f"{base_url}/api/edit/games/{new_game['id']}/challenges/{ch_id}/attachment",
                        json={"attachmentType": "Remote", "remoteUrl": att["url"]}
                    )
                elif att.get("type") == "Local":
                    filename = att["filename"]
                    full_path = os.path.join(backup_dir, "attachments", filename)
                    if os.path.exists(full_path):
                        with open(full_path, "rb") as f:
                            files = {"files": (filename, f, "application/octet-stream")}
                            upload_res = session.post(f"{base_url}/api/assets", files=files)
                            upload_res.raise_for_status()
                            asset = upload_res.json()[0]
                            session.post(
                                f"{base_url}/api/edit/games/{new_game['id']}/challenges/{ch_id}/attachment",
                                json={"attachmentType": "Local", "fileHash": asset["hash"]}
                            )
                    else:
                        print(f"⚠️ Attachment file not found: {full_path}")

            print(f"✅ Imported challenge: {ch['title']}")

        except Exception as e:
            print(f"❌ Failed to import challenge {ch.get('title', '???')}: {e}")

def main():
    parser = argparse.ArgumentParser(description="GZCTF Cloner via Token")
    parser.add_argument("--url", required=True, help="Source base URL")
    parser.add_argument("--token", required=True, help="GZCTF_Token cookie value for source session")
    parser.add_argument("--invite-code", help="Custom invite code")
    parser.add_argument("--newgame", action="store_true", help="New game from selected challenges")
    parser.add_argument("--dst-url", help="Destination base URL")
    parser.add_argument("--dst-token", help="Destination GZCTF_Token cookie value")
    parser.add_argument("--export", action="store_true", help="Export a game's backup to JSON")
    parser.add_argument("--import", dest="import_file", help="Path to backup.json to restore a game from")

    args = parser.parse_args()

    src_url = args.url.rstrip("/")
    src_sess = session_with_token(src_url, args.token)

    dst_url = args.dst_url.rstrip("/") if args.dst_url else src_url
    dst_token = args.dst_token if args.dst_token else args.token
    dst_sess = session_with_token(dst_url, dst_token)

    games = fetch_games(src_sess, src_url)

    if args.export:
        export_game_prompt(src_sess, src_url)
        return

    if args.import_file:
        import_game_from_backup(src_sess, src_url, args.import_file)
        return

    if args.newgame:
        all_challenges = []
        for g in games:
            chs = fetch_challenges(src_sess, src_url, g["id"])
            for ch in chs:
                ch["game_title"] = g["title"]
                try:
                    full = fetch_challenge_config(src_sess, src_url, g["id"], ch["id"])
                    ch["originalScore"] = full.get("originalScore", ch.get("score", 0))
                except:
                    ch["originalScore"] = ch.get("score", 0)
                all_challenges.append(ch)

        if not all_challenges:
            print("❌ No challenges available in any games.")
            return

        all_challenges.sort(key=lambda ch: ch["id"])
        print("\n📦 Available Challenges:")
        for ch in all_challenges:
            pts = ch.get("originalScore", ch.get("score", 0))
            print(f"{ch['id']:>3} | {ch['game_title']:<3} | [{ch.get('category','-')}] {ch['title']} ({pts} pts)")

        print()
        ids = input("\n🔢 Enter challenge IDs to export (comma-separated), or press Enter to export all: ").strip()

        if not ids:
            selected = all_challenges
        else:
            selected = [ch for ch in all_challenges if str(ch["id"]) in map(str.strip, ids)]
            if not selected:
                print("❌ No valid challenges selected.")
                return

        title = input("\n🎮 New game title: ").strip()
        new_game = create_game(dst_sess, dst_url, title, args.invite_code)
        print(f"\n✅ Created game: {new_game['title']} (ID: {new_game['id']})")
        duplicate_selected_challenges(src_sess, dst_sess, src_url, dst_url, src_url, selected, new_game["id"])

    elif len(games) > 0:
        print("\n📚 Available Games:")
        games.sort(key=lambda g: g["id"])
        for g in games:
            print(f"{g['id']:>3} | {g['title']}")

        gid = input("\n🎯 Enter game ID to duplicate: ").strip()
        original = next((g for g in games if str(g["id"]) == gid), None)
        if not original:
            print("❌ Invalid game ID")
            return

        chs_raw = fetch_challenges(src_sess, src_url, original["id"])
        chs = []
        for ch in chs_raw:
            try:
                full = fetch_challenge_config(src_sess, src_url, original["id"], ch["id"])
                ch["originalScore"] = full.get("originalScore", ch.get("score", 0))
            except:
                ch["originalScore"] = ch.get("score", 0)
            chs.append(ch)
        if not chs:
            print("⚠️ No challenges found in selected game.")
            return

        print(f"\n🧩 Found {len(chs)} challenges.")
        if input("💭 Duplicate all? (y/n): ").strip().lower() != "y":
            print("\n📦 Available Challenges:")
            chs.sort(key=lambda ch: ch["id"])
            for ch in chs:
                pts = ch.get("originalScore", ch.get("score", 0))
                game_title = original.get("title", "Unknown")
                print(f"{ch['id']:>3} | {game_title:<10} | [{ch.get('category','-')}] {ch['title']} ({pts} pts)")

            ids = input("\n🔢 IDs to copy: ").split(",")
            chs = [c for c in chs if str(c["id"]) in map(str.strip, ids)]

        new_game = create_game(dst_sess, dst_url, original["title"] + " (Copy)", args.invite_code)
        print(f"\n✅ Created new hidden game: {new_game['title']} (ID: {new_game['id']})")
        duplicate_selected_challenges(src_sess, dst_sess, src_url, dst_url, src_url, chs, new_game["id"])

    else:
        print("❌ No games available.")

    print("\n🎉 Duplication complete.")

if __name__ == "__main__":
    main()
