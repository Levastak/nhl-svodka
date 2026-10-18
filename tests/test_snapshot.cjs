/* Published data updates must not mix old protocols with new day results. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
let versions = ['v1', 'v1'], missing = null, calls = [], sheetOpen = false;
const payload = {
  data: {results_date:'2026-10-17',upcoming_date:'2026-10-18',standings:[],heads:{}},
  archive: {games:[]}, box: {games:[]}, model: {games:[]}, names_ru: {'New Player':'Новый Игрок'},
  edge: {findings:[]}, stories: [], news_live: {items:[{id:'same',title:'Заголовок',text:'Исправленный текст'}]}
};
const context = vm.createContext({setInterval() {}, window:{scrollY:0,scrollTo() {}},
  document:{hidden:false,addEventListener() {},querySelector() {return {hidden:!sheetOpen,addEventListener() {}}}},
  async fetch(url) {
    calls.push(url);
    const name = url.split('/').pop().split('?')[0];
    if(name === 'version.txt') return {ok:true,text:async()=>versions.length>1?versions.shift():versions[0]};
    return {ok:name !== missing,json:async()=>structuredClone(payload[name.replace('.json','')])};
  }});
for(const file of ['site/core.js','site/views.js','site/live.js']) {
  let code=fs.readFileSync(path.join(root,file),'utf8');
  if(file.endsWith('live.js'))code=code.slice(0,code.indexOf('/* ---------- запуск ---------- */'));
  vm.runInContext(code,context,{filename:file});
}
const run=code=>vm.runInContext(code,context);
run("D={results_date:'2026-10-16',upcoming_date:'2026-10-17'};function rerenderKeep(){};LIVE.old={state:'post'}");
(async()=>{
  assert.equal(await run('refreshSnapshot()'),true);
  assert.equal(run('D.results_date'),'2026-10-17');
  assert.equal(run('NL[0].text'),'Исправленный текст');
  assert.equal(run('Object.keys(LIVE).length'),0,'old scoreboard cleared on date change');
  calls=[];
  assert.equal(await run('refreshSnapshot()'),false);
  assert.equal(calls.length,1,'unchanged version only costs a tiny version request');
  versions=['v2','v2'];missing='box.json';
  assert.equal(await run('refreshSnapshot()'),false);
  assert.equal(run('SNAP_VERSION'),'v1','a failed protocol fetch does not accept a new snapshot');
  assert.equal(run('D.results_date'),'2026-10-17');
  missing=null;versions=['v2','v3'];
  assert.equal(await run('refreshSnapshot()'),false,'deploy during a batch is retried later');
  assert.equal(run('SNAP_VERSION'),'v1');
  versions=['v3','v3'];sheetOpen=true;calls=[];
  assert.equal(await run('refreshSnapshot()'),false);
  assert.equal(calls.length,0,'do not interrupt a reader in an open article');
  sheetOpen=false;
  assert.equal(await run('refreshSnapshot()'),true,'retry succeeds once the snapshot is complete');
  assert.equal(run('SNAP_VERSION'),'v3');
  run(`const edgeDay=days=>{const ref=[D.results_date,new Date().toLocaleDateString('en-CA',{timeZone:'America/New_York'})].sort().pop();return new Date(Date.parse(ref+'T12:00:00Z')-days*864e5).toISOString().slice(0,10)};`);
  assert.equal(run('freshEdge({date:edgeDay(4)})'),true);
  assert.equal(run('freshEdge({date:edgeDay(5)})'),false);
  assert.equal(run('freshEdge({})'),false);
  console.log('Snapshot refresh, failure recovery and EDGE freshness checks passed');
})().catch(error=>{console.error(error);process.exitCode=1});
