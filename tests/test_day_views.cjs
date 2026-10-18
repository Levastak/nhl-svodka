/* Exercise the actual browser rendering functions without network or a DOM. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const context = vm.createContext({setInterval() {}, window: {}, document: {addEventListener() {}, querySelector() {return {addEventListener() {}}}}});
for (const file of ['site/core.js', 'site/views.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), context, {filename: file});
}
const run = code => vm.runInContext(code, context);
run(`
  D={results_date:'2026-10-17',week:[{id:1,date:'2026-10-17'},{id:2,date:'2026-10-17'}],
     daily:{date:'2026-10-17',auto:true,game_ids:[1],heroes:[{name:'Early Star',team:'WSH',pos:'R',line:'1+0'}]}};
  A={games:[{id:1,date:'2026-10-17',home:'WSH',away:'NJD',hs:4,as:2}]};
  BOX={date:'2026-10-17',games:[{id:1,players:[{}]},{id:2,players:[{}]}]};
`);
assert.equal(run('heroesSec()'), '');
assert.match(run('vResults()'), /Игровой день ещё не завершён/);
assert.match(run('vResults()'), /Завершённые матчи/);
run("A.games.push({id:2,date:'2026-10-17',home:'CHI',away:'DAL',hs:0,as:4})");
assert.equal(run('heroesSec()'), '', 'stale first-game selection stays hidden even after the last game');
run('D.daily.game_ids=[1,2]');
assert.match(run('heroesSec()'), /Герои игрового дня/);
assert.doesNotMatch(run('vResults()'), /Игровой день ещё не завершён/);
run("D.results_status={date:'2026-10-17',scheduled_ids:[1,2],finished_ids:[1]};D.week=[]");
assert.equal(run('heroesSec()'), '', 'official in-progress slate wins over archived scores');
run('D.results_status.finished_ids=[1,2]');
assert.match(run('heroesSec()'), /Герои игрового дня/, 'official slate survives rolling schedule');
run('BOX.games.pop()');
assert.equal(run('heroesSec()'), '', 'wait for the last protocol as well as the score');
console.log('Day rendering checks passed');
