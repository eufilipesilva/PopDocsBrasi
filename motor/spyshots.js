const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const spec=JSON.parse(fs.readFileSync(process.argv[2]||'ovspec.json'));
const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
await p.goto(require('url').pathToFileURL(require('path').join(process.cwd(),'spy.html')).href);await p.evaluate(()=>document.fonts.load('700 100px Oswald'));await p.evaluate(()=>document.fonts.load('500 30px "IBM Plex Mono"'));await p.evaluate(()=>document.fonts.ready);
const C=fs.existsSync('cores.json')?JSON.parse(fs.readFileSync('cores.json')):{};await p.evaluate(C=>window.theme(C),C);
for(const s of spec){const d=`ov/${s.id}`;fs.mkdirSync(d,{recursive:true});
 for(let i=0;i<s.frames;i++){const pr=(i+0.5)/s.frames;await p.evaluate(([k,pr,P,i])=>window.ov(k,pr,P,i),[s.kind,pr,s.params||{},i]);
  await p.screenshot({path:`${d}/${String(i).padStart(3,'0')}.png`,omitBackground:true});}}
await b.close();console.log('ok')})();
