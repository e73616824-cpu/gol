import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from futbol_db import setup_db, init_lig, takimlari_getir, oyunculari_getir, otomatik_maclari_oyna, bu_hafta_maclari, fikstur_olustur, takim_bilgisi

BOT_TOKEN = os.getenv("BOT_TOKEN", "8618492952:AAFk5EPHoYYl9ZMJLYTDiEjrjlMyuhPkAl8")
LIG_ADI = "Premier League"  # Varsayılan lig

setup_db()

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ Futbol Ligi Botu\n"
        "— Maçları bot otomatik oynatıyor.\n\n"
        "Komutlar:\n"
        "/lig - Lig tablosu\n"
        "/kadro <takim_id> - Kadro\n"
        "/hafta <hafta_no> - O haftanın maçları\n"
        "/fikstur - Fikstür oluştur (admin)\n"
        "/oto <hafta_no> - Haftanın maçlarını otomatik oynat (admin)\n"
        "/lig_baslat - Lig ve takımlar yükle (admin)"
    )

async def lig_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_lig(LIG_ADI)
    await update.message.reply_text("Lig başlatıldı! Şimdi /fikstur ile fikstürü oluşturun.")

async def lig_tablo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tablo = takimlari_getir(LIG_ADI)
    metin = "🏆 Lig Tablosu\n"
    for i, t in enumerate(tablo, 1):
        metin += f"{i}. {t['isim']} | {t['puan']} P | {t['galibiyet']}G {t['beraberlik']}B {t['maglubiyet']}M | A:{t['atilan_gol']} Y:{t['yenilen_gol']}\n"
    await update.message.reply_text(metin)

async def kadro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Takım ID girin (örn: /kadro 1)")
        return
    takim_id = int(args[0])
    oyuncular = oyunculari_getir(takim_id)
    takim = takim_bilgisi(takim_id)
    metin = f"Kadro: {takim['isim']}\n"
    for o in oyuncular:
        metin += f"{o['isim']} — {o['pozisyon']} — Güç:{o['guc']}\n"
    await update.message.reply_text(metin)

async def hafta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hafta = 1
    args = context.args
    if args and args[0].isdigit():
        hafta = int(args[0])
    maclar = bu_hafta_maclari(LIG_ADI, hafta)
    if not maclar:
        await update.message.reply_text("Bu hafta maçı yok ya da oynanmış.")
        return
    metin = f"Hafta {hafta} Maçları:\n"
    for m in maclar:
        ev = takim_bilgisi(m["ev_takim"])
        dep = takim_bilgisi(m["dep_takim"])
        metin += f"{ev['isim']} vs {dep['isim']}\n"
    await update.message.reply_text(metin)

async def otomatik_oynat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hafta = 1
    args = context.args
    if args and args[0].isdigit():
        hafta = int(args[0])
    otomatik_maclari_oyna(LIG_ADI, hafta)
    await update.message.reply_text(f"Hafta {hafta} maçları oynandı!")

async def fikstur_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fikstur_olustur(LIG_ADI)
    await update.message.reply_text("Fikstür oluşturuldu. /hafta 1 ile ilk maçları görebilirsiniz.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lig_baslat", lig_baslat))
    app.add_handler(CommandHandler("lig", lig_tablo))
    app.add_handler(CommandHandler("kadro", kadro))
    app.add_handler(CommandHandler("hafta", hafta))
    app.add_handler(CommandHandler("oto", otomatik_oynat))
    app.add_handler(CommandHandler("fikstur", fikstur_cmd))
    logging.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
