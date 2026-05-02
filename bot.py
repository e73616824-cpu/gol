"""
Ana Telegram bot dosyası.
Komutlar: /start, /lig_olustur, /takim_sec, /takimim,
          /lig_tablosu, /hafta_oyna, /fikstur
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from futbol_db import (
    init_db,
    lig_olustur,
    lig_getir,
    aktif_ligler,
    takim_sec,
    kullanici_takimi,
    hafta_oyna,
    puan_tablosu_getir,
    fikstur_getir,
)
from futbol_data import LIGLER, get_lig, get_takim

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Yardımcı ─────────────────────────────────────────────────────────────────

def chat_id(update: Update) -> str:
    return str(update.effective_chat.id)


def user_id(update: Update) -> str:
    return str(update.effective_user.id)


def _mac_mesaji(sonuc: dict) -> str:
    ev = sonuc["ev_takim"]
    dep = sonuc["dep_takim"]
    satirlar = [
        f"⚽ <b>MAÇ BAŞLIYOR!</b>",
        f"🏟️ <i>{ev.get('stadyum', 'Ev Sahası')}</i>\n",
    ]

    for olay in sonuc["olaylar"]:
        dk = f"<code>{str(olay['dakika']).rjust(2)}'</code>"
        if olay["tip"] == "gol":
            emoji = "🟢" if olay["takim"] == ev["kisaad"] else "🔴"
            satirlar.append(f"{dk} {emoji} <b>GOL! {olay['oyuncu']}</b> ({olay['takim']})")
        elif olay["tip"] == "sari":
            satirlar.append(f"{dk} 🟡 Sarı kart: {olay['oyuncu']} ({olay['takim']})")
        elif olay["tip"] == "kirmizi":
            satirlar.append(f"{dk} 🔴 Kırmızı kart: {olay['oyuncu']} ({olay['takim']})")

    ev_gol = sonuc["ev_gol"]
    dep_gol = sonuc["dep_gol"]
    satirlar.append(f"\n⏱️ <b>MAÇIN SONU!</b>")
    satirlar.append(
        f"{ev.get('emoji', '')} <b>{ev['kisaad']} {ev_gol} – {dep_gol} {dep['kisaad']}</b> {dep.get('emoji', '')}"
    )

    if ev_gol > dep_gol:
        satirlar.append(f"🏆 <b>{ev['kisaad']}</b> kazandı!")
    elif dep_gol > ev_gol:
        satirlar.append(f"🏆 <b>{dep['kisaad']}</b> kazandı!")
    else:
        satirlar.append("🤝 <b>Beraberlik!</b>")

    return "\n".join(satirlar)


def _puan_tablosu_mesaji(tablo: list[dict], lig_adi: str, hafta: int, toplam: int) -> str:
    madalyalar = ["🥇", "🥈", "🥉"]
    satirlar = [f"📊 <b>{lig_adi} — Puan Durumu</b>", f"Hafta {hafta}/{toplam}\n"]
    for i, t in enumerate(tablo):
        pos = madalyalar[i] if i < 3 else f"<b>{i + 1}.</b>"
        av = f"+{t['averaj']}" if t["averaj"] >= 0 else str(t["averaj"])
        satirlar.append(
            f"{pos} {t.get('emoji', '')} <b>{t['takim_adi']}</b> — "
            f"{t['puan']}P | {t['oynadigi']}O "
            f"{t['galibiyet']}G {t['beraberlik']}B {t['maglubiyet']}M | "
            f"{t['attigi']}:{t['yedigi']} ({av})"
        )
    return "\n".join(satirlar)


# ─── Komutlar ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(
        "⚽ <b>Futbol Botuna Hoş Geldin!</b>\n\n"
        "Bu bot ile kendi futbol ligi simülasyonunu yönetebilirsin.\n\n"
        "<b>Komutlar:</b>\n"
        "/lig_olustur — Yeni bir lig başlat\n"
        "/takim_sec — Bir takım seç\n"
        "/takimim — Seçtiğin takımı gör\n"
        "/lig_tablosu — Puan durumunu gör\n"
        "/hafta_oyna — Bir sonraki haftayı oyna\n"
        "/fikstur — Fikstürü gör\n"
    )


async def lig_olustur_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lig seçim menüsü göster."""
    klavye = []
    for lig_id, lig in LIGLER.items():
        klavye.append([
            InlineKeyboardButton(
                f"{lig['emoji']} {lig['ad']} ({len(lig['takimlar'])} takım)",
                callback_data=f"lig_sec:{lig_id}",
            )
        ])

    await update.message.reply_html(
        "🏆 <b>Hangi ligi başlatmak istiyorsun?</b>",
        reply_markup=InlineKeyboardMarkup(klavye),
    )


async def lig_sec_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    lig_id = query.data.split(":")[1]
    cid = str(query.message.chat.id)

    try:
        sonuc = lig_olustur(cid, lig_id)
        lig_verisi = get_lig(lig_id)
        takim_listesi = "\n".join(
            f"{t['emoji']} {t['ad']}" for t in lig_verisi["takimlar"]
        )
        await query.edit_message_text(
            f"✅ <b>{lig_verisi['emoji']} {sonuc['lig_adi']} Başlatıldı!</b>\n\n"
            f"📅 Toplam Hafta: {sonuc['toplam_hafta']}\n\n"
            f"<b>Takımlar:</b>\n{takim_listesi}\n\n"
            f"Takım seçmek için: /takim_sec",
            parse_mode="HTML",
        )
    except ValueError as e:
        await query.edit_message_text(f"❌ {e}")


async def takim_sec_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Aktif liglerdeki takımları listele."""
    cid = chat_id(update)
    ligler = aktif_ligler(cid)

    if not ligler:
        await update.message.reply_html(
            "❌ Aktif lig yok. Önce /lig_olustur komutunu kullan."
        )
        return

    klavye = []
    for lig in ligler:
        lig_verisi = get_lig(lig["lig_id"])
        if not lig_verisi:
            continue
        for takim in lig_verisi["takimlar"]:
            klavye.append([
                InlineKeyboardButton(
                    f"{takim['emoji']} {takim['ad']} ({lig_verisi['emoji']} {lig['lig_adi']})",
                    callback_data=f"takim_sec:{lig['lig_id']}:{takim['id']}",
                )
            ])

    await update.message.reply_html(
        "⚽ <b>Hangi takımı seçmek istiyorsun?</b>",
        reply_markup=InlineKeyboardMarkup(klavye),
    )


async def takim_sec_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, lig_id, takim_id = query.data.split(":")
    uid = str(query.from_user.id)
    cid = str(query.message.chat.id)

    takim = get_takim(lig_id, takim_id)
    lig_verisi = get_lig(lig_id)
    if not takim or not lig_verisi:
        await query.edit_message_text("❌ Takım bulunamadı.")
        return

    takim_sec(uid, cid, lig_id, takim_id)

    oyuncu_listesi = "\n".join(
        f"  • {o['ad']} ({o['mevki']}) — {o['overall']} OVR"
        for o in takim["oyuncular"]
    )
    await query.edit_message_text(
        f"✅ <b>{takim['emoji']} {takim['ad']}</b> seçildi!\n"
        f"🏆 Lig: {lig_verisi['emoji']} {lig_verisi['ad']}\n"
        f"🏟️ Stadyum: {takim['stadyum']}\n\n"
        f"<b>Kadro:</b>\n{oyuncu_listesi}",
        parse_mode="HTML",
    )


async def takimim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = chat_id(update)
    uid = user_id(update)
    ligler = aktif_ligler(cid)

    if not ligler:
        await update.message.reply_html("❌ Aktif lig yok.")
        return

    mesajlar = []
    for lig in ligler:
        takim_id = kullanici_takimi(uid, cid, lig["lig_id"])
        if not takim_id:
            continue
        takim = get_takim(lig["lig_id"], takim_id)
        lig_verisi = get_lig(lig["lig_id"])
        if not takim:
            continue
        oyuncu_listesi = "\n".join(
            f"  • {o['ad']} ({o['mevki']}) — {o['overall']} OVR"
            for o in takim["oyuncular"]
        )
        mesajlar.append(
            f"{takim['emoji']} <b>{takim['ad']}</b>\n"
            f"🏆 {lig_verisi['emoji']} {lig['lig_adi']}\n"
            f"🏟️ {takim['stadyum']}\n\n"
            f"<b>Kadro:</b>\n{oyuncu_listesi}"
        )

    if not mesajlar:
        await update.message.reply_html(
            "❌ Henüz bir takım seçmedin. /takim_sec komutunu kullan."
        )
        return

    await update.message.reply_html("\n\n".join(mesajlar))


async def lig_tablosu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = chat_id(update)
    ligler = aktif_ligler(cid)

    # Biten ligleri de dahil et
    from futbol_db import get_conn
    import json
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM liglar WHERE chat_id=?", (cid,)
        ).fetchall()

    if not rows:
        await update.message.reply_html("❌ Henüz lig oluşturulmadı. /lig_olustur komutunu kullan.")
        return

    for row in rows:
        d = dict(row)
        tablo = puan_tablosu_getir(cid, d["lig_id"])
        if not tablo:
            continue
        mesaj = _puan_tablosu_mesaji(tablo, d["lig_adi"], d["mevcut_hafta"], d["toplam_hafta"])
        await update.message.reply_html(mesaj)


async def hafta_oyna_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = chat_id(update)
    ligler = aktif_ligler(cid)

    if not ligler:
        await update.message.reply_html(
            "❌ Aktif lig yok. /lig_olustur ile bir lig başlat."
        )
        return

    if len(ligler) == 1:
        await _hafta_oyna_lig(update, cid, ligler[0]["lig_id"])
        return

    # Birden fazla lig varsa seçim menüsü
    klavye = [
        [InlineKeyboardButton(
            f"{get_lig(l['lig_id'])['emoji']} {l['lig_adi']}",
            callback_data=f"hafta_oyna:{l['lig_id']}",
        )]
        for l in ligler
    ]
    await update.message.reply_html(
        "⚽ <b>Hangi ligde hafta oynamak istiyorsun?</b>",
        reply_markup=InlineKeyboardMarkup(klavye),
    )


async def hafta_oyna_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lig_id = query.data.split(":")[1]
    cid = str(query.message.chat.id)
    await query.delete_message()
    await _hafta_oyna_lig_chat(context, cid, lig_id, query.message.chat.id)


async def _hafta_oyna_lig(update: Update, cid: str, lig_id: str) -> None:
    """update.message üzerinden hafta oynat."""
    await update.message.reply_html("⏳ Maçlar simüle ediliyor...")
    try:
        sonuc = hafta_oyna(cid, lig_id)
    except ValueError as e:
        await update.message.reply_html(f"❌ {e}")
        return

    lig_verisi = get_lig(lig_id)
    await update.message.reply_html(
        f"{lig_verisi['emoji']} <b>{lig_verisi['ad']} — Hafta {sonuc['hafta']}</b>\n"
        f"Maçlar başlıyor... ⚽"
    )

    for mac_sonucu in sonuc["maclar"]:
        await update.message.reply_html(_mac_mesaji(mac_sonucu))

    tablo = sorted(
        sonuc["puan_tablosu"].values(),
        key=lambda x: (-x["puan"], -x["averaj"], -x["attigi"]),
    )
    await update.message.reply_html(
        _puan_tablosu_mesaji(tablo, lig_verisi["ad"], sonuc["hafta"], sonuc["toplam_hafta"])
    )

    if sonuc["bitti"]:
        sampiyion = tablo[0]
        await update.message.reply_html(
            f"🏆 <b>{lig_verisi['emoji']} {lig_verisi['ad']} SONA ERDİ!</b>\n\n"
            f"👑 Şampiyon: <b>{sampiyion['emoji']} {sampiyion['takim_adi']}</b> "
            f"— {sampiyion['puan']} puan\n\n"
            f"🥇 {tablo[0]['takim_adi']} — {tablo[0]['puan']}P\n"
            + (f"🥈 {tablo[1]['takim_adi']} — {tablo[1]['puan']}P\n" if len(tablo) > 1 else "")
            + (f"🥉 {tablo[2]['takim_adi']} — {tablo[2]['puan']}P" if len(tablo) > 2 else "")
        )


async def _hafta_oyna_lig_chat(context: ContextTypes.DEFAULT_TYPE,
                                cid: str, lig_id: str, chat_id_int: int) -> None:
    """Callback üzerinden hafta oynat (bot.send_message kullanır)."""
    try:
        sonuc = hafta_oyna(cid, lig_id)
    except ValueError as e:
        await context.bot.send_message(chat_id_int, f"❌ {e}", parse_mode="HTML")
        return

    lig_verisi = get_lig(lig_id)
    await context.bot.send_message(
        chat_id_int,
        f"{lig_verisi['emoji']} <b>{lig_verisi['ad']} — Hafta {sonuc['hafta']}</b>\nMaçlar başlıyor... ⚽",
        parse_mode="HTML",
    )

    for mac_sonucu in sonuc["maclar"]:
        await context.bot.send_message(chat_id_int, _mac_mesaji(mac_sonucu), parse_mode="HTML")

    tablo = sorted(
        sonuc["puan_tablosu"].values(),
        key=lambda x: (-x["puan"], -x["averaj"], -x["attigi"]),
    )
    await context.bot.send_message(
        chat_id_int,
        _puan_tablosu_mesaji(tablo, lig_verisi["ad"], sonuc["hafta"], sonuc["toplam_hafta"]),
        parse_mode="HTML",
    )

    if sonuc["bitti"]:
        sampiyion = tablo[0]
        await context.bot.send_message(
            chat_id_int,
            f"🏆 <b>{lig_verisi['emoji']} {lig_verisi['ad']} SONA ERDİ!</b>\n\n"
            f"👑 Şampiyon: <b>{sampiyion['emoji']} {sampiyion['takim_adi']}</b> "
            f"— {sampiyion['puan']} puan\n\n"
            f"🥇 {tablo[0]['takim_adi']} — {tablo[0]['puan']}P\n"
            + (f"🥈 {tablo[1]['takim_adi']} — {tablo[1]['puan']}P\n" if len(tablo) > 1 else "")
            + (f"🥉 {tablo[2]['takim_adi']} — {tablo[2]['puan']}P" if len(tablo) > 2 else ""),
            parse_mode="HTML",
        )


async def fikstur_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = chat_id(update)
    ligler = aktif_ligler(cid)

    if not ligler:
        await update.message.reply_html("❌ Aktif lig yok.")
        return

    for lig in ligler:
        veri = fikstur_getir(cid, lig["lig_id"])
        if not veri:
            continue

        lig_verisi = get_lig(lig["lig_id"])
        satirlar = [
            f"📅 <b>{lig_verisi['emoji']} {veri['lig_adi']} — Fikstür</b>",
            f"Mevcut Hafta: {veri['mevcut_hafta']}/{veri['toplam_hafta']}\n",
        ]

        for hafta_no, hafta_maclari in enumerate(veri["fikstur"], start=1):
            durum = "▶️" if hafta_no == veri["mevcut_hafta"] + 1 else (
                "✅" if hafta_no <= veri["mevcut_hafta"] else "⬜"
            )
            satirlar.append(f"{durum} <b>Hafta {hafta_no}</b>")
            for mac in hafta_maclari:
                ev = get_takim(lig["lig_id"], mac["ev"])
                dep = get_takim(lig["lig_id"], mac["dep"])
                if ev and dep:
                    satirlar.append(
                        f"  {ev['emoji']} {ev['kisaad']} vs {dep['kisaad']} {dep['emoji']}"
                    )

        # Telegram mesaj limiti: 4096 karakter
        mesaj = "\n".join(satirlar)
        if len(mesaj) > 4000:
            mesaj = mesaj[:4000] + "\n...(devamı var)"

        await update.message.reply_html(mesaj)


# ─── Ana Fonksiyon ────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN ortam değişkeni bulunamadı! "
            "Railway'de Variables sekmesinden ekle."
        )

    init_db()
    logger.info("✅ Veritabanı hazır.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lig_olustur", lig_olustur_cmd))
    app.add_handler(CommandHandler("takim_sec", takim_sec_cmd))
    app.add_handler(CommandHandler("takimim", takimim_cmd))
    app.add_handler(CommandHandler("lig_tablosu", lig_tablosu_cmd))
    app.add_handler(CommandHandler("hafta_oyna", hafta_oyna_cmd))
    app.add_handler(CommandHandler("fikstur", fikstur_cmd))

    app.add_handler(CallbackQueryHandler(lig_sec_callback, pattern=r"^lig_sec:"))
    app.add_handler(CallbackQueryHandler(takim_sec_callback, pattern=r"^takim_sec:"))
    app.add_handler(CallbackQueryHandler(hafta_oyna_callback, pattern=r"^hafta_oyna:"))

    logger.info("🤖 Bot başlatılıyor...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
