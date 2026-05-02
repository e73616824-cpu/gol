const { getLeagues, getLeagueById } = require('../data/leagues');
const { initLeague, simulateMatchDay } = require('../matchEngine');
const {
  getLeagueState, saveLeagueState,
  setAnnounceChannel, getGuildData, saveGuildData
} = require('../utils/dataManager');

function esc(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Admin mi kontrolü — chat creator veya admin
async function isAdmin(ctx) {
  try {
    const member = await ctx.telegram.getChatMember(ctx.chat.id, ctx.from.id);
    return ['creator', 'administrator'].includes(member.status);
  } catch {
    return false;
  }
}

module.exports = (bot) => {

  // /admin — yardım menüsü
  bot.command('admin', async (ctx) => {
    if (!(await isAdmin(ctx))) {
      return ctx.reply('❌ Bu komut için yönetici yetkisi gerekli!');
    }

    return ctx.reply(
      '⚙️ <b>Admin Komutları</b>\n\n' +
      '/ligbaslat &lt;lig_id&gt; — Lig başlat\n' +
      '/ligdurdur &lt;lig_id&gt; — Ligi durdur\n' +
      '/ligsifirla &lt;lig_id&gt; — Ligi sıfırla\n' +
      '/ligler — Aktif ligleri göster\n' +
      '/adminpuan &lt;lig_id&gt; — Puan durumu\n' +
      '/simule [lig_id] — Manuel maç simülasyonu\n' +
      '/kanal — Bu kanalı duyuru kanalı yap\n\n' +
      '<b>Lig ID\'leri:</b>\n' +
      '<code>premier_league</code> | <code>la_liga</code> | <code>bundesliga</code>\n' +
      '<code>serie_a</code> | <code>ligue_1</code> | <code>eredivisie</code> | <code>primeira_liga</code>',
      { parse_mode: 'HTML' }
    );
  });

  // /ligbaslat <lig_id>
  bot.command('ligbaslat', async (ctx) => {
    if (!(await isAdmin(ctx))) return ctx.reply('❌ Yönetici yetkisi gerekli!');

    const leagueId = ctx.message.text.split(' ')[1]?.toLowerCase();
    if (!leagueId) {
      const leagues = getLeagues();
      let msg = '📋 <b>Mevcut Ligler:</b>\n\n';
      for (const l of leagues) {
        msg += `${l.emoji} <code>${l.id}</code> — ${esc(l.name)}\n`;
      }
      msg += '\nKullanım: /ligbaslat &lt;lig_id&gt;';
      return ctx.reply(msg, { parse_mode: 'HTML' });
    }

    const existing = getLeagueState(String(ctx.chat.id), leagueId);
    if (existing && existing.status === 'active') {
      return ctx.reply(
        `⚠️ <b>${esc(existing.leagueName)}</b> zaten aktif!\nDurdurmak için: /ligdurdur ${leagueId}`,
        { parse_mode: 'HTML' }
      );
    }

    try {
      const state = initLeague(String(ctx.chat.id), leagueId);
      const leagueData = getLeagueById(leagueId);
      const teamList = leagueData.teams.map(t => `${t.emoji} ${t.name}`).join('\n');

      return ctx.reply(
        `✅ <b>${leagueData.emoji} ${esc(state.leagueName)} Başlatıldı!</b>\n\n` +
        `🏟️ Takım Sayısı: ${leagueData.teams.length} takım\n` +
        `📅 Toplam Hafta: ${state.totalRounds} hafta\n` +
        `⚡ Otomatik Maçlar: Her gün 18:00 ve 20:00 (TR)\n\n` +
        `<b>Takımlar:</b>\n${teamList}\n\n` +
        `📢 Duyuruları bu kanala göndermek için: /kanal`,
        { parse_mode: 'HTML' }
      );
    } catch (err) {
      return ctx.reply(`❌ Hata: ${err.message}`);
    }
  });

  // /ligdurdur <lig_id>
  bot.command('ligdurdur', async (ctx) => {
    if (!(await isAdmin(ctx))) return ctx.reply('❌ Yönetici yetkisi gerekli!');

    const leagueId = ctx.message.text.split(' ')[1]?.toLowerCase();
    if (!leagueId) return ctx.reply('Kullanım: /ligdurdur &lt;lig_id&gt;', { parse_mode: 'HTML' });

    const state = getLeagueState(String(ctx.chat.id), leagueId);
    if (!state) return ctx.reply('❌ Bu lig bulunamadı veya başlatılmadı.');

    state.status = 'stopped';
    saveLeagueState(String(ctx.chat.id), leagueId, state);
    return ctx.reply(`⏹️ <b>${esc(state.leagueName)}</b> durduruldu.`, { parse_mode: 'HTML' });
  });

  // /ligsifirla <lig_id>
  bot.command('ligsifirla', async (ctx) => {
    if (!(await isAdmin(ctx))) return ctx.reply('❌ Yönetici yetkisi gerekli!');

    const leagueId = ctx.message.text.split(' ')[1]?.toLowerCase();
    if (!leagueId) return ctx.reply('Kullanım: /ligsifirla &lt;lig_id&gt;', { parse_mode: 'HTML' });

    const guildData = getGuildData(String(ctx.chat.id));
    if (guildData.leagues && guildData.leagues[leagueId]) {
      delete guildData.leagues[leagueId];
      saveGuildData(String(ctx.chat.id), guildData);
      return ctx.reply(`🔄 <b>${leagueId}</b> ligi sıfırlandı.`, { parse_mode: 'HTML' });
    }
    return ctx.reply('❌ Lig bulunamadı.');
  });

  // /ligler — aktif ligleri listele
  bot.command('ligler', async (ctx) => {
    if (!(await isAdmin(ctx))) return ctx.reply('❌ Yönetici yetkisi gerekli!');

    const guildData = getGuildData(String(ctx.chat.id));
    const activeLeagues = Object.values(guildData.leagues || {});

    if (activeLeagues.length === 0) {
      const leagues = getLeagues();
      let msg = '📋 <b>Başlatılabilir Ligler:</b>\n\n';
      for (const l of leagues) {
        msg += `${l.emoji} <code>${l.id}</code> — ${esc(l.name)} (${l.teams.length} takım)\n`;
      }
      msg += '\n/ligbaslat &lt;id&gt; ile başlatabilirsiniz.';
      return ctx.reply(msg, { parse_mode: 'HTML' });
    }

    let msg = '🏆 <b>Aktif Ligler</b>\n\n';
    for (const state of activeLeagues) {
      const statusEmoji = state.status === 'active' ? '🟢' : state.status === 'stopped' ? '🔴' : '🏁';
      msg += `${statusEmoji} <b>${esc(state.leagueName)}</b>\n`;
      msg += `   Durum: ${state.status} | Hafta: ${state.currentRound}/${state.totalRounds}\n\n`;
    }

    return ctx.reply(msg, { parse_mode: 'HTML' });
  });

  // /adminpuan <lig_id>
  bot.command('adminpuan', async (ctx) => {
    if (!(await isAdmin(ctx))) return ctx.reply('❌ Yönetici yetkisi gerekli!');

    const leagueId = ctx.message.text.split(' ')[1]?.toLowerCase();
    if (!leagueId) return ctx.reply('Kullanım: /adminpuan &lt;lig_id&gt;', { parse_mode: 'HTML' });

    const state = getLeagueState(String(ctx.chat.id), leagueId);
    if (!state) return ctx.reply('❌ Bu lig bulunamadı.');

    const sorted = Object.values(state.standings)
      .sort((a, b) => b.points - a.points || b.goalDiff - a.goalDiff);

    const medals = ['🥇', '🥈', '🥉'];
    let msg = `📊 <b>${esc(state.leagueName)} — Puan Durumu</b>\nHafta ${state.currentRound}/${state.totalRounds}\n\n`;
    for (const [i, t] of sorted.entries()) {
      const pos = medals[i] || `<b>${i + 1}.</b>`;
      const gd = t.goalDiff >= 0 ? `+${t.goalDiff}` : `${t.goalDiff}`;
      msg += `${pos} <b>${esc(t.teamName)}</b> — ${t.points}P | ${t.played}O ${t.won}G ${t.drawn}B ${t.lost}M | ${t.goalsFor}:${t.goalsAgainst} (${gd})\n`;
    }

    return ctx.reply(msg, { parse_mode: 'HTML' });
  });

  // /simule [lig_id] — manuel maç
  bot.command('simule', async (ctx) => {
    if (!(await isAdmin(ctx))) return ctx.reply('❌ Yönetici yetkisi gerekli!');

    await ctx.reply('⏳ Maç simülasyonu başlıyor...');
    try {
      await simulateMatchDay(bot);
    } catch (err) {
      await ctx.reply(`❌ Simülasyon hatası: ${err.message}`);
    }
  });

  // /kanal — bu kanalı duyuru kanalı yap
  bot.command('kanal', async (ctx) => {
    if (!(await isAdmin(ctx))) return ctx.reply('❌ Yönetici yetkisi gerekli!');

    setAnnounceChannel(String(ctx.chat.id), String(ctx.chat.id));
    return ctx.reply(
      `✅ Bu kanal/grup duyuru kanalı olarak ayarlandı!\nMaç sonuçları buraya gönderilecek.`
    );
  });

};
