const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const ONLY=process.argv.slice(2).map(Number);const S=JSON.parse(fs.readFileSync('scenes.json'));const P=JSON.parse(fs.readFileSync('plan.json'));
const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
await p.goto(require('url').pathToFileURL(require('path').join(process.cwd(),'frame.html')).href);await p.evaluate(M=>{window.META=M},JSON.parse(fs.readFileSync('meta.json')));await p.evaluate(()=>document.fonts.ready);fs.mkdirSync('png',{recursive:true});fs.mkdirSync('subs',{recursive:true});
for(let i=0;i<S.length;i++){if(ONLY.length&&!ONLY.includes(i))continue;for(let k=0;k<P[i].steps.length;k++){await p.evaluate(([s,k])=>window.draw(s,k),[S[i],k]);await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(40);
 await p.screenshot({path:`png/${String(i).padStart(2,'0')}_${k}.png`,omitBackground:true});}
 // extra photos of the scene: the same states, with the caption, credit and date of each photo
 for(let j=0;j<(S[i].fundos||[]).length;j++){const x=S[i].fundos[j];const s2=Object.assign({},S[i],{credit:x.credit,date:x.date||''});if('cap' in S[i]&&S[i].t!=='title')s2.cap=x.cap;
  for(let k=0;k<P[i].steps.length;k++){await p.evaluate(([s,k])=>window.draw(s,k),[s2,k]);await p.waitForTimeout(40);await p.screenshot({path:`png/${String(i).padStart(2,'0')}_f${j+1}_${k}.png`,omitBackground:true});}}
 for(let m=0;m<P[i].subs.length;m++){await p.evaluate(t=>window.sub(t),P[i].subs[m][2]);await p.screenshot({path:`subs/${String(i).padStart(2,'0')}_${m}.png`,omitBackground:true,clip:{x:0,y:780,width:1920,height:300}});}}
await b.close();console.log('ok')})();
