const { getUserTeam, getTrainingData, saveTrainingData } = require('../utils/dataManager');
const { getTeamById } = require('../data/leagues');

function esc(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

const TRAINING_TYPES = {
  kondisyon:     { name: 'Kondisyon Antrenmanı', emoji: '🏃', xpBase: 20, desc: 'Oyuncuların dayanıklılığını artırır' },
  teknik:        { name: 'Teknik Antrenman',     emoji: '⚽', xpBase: 25, desc: 'Top kontrolü ve pas geliştirir' },
  taktik:        { name: 'Taktik Antrenman',     emoji: '📋', xpBase: 30, desc: 'Savunma ve hücum organizasyonu' },
  gucantrenman:  { name: 'Güç Antrenmanı',       emoji: '💪', xpBase: 20, desc: 'Fiziksel güç ve hız' },
  atismapraktik: { name: 'Atış Pratiği',         emoji: '🎯', xpBase: 28, desc: 'Şut isabeti ve güç' },
};

const COOLDOWN_HOURS = 6;

module.exports = (bot) => {

  // /antrenman [tip]
  bot.command('antrenman', async (ctx) => {
    const guildId = String(ctx.chat.id);
    const userId = String(ctx.from.id);

    const myTeamId = getUserTeam(guildId, userId);
    if (!myTeamId) {
      return ctx.reply('❌ Önce takım seç: /takimsec &lt;takım adı&gt;', { parse_mode: 'HTML' });
    }

    const teamData = getTeamById(myTeamId);
    if (!teamData) return ctx.reply('❌ Takım bulunamadı.');
    const { team } = teamData;

    // Antrenman tipi args'tan al: /antrenman kondisyon
    const sub = ctx.message.text.split(' ')[1]?.toLowerCase();

    // Liste göster
    if (!sub) {
      const trainingData = getTrainingData(guildId, userId);
      const lastTraining = trainingData?.lastTraining;
      const cooldownMs = COOLDOWN_HOURS * 60 * 60 * 1000;
      const canTrain = !lastTraining || (Date.now() - lastTraining) > cooldownMs;
      const nextTraining = lastTraining ? new Date(lastTraining + cooldownMs) : null;

      let msg = `${team.emoji} <b>${esc(team.name)} — Antrenman</b>\n\n`;
      for (const [key, t] of Object.entries(TRAINING_TYPES)) {
        msg += `${t.emoji} /antrenman ${key}\n   <i>${t.desc}</i>\n\n`;
      }

      msg += canTrain
        ? '✅ <b>Antrenman yapabilirsin!</b>'
        : `⏳ Sonraki antrenman: <b>${nextTraining?.toLocaleTimeString('tr-TR')}</b>`;
      msg += `\n📈 Toplam seans: ${trainingData?.totalSessions || 0}`;

      return ctx.reply(msg, { parse_mode: 'HTML' });
    }

    // Cooldown kontrolü
    const trainingData = getTrainingData(guildId, userId) || { lastTraining: null, totalSessions: 0, history: [] };
    const cooldownMs = COOLDOWN_HOURS * 60 * 60 * 1000;

    if (trainingData.lastTraining && (Date.now() - trainingData.lastTraining) < cooldownMs) {
      const remaining = Math.ceil((trainingData.lastTraining + cooldownMs - Date.now()) / 60000);
      return ctx.reply(`⏳ Antrenman için <b>${remaining} dakika</b> daha bekle!`, { parse_mode: 'HTML' });
    }

    const trainingType = TRAINING_TYPES[sub];
    if (!trainingType) {
      return ctx.reply('❌ Geçersiz antrenman tipi. Kullanım: /antrenman', { parse_mode: 'HTML' });
    }

    // Simülasyon
    const xpGained = trainingType.xpBase + Math.floor(Math.random() * 15);
    const playersBoosted = Math.floor(Math.random() * 5) + 3;
    const shuffled = [...team.players].sort(() => Math.random() - 0.5);
    const featured = shuffled.slice(0, 3).map(p => `• <b>${esc(p.name)}</b> (${p.position})`).join('\n');

    const resultLines = [
      '🌟 Mükemmel antrenman! Takım harika bir form tutturdu.',
      '✅ İyi bir antrenman geçti. Oyuncular motivasyonlu.',
      '📈 Verimli çalışma. Bazı oyuncular dikkat çekti.',
      '⚽ Solid bir antrenman. Taktikler oturdu.',
      '💪 Fiziksel antrenman tamamlandı. Takım güçlendi.',
    ];
    const resultText = resultLines[Math.floor(Math.random() * resultLines.length)];

    // Kaydet
    trainingData.lastTraining = Date.now();
    trainingData.totalSessions = (trainingData.totalSessions || 0) + 1;
    if (!trainingData.history) trainingData.history = [];
    trainingData.history.unshift({ type: sub, xp: xpGained, date: Date.now() });
    if (trainingData.history.length > 20) trainingData.history = trainingData.history.slice(0, 20);
    saveTrainingData(guildId, userId, trainingData);

    return ctx.reply(
      `${trainingType.emoji} <b>${esc(trainingType.name)} Tamamlandı!</b>\n\n` +
      `${resultText}\n\n` +
      `⭐ XP Kazanıldı: <b>+${xpGained} XP</b>\n` +
      `👥 Etkilenen Oyuncu: <b>${playersBoosted} oyuncu</b>\n\n` +
      `🌟 <b>Öne Çıkan Oyuncular:</b>\n${featured}\n\n` +
      `⏳ Sonraki antrenman: ${COOLDOWN_HOURS} saat sonra`,
      { parse_mode: 'HTML' }
    );
  });

};
