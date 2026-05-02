"""
Veritabanı işlemleri — JSON dosya tabanlı kalıcı depolama.
Her chat için ayrı bir guild_<chat_id>.json dosyası kullanılır.
"""

import json
import os
import time
from pathlib import Path

DATA_DIR = Path("data")


def _ensure_dir():
    DATA_DIR.mkdir(exist_ok=True)


def _guild_file(guild_id: str) -> Path:
    return DATA_DIR / f"guild_{guild_id}.json"


def get_guild_data(guild_id: str) -> dict:
    _ensure_dir()
    path = _guild_file(guild_id)
    if not path.exists():
        default = {
            "guild_id": guild_id,
            "leagues": {},
            "user_teams": {},
            "transfers": [],
            "training_sessions": {},
            "match_log": [],
            "announce_channel": None,
            "created_at": int(time.time() * 1000),
        }
        path.write_text(json.dumps(default, indent=2, ensure_ascii=False))
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_guild_data(guild_id: str, data: dict):
    _ensure_dir()
    _guild_file(guild_id).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_all_guild_ids() -> list[str]:
    _ensure_dir()
    return [
        f.stem.replace("guild_", "")
        for f in DATA_DIR.iterdir()
        if f.name.startswith("guild_") and f.suffix == ".json"
    ]


# ─── Kullanıcı Takımı ─────────────────────────────────────────────────────────

def get_user_team(guild_id: str, user_id: str) -> str | None:
    data = get_guild_data(guild_id)
    return data.get("user_teams", {}).get(user_id)


def set_user_team(guild_id: str, user_id: str, team_id: str):
    data = get_guild_data(guild_id)
    data.setdefault("user_teams", {})[user_id] = team_id
    save_guild_data(guild_id, data)


# ─── Lig Durumu ───────────────────────────────────────────────────────────────

def get_league_state(guild_id: str, league_id: str) -> dict | None:
    data = get_guild_data(guild_id)
    return data.get("leagues", {}).get(league_id)


def save_league_state(guild_id: str, league_id: str, state: dict):
    data = get_guild_data(guild_id)
    data.setdefault("leagues", {})[league_id] = state
    save_guild_data(guild_id, data)


# ─── Maç Logu ─────────────────────────────────────────────────────────────────

def add_match_to_log(guild_id: str, match_result: dict):
    data = get_guild_data(guild_id)
    log = data.setdefault("match_log", [])
    log.insert(0, match_result)
    if len(log) > 100:
        data["match_log"] = log[:100]
    save_guild_data(guild_id, data)


def get_match_log(guild_id: str, limit: int = 20) -> list:
    data = get_guild_data(guild_id)
    return data.get("match_log", [])[:limit]


# ─── Duyuru Kanalı ────────────────────────────────────────────────────────────

def set_announce_channel(guild_id: str, channel_id: str):
    data = get_guild_data(guild_id)
    data["announce_channel"] = channel_id
    save_guild_data(guild_id, data)


def get_announce_channel(guild_id: str) -> str | None:
    data = get_guild_data(guild_id)
    return data.get("announce_channel")


# ─── Antrenman ────────────────────────────────────────────────────────────────

def get_training_data(guild_id: str, user_id: str) -> dict | None:
    data = get_guild_data(guild_id)
    return data.get("training_sessions", {}).get(user_id)


def save_training_data(guild_id: str, user_id: str, training_data: dict):
    data = get_guild_data(guild_id)
    data.setdefault("training_sessions", {})[user_id] = training_data
    save_guild_data(guild_id, data)
