// Renderiza PNGs transparentes a partir de HTML. uso: node png.js lista.json  ([{html, out, w, h}])
const {chromium} = require('playwright'); const fs = require('fs');
(async () => {
  const L = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch();
  for (const it of L) {
    const p = await b.newPage({viewport: {width: it.w, height: it.h}});
    await p.setContent(it.html, {waitUntil: 'networkidle'});
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({path: it.out, omitBackground: true}); await p.close();
  }
  await b.close();
})();
