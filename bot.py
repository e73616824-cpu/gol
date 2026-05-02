"""
⚽ Futbol Telegram Botu — Python (python-telegram-bot 21.x)
"""

import logging
import os
import random
import time
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from futbol_data import (
    get_leagues,
    get_league_by_id,
    get_team_by_id,
    search_team,
    search_player,
)
from futbol_db import (
    get_guild_data,
    save_guild_data,
    get_all_guild_ids,
    get_user_team,
    set_user_team,
    get_league_state,
    save_league_state,
    add_match_to_log,
    get_match_log,
    set_announce_channel,
    get_training_data,
    save_training_data,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Yardımcı ─────────────────────────────────────────────────────────────────

def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def now_ms() -> int:
    return int(time.time() * 1000)


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, update.effective_user.id
        )
        return member.status in ("creator", "administrator")
    except Exception:
        return False


# ─── Maç Simülasyonu ──────────────────────────────────────────────────────────

def get_team_strength(team: dict) -> float:
    players = team.get("players", [])
    if not players:
        return 70.0
    return sum(p.get("overall", 70) for p in players) / len(players)


def simulate_goals(strength: float, opp_strength: float) -> int:
    diff = strength - opp_strength
    base = 1.5 + (diff / 30)
    max_goals = max(0, round(base + random.random() * 2.5))
    return max(0, min(max_goals, 7))


def pick_scorer(players: list) -> str:
    weights = {
        "ST": 40, "LW": 25, "RW": 25, "CAM": 20,
        "CM": 10, "LB": 3, "RB": 3, "CB": 2, "GK": 0,
    }
    pool = []
    for p in players:
        w = weights.get(p.get("position", ""), 5)
        pool.extend([p["name"]] * w)
    if not pool:
        return random.choice(players)["name"]
    return random.choice(pool)


def generate_match_events(home_team: dict, away_team: dict, home_goals: int, away_goals: int) -> list:
    events = []
    used_minutes: set = set()

    def get_minute():
        while True:
            m = random.randint(1, 90)
            if m not in used_minutes:
                used_minutes.add(m)
                return m

    for _ in range(home_goals):
        events.append({
            "type": "goal",
            "team": home_team["short_name"],
            "player": pick_scorer(home_team["players"]),
            "minute": get_minute(),
        })
    for _ in range(away_goals):
        events.append({
            "type": "goal",
            "team": away_team["short_name"],
            "player": pick_scorer(away_team["players"]),
            "minute": get_minute(),
        })

    card_count = random.randint(1, 4)
    for _ in range(card_count):
        team = random.choice([home_team, away_team])
        player = random.choice(team["players"])
        events.append({
            "type": "yellow",
            "team": team["short_name"],
            "player": player["name"],
            "minute": get_minute(),
        })

    if random.random() < 0.1:
        team = random.choice([home_team, away_team])
        player = random.choice(team["players"])
        events.append({
            "type": "red",
            "team": team["short_name"],
            "player": player["name"],
            "minute": get_minute(),
        })

    return sorted(events, key=lambda e: e["minute"])


def build_match_message(home_team: dict, away_team: dict, result: dict) -> str:
    lines = [
        "⚽ <b>MAÇA BAŞLANIYOR!</b>",
        f"🏟️ <i>{esc(home_team.get('stadium', 'Ev Sahası'))}</i>\n",
    ]

    for ev in result["events"]:
        min_str = f"<code>{str(ev['minute']).rjust(2)}'</code>"
        if ev["type"] == "goal":
            emoji = "🟢" if ev["team"] == home_team["short_name"] else "🔴"
            lines.append(f"{min_str} {emoji} <b>GOL! {esc(ev['player'])}</b> ({esc(ev['team'])})")
        elif ev["type"] == "yellow":
            lines.append(f"{min_str} 🟡 Sarı kart: {esc(ev['player'])} ({esc(ev['team'])})")
        elif ev["type"] == "red":
            lines.append(f"{min_str} 🔴 Kırmızı kart: {esc(ev['player'])} ({esc(ev['team'])})")

    lines.append("\n⏱️ <b>MAÇIN SONU!</b>")
    lines.append(
        f"{home_team.get('emoji', '')} <b>{esc(home_team['short_name'])} "
        f"{result['home_goals']} – {result['away_goals']} "
        f"{esc(away_team['short_name'])}</b> {away_team.get('emoji', '')}"
    )

    if result["home_goals"] > result["away_goals"]:
        lines.append(f"🏆 <b>{esc(home_team['short_name'])}</b> kazandı!")
    elif result["away_goals"] > result["home_goals"]:
        lines.append(f"🏆 <b>{esc(away_team['short_name'])}</b> kazandı!")
    else:
        lines.append("🤝 <b>Beraberlik!</b>")

    return "\n".join(lines)


def simulate_match(home_team: dict, away_team: dict) -> dict:
    home_str = get_team_strength(home_team)
    away_str = get_team_strength(away_team)
    home_adv = 3
    home_goals = simulate_goals(home_str + home_adv, away_str)
    away_goals = simulate_goals(away_str, home_str + home_adv)
    events = generate_match_events(home_team, away_team, home_goals, away_goals)
    return {
        "home_team": home_team["short_name"],
        "away_team": away_team["short_name"],
        "home_goals": home_goals,
        "away_goals": away_goals,
        "events": events,
        "timestamp": now_ms(),
    }


# ─── Fikstür & Lig ────────────────────────────────────────────────────────────

def generate_fixtures(teams: list) -> list:
    fixtures = []
    n = len(teams)
    for rnd in range((n - 1) * 2):
        round_fixtures = []
        for i in range(n // 2):
            home = (rnd + i) % (n - 1)
            away = (n - 1 - i + rnd) % (n - 1)
            fixed_home = n - 1 if i == 0 else home
            fixed_away = away
            if rnd < n - 1:
                round_fixtures.append({"home": teams[fixed_home]["id"], "away": teams[fixed_away]["id"]})
            else:
                round_fixtures.append({"home": teams[fixed_away]["id"], "away": teams[fixed_home]["id"]})
        fixtures.append({"round": rnd + 1, "matches": round_fixtures})
    return fixtures


def init_league(guild_id: str, league_id: str) -> dict:
    league_data = get_league_by_id(league_id)
    if not league_data:
        raise ValueError(f"Lig bulunamadı: {league_id}")

    teams = league_data["teams"]
    fixtures = generate_fixtures(teams)

    standings = {}
    for team in teams:
        standings[team["id"]] = {
            "team_id": team["id"],
            "team_name": team["short_name"],
            "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "goals_for": 0, "goals_against": 0, "goal_diff": 0, "points": 0,
        }

    state = {
        "league_id": league_id,
        "league_name": league_data["name"],
        "status": "active",
        "current_round": 0,
        "total_rounds": len(fixtures),
        "fixtures": fixtures,
        "standings": standings,
        "started_at": now_ms(),
        "last_match_day": None,
    }
    save_league_state(guild_id, league_id, state)
    return state


def update_standings(standings: dict, home_id: str, away_id: str, home_goals: int, away_goals: int):
    h = standings.get(home_id)
    a = standings.get(away_id)
    if not h or not a:
        return
    h["played"] += 1
    a["played"] += 1
    h["goals_for"] += home_goals
    h["goals_against"] += away_goals
    a["goals_for"] += away_goals
    a["goals_against"] += home_goals
    h["goal_diff"] = h["goals_for"] - h["goals_against"]
    a["goal_diff"] = a["goals_for"] - a["goals_against"]
    if home_goals > away_goals:
        h["won"] += 1
        h["points"] += 3
        a["lost"] += 1
    elif away_goals > home_goals:
        a["won"] += 1
        a["points"] += 3
        h["lost"] += 1
    else:
        h["drawn"] += 1
        a["drawn"] += 1
        h["points"] += 1
        a["points"] += 1


async def simulate_match_day(context: ContextTypes.DEFAULT_TYPE):
    """Zamanlanmış görev: tüm aktif liglerde bir hafta simüle et."""
    guild_ids = get_all_guild_ids()
    for guild_id in guild_ids:
        try:
            guild_data = get_guild_data(guild_id)
            chat_id = guild_data.get("announce_channel") or guild_id

            for league_id, state in list(guild_data.get("leagues", {}).items()):
                if state.get("status") != "active":
                    continue

                next_round = state["current_round"] + 1

                if next_round > state["total_rounds"]:
                    state["status"] = "finished"
                    save_league_state(guild_id, league_id, state)
                    sorted_teams = sorted(
                        state["standings"].values(),
                        key=lambda t: (-t["points"], -t["goal_diff"])
                    )
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"🏆 <b>{esc(state['league_name'])} — ŞAMPİYON!</b>\n\n"
                            f"👑 <b>{esc(sorted_teams[0]['team_name'])}</b> şampiyon oldu!\n\n"
                            f"🥇 {esc(sorted_teams[0]['team_name'])} — {sorted_teams[0]['points']} puan\n"
                            f"🥈 {esc(sorted_teams[1]['team_name'])} — {sorted_teams[1]['points']} puan\n"
                            f"🥉 {esc(sorted_teams[2]['team_name'])} — {sorted_teams[2]['points']} puan"
                        ),
                        parse_mode="HTML",
                    )
                    continue

                league_data = get_league_by_id(league_id)
                if not league_data:
                    continue

                round_data = state["fixtures"][next_round - 1]

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"{league_data['emoji']} <b>{esc(state['league_name'])} — Hafta {next_round}</b>\n\n"
                        "Maçlar simüle ediliyor... ⚽"
                    ),
                    parse_mode="HTML",
                )

                for match in round_data["matches"]:
                    home_team = next((t for t in league_data["teams"] if t["id"] == match["home"]), None)
                    away_team = next((t for t in league_data["teams"] if t["id"] == match["away"]), None)
                    if not home_team or not away_team:
                        continue

                    result = simulate_match(home_team, away_team)
                    update_standings(state["standings"], match["home"], match["away"],
                                     result["home_goals"], result["away_goals"])
                    add_match_to_log(guild_id, {**result, "league": state["league_name"]})

                    msg = build_match_message(home_team, away_team, result)
                    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
                    import asyncio
                    await asyncio.sleep(1.5)

                state["current_round"] = next_round
                state["last_match_day"] = now_ms()
                save_league_state(guild_id, league_id, state)

                medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                top5 = sorted(
                    state["standings"].values(),
                    key=lambda t: (-t["points"], -t["goal_diff"])
                )[:5]
                stand_text = "\n".join(
                    f"{medals[i]} <b>{esc(t['team_name'])}</b> — {t['points']} puan "
                    f"({t['won']}G {t['drawn']}B {t['lost']}M)"
                    for i, t in enumerate(top5)
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"📊 <b>{esc(state['league_name'])} — Hafta {next_round} Sonrası (İlk 5)</b>\n\n{stand_text}",
                    parse_mode="HTML",
                )

        except Exception as err:
            logger.error(f"Chat {guild_id} match day error: {err}")


# ─── Komutlar ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ <b>Futbol Botuna Hoş Geldin!</b>\n\n"
        "Bir takım seçerek başla: /takimsec &lt;takım adı&gt;\n"
        "Tüm komutlar için: /yardim",
        parse_mode="HTML",
    )


async def cmd_yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ <b>Futbol Botu — Komutlar</b>\n\n"
        "👤 <b>Takım Komutları</b>\n"
        "/takim — Takım bilgisi\n"
        "/takimsec &lt;takım adı&gt; — Takım seç\n"
        "/kadro [takım adı] — Kadro görüntüle\n"
        "/takimlar [lig_id] — Tüm takımlar\n\n"
        "🏋️ <b>Antrenman</b>\n"
        "/antrenman — Antrenman listesi\n"
        "/antrenman kondisyon — Kondisyon\n"
        "/antrenman teknik — Teknik\n"
        "/antrenman taktik — Taktik\n"
        "/antrenman gucantrenman — Güç\n"
        "/antrenman atismapraktik — Atış pratiği\n\n"
        "💰 <b>Transfer</b>\n"
        "/transfer — Transfer menüsü\n"
        "/transferara &lt;oyuncu&gt; — Oyuncu ara\n"
        "/oyuncu &lt;oyuncu&gt; — Oyuncu detayı\n"
        "/pazar — Günlük transfer pazarı\n\n"
        "📊 <b>Lig &amp; Sonuçlar</b>\n"
        "/puan &lt;lig_id&gt; — Puan durumu\n"
        "/sonuclar — Son maç sonuçları\n"
        "/fikstür &lt;lig_id&gt; — Yaklaşan maçlar\n\n"
        "⚙️ <b>Admin (Yönetici)</b>\n"
        "/ligbaslat &lt;lig_id&gt; — Lig başlat\n"
        "/ligdurdur &lt;lig_id&gt; — Ligi durdur\n"
        "/ligsifirla &lt;lig_id&gt; — Ligi sıfırla\n"
        "/ligler — Aktif ligler\n"
        "/adminpuan &lt;lig_id&gt; — Puan tablosu\n"
        "/simule — Manuel maç simülasyonu\n"
        "/kanal — Duyuru kanalı ayarla\n\n"
        "🌍 <b>Lig ID'leri:</b>\n"
        "<code>premier_league</code> <code>la_liga</code> <code>bundesliga</code>\n"
        "<code>serie_a</code> <code>ligue_1</code> <code>eredivisie</code> <code>primeira_liga</code>\n\n"
        "<i>⚡ Maçlar her gün 18:00 ve 20:00'de otomatik oynanır!</i>",
        parse_mode="HTML",
    )


# ─── Takım Komutları ──────────────────────────────────────────────────────────

async def cmd_takim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guild_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    my_team_id = get_user_team(guild_id, user_id)

    if not my_team_id:
        await update.message.reply_text(
            "⚽ <b>Takım Seç</b>\n\n"
            "/takimsec &lt;takım adı&gt; — Takım seç\n"
            "/kadro [takım adı] — Kadro görüntüle\n"
            "/takimlar [lig_id] — Tüm takımlar\n\n"
            "<b>Örnek:</b>\n/takimsec Real Madrid\n/takimsec Manchester City",
            parse_mode="HTML",
        )
        return

    team_data = get_team_by_id(my_team_id)
    if not team_data:
        await update.message.reply_text("❌ Takım bulunamadı.")
        return

    team = team_data["team"]
    league = team_data["league"]
    avg_overall = round(sum(p["overall"] for p in team["players"]) / len(team["players"]))

    await update.message.reply_text(
        f"{team['emoji']} <b>{esc(team['name'])}</b>\n\n"
        f"🏆 Lig: {league['emoji']} {esc(league['name'])}\n"
        f"🏟️ Stat: {esc(team['stadium'])}\n"
        f"👔 Teknik Direktör: {esc(team['manager'])}\n"
        f"👥 Kadro: {len(team['players'])} oyuncu\n"
        f"⭐ Ort. Güç: {avg_overall} OVR\n"
        f"💰 Bütçe: €{team['budget'] // 1000000}M\n\n"
        "/kadro — Kadroyu görüntüle\n"
        "/takimsec &lt;ad&gt; — Takım değiştir",
        parse_mode="HTML",
    )


async def cmd_takimsec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guild_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    team_name = " ".join(context.args).strip() if context.args else ""

    if not team_name:
        await update.message.reply_text(
            "Kullanım: /takimsec &lt;takım adı&gt;\nÖrnek: /takimsec Manchester City",
            parse_mode="HTML",
        )
        return

    results = search_team(team_name)
    if not results:
        await update.message.reply_text(
            f"❌ <b>{esc(team_name)}</b> bulunamadı.\nTüm takımlar için: /takimlar",
            parse_mode="HTML",
        )
        return

    team = results[0]["team"]
    league = results[0]["league"]
    set_user_team(guild_id, user_id, team["id"])

    await update.message.reply_text(
        f"✅ <b>Takımın Seçildi: {team['emoji']} {esc(team['name'])}</b>\n\n"
        f"🏆 Lig: {league['emoji']} {esc(league['name'])}\n"
        f"🏟️ Stat: {esc(team['stadium'])}\n"
        f"👔 Teknik Direktör: {esc(team['manager'])}\n"
        f"👥 Kadro: {len(team['players'])} oyuncu\n"
        f"💰 Bütçe: €{team['budget'] // 1000000}M\n\n"
        "Artık antrenman yapabilir ve transfer izleyebilirsin!\n"
        "/antrenman — Antrenman yapmaya başla",
        parse_mode="HTML",
    )


async def cmd_kadro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guild_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    team_name = " ".join(context.args).strip() if context.args else ""

    if team_name:
        results = search_team(team_name)
        if not results:
            await update.message.reply_text(f"❌ <b>{esc(team_name)}</b> bulunamadı.", parse_mode="HTML")
            return
        team_data = results[0]
    else:
        my_team_id = get_user_team(guild_id, user_id)
        if not my_team_id:
            await update.message.reply_text(
                "❌ Önce bir takım seç: /takimsec &lt;takım adı&gt;", parse_mode="HTML"
            )
            return
        team_data = get_team_by_id(my_team_id)
        if not team_data:
            await update.message.reply_text("❌ Takım verisi bulunamadı.")
            return

    team = team_data["team"]
    league = team_data["league"]
    pos_order = ["GK", "CB", "RB", "LB", "DM", "CM", "CAM", "RW", "LW", "ST"]
    pos_emoji = {
        "GK": "🧤", "CB": "🛡️", "RB": "🛡️", "LB": "🛡️",
        "CM": "⚙️", "CAM": "🎯", "DM": "🛡️", "RW": "⚡", "LW": "⚡", "ST": "🔥",
    }

    by_pos: dict = {}
    for p in team["players"]:
        by_pos.setdefault(p["position"], []).append(p)

    msg = f"{team['emoji']} <b>{esc(team['name'])} — Kadro</b>\n{league['emoji']} {esc(league['name'])}\n\n"
    for pos in pos_order:
        players = by_pos.get(pos, [])
        if not players:
            continue
        msg += f"{pos_emoji.get(pos, '⚽')} <b>{pos}</b>\n"
        for p in players:
            msg += f"  • {esc(p['name'])} ({esc(p['nationality'])}) — OVR: <b>{p['overall']}</b>\n"
        msg += "\n"

    if len(msg) > 4096:
        msg = msg[:4000] + "\n<i>...(liste kısaltıldı)</i>"

    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_takimlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    league_id = context.args[0].lower() if context.args else ""

    if not league_id:
        leagues = get_leagues()
        msg = "🌍 <b>Tüm Ligler</b>\n\n"
        for lg in leagues:
            msg += f"{lg['emoji']} <b>{esc(lg['name'])}</b> — <code>{lg['id']}</code> ({len(lg['teams'])} takım)\n"
        msg += "\nDetay için: /takimlar &lt;lig_id&gt;"
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    league = get_league_by_id(league_id)
    if not league:
        await update.message.reply_text(f"❌ <b>{esc(league_id)}</b> ligi bulunamadı.", parse_mode="HTML")
        return

    msg = f"{league['emoji']} <b>{esc(league['name'])} — Takımlar</b>\n\n"
    for t in league["teams"]:
        msg += f"{t['emoji']} <b>{esc(t['name'])}</b>\n   🏟️ {esc(t['stadium'])} | 👔 {esc(t['manager'])}\n\n"

    await update.message.reply_text(msg, parse_mode="HTML")


# ─── Antrenman ────────────────────────────────────────────────────────────────

TRAINING_TYPES = {
    "kondisyon":     {"name": "Kondisyon Antrenmanı", "emoji": "🏃", "xp_base": 20, "desc": "Oyuncuların dayanıklılığını artırır"},
    "teknik":        {"name": "Teknik Antrenman",     "emoji": "⚽", "xp_base": 25, "desc": "Top kontrolü ve pas geliştirir"},
    "taktik":        {"name": "Taktik Antrenman",     "emoji": "📋", "xp_base": 30, "desc": "Savunma ve hücum organizasyonu"},
    "gucantrenman":  {"name": "Güç Antrenmanı",       "emoji": "💪", "xp_base": 20, "desc": "Fiziksel güç ve hız"},
    "atismapraktik": {"name": "Atış Pratiği",         "emoji": "🎯", "xp_base": 28, "desc": "Şut isabeti ve güç"},
}
COOLDOWN_HOURS = 6


async def cmd_antrenman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guild_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)

    my_team_id = get_user_team(guild_id, user_id)
    if not my_team_id:
        await update.message.reply_text(
            "❌ Önce takım seç: /takimsec &lt;takım adı&gt;", parse_mode="HTML"
        )
        return

    team_data = get_team_by_id(my_team_id)
    if not team_data:
        await update.message.reply_text("❌ Takım bulunamadı.")
        return

    team = team_data["team"]
    sub = context.args[0].lower() if context.args else ""

    if not sub:
        training_data = get_training_data(guild_id, user_id) or {}
        last_training = training_data.get("last_training")
        cooldown_ms = COOLDOWN_HOURS * 3600 * 1000
        can_train = not last_training or (now_ms() - last_training) > cooldown_ms

        msg = f"{team['emoji']} <b>{esc(team['name'])} — Antrenman</b>\n\n"
        for key, t in TRAINING_TYPES.items():
            msg += f"{t['emoji']} /antrenman {key}\n   <i>{t['desc']}</i>\n\n"

        if can_train:
            msg += "✅ <b>Antrenman yapabilirsin!</b>"
        else:
            remaining_ms = last_training + cooldown_ms - now_ms()
            remaining_min = remaining_ms // 60000
            msg += f"⏳ Sonraki antrenman: <b>{remaining_min} dakika</b> sonra"
        msg += f"\n📈 Toplam seans: {training_data.get('total_sessions', 0)}"
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    training_data = get_training_data(guild_id, user_id) or {"last_training": None, "total_sessions": 0, "history": []}
    cooldown_ms = COOLDOWN_HOURS * 3600 * 1000

    if training_data.get("last_training") and (now_ms() - training_data["last_training"]) < cooldown_ms:
        remaining = (training_data["last_training"] + cooldown_ms - now_ms()) // 60000
        await update.message.reply_text(
            f"⏳ Antrenman için <b>{remaining} dakika</b> daha bekle!", parse_mode="HTML"
        )
        return

    training_type = TRAINING_TYPES.get(sub)
    if not training_type:
        await update.message.reply_text("❌ Geçersiz antrenman tipi. Kullanım: /antrenman", parse_mode="HTML")
        return

    xp_gained = training_type["xp_base"] + random.randint(0, 14)
    players_boosted = random.randint(3, 7)
    featured = random.sample(team["players"], min(3, len(team["players"])))
    featured_text = "\n".join(f"• <b>{esc(p['name'])}</b> ({p['position']})" for p in featured)

    result_lines = [
        "🌟 Mükemmel antrenman! Takım harika bir form tutturdu.",
        "✅ İyi bir antrenman geçti. Oyuncular motivasyonlu.",
        "📈 Verimli çalışma. Bazı oyuncular dikkat çekti.",
        "⚽ Solid bir antrenman. Taktikler oturdu.",
        "💪 Fiziksel antrenman tamamlandı. Takım güçlendi.",
    ]
    result_text = random.choice(result_lines)

    training_data["last_training"] = now_ms()
    training_data["total_sessions"] = training_data.get("total_sessions", 0) + 1
    history = training_data.get("history", [])
    history.insert(0, {"type": sub, "xp": xp_gained, "date": now_ms()})
    training_data["history"] = history[:20]
    save_training_data(guild_id, user_id, training_data)

    await update.message.reply_text(
        f"{training_type['emoji']} <b>{esc(training_type['name'])} Tamamlandı!</b>\n\n"
        f"{result_text}\n\n"
        f"⭐ XP Kazanıldı: <b>+{xp_gained} XP</b>\n"
        f"👥 Etkilenen Oyuncu: <b>{players_boosted} oyuncu</b>\n\n"
        f"🌟 <b>Öne Çıkan Oyuncular:</b>\n{featured_text}\n\n"
        f"⏳ Sonraki antrenman: {COOLDOWN_HOURS} saat sonra",
        parse_mode="HTML",
    )


# ─── Transfer ─────────────────────────────────────────────────────────────────

def estimate_value(player: dict) -> float:
    age = player.get("age", 27)
    if age < 23:
        age_factor = 1.5
    elif age < 27:
        age_factor = 1.2
    elif age < 30:
        age_factor = 1.0
    elif age < 33:
        age_factor = 0.7
    else:
        age_factor = 0.4
    pos_mult = {
        "ST": 1.3, "CAM": 1.2, "LW": 1.2, "RW": 1.2,
        "CM": 1.0, "CB": 0.9, "RB": 0.9, "LB": 0.9, "GK": 0.8,
    }.get(player.get("position", ""), 1.0)
    raw = ((player.get("overall", 70) - 60) / 30) ** 2 * 150 * age_factor * pos_mult
    return round(max(raw, 1) * 10) / 10


def generate_market() -> list:
    leagues = get_leagues()
    all_players = []
    for league in leagues:
        for team in league["teams"]:
            for player in team["players"]:
                if 75 <= player.get("overall", 0) <= 85:
                    all_players.append({"player": player, "team": team, "league": league, "value": estimate_value(player)})
    random.shuffle(all_players)
    return all_players[:8]


async def cmd_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 <b>Transfer Sistemi</b>\n\n"
        "/transferara &lt;oyuncu adı&gt; — Oyuncu ara\n"
        "/oyuncu &lt;oyuncu adı&gt; — Oyuncu detayı\n"
        "/pazar — Günlük transfer pazarı\n\n"
        "<b>Örnekler:</b>\n/transferara Haaland\n/transferara Mbappe\n/oyuncu Vinicius",
        parse_mode="HTML",
    )


async def cmd_transferara(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip() if context.args else ""
    if not query:
        await update.message.reply_text("Kullanım: /transferara &lt;oyuncu adı&gt;", parse_mode="HTML")
        return

    results = search_player(query)
    if not results:
        await update.message.reply_text(f"❌ <b>{esc(query)}</b> için sonuç bulunamadı.", parse_mode="HTML")
        return

    shown = results[:10]
    msg = f"🔍 <b>Transfer Araması: \"{esc(query)}\"</b>\n\n"
    for r in shown:
        p = r["player"]
        val = estimate_value(p)
        msg += (
            f"<b>{esc(p['name'])}</b> | {p['position']} | OVR: {p['overall']} | "
            f"{r['team']['emoji']} {esc(r['team']['short_name'])} | 💰 €{val}M\n"
        )
    if len(results) > 10:
        msg += f"\n<i>{len(results)} sonuç bulundu, ilk 10 gösteriliyor</i>"

    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_oyuncu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip() if context.args else ""
    if not query:
        await update.message.reply_text("Kullanım: /oyuncu &lt;oyuncu adı&gt;", parse_mode="HTML")
        return

    results = search_player(query)
    if not results:
        await update.message.reply_text(f"❌ <b>{esc(query)}</b> bulunamadı.", parse_mode="HTML")
        return

    r = results[0]
    player = r["player"]
    team = r["team"]
    league = r["league"]
    value = estimate_value(player)

    await update.message.reply_text(
        f"👤 <b>{esc(player['name'])}</b>\n\n"
        f"🏃 Mevki: <b>{player['position']}</b>\n"
        f"🌍 Milliyet: {esc(player['nationality'])}\n"
        f"🎂 Yaş: {player['age']}\n"
        f"⭐ OVR: <b>{player['overall']}</b>\n"
        f"💰 Tahmini Değer: €{value}M\n"
        f"💵 Maaş: £{player['wage'] // 1000}K/hafta\n"
        f"🏟️ Mevcut Takım: {team['emoji']} {esc(team['name'])}\n"
        f"🏆 Lig: {league['emoji']} {esc(league['name'])}",
        parse_mode="HTML",
    )


async def cmd_pazar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    market = generate_market()
    msg = "💰 <b>Transfer Pazarı — Günlük Teklifler</b>\n\n"
    for item in market:
        p = item["player"]
        msg += (
            f"<b>{esc(p['name'])}</b> ({p['position']}) OVR: {p['overall']}\n"
            f"  {item['team']['emoji']} {esc(item['team']['short_name'])} | "
            f"💰 €{item['value']}M | 🌍 {esc(p['nationality'])}\n\n"
        )
    msg += "<i>Detay için: /oyuncu &lt;isim&gt;</i>"
    await update.message.reply_text(msg, parse_mode="HTML")


# ─── Lig & Sonuçlar ───────────────────────────────────────────────────────────

async def cmd_puan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guild_id = str(update.effective_chat.id)
    league_id = context.args[0].lower() if context.args else ""

    if not league_id:
        leagues = get_leagues()
        msg = "📊 <b>Puan Durumu</b>\n\nLig belirtin:\n\n"
        for lg in leagues:
            msg += f"{lg['emoji']} <code>/puan {lg['id']}</code> — {esc(lg['name'])}\n"
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    state = get_league_state(guild_id, league_id)
    if not state:
        await update.message.reply_text(
            f"❌ <b>{esc(league_id)}</b> ligi başlatılmamış.\nAdmin: /ligbaslat {league_id}",
            parse_mode="HTML",
        )
        return

    sorted_teams = sorted(
        state["standings"].values(),
        key=lambda t: (-t["points"], -t["goal_diff"])
    )
    medals = ["🥇", "🥈", "🥉"]
    league_data = get_league_by_id(league_id)

    msg = f"{league_data['emoji'] if league_data else '🏆'} <b>{esc(state['league_name'])} — Puan Durumu</b>\n"
    msg += f"📅 Hafta {state['current_round']}/{state['total_rounds']}\n\n"

    for i, t in enumerate(sorted_teams):
        pos = medals[i] if i < 3 else f"{i + 1}."
        gd = f"+{t['goal_diff']}" if t["goal_diff"] >= 0 else str(t["goal_diff"])
        msg += f"{pos} <b>{esc(t['team_name'])}</b> — <b>{t['points']}P</b>\n"
        msg += f"    {t['played']}O {t['won']}G {t['drawn']}B {t['lost']}M | {t['goals_for']}:{t['goals_against']} ({gd})\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_sonuclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guild_id = str(update.effective_chat.id)
    log = get_match_log(guild_id, 10)
    if not log:
        await update.message.reply_text("❌ Henüz hiç maç oynanmadı.")
        return

    msg = "📋 <b>Son Maç Sonuçları</b>\n\n"
    for m in log:
        from datetime import datetime
        date = datetime.fromtimestamp(m["timestamp"] / 1000).strftime("%d.%m.%Y")
        if m["home_goals"] > m["away_goals"]:
            winner = "›"
        elif m["away_goals"] > m["home_goals"]:
            winner = "‹"
        else:
            winner = "="
        msg += f"<b>{esc(m['home_team'])} {m['home_goals']}–{m['away_goals']} {esc(m['away_team'])}</b> {winner}  <i>{date}</i>\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_fikstür(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guild_id = str(update.effective_chat.id)
    league_id = context.args[0].lower() if context.args else ""

    if not league_id:
        leagues = get_leagues()
        msg = "📅 <b>Fikstür</b>\n\nLig belirtin:\n\n"
        for lg in leagues:
            msg += f"{lg['emoji']} <code>/fikstür {lg['id']}</code> — {esc(lg['name'])}\n"
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    state = get_league_state(guild_id, league_id)
    if not state:
        await update.message.reply_text(f"❌ <b>{esc(league_id)}</b> ligi başlatılmamış.", parse_mode="HTML")
        return

    league_data = get_league_by_id(league_id)
    if not league_data:
        await update.message.reply_text("❌ Lig verisi bulunamadı.")
        return

    next_round = state["current_round"] + 1
    show_rounds = state["fixtures"][next_round - 1: next_round + 2]

    if not show_rounds:
        await update.message.reply_text("🏁 Fikstür tamamlandı, maç kalmadı.")
        return

    msg = f"{league_data['emoji']} <b>{esc(state['league_name'])} — Fikstür</b>\n"
    msg += f"Mevcut Hafta: {state['current_round']}/{state['total_rounds']}\n\n"

    for rnd in show_rounds:
        is_current = rnd["round"] == next_round
        msg += f"<b>📅 Hafta {rnd['round']}{' (Sonraki)' if is_current else ''}</b>\n"
        for match in rnd["matches"]:
            home_team = next((t for t in league_data["teams"] if t["id"] == match["home"]), None)
            away_team = next((t for t in league_data["teams"] if t["id"] == match["away"]), None)
            if not home_team or not away_team:
                continue
            msg += f"  {home_team['emoji']} {esc(home_team['short_name'])} vs {esc(away_team['short_name'])} {away_team['emoji']}\n"
        msg += "\n"

    await update.message.reply_text(msg, parse_mode="HTML")


# ─── Admin Komutları ──────────────────────────────────────────────────────────

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Bu komut için yönetici yetkisi gerekli!")
        return

    await update.message.reply_text(
        "⚙️ <b>Admin Komutları</b>\n\n"
        "/ligbaslat &lt;lig_id&gt; — Lig başlat\n"
        "/ligdurdur &lt;lig_id&gt; — Ligi durdur\n"
        "/ligsifirla &lt;lig_id&gt; — Ligi sıfırla\n"
        "/ligler — Aktif ligleri göster\n"
        "/adminpuan &lt;lig_id&gt; — Puan durumu\n"
        "/simule [lig_id] — Manuel maç simülasyonu\n"
        "/kanal — Bu kanalı duyuru kanalı yap\n\n"
        "<b>Lig ID'leri:</b>\n"
        "<code>premier_league</code> | <code>la_liga</code> | <code>bundesliga</code>\n"
        "<code>serie_a</code> | <code>ligue_1</code> | <code>eredivisie</code> | <code>primeira_liga</code>",
        parse_mode="HTML",
    )


async def cmd_ligbaslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
        return

    guild_id = str(update.effective_chat.id)
    league_id = context.args[0].lower() if context.args else ""

    if not league_id:
        leagues = get_leagues()
        msg = "📋 <b>Mevcut Ligler:</b>\n\n"
        for lg in leagues:
            msg += f"{lg['emoji']} <code>{lg['id']}</code> — {esc(lg['name'])}\n"
        msg += "\nKullanım: /ligbaslat &lt;lig_id&gt;"
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    existing = get_league_state(guild_id, league_id)
    if existing and existing.get("status") == "active":
        await update.message.reply_text(
            f"⚠️ <b>{esc(existing['league_name'])}</b> zaten aktif!\nDurdurmak için: /ligdurdur {league_id}",
            parse_mode="HTML",
        )
        return

    try:
        state = init_league(guild_id, league_id)
        league_data = get_league_by_id(league_id)
        team_list = "\n".join(f"{t['emoji']} {t['name']}" for t in league_data["teams"])

        await update.message.reply_text(
            f"✅ <b>{league_data['emoji']} {esc(state['league_name'])} Başlatıldı!</b>\n\n"
            f"🏟️ Takım Sayısı: {len(league_data['teams'])} takım\n"
            f"📅 Toplam Hafta: {state['total_rounds']} hafta\n"
            f"⚡ Otomatik Maçlar: Her gün 18:00 ve 20:00 (TR)\n\n"
            f"<b>Takımlar:</b>\n{team_list}\n\n"
            "📢 Duyuruları bu kanala göndermek için: /kanal",
            parse_mode="HTML",
        )
    except ValueError as err:
        await update.message.reply_text(f"❌ Hata: {err}")


async def cmd_ligdurdur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
        return

    guild_id = str(update.effective_chat.id)
    league_id = context.args[0].lower() if context.args else ""

    if not league_id:
        await update.message.reply_text("Kullanım: /ligdurdur &lt;lig_id&gt;", parse_mode="HTML")
        return

    state = get_league_state(guild_id, league_id)
    if not state:
        await update.message.reply_text("❌ Bu lig bulunamadı veya başlatılmadı.")
        return

    state["status"] = "stopped"
    save_league_state(guild_id, league_id, state)
    await update.message.reply_text(f"⏹️ <b>{esc(state['league_name'])}</b> durduruldu.", parse_mode="HTML")


async def cmd_ligsifirla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
        return

    guild_id = str(update.effective_chat.id)
    league_id = context.args[0].lower() if context.args else ""

    if not league_id:
        await update.message.reply_text("Kullanım: /ligsifirla &lt;lig_id&gt;", parse_mode="HTML")
        return

    data = get_guild_data(guild_id)
    if league_id in data.get("leagues", {}):
        del data["leagues"][league_id]
        save_guild_data(guild_id, data)
        await update.message.reply_text(f"🔄 <b>{esc(league_id)}</b> ligi sıfırlandı.", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Lig bulunamadı.")


async def cmd_ligler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
        return

    guild_id = str(update.effective_chat.id)
    data = get_guild_data(guild_id)
    active_leagues = list(data.get("leagues", {}).values())

    if not active_leagues:
        leagues = get_leagues()
        msg = "📋 <b>Başlatılabilir Ligler:</b>\n\n"
        for lg in leagues:
            msg += f"{lg['emoji']} <code>{lg['id']}</code> — {esc(lg['name'])} ({len(lg['teams'])} takım)\n"
        msg += "\n/ligbaslat &lt;id&gt; ile başlatabilirsiniz."
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    msg = "🏆 <b>Aktif Ligler</b>\n\n"
    for state in active_leagues:
        status_emoji = "🟢" if state["status"] == "active" else ("🔴" if state["status"] == "stopped" else "🏁")
        msg += f"{status_emoji} <b>{esc(state['league_name'])}</b>\n"
        msg += f"   Durum: {state['status']} | Hafta: {state['current_round']}/{state['total_rounds']}\n\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_adminpuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
        return

    guild_id = str(update.effective_chat.id)
    league_id = context.args[0].lower() if context.args else ""

    if not league_id:
        await update.message.reply_text("Kullanım: /adminpuan &lt;lig_id&gt;", parse_mode="HTML")
        return

    state = get_league_state(guild_id, league_id)
    if not state:
        await update.message.reply_text("❌ Bu lig bulunamadı.")
        return

    sorted_teams = sorted(
        state["standings"].values(),
        key=lambda t: (-t["points"], -t["goal_diff"])
    )
    medals = ["🥇", "🥈", "🥉"]
    msg = f"📊 <b>{esc(state['league_name'])} — Puan Durumu</b>\nHafta {state['current_round']}/{state['total_rounds']}\n\n"

    for i, t in enumerate(sorted_teams):
        pos = medals[i] if i < 3 else f"<b>{i + 1}.</b>"
        gd = f"+{t['goal_diff']}" if t["goal_diff"] >= 0 else str(t["goal_diff"])
        msg += (
            f"{pos} <b>{esc(t['team_name'])}</b> — {t['points']}P | "
            f"{t['played']}O {t['won']}G {t['drawn']}B {t['lost']}M | "
            f"{t['goals_for']}:{t['goals_against']} ({gd})\n"
        )

    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_simule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
        return

    await update.message.reply_text("⏳ Maç simülasyonu başlıyor...")
    try:
        await simulate_match_day(context)
    except Exception as err:
        await update.message.reply_text(f"❌ Simülasyon hatası: {err}")


async def cmd_kanal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
        return

    guild_id = str(update.effective_chat.id)
    set_announce_channel(guild_id, guild_id)
    await update.message.reply_text(
        "✅ Bu kanal/grup duyuru kanalı olarak ayarlandı!\nMaç sonuçları buraya gönderilecek."
    )


# ─── Ana Giriş ────────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("❌ TELEGRAM_TOKEN bulunamadı! Railway ortam değişkenlerini kontrol et.")
        raise SystemExit(1)

    app = Application.builder().token(token).build()

    # Komutları kaydet
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("yardim", cmd_yardim))

    # Takım
    app.add_handler(CommandHandler("takim", cmd_takim))
    app.add_handler(CommandHandler("takimsec", cmd_takimsec))
    app.add_handler(CommandHandler("kadro", cmd_kadro))
    app.add_handler(CommandHandler("takimlar", cmd_takimlar))

    # Antrenman
    app.add_handler(CommandHandler("antrenman", cmd_antrenman))

    # Transfer
    app.add_handler(CommandHandler("transfer", cmd_transfer))
    app.add_handler(CommandHandler("transferara", cmd_transferara))
    app.add_handler(CommandHandler("oyuncu", cmd_oyuncu))
    app.add_handler(CommandHandler("pazar", cmd_pazar))

    # Lig & Sonuçlar
    app.add_handler(CommandHandler("puan", cmd_puan))
    app.add_handler(CommandHandler("sonuclar", cmd_sonuclar))
    app.add_handler(CommandHandler(["fikstür", "fikstur"], cmd_fikstür))

    # Admin
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("ligbaslat", cmd_ligbaslat))
    app.add_handler(CommandHandler("ligdurdur", cmd_ligdurdur))
    app.add_handler(CommandHandler("ligsifirla", cmd_ligsifirla))
    app.add_handler(CommandHandler("ligler", cmd_ligler))
    app.add_handler(CommandHandler("adminpuan", cmd_adminpuan))
    app.add_handler(CommandHandler("simule", cmd_simule))
    app.add_handler(CommandHandler("kanal", cmd_kanal))

    # Zamanlanmış görevler — Türkiye saati UTC+3
    # 18:00 TR = 15:00 UTC, 20:00 TR = 17:00 UTC
    job_queue = app.job_queue
    job_queue.run_daily(simulate_match_day, time=datetime(2000, 1, 1, 15, 0, tzinfo=timezone.utc).timetz())
    job_queue.run_daily(simulate_match_day, time=datetime(2000, 1, 1, 17, 0, tzinfo=timezone.utc).timetz())

    logger.info("✅ Bot başlatıldı!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
