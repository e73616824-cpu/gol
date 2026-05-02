const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '../../data');

function ensureDir() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
}

function getGuildData(guildId) {
  ensureDir();
  const file = path.join(DATA_DIR, `guild_${guildId}.json`);
  if (!fs.existsSync(file)) {
    const defaultData = {
      guildId,
      leagues: {},
      userTeams: {},
      transfers: [],
      trainingSessions: {},
      matchLog: [],
      announceChannel: null,
      adminRoles: [],
      createdAt: Date.now()
    };
    fs.writeFileSync(file, JSON.stringify(defaultData, null, 2));
    return defaultData;
  }
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function saveGuildData(guildId, data) {
  ensureDir();
  const file = path.join(DATA_DIR, `guild_${guildId}.json`);
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
}

function getAllGuildIds() {
  ensureDir();
  return fs.readdirSync(DATA_DIR)
    .filter(f => f.startsWith('guild_') && f.endsWith('.json'))
    .map(f => f.replace('guild_', '').replace('.json', ''));
}

function getUserTeam(guildId, userId) {
  const data = getGuildData(guildId);
  return data.userTeams[userId] || null;
}

function setUserTeam(guildId, userId, teamId) {
  const data = getGuildData(guildId);
  data.userTeams[userId] = teamId;
  saveGuildData(guildId, data);
}

function getLeagueState(guildId, leagueId) {
  const data = getGuildData(guildId);
  return data.leagues[leagueId] || null;
}

function saveLeagueState(guildId, leagueId, state) {
  const data = getGuildData(guildId);
  data.leagues[leagueId] = state;
  saveGuildData(guildId, data);
}

function addMatchToLog(guildId, matchResult) {
  const data = getGuildData(guildId);
  data.matchLog.unshift(matchResult);
  if (data.matchLog.length > 100) data.matchLog = data.matchLog.slice(0, 100);
  saveGuildData(guildId, data);
}

function getMatchLog(guildId, limit = 20) {
  const data = getGuildData(guildId);
  return data.matchLog.slice(0, limit);
}

function setAnnounceChannel(guildId, channelId) {
  const data = getGuildData(guildId);
  data.announceChannel = channelId;
  saveGuildData(guildId, data);
}

function getAnnounceChannel(guildId) {
  const data = getGuildData(guildId);
  return data.announceChannel;
}

function getTrainingData(guildId, userId) {
  const data = getGuildData(guildId);
  return data.trainingSessions[userId] || null;
}

function saveTrainingData(guildId, userId, trainingData) {
  const data = getGuildData(guildId);
  if (!data.trainingSessions) data.trainingSessions = {};
  data.trainingSessions[userId] = trainingData;
  saveGuildData(guildId, data);
}

function getCustomSquad(guildId, teamId) {
  const data = getGuildData(guildId);
  if (!data.customSquads) return null;
  return data.customSquads[teamId] || null;
}

function saveCustomSquad(guildId, teamId, squad) {
  const data = getGuildData(guildId);
  if (!data.customSquads) data.customSquads = {};
  data.customSquads[teamId] = squad;
  saveGuildData(guildId, data);
}

module.exports = {
  getGuildData,
  saveGuildData,
  getAllGuildIds,
  getUserTeam,
  setUserTeam,
  getLeagueState,
  saveLeagueState,
  addMatchToLog,
  getMatchLog,
  setAnnounceChannel,
  getAnnounceChannel,
  getTrainingData,
  saveTrainingData,
  getCustomSquad,
  saveCustomSquad,
};
