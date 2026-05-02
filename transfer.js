const { searchPlayer, getLeagues } = require('../data/leagues');

function esc(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function estimateValue(player) {
  const ageFactor = player.age < 23 ? 1.5 : player.age < 27 ? 1.2 : player.age < 30 ? 1.0 : player.age < 33 ? 0.7 : 0.4;
  const posMultiplier = { ST: 1.3, CAM: 1.2, LW: 1.2, RW: 1.2, CM: 1.0, CB: 0.9, RB: 0.9, LB: 0.9, GK: 0.8 }[player.position] || 1;
  const raw = Math.pow((player.overall - 60) / 30, 2) * 150 * ageFactor * posMultiplier;
  return Math.round(Math.max(raw, 1) * 10) / 10;
}

function generateMarket() {
  const leagues = getLeagues();
  const allPlayers = [];
  for (const league of leagues) {
    for (const team of league.teams) {
      for (const player of team.players) {
        if (player.overall >= 75 && player.overall <= 85) {
          allPlayers.push({ player, team, league, value: estimateValue(player) });
        }
      }
    }
  }
  return allPlayers.sort(() => Math.random() - 0.5).slice(0, 8);
}

module.exports = (bot) => {

  // /transfer — yardım
  bot.command('transfer', async (ctx) => {
    return ctx.reply(
      '💰 <b>Transfer Sistemi</b>\n\n' +
      '/transferara &lt;oyuncu adı&gt; — Oyuncu ara\n' +
      '/oyuncu &lt;oyuncu adı&gt; — Oyuncu detayı\n' +
      '/pazar — Günlük transfer pazarı\n\n' +
      '<b>Örnekler:</b>\n' +
      '/transferara Haaland\n' +
      '/transferara Mbappe\n' +
      '/oyuncu Vinicius',
      { parse_mode: 'HTML' }
    );
  });

  // /transferara <oyuncu adı>
  bot.command('transferara', async (ctx) => {
    const query = ctx.message.text.split(' ').slice(1).join(' ').trim();
    if (!query) return ctx.reply('Kullanım: /transferara &lt;oyuncu adı&gt;', { parse_mode: 'HTML' });

    const results = searchPlayer(query);
    if (results.length === 0) {
      return ctx.reply(`❌ <b>${esc(query)}</b> için sonuç bulunamadı.`, { parse_mode: 'HTML' });
    }

    const shown = results.slice(0, 10);
    let msg = `🔍 <b>Transfer Araması: "${esc(query)}"</b>\n\n`;
    for (const r of shown) {
      const p = r.player;
      const val = estimateValue(p);
      msg += `<b>${esc(p.name)}</b> | ${p.position} | OVR: ${p.overall} | ${r.team.emoji} ${esc(r.team.shortName)} | 💰 €${val}M\n`;
    }
    if (results.length > 10) {
      msg += `\n<i>${results.length} sonuç bulundu, ilk 10 gösteriliyor</i>`;
    }

    return ctx.reply(msg, { parse_mode: 'HTML' });
  });

  // /oyuncu <oyuncu adı>
  bot.command('oyuncu', async (ctx) => {
    const query = ctx.message.text.split(' ').slice(1).join(' ').trim();
    if (!query) return ctx.reply('Kullanım: /oyuncu &lt;oyuncu adı&gt;', { parse_mode: 'HTML' });

    const results = searchPlayer(query);
    if (results.length === 0) {
      return ctx.reply(`❌ <b>${esc(query)}</b> bulunamadı.`, { parse_mode: 'HTML' });
    }

    const { player, team, league } = results[0];
    const value = estimateValue(player);

    return ctx.reply(
      `👤 <b>${esc(player.name)}</b>\n\n` +
      `🏃 Mevki: <b>${player.position}</b>\n` +
      `🌍 Milliyet: ${esc(player.nationality)}\n` +
      `🎂 Yaş: ${player.age}\n` +
      `⭐ OVR: <b>${player.overall}</b>\n` +
      `💰 Tahmini Değer: €${value}M\n` +
      `💵 Maaş: £${(player.wage / 1000).toFixed(0)}K/hafta\n` +
      `🏟️ Mevcut Takım: ${team.emoji} ${esc(team.name)}\n` +
      `🏆 Lig: ${league.emoji} ${esc(league.name)}`,
      { parse_mode: 'HTML' }
    );
  });

  // /pazar — günlük market
  bot.command('pazar', async (ctx) => {
    const market = generateMarket();
    let msg = '💰 <b>Transfer Pazarı — Günlük Teklifler</b>\n\n';
    for (const item of market) {
      msg += `<b>${esc(item.player.name)}</b> (${item.player.position}) OVR: ${item.player.overall}\n`;
      msg += `  ${item.team.emoji} ${esc(item.team.shortName)} | 💰 €${item.value}M | 🌍 ${esc(item.player.nationality)}\n\n`;
    }
    msg += '<i>Detay için: /oyuncu &lt;isim&gt;</i>';
    return ctx.reply(msg, { parse_mode: 'HTML' });
  });

};
