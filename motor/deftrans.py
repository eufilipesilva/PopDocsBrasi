"""Default transition for each boundary (scene i -> i+1). The Studio panel edits the result."""
KINDS = {  # name: (label for the panel, default duration in seconds)
 'zoom': ('Avanço com escurecimento', .4), 'dissolve': ('Dissolver', 1.0), 'cut': ('Corte seco', 0),
 'scan': ('Linha de scanner', .7), 'paper': ('Folha de papel deslizando', .6), 'flash': ('Flash de câmera', .4),
 'whip': ('Chicote com desfoque', .5), 'glitch': ('Glitch digital', .5),
 'redact': ('Tarja preta (censura)', .8), 'stamp': ('Carimbo CONFIDENCIAL', 1.0), 'terminal': ('Terminal de busca', 1.7),
 'decrypt': ('Descriptografando', .8), 'cctv': ('Câmera de vigilância', 1.2),
 'shred': ('Fragmentadora de papel', .9), 'pixel': ('Pixelado (identidade protegida)', .6), 'static': ('Sinal perdido (chuvisco)', .6),
 'enhance': ('Ampliar e melhorar imagem', 1.0), 'vhs': ('Fita VHS rebobinando', .8),
 'fingerprint': ('Impressão digital', 1.3),
 'search': ('Busca no banco de dados', 1.6)}
CORES_PADRAO = {'fundo': '#0B0B0B', 'texto': '#F2F2F2', 'destaque': '#F2F2F2', 'papel': '#EDEDED', 'fotos': 'pb'}
PALETAS = {  # ready-made color sets offered in the Studio
 'Dossiê (padrão)': CORES_PADRAO,
 'Alerta vermelho': {'fundo': '#0B0B0B', 'texto': '#F2F2F2', 'destaque': '#E0443B', 'papel': '#EDEDED', 'fotos': 'pb'},
 'Arquivo sépia': {'fundo': '#15110C', 'texto': '#F1E6D0', 'destaque': '#D2A85A', 'papel': '#E9DFC8', 'fotos': 'tom'},
 'Noite azul': {'fundo': '#0A0F1A', 'texto': '#EAF0F7', 'destaque': '#4FB3FF', 'papel': '#E6ECF2', 'fotos': 'tom'},
 'Terminal verde': {'fundo': '#060B07', 'texto': '#E3F2E6', 'destaque': '#3DDC84', 'papel': '#E8EFE9', 'fotos': 'pb'},
 'Ouro e preto': {'fundo': '#0D0B08', 'texto': '#F4EFE6', 'destaque': '#E2B13C', 'papel': '#EFE8DA', 'fotos': 'pb'},
 'Cores originais': {'fundo': '#0B0B0B', 'texto': '#F2F2F2', 'destaque': '#F2F2F2', 'papel': '#EDEDED', 'fotos': 'cor'}}
def default_transitions(S, cfg):
    ch = [i for i, s in enumerate(S) if s['t'] == 'chapter']; arch = 'ARQUIVO CONFIDENCIAL'   # the archive number is internal only: never shown in the video
    slug = cfg.get('slug', 'dossie'); T = []
    for i in range(len(S) - 1):
        a, b = S[i]['t'], S[i + 1]['t']; k, P = 'zoom', {}
        if b == 'end': k = 'dissolve'
        elif b == 'chapter':
            n = S[i + 1].get('num', '')
            if ch.index(i + 1) % 2 == 0: k, P = 'decrypt', {'text': f'CAPÍTULO {n}', 'sub': cfg.get('brand', 'POPDOCSBRASIL · DOSSIÊ')}
            else: k, P = 'terminal', {'lines': [f'> acessar /arquivos/popdocs/{slug}', f'> abrir capitulo_{n}.dossie'], 'ok': f'CAPÍTULO {n} ENCONTRADO'}
        elif a == 'chapter': k = 'scan'
        elif b == 'photo': k = 'flash'
        elif b == 'headline': k = 'paper'
        T.append({'from': i, 'to': i + 1, 'kind': k, 'params': P})
    return T
