const { getLeagueById } = require('./data/leagues');
const {
  getLeagueState, saveLeagueState, addMatchToLog,
  getGuildData, saveGuildData, getAllGuildIds
} = require('./utils/dataManager');

function esc(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ─── Maç Simülasyonu ──────────────────────────────────────────────────────────

function getTeamStrength(team) {
  const players = team.players || [];
  if (players.length === 0) return 70;
  return players.reduce((sum, p) => sum + (p.overall || 70), 0) / players.length;
}

function simulateGoals(strength, oppStrength) {
  const diff = strength - oppStrength;
  const base = 1.5 + (diff / 30);
  const maxGoals = Math.max(0, Math.round(base + (Math.random() * 2.5)));
  return Math.max(0, Math.min(maxGoals, 7));
}

function pickScorer(players) {
  const weights = { ST: 40, LW: 25, RW: 25, CAM: 20, CM: 10, LB: 3, RB: 3, CB: 2, GK: 0 };
  const pool = [];
  for (const p of players) {
    const w = weights[p.position] || 5;
    for (let i = 0; i < w; i++) pool.push(p.name);
  }
  if (pool.length === 0) return players[Math.floor(Math.random() * players.length)].name;
  return pool[Math.floor(Math.random() * pool.length)];
}

function generateMatchEvents(homeTeam, awayTeam, homeGoals, awayGoals) {
  const events = [];
  const usedMinutes = new Set();

  const getMinute = () => {
    let m;
    do { m = Math.floor(Math.random() * 90) + 1; } while (usedMinutes.has(m));
    usedMinutes.add(m);
    return m;
  };

  for (let i = 0; i < homeGoals; i++)
    events.push({ type: 'goal', team: homeTeam.shortName, player: pickScorer(homeTeam.players), minute: getMinute() });
  for (let i = 0; i < awayGoals; i++)
    events.push({ type: 'goal', team: awayTeam.shortName, player: pickScorer(awayTeam.players), minute: getMinute() });

  const cardCount = Math.floor(Math.random() * 4) + 1;
  for (let i = 0; i < cardCount; i++) {
    const team = Math.random() > 0.5 ? homeTeam : awayTeam;
    const player = team.players[Math.floor(Math.random() * team.players.length)];
    events.push({ type: 'yellow', team: team.shortName, player: player.name, minute: getMinute() });
  }

  if (Math.random() < 0.1) {
    const team = Math.random() > 0.5 ? homeTeam : awayTeam;
    const player = team.players[Math.floor(Math.random() * team.players.length)];
    events.push({ type: 'red', team: team.shortName, player: player.name, minute: getMinute() });
  }

  return events.sort((a, b) => a.minute - b.minute);
}

function buildMatchMessage(homeTeam, awayTeam, result) {
  const lines = [];
  lines.push(`⚽ <b>MAÇA BAŞLANIYOR!</b>`);
  lines.push(`🏟️ <i>${esc(homeTeam.stadium || 'Ev Sahası')}</i>\n`);

  for (const ev of result.events) {
    const min = `<code>${String(ev.minute).padStart(2, ' ')}'</code>`;
    if (ev.type === 'goal') {
      const emoji = ev.team === homeTeam.shortName ? '🟢' : '🔴';
      lines.push(`${min} ${emoji} <b>GOL! ${esc(ev.player)}</b> (${esc(ev.team)})`);
    } else if (ev.type === 'yellow') {
      lines.push(`${min} 🟡 Sarı kart: ${esc(ev.player)} (${esc(ev.team)})`);
    } else if (ev.type === 'red') {
      lines.push(`${min} 🔴 Kırmızı kart: ${esc(ev.player)} (${esc(ev.team)})`);
    }
  }

  lines.push(`\n⏱️ <b>MAÇIN SONU!</b>`);
  lines.push(
    `${homeTeam.emoji || ''} <b>${esc(homeTeam.shortName)} ${result.homeGoals} – ${result.awayGoals} ${esc(awayTeam.shortName)}</b> ${awayTeam.emoji || ''}`
  );

  if (result.homeGoals > result.awayGoals)
    lines.push(`🏆 <b>${esc(homeTeam.shortName)}</b> kazandı!`);
  else if (result.awayGoals > result.homeGoals)
    lines.push(`🏆 <b>${esc(awayTeam.shortName)}</b> kazandı!`);
  else
    lines.push(`🤝 <b>Beraberlik!</b>`);

  return lines.join('\n');
}

function simulateMatch(homeTeam, awayTeam) {
  const homeStr = getTeamStrength(homeTeam);
  const awayStr = getTeamStrength(awayTeam);
  const homeAdv = 3;
  const homeGoals = simulateGoals(homeStr + homeAdv, awayStr);
  const awayGoals = simulateGoals(awayStr, homeStr + homeAdv);
  const events = generateMatchEvents(homeTeam, awayTeam, homeGoals, awayGoals);

  return {
    homeTeam: homeTeam.shortName,
    awayTeam: awayTeam.shortName,
    homeGoals,
    awayGoals,
    events,
    timestamp: Date.now()
  };
}

// ─── Fikstür Üretimi ──────────────────────────────────────────────────────────

function generateFixtures(teams) {
  const fixtures = [];
  const n = teams.length;

  for (let round = 0; round < (n - 1) * 2; round++) {
    const roundFixtures = [];
    for (let i = 0; i < Math.floor(n / 2); i++) {
      const home = (round + i) % (n - 1);
      const away = (n - 1 - i + round) % (n - 1);
      const fixedHome = i === 0 ? n - 1 : home;
      const fixedAway = i === 0 ? away : away;

      if (round < n - 1) {
        roundFixtures.push({ home: teams[fixedHome].id, away: teams[fixedAway].id });
      } else {
        roundFixtures.push({ home: teams[fixedAway].id, away: teams[fixedHome].id });
      }
    }
    fixtures.push({ round: round + 1, matches: roundFixtures });
  }

  return fixtures;
}

function initLeague(guildId, leagueId) {
  const leagueData = getLeagueById(leagueId);
  if (!leagueData) throw new Error(`Lig bulunamadı: ${leagueId}`);

  const teams = leagueData.teams;
  const fixtures = generateFixtures(teams);

  const standings = {};
  for (const team of teams) {
    standings[team.id] = {
      teamId: team.id,
      teamName: team.shortName,
      played: 0, won: 0, drawn: 0, lost: 0,
      goalsFor: 0, goalsAgainst: 0, goalDiff: 0, points: 0
    };
  }

  const state = {
    leagueId,
    leagueName: leagueData.name,
    status: 'active',
    currentRound: 0,
    totalRounds: fixtures.length,
    fixtures,
    standings,
    startedAt: Date.now(),
    lastMatchDay: null
  };

  saveLeagueState(guildId, leagueId, state);
  return state;
}

function updateStandings(standings, homeId, awayId, homeGoals, awayGoals) {
  const h = standings[homeId];
  const a = standings[awayId];
  if (!h || !a) return;

  h.played++; a.played++;
  h.goalsFor += homeGoals; h.goalsAgainst += awayGoals;
  a.goalsFor += awayGoals; a.goalsAgainst += homeGoals;
  h.goalDiff = h.goalsFor - h.goalsAgainst;
  a.goalDiff = a.goalsFor - a.goalsAgainst;

  if (homeGoals > awayGoals) { h.won++; h.points += 3; a.lost++; }
  else if (awayGoals > homeGoals) { a.won++; a.points += 3; h.lost++; }
  else { h.drawn++; a.drawn++; h.points++; a.points++; }
}

// ─── Otomatik Maç Günü ────────────────────────────────────────────────────────

async function simulateMatchDay(bot) {
  const guildIds = getAllGuildIds();

  for (const guildId of guildIds) {
    try {
      const guildData = getGuildData(guildId);
      const chatId = guildData.announceChannel || guildId;

      for (const [leagueId, state] of Object.entries(guildData.leagues || {})) {
        if (state.status !== 'active') continue;

        const nextRound = state.currentRound + 1;

        // Lig bitti
        if (nextRound > state.totalRounds) {
          state.status = 'finished';
          saveLeagueState(guildId, leagueId, state);

          const sorted = Object.values(state.standings)
            .sort((a, b) => b.points - a.points || b.goalDiff - a.goalDiff);

          await bot.telegram.sendMessage(
            chatId,
            `🏆 <b>${esc(state.leagueName)} — ŞAMPİYON!</b>\n\n` +
            `👑 <b>${esc(sorted[0].teamName)}</b> şampiyon oldu!\n\n` +
            `🥇 ${esc(sorted[0]?.teamName)} — ${sorted[0]?.points} puan\n` +
            `🥈 ${esc(sorted[1]?.teamName)} — ${sorted[1]?.points} puan\n` +
            `🥉 ${esc(sorted[2]?.teamName)} — ${sorted[2]?.points} puan`,
            { parse_mode: 'HTML' }
          );
          continue;
        }

        const leagueData = getLeagueById(leagueId);
        if (!leagueData) continue;

        const roundData = state.fixtures[nextRound - 1];
        if (!roundData) continue;

        await bot.telegram.sendMessage(
          chatId,
          `${leagueData.emoji} <b>${esc(state.leagueName)} — Hafta ${nextRound}</b>\n\nMaçlar simüle ediliyor... ⚽`,
          { parse_mode: 'HTML' }
        );

        for (const match of roundData.matches) {
          const homeTeamData = leagueData.teams.find(t => t.id === match.home);
          const awayTeamData = leagueData.teams.find(t => t.id === match.away);
          if (!homeTeamData || !awayTeamData) continue;

          const result = simulateMatch(homeTeamData, awayTeamData);
          updateStandings(state.standings, match.home, match.away, result.homeGoals, result.awayGoals);
          addMatchToLog(guildId, { ...result, league: state.leagueName });

          const msg = buildMatchMessage(homeTeamData, awayTeamData, result);
          await bot.telegram.sendMessage(chatId, msg, { parse_mode: 'HTML' });
          await new Promise(r => setTimeout(r, 1500));
        }

        state.currentRound = nextRound;
        state.lastMatchDay = Date.now();
        saveLeagueState(guildId, leagueId, state);

        // Hafta sonu mini puan durumu
        const medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'];
        const sorted = Object.values(state.standings)
          .sort((a, b) => b.points - a.points || b.goalDiff - a.goalDiff)
          .slice(0, 5);

        const standText = sorted.map((t, i) =>
          `${medals[i]} <b>${esc(t.teamName)}</b> — ${t.points} puan (${t.won}G ${t.drawn}B ${t.lost}M)`
        ).join('\n');

        await bot.telegram.sendMessage(
          chatId,
          `📊 <b>${esc(state.leagueName)} — Hafta ${nextRound} Sonrası (İlk 5)</b>\n\n${standText}`,
          { parse_mode: 'HTML' }
        );
      }
    } catch (err) {
      console.error(`Chat ${guildId} match day error:`, err.message);
    }
  }
}

module.exports = { simulateMatch, simulateMatchDay, initLeague, generateFixtures, getTeamStrength };
