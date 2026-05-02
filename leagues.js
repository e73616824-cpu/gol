const premierLeague = require('./pl_teams');
const { laLiga, bundesliga, serieA } = require('./other_leagues');
const { ligue1, eredivisie, primeiraLiga } = require('./more_leagues');

// Top 10 Leagues
const ALL_LEAGUES = [
  premierLeague,   // 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League
  laLiga,          // 🇪🇸 La Liga
  bundesliga,      // 🇩🇪 Bundesliga
  serieA,          // 🇮🇹 Serie A
  ligue1,          // 🇫🇷 Ligue 1
  eredivisie,      // 🇳🇱 Eredivisie
  primeiraLiga,    // 🇵🇹 Primeira Liga
];

function getLeagues() {
  return ALL_LEAGUES;
}

function getLeagueById(id) {
  return ALL_LEAGUES.find(l => l.id === id);
}

function getTeamById(teamId) {
  for (const league of ALL_LEAGUES) {
    const team = league.teams.find(t => t.id === teamId);
    if (team) return { team, league };
  }
  return null;
}

function getAllTeams() {
  return ALL_LEAGUES.flatMap(l => l.teams.map(t => ({ ...t, leagueId: l.id, leagueName: l.name })));
}

function getPlayerById(playerId) {
  for (const league of ALL_LEAGUES) {
    for (const team of league.teams) {
      const player = team.players.find(p => p.id === playerId);
      if (player) return { player, team, league };
    }
  }
  return null;
}

function searchPlayer(name) {
  const results = [];
  const query = name.toLowerCase();
  for (const league of ALL_LEAGUES) {
    for (const team of league.teams) {
      for (const player of team.players) {
        if (player.name.toLowerCase().includes(query)) {
          results.push({ player, team, league });
        }
      }
    }
  }
  return results;
}

function searchTeam(name) {
  const query = name.toLowerCase();
  const results = [];
  for (const league of ALL_LEAGUES) {
    for (const team of league.teams) {
      if (team.name.toLowerCase().includes(query) || team.shortName.toLowerCase().includes(query)) {
        results.push({ team, league });
      }
    }
  }
  return results;
}

module.exports = { getLeagues, getLeagueById, getTeamById, getAllTeams, getPlayerById, searchPlayer, searchTeam };
