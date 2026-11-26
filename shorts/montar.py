"""Monta pastas de Shorts a partir de episódios prontos, reaproveitando cenas e narração (mesmo texto = áudio em cache, sem gastar créditos).
uso: python -X utf8 shorts/montar.py [nome ...]   (sem nome: todos)"""
import json, os, shutil, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# nome: episódio, cenas (numeradas como no Estúdio), título do cabeçalho, nota opcional no cartão final
SHORTS = {
    'jensanity-short1': dict(ep='jensanity', cenas=[1, 2, 3, 52], titulo='JENSEN HUANG'),
    'jensanity-short2': dict(ep='jensanity', cenas=[7, 8, 9, 27], titulo='JENSEN HUANG'),
    'diesel-short1': dict(ep='diesel', cenas=[1, 2, 3, 5], titulo='RUDOLF DIESEL'),
    'diesel-short2': dict(ep='diesel', cenas=[48, 50, 51, 52], titulo='RUDOLF DIESEL',
                          nota='Se você precisa de ajuda, ligue 188 (CVV) ou acesse cvv.org.br'),
    'eastman-short1': dict(ep='eastman', cenas=[53, 54, 55, 56, 57], titulo='GEORGE EASTMAN'),
    'eastman-short2': dict(ep='eastman', cenas=[25, 26, 27, 28, 29], titulo='GEORGE EASTMAN'),
    # resumos escritos (texto aprovado pelo Filipe em 26/11/2026): (cena do episódio usada como imagem, narração nova)
    'diesel-escrito': dict(ep='diesel', titulo='RUDOLF DIESEL', nota='Se você precisa de ajuda, ligue 188 (CVV) ou acesse cvv.org.br', cenas=[
        (4, 'Setembro de 1913. Rudolf Diesel, o nome que está em quase todo posto do Brasil, embarca num navio rumo à Inglaterra.'),
        (3, 'Pede para ser acordado às seis e quinze. Nunca foi acordado. A cama estava intacta.'),
        (42, 'Dias depois, um corpo é avistado no mar, e o filho reconhece os objetos dos bolsos.'),
        (45, 'Logo vem outra notícia: Diesel estava falido.'),
        (48, 'A maioria dos biógrafos fala em suicídio.'),
        (50, 'Mas uma manchete da época dizia que ele foi jogado ao mar.'),
        (53, 'E há quem defenda que ele foi levado em segredo para o Canadá. Nenhuma prova confirmou essas versões.'),
        (60, 'Desespero, crime ou fuga? No dossiê completo, eu mostro o que cada versão tem de prova, e o que não tem. Assiste no canal e me diz qual é a sua.')]),
    'eastman-escrito': dict(ep='eastman', titulo='GEORGE EASTMAN', cenas=[
        (16, 'Em 1877, um bancário de 23 anos compra uma câmera para uma viagem que nunca fez.'),
        (17, 'Cada foto exigia uma placa de vidro preparada na hora.'),
        (22, 'Ele fica obcecado: experiências na cozinha da mãe, 469 tentativas fracassadas, noites dormindo na fábrica.'),
        (4, 'O nome dele: George Eastman. O nome que ele inventou: Kodak.'),
        (29, 'Você aperta o botão, nós fazemos o resto.'),
        (53, 'Em 1975, um engenheiro da Kodak monta a primeira câmera digital autônoma do mundo.'),
        (56, 'Segundo ele, a diretoria respondeu: que bonitinho, mas não conte para ninguém.'),
        (59, 'Em 2012, a Kodak pede recuperação judicial.'),
        (65, 'Como a empresa que inventou a câmera digital foi parar na recuperação judicial? A resposta é mais complicada do que parece, e está no dossiê completo, no canal.')]),
}
for nome in (sys.argv[1:] or SHORTS):
    c = SHORTS[nome]; SRC = os.path.join(R, 'videos', c['ep']); cenas = c['cenas']
    cfg = json.load(open(f'{SRC}/video.json')); S = json.load(open(f'{SRC}/scenes.json')); T = json.load(open(f'{SRC}/transitions.json'))
    orig = {(t['from'], t['to']): t for t in T}
    D = os.path.join(R, 'shorts', nome); os.makedirs(D, exist_ok=True)
    for sub in ('img', 'audio', 'musica'):
        if os.path.exists(f'{SRC}/{sub}') and not os.path.exists(f'{D}/{sub}'): shutil.copytree(f'{SRC}/{sub}', f'{D}/{sub}')
    shutil.copy(f'{SRC}/fotos.json', D)
    v = dict(cfg, slug=nome)
    if v.get('musicas'): v['musicas'] = [dict(v['musicas'][0], cena=1)]   # um Short usa só a primeira música
    json.dump(v, open(f'{D}/video.json', 'w'), ensure_ascii=False, indent=1)
    json.dump([dict(S[k[0] - 1], n=k[1]) if isinstance(k, tuple) else S[k - 1] for k in cenas], open(f'{D}/scenes.json', 'w'), ensure_ascii=False, indent=1)
    cenas = [k[0] if isinstance(k, tuple) else k for k in cenas]
    tr = []
    for k in range(len(cenas) - 1):
        a, b = cenas[k] - 1, cenas[k + 1] - 1
        t = dict(orig.get((a, b), {'kind': 'zoom', 'params': {}}))
        if t['kind'] in ('decrypt', 'terminal') and t.get('params'): t = {'kind': 'zoom', 'params': {}}   # textos de capítulo não cabem num Short
        t['from'] = k; t['to'] = k + 1; tr.append(t)
    json.dump(tr, open(f'{D}/transitions.json', 'w'), ensure_ascii=False, indent=1)
    json.dump(dict(episodio=c['ep'], kicker='POPDOCSBRASIL · DOSSIÊ', titulo=c['titulo'], nota=c.get('nota', '')), open(f'{D}/short.json', 'w'), ensure_ascii=False)
    print(nome, cenas, [t['kind'] for t in tr])
