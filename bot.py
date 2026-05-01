import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import futbol_db as db

# ─── Yapılandırma ─────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Yardımcı ─────────────────────────────────────────────────────────────────

def _arg(args: list[str], idx: int) -> str | None:
    """args listesinden güvenli eleman al."""
    return args[idx] if len(args) > idx else None


def _int_arg(args: list[str], idx: int) -> int | None:
    """args listesinden güvenli int al."""
    val = _arg(args, idx)
    return int(val) if val and val.isdigit() else None


# ─── Komutlar ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metin = (
        "⚽ *Futbol Ligi Botu*\n\n"
        "Komutlar:\n"
        "/lig\\_olustur \\<lig\\_adi\\> — Yeni lig oluştur\n"
        "/takim\\_sec \\<takim\\_id\\> — Takım seç\n"
        "/takimim — Seçtiğin takımın kadrosu\n"
        "/lig\\_tablosu \\<lig\\_id\\> — Puan tablosu\n"
        "/hafta\\_oyna \\<lig\\_id\\> \\<hafta\\> — Haftayı oynat\n"
        "/fikstur \\<lig\\_id\\> — Fikstürü göster\n"
    )
    await update.message.reply_text(metin, parse_mode="MarkdownV2")


async def cmd_lig_olustur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /lig_olustur <lig_adi>
    Örnek: /lig_olustur Premier League
    """
    if not context.args:
        await update.message.reply_text(
            "❌ Kullanım: /lig_olustur <lig_adi>\n"
            "Örnek: /lig_olustur Premier League\n\n"
            "Hazır ligler: Premier League, La Liga, Bundesliga"
        )
        return

    lig_adi = " ".join(context.args)
    try:
        sonuc = db.lig_olustur(lig_adi)
        lig_id = sonuc["lig_id"]

        if not sonuc["yeni"]:
            await update.message.reply_text(
                f"ℹ️ '{lig_adi}' zaten mevcut (Lig ID: {lig_id}).\n"
                f"Fikstür oluşturmak için: /fikstur {lig_id}"
            )
            return

        takimlar = db.takimlari_getir(lig_id)
        takim_listesi = "\n".join(
            f"  {t['takim_id']}. {t['isim']}" for t in takimlar
        ) or "  (Takım yüklenmedi — özel lig)"

        await update.message.reply_text(
            f"✅ Lig oluşturuldu!\n"
            f"📋 Lig: {lig_adi} (ID: {lig_id})\n\n"
            f"Takımlar:\n{takim_listesi}\n\n"
            f"Fikstür oluşturmak için:\n/fikstur {lig_id}"
        )
    except Exception as e:
        logger.error(f"cmd_lig_olustur: {e}")
        await update.message.reply_text(f"❌ Hata: {e}")


async def cmd_takim_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /takim_sec <takim_id>
    Örnek: /takim_sec 3
    """
    takim_id = _int_arg(context.args, 0)
    if takim_id is None:
        await update.message.reply_text(
            "❌ Kullanım: /takim_sec <takim_id>\n"
            "Örnek: /takim_sec 3\n\n"
            "Takım ID'lerini görmek için /lig_tablosu <lig_id> kullan."
        )
        return

    takim = db.takim_bilgisi(takim_id)
    if not takim:
        await update.message.reply_text(f"❌ {takim_id} ID'li takım bulunamadı.")
        return

    kullanici_id = update.effective_user.id
    basarili = db.takim_sec(kullanici_id, takim_id)
    if basarili:
        await update.message.reply_text(
            f"✅ Takımın seçildi: {takim['isim']}\n"
            f"Kadroyu görmek için: /takimim"
        )
    else:
        await update.message.reply_text("❌ Takım seçilirken hata oluştu.")


async def cmd_takimim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/takimim — Kullanıcının seçtiği takımın kadrosunu göster."""
    kullanici_id = update.effective_user.id
    takim = db.kullanici_takimi(kullanici_id)

    if not takim:
        await update.message.reply_text(
            "❌ Henüz takım seçmedin.\n"
            "Kullanım: /takim_sec <takim_id>"
        )
        return

    oyuncular = db.oyunculari_getir(takim["takim_id"])
    satirlar = [f"🏟️ {takim['isim']} Kadrosu\n"]
    for o in oyuncular:
        satirlar.append(f"  {o['pozisyon']:<10} {o['isim']:<22} Güç: {o['guc']}")

    satirlar.append(
        f"\n📊 {takim['puan']}P | "
        f"{takim['galibiyet']}G {takim['beraberlik']}B {takim['maglubiyet']}M | "
        f"A:{takim['atilan_gol']} Y:{takim['yenilen_gol']}"
    )
    await update.message.reply_text("\n".join(satirlar))


async def cmd_lig_tablosu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /lig_tablosu <lig_id>
    Örnek: /lig_tablosu 1
    """
    lig_id = _int_arg(context.args, 0)
    if lig_id is None:
        await update.message.reply_text(
            "❌ Kullanım: /lig_tablosu <lig_id>\n"
            "Örnek: /lig_tablosu 1"
        )
        return

    lig = db.lig_bilgisi_id(lig_id)
    if not lig:
        await update.message.reply_text(f"❌ {lig_id} ID'li lig bulunamadı.")
        return

    takimlar = db.takimlari_getir(lig_id)
    if not takimlar:
        await update.message.reply_text("ℹ️ Bu ligde henüz takım yok.")
        return

    baslik = f"🏆 {lig['lig_adi']} Puan Tablosu\n"
    baslik += f"{'#':<3} {'Takım':<22} {'P':>3} {'O':>3} {'G':>3} {'B':>3} {'M':>3} {'A':>3} {'Y':>3} {'AV':>4}\n"
    baslik += "─" * 55 + "\n"

    satirlar = [baslik]
    for i, t in enumerate(takimlar, 1):
        av = t["atilan_gol"] - t["yenilen_gol"]
        oyun = t["galibiyet"] + t["beraberlik"] + t["maglubiyet"]
        satirlar.append(
            f"{i:<3} {t['isim']:<22} {t['puan']:>3} {oyun:>3} "
            f"{t['galibiyet']:>3} {t['beraberlik']:>3} {t['maglubiyet']:>3} "
            f"{t['atilan_gol']:>3} {t['yenilen_gol']:>3} {av:>+4}"
        )

    await update.message.reply_text("\n".join(satirlar))


async def cmd_hafta_oyna(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /hafta_oyna <lig_id> <hafta>
    Örnek: /hafta_oyna 1 3
    """
    lig_id = _int_arg(context.args, 0)
    hafta  = _int_arg(context.args, 1)

    if lig_id is None or hafta is None:
        await update.message.reply_text(
            "❌ Kullanım: /hafta_oyna <lig_id> <hafta>\n"
            "Örnek: /hafta_oyna 1 3"
        )
        return

    lig = db.lig_bilgisi_id(lig_id)
    if not lig:
        await update.message.reply_text(f"❌ {lig_id} ID'li lig bulunamadı.")
        return

    try:
        sonuclar = db.hafta_oyna(lig_id, hafta)
    except Exception as e:
        logger.error(f"cmd_hafta_oyna: {e}")
        await update.message.reply_text(f"❌ Hata: {e}")
        return

    if not sonuclar:
        await update.message.reply_text(
            f"ℹ️ {lig['lig_adi']} — Hafta {hafta} maçları zaten oynanmış "
            f"ya da fikstürde bu hafta yok.\n"
            f"Fikstürü görmek için: /fikstur {lig_id}"
        )
        return

    satirlar = [f"⚽ {lig['lig_adi']} — Hafta {hafta} Sonuçları\n"]
    for s in sonuclar:
        if s["ev_gol"] > s["dep_gol"]:
            emoji = "🏠"
        elif s["ev_gol"] < s["dep_gol"]:
            emoji = "✈️"
        else:
            emoji = "🤝"
        satirlar.append(
            f"{emoji} {s['ev']} {s['ev_gol']} - {s['dep_gol']} {s['dep']}"
        )

    satirlar.append(f"\n📊 Tablo için: /lig_tablosu {lig_id}")
    await update.message.reply_text("\n".join(satirlar))


async def cmd_fikstur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /fikstur <lig_id>
    Fikstür yoksa oluşturur, sonra tüm haftaları gösterir.
    Örnek: /fikstur 1
    """
    lig_id = _int_arg(context.args, 0)
    if lig_id is None:
        await update.message.reply_text(
            "❌ Kullanım: /fikstur <lig_id>\n"
            "Örnek: /fikstur 1"
        )
        return

    lig = db.lig_bilgisi_id(lig_id)
    if not lig:
        await update.message.reply_text(f"❌ {lig_id} ID'li lig bulunamadı.")
        return

    try:
        yeni_mac = db.fikstur_olustur(lig_id)
        if yeni_mac > 0:
            await update.message.reply_text(
                f"✅ Fikstür oluşturuldu! ({yeni_mac} maç)"
            )
    except Exception as e:
        logger.error(f"cmd_fikstur fikstur_olustur: {e}")
        await update.message.reply_text(f"❌ Fikstür oluşturulurken hata: {e}")
        return

    maclar = db.fikstur_getir(lig_id)
    if not maclar:
        await update.message.reply_text(
            "ℹ️ Fikstür boş. Önce ligi oluştur: /lig_olustur <lig_adi>"
        )
        return

    # Haftalara göre grupla
    haftalar: dict[int, list] = {}
    for m in maclar:
        haftalar.setdefault(m["hafta"], []).append(m)

    satirlar = [f"📅 {lig['lig_adi']} Fikstürü\n"]
    for hafta_no in sorted(haftalar):
        satirlar.append(f"── Hafta {hafta_no} ──")
        for m in haftalar[hafta_no]:
            ev  = db.takim_bilgisi(m["ev_takim"])
            dep = db.takim_bilgisi(m["dep_takim"])
            ev_isim  = ev["isim"]  if ev  else "?"
            dep_isim = dep["isim"] if dep else "?"
            if m["oynanmis"]:
                satirlar.append(f"  ✅ {ev_isim} {m['ev_gol']} - {m['dep_gol']} {dep_isim}")
            else:
                satirlar.append(f"  🕐 {ev_isim} vs {dep_isim}")

    # Telegram mesaj limiti 4096 karakter — uzunsa böl
    metin = "\n".join(satirlar)
    if len(metin) <= 4096:
        await update.message.reply_text(metin)
    else:
        for i in range(0, len(metin), 4096):
            await update.message.reply_text(metin[i:i + 4096])


# ─── Ana fonksiyon ────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN ortam değişkeni ayarlanmamış!")

    # Veritabanını başlat
    db.setup_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("lig_olustur",  cmd_lig_olustur))
    app.add_handler(CommandHandler("takim_sec",    cmd_takim_sec))
    app.add_handler(CommandHandler("takimim",      cmd_takimim))
    app.add_handler(CommandHandler("lig_tablosu",  cmd_lig_tablosu))
    app.add_handler(CommandHandler("hafta_oyna",   cmd_hafta_oyna))
    app.add_handler(CommandHandler("fikstur",      cmd_fikstur))

    logger.info("Bot başlatılıyor...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
