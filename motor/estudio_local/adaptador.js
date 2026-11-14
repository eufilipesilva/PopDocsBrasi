/* Estúdio PopDocs local: gives the page the same `claude.use('db')` / `claude.use('assets')` it has inside Claude,
   backed by the local server (servidor.py) and the video folders on disk. */
(function(){
  const KINDS = ['zoom','dissolve','cut','scan','paper','flash','whip','glitch','redact','stamp','terminal','decrypt','cctv','shred','pixel','static','enhance','vhs','fingerprint','search'];
  const S = {};            // slug -> {video, scenes:{id:doc}, fotos:{key:doc}}
  const L = {};            // path -> [listeners]
  const pending = {};      // temp upload id -> {data, type}
  const api = async (url, body) => {
    const r = await fetch(url, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    const j = await r.json().catch(()=>({}));
    if (!r.ok) throw {code:'unavailable', message:j.erro || ('erro ' + r.status)};
    return j;
  };
  const split = p => { const i = p.lastIndexOf('/'); return [p.slice(0, i), p.slice(i + 1)]; };
  const docSnap = (id, d) => ({id, exists: !!d, data: () => d ? JSON.parse(JSON.stringify(d)) : undefined, metadata:{fromCache:false, hasPendingWrites:false}});
  const qSnap = obj => { const docs = Object.entries(obj || {}).map(([id, d]) => docSnap(id, d)); return {docs, size:docs.length, empty:!docs.length, docChanges:()=>[], metadata:{fromCache:false, hasPendingWrites:false}}; };
  async function load(slug, force){ if (!S[slug] || force) S[slug] = await api('/api/video/' + slug); return S[slug]; }
  function target(path){ // -> [container object, key, slug, kind]
    const p = path.split('/');
    if (p[0] === 'videos' && p.length === 2) return [S[p[1]], 'video', p[1], 'video'];
    if (p[0] === 'videos' && p.length === 4) return [S[p[1]] && S[p[1]][p[2]], p[3], p[1], p[2]];
    return [null, null, null, null];
  }
  function emit(slug){
    const st = S[slug]; if (!st) return;
    (L['videos/' + slug] || []).forEach(fn => fn(docSnap(slug, st.video)));
    (L['videos/' + slug + '/scenes'] || []).forEach(fn => fn(qSnap(st.scenes)));
    (L['videos/' + slug + '/fotos'] || []).forEach(fn => fn(qSnap(st.fotos)));
  }
  const saveT = {};
  function scheduleSave(slug){
    clearTimeout(saveT[slug]);
    saveT[slug] = setTimeout(async () => {
      const st = S[slug];
      try { await api('/api/video/' + slug + '/salvar', {video: st.video, scenes: st.scenes, fotos: st.fotos}); }
      catch (e) { panel('Não consegui salvar no disco: ' + e.message, true); }
    }, 600);
  }
  async function write(path, data, replace){
    const [ctn, key, slug, kind] = target(path);
    if (!slug) throw {code:'invalid_argument', message:'caminho desconhecido'};
    await load(slug);
    const st = S[slug];
    if (kind === 'fotos' && data.asset && pending[data.asset]) {           // a new photo from the upload form
      const up = pending[data.asset]; delete pending[data.asset];
      const r = await api('/api/video/' + slug + '/foto', {key, data: up.data, cap: data.cap || '', credit: data.credit || '', license: data.license || ''});
      await load(slug, true); emit(slug); return;
    }
    if (kind === 'video') st.video = replace ? data : Object.assign({}, st.video, data);
    else { const box = st[kind]; box[key] = replace ? data : Object.assign({}, box[key] || {}, data); }
    emit(slug);
    scheduleSave(slug);
  }
  function panel(text){ window.dispatchEvent(new CustomEvent('popdocs-erro', {detail: text})); }
  async function flush(slug){   // write pending edits to disk now
    clearTimeout(saveT[slug]); const st = S[slug]; if (!st) return;
    await api('/api/video/' + slug + '/salvar', {video: st.video, scenes: st.scenes, fotos: st.fotos});
  }
  // What only the local Studio can do. The page (estudio.html) draws the interface for it.
  window.POPDOCS_LOCAL = {
    render: async (slug, modo) => { await flush(slug); return api('/api/render/' + slug, {modo: modo || 'final'}); },
    status: slug => api('/api/render/' + slug),
    cancel: slug => api('/api/render/' + slug + '/cancelar', {}),
    youtube: (slug, texto) => api('/api/video/' + slug + '/youtube', {texto}),
    reload: async slug => { await flush(slug); await load(slug, true); emit(slug); }
  };
  const db = {
    doc(path){
      const [col, id] = split(path);
      return {id, path,
        get: async () => { if (path === 'config/studio') return docSnap(id, cfg()); const [c, k, slug] = target(path); await load(slug); const t = target(path); return docSnap(id, k === 'video' ? S[slug].video : t[0] && t[0][k]); },
        set: d => write(path, d, true), update: d => write(path, d, false), delete: async () => write(path, {deleted:true}, false),
        acquire: async () => ({acquired:true}),
        onSnapshot(fn, err){
          if (path === 'config/studio') { setTimeout(() => fn(docSnap(id, cfg())), 0); return () => {}; }
          (L[path] = L[path] || []).push(fn);
          const slug = path.split('/')[1];
          load(slug).then(() => emit(slug)).catch(e => err && err(e));
          return () => { L[path] = (L[path] || []).filter(f => f !== fn); };
        },
        collection: sub => db.collection(path + '/' + sub)};
    },
    collection(path){
      return {path, doc: id => db.doc(path + '/' + (id || ('s' + Date.now().toString(36)))),
        add: async d => { const id = 's' + Date.now().toString(36); await write(path + '/' + id, d, true); return db.doc(path + '/' + id); },
        where(){ return this; }, orderBy(){ return this; }, limit(){ return this; },
        get: async () => qSnap({}),
        onSnapshot(fn, err){
          if (path === 'videos') {
            api('/api/videos').then(list => fn(qSnap(Object.fromEntries(list.map(v => [v.id, v]))))).catch(e => err && err(e));
            return () => {};
          }
          (L[path] = L[path] || []).push(fn);
          const slug = path.split('/')[1];
          load(slug).then(() => emit(slug)).catch(e => err && err(e));
          return () => { L[path] = (L[path] || []).filter(f => f !== fn); };
        }};
    }
  };
  function cfg(){ return {previews: Object.fromEntries(KINDS.map(k => [k, '/transicoes/' + k + '.mp4']))}; }
  const assets = {
    upload: file => new Promise((res, rej) => { const fr = new FileReader();
      fr.onload = () => { const id = 'tmp' + Math.random().toString(36).slice(2, 10); pending[id] = {data: fr.result, type: file.type}; res({id, url: fr.result, sizeBytes: file.size, contentType: file.type}); };
      fr.onerror = () => rej({code:'invalid_request', message:'não consegui ler o arquivo'}); fr.readAsDataURL(file); }),
    list: async () => ({assets: [], usage: {files:0, bytes:0, maxFiles:0, maxBytes:0}}), delete: async () => ({deleted:false})
  };
  window.claude = {use: async name => name === 'db' ? db : name === 'assets' ? assets : null};
})();
