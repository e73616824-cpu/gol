const { getLeagues, getLeagueById } = require('../data/leagues');
const { getLeagueState, getMatchLog } = require('../utils/dataManager');

function esc(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

module.exports = (bot) => {

  // /puan <lig_id>
  bot.command('puan', async (ctx) => {
    const leagueId = ctx.message.text.split(' ')[1]?.toLowerCase();

    if (!leagueId) {
      const leagues = getLeagues();
      let msg = '📊 <b>Puan Durumu</b>\n\nLig belirtin:\n\n';
      for (const l of leagues) {
        msg += `${l.emoji} <code>/puan ${l.id}</code> — ${esc(l.name)}\n`;
      }
      return ctx.reply(msg, { parse_mode: 'HTML' });
    }

    const state = getLeagueState(String(ctx.chat.id), leagueId);
    if (!state) {
      return ctx.reply(
        `❌ <b>${esc(leagueId)}</b> ligi başlatılmamış.\nAdmin: /ligbaslat ${leagueId}`,
        { parse_mode: 'HTML' }
      );
    }

    const sorted = Object.values(state.standings)
      .sort((a, b) => b.points - a.points || b.goalDiff - a.goalDiff);

    const medals = ['🥇', '🥈', '🥉'];
    const leagueData = getLeagueById(leagueId);

    let msg = `${leagueData?.emoji || '🏆'} <b>${esc(state.leagueName)} — Puan Durumu</b>\n`;
    msg += `📅 Hafta ${state.currentRound}/${state.totalRounds}\n\n`;

    for (const [i, t] of sorted.entries()) {
      const pos = medals[i] || `${i + 1}.`;
      const gd = t.goalDiff >= 0 ? `+${t.goalDiff}` : `${t.goalDiff}`;
      msg += `${pos} <b>${esc(t.teamName)}</b> — <b>${t.points}P</b>\n`;
      msg += `    ${t.played}O ${t.won}G ${t.drawn}B ${t.lost}M | ${t.goalsFor}:${t.goalsAgainst} (${gd})\n`;
    }

    return ctx.reply(msg, { parse_mode: 'HTML' });
  });

  // /sonuclar — son maçlar
  bot.command('sonuclar', async (ctx) => {
    const log = getMatchLog(String(ctx.chat.id), 10);
    if (log.length === 0) return ctx.reply('❌ Henüz hiç maç oynanmadı.');

    let msg = '📋 <b>Son Maç Sonuçları</b>\n\n';
    for (const m of log) {
      const date = new Date(m.timestamp).toLocaleDateString('tr-TR');
      const winner = m.homeGoals > m.awayGoals ? '›' : m.awayGoals > m.homeGoals ? '‹' : '=';
      msg += `<b>${esc(m.homeTeam)} ${m.homeGoals}–${m.awayGoals} ${esc(m.awayTeam)}</b> ${winner}  <i>${date}</i>\n`;
    }

    return ctx.reply(msg, { parse_mode: 'HTML' });
  });

  // /fikstür <lig_id>
  bot.command('fikstür', async (ctx) => {
    const leagueId = ctx.message.text.split(' ')[1]?.toLowerCase();

    if (!leagueId) {
      const leagues = getLeagues();
      let msg = '📅 <b>Fikstür</b>\n\nLig belirtin:\n\n';
      for (const l of leagues) {
        msg += `${l.emoji} <code>/fikstür ${l.id}</code> — ${esc(l.name)}\n`;
      }
      return ctx.reply(msg, { parse_mode: 'HTML' });
    }

    const state = getLeagueState(String(ctx.chat.id), leagueId);
    if (!state) {
      return ctx.reply(`❌ <b>${esc(leagueId)}</b> ligi başlatılmamış.`, { parse_mode: 'HTML' });
    }

    const leagueData = getLeagueById(leagueId);
    if (!leagueData) return ctx.reply('❌ Lig verisi bulunamadı.');

    // Sonraki 3 haftayı göster
    const nextRound = state.currentRound + 1;
    const showRounds = state.fixtures.slice(nextRound - 1, nextRound + 2);

    if (showRounds.length === 0) {
      return ctx.reply('🏁 Fikstür tamamlandı, maç kalmadı.');
    }

    let msg = `${leagueData.emoji} <b>${esc(state.leagueName)} — Fikstür</b>\n`;
    msg += `Mevcut Hafta: ${state.currentRound}/${state.totalRounds}\n\n`;

    for (const round of showRounds) {
      const isCurrent = round.round === nextRound;
      msg += `<b>📅 Hafta ${round.round}${isCurrent ? ' (Sonraki)' : ''}</b>\n`;
      for (const match of round.matches) {
        const homeTeam = leagueData.teams.find(t => t.id === match.home);
        const awayTeam = leagueData.teams.find(t => t.id === match.away);
        if (!homeTeam || !awayTeam) continue;
        msg += `  ${homeTeam.emoji} ${esc(homeTeam.shortName)} vs ${esc(awayTeam.shortName)} ${awayTeam.emoji}\n`;
      }
      msg += '\n';
    }

    return ctx.reply(msg, { parse_mode: 'HTML' });
  });

  // /yardim — tüm komutlar
  bot.command('yardim', async (ctx) => {
    return ctx.reply(
      '⚽ <b>Futbol Botu — Komutlar</b>\n\n' +

      '👤 <b>Takım Komutları</b>\n' +
      '/takim — Takım bilgisi\n' +
      '/takimsec &lt;takım adı&gt; — Takım seç\n' +
      '/kadro [takım adı] — Kadro görüntüle\n' +
      '/takimlar [lig_id] — Tüm takımlar\n\n' +

      '🏋️ <b>Antrenman</b>\n' +
      '/antrenman — Antrenman listesi\n' +
      '/antrenman kondisyon — Kondisyon\n' +
      '/antrenman teknik — Teknik\n' +
      '/antrenman taktik — Taktik\n' +
      '/antrenman gucantrenman — Güç\n' +
      '/antrenman atismapraktik — Atış pratiği\n\n' +

      '💰 <b>Transfer</b>\n' +
      '/transfer — Transfer menüsü\n' +
      '/transferara &lt;oyuncu&gt; — Oyuncu ara\n' +
      '/oyuncu &lt;oyuncu&gt; — Oyuncu detayı\n' +
      '/pazar — Günlük transfer pazarı\n\n' +

      '📊 <b>Lig &amp; Sonuçlar</b>\n' +
      '/puan &lt;lig_id&gt; — Puan durumu\n' +
      '/sonuclar — Son maç sonuçları\n' +
      '/fikstür &lt;lig_id&gt; — Yaklaşan maçlar\n\n' +

      '⚙️ <b>Admin (Yönetici)</b>\n' +
      '/ligbaslat &lt;lig_id&gt; — Lig başlat\n' +
      '/ligdurdur &lt;lig_id&gt; — Ligi durdur\n' +
      '/ligsifirla &lt;lig_id&gt; — Ligi sıfırla\n' +
      '/ligler — Aktif ligler\n' +
      '/adminpuan &lt;lig_id&gt; — Puan tablosu\n' +
      '/simule — Manuel maç simülasyonu\n' +
      '/kanal — Duyuru kanalı ayarla\n\n' +

      '🌍 <b>Lig ID\'leri:</b>\n' +
      '<code>premier_league</code> <code>la_liga</code> <code>bundesliga</code>\n' +
      '<code>serie_a</code> <code>ligue_1</code> <code>eredivisie</code> <code>primeira_liga</code>\n\n' +

      '<i>⚡ Maçlar her gün 18:00 ve 20:00\'de otomatik oynanır!</i>',
      { parse_mode: 'HTML' }
    );
  });

};
