require('dotenv').config();
const { Telegraf } = require('telegraf');
const cron = require('node-cron');
const { simulateMatchDay } = require('./src/matchEngine');

const token = process.env.TELEGRAM_TOKEN;
if (!token) {
  console.error('❌ TELEGRAM_TOKEN bulunamadı! Railway ortam değişkenlerini kontrol et.');
  process.exit(1);
}

const bot = new Telegraf(token);

// Komutları yükle
require('./src/commands/takim')(bot);
require('./src/commands/antrenman')(bot);
require('./src/commands/transfer')(bot);
require('./src/commands/admin')(bot);
require('./src/commands/misc')(bot);

bot.start((ctx) =>
  ctx.reply(
    '⚽ <b>Futbol Botuna Hoş Geldin!</b>\n\n' +
    'Bir takım seçerek başla: /takimsec &lt;takım adı&gt;\n' +
    'Tüm komutlar için: /yardim',
    { parse_mode: 'HTML' }
  )
);

// Türkiye saati UTC+3 → 18:00 TR = 15:00 UTC, 20:00 TR = 17:00 UTC
cron.schedule('0 15 * * *', () => {
  console.log('⚽ 18:00 TR — Maç simülasyonu başlıyor...');
  simulateMatchDay(bot).catch(console.error);
});

cron.schedule('0 17 * * *', () => {
  console.log('⚽ 20:00 TR — Maç simülasyonu başlıyor...');
  simulateMatchDay(bot).catch(console.error);
});

bot.launch().then(() => {
  console.log('✅ Bot başlatıldı!');
});

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
