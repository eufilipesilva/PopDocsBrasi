// Gera banner.png (2560x1440) e foto-perfil.png (800x800) a partir de arte.html
const path = require('path');
const { chromium } = require(path.join(__dirname, '..', 'motor', 'node_modules', 'playwright'));
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 2560, height: 2400 } });
  await p.goto('file://' + path.join(__dirname, 'arte.html').replace(/\\/g, '/'));
  await p.waitForTimeout(2500);
  await (await p.$('#banner')).screenshot({ path: path.join(__dirname, 'banner.png') });
  await (await p.$('#avatar')).screenshot({ path: path.join(__dirname, 'foto-perfil.png') });
  await b.close();
})();
