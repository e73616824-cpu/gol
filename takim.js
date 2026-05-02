const { getUserTeam, setUserTeam } = require('../utils/dataManager');
const { getLeagues, getLeagueById, getTeamById, searchTeam } = require('../data/leagues');

function esc(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

module.exports = (bot) => {

  // /takim — kendi takımını göster
  bot.command('takim', async (ctx) => {
    const myTeamId = getUserTeam(String(ctx.chat.id), String(ctx.from.id));
    if (!myTeamId) {
      return ctx.reply(
        '⚽ <b>Takım Seç</b>\n\n' +
        '/takimsec &lt;takım adı&gt; — Takım seç\n' +
        '/kadro [takım adı] — Kadro görüntüle\n' +
        '/takimlar [lig_id] — Tüm takımlar\n\n' +
        '<b>Örnek:</b>\n' +
        '/takimsec Real Madrid\n' +
        '/takimsec Manchester City',
        { parse_mode: 'HTML' }
      );
    }

    const teamData = getTeamById(myTeamId);
    if (!teamData) return ctx.reply('❌ Takım bulunamadı.');

    const { team, league } = teamData;
    const avgOverall = Math.round(team.players.reduce((s, p) => s + p.overall, 0) / team.players.length);

    return ctx.reply(
      `${team.emoji} <b>${esc(team.name)}</b>\n\n` +
      `🏆 Lig: ${league.emoji} ${esc(league.name)}\n` +
      `🏟️ Stat: ${esc(team.stadium)}\n` +
      `👔 Teknik Direktör: ${esc(team.manager)}\n` +
      `👥 Kadro: ${team.players.length} oyuncu\n` +
      `⭐ Ort. Güç: ${avgOverall} OVR\n` +
      `💰 Bütçe: €${(team.budget / 1000000).toFixed(0)}M\n\n` +
      `/kadro — Kadroyu görüntüle\n` +
      `/takimsec &lt;ad&gt; — Takım değiştir`,
      { parse_mode: 'HTML' }
    );
  });

  // /takimsec <takım adı>
  bot.command('takimsec', async (ctx) => {
    const teamName = ctx.message.text.split(' ').slice(1).join(' ').trim();
    if (!teamName) {
      return ctx.reply(
        'Kullanım: /takimsec &lt;takım adı&gt;\nÖrnek: /takimsec Manchester City',
        { parse_mode: 'HTML' }
      );
    }

    const results = searchTeam(teamName);
    if (results.length === 0) {
      return ctx.reply(
        `❌ <b>${esc(teamName)}</b> bulunamadı.\nTüm takımlar için: /takimlar`,
        { parse_mode: 'HTML' }
      );
    }

    const { team, league } = results[0];
    setUserTeam(String(ctx.chat.id), String(ctx.from.id), team.id);

    return ctx.reply(
      `✅ <b>Takımın Seçildi: ${team.emoji} ${esc(team.name)}</b>\n\n` +
      `🏆 Lig: ${league.emoji} ${esc(league.name)}\n` +
      `🏟️ Stat: ${esc(team.stadium)}\n` +
      `👔 Teknik Direktör: ${esc(team.manager)}\n` +
      `👥 Kadro: ${team.players.length} oyuncu\n` +
      `💰 Bütçe: €${(team.budget / 1000000).toFixed(0)}M\n\n` +
      `Artık antrenman yapabilir ve transfer izleyebilirsin!\n` +
      `/antrenman — Antrenman yapmaya başla`,
      { parse_mode: 'HTML' }
    );
  });

  // /kadro [takım adı]
  bot.command('kadro', async (ctx) => {
    const teamName = ctx.message.text.split(' ').slice(1).join(' ').trim();
    let teamData;

    if (teamName) {
      const results = searchTeam(teamName);
      if (results.length === 0) {
        return ctx.reply(`❌ <b>${esc(teamName)}</b> bulunamadı.`, { parse_mode: 'HTML' });
      }
      teamData = results[0];
    } else {
      const myTeamId = getUserTeam(String(ctx.chat.id), String(ctx.from.id));
      if (!myTeamId) {
        return ctx.reply('❌ Önce bir takım seç: /takimsec &lt;takım adı&gt;', { parse_mode: 'HTML' });
      }
      teamData = getTeamById(myTeamId);
      if (!teamData) return ctx.reply('❌ Takım verisi bulunamadı.');
    }

    const { team, league } = teamData;
    const posOrder = ['GK', 'CB', 'RB', 'LB', 'DM', 'CM', 'CAM', 'RW', 'LW', 'ST'];
    const posEmoji = { GK: '🧤', CB: '🛡️', RB: '🛡️', LB: '🛡️', CM: '⚙️', CAM: '🎯', DM: '🛡️', RW: '⚡', LW: '⚡', ST: '🔥' };

    const byPosition = {};
    for (const p of team.players) {
      if (!byPosition[p.position]) byPosition[p.position] = [];
      byPosition[p.position].push(p);
    }

    let msg = `${team.emoji} <b>${esc(team.name)} — Kadro</b>\n${league.emoji} ${esc(league.name)}\n\n`;

    for (const pos of posOrder) {
      const players = byPosition[pos];
      if (!players || players.length === 0) continue;
      msg += `${posEmoji[pos] || '⚽'} <b>${pos}</b>\n`;
      for (const p of players) {
        msg += `  • ${esc(p.name)} (${esc(p.nationality)}) — OVR: <b>${p.overall}</b>\n`;
      }
      msg += '\n';
    }

    if (msg.length > 4096) msg = msg.substring(0, 4000) + '\n<i>...(liste kısaltıldı)</i>';

    return ctx.reply(msg, { parse_mode: 'HTML' });
  });

  // /takimlar [lig_id]
  bot.command('takimlar', async (ctx) => {
    const leagueId = ctx.message.text.split(' ')[1]?.toLowerCase();

    if (!leagueId) {
      const leagues = getLeagues();
      let msg = '🌍 <b>Tüm Ligler</b>\n\n';
      for (const l of leagues) {
        msg += `${l.emoji} <b>${esc(l.name)}</b> — <code>${l.id}</code> (${l.teams.length} takım)\n`;
      }
      msg += '\nDetay için: /takimlar &lt;lig_id&gt;';
      return ctx.reply(msg, { parse_mode: 'HTML' });
    }

    const league = getLeagueById(leagueId);
    if (!league) return ctx.reply(`❌ <b>${esc(leagueId)}</b> ligi bulunamadı.`, { parse_mode: 'HTML' });

    let msg = `${league.emoji} <b>${esc(league.name)} — Takımlar</b>\n\n`;
    for (const t of league.teams) {
      msg += `${t.emoji} <b>${esc(t.name)}</b>\n`;
      msg += `   🏟️ ${esc(t.stadium)} | 👔 ${esc(t.manager)}\n\n`;
    }

    return ctx.reply(msg, { parse_mode: 'HTML' });
  });

};
