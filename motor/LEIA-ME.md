# Motor de vídeos do PopDocsBrasil

Ferramenta que transforma um roteiro aprovado em vídeo pronto para o YouTube: narração, cenas, fotos, transições, música, legendas e thumbnail.

- **Estúdio (mesa de montagem):** https://claude.ai/artifact/3txeBgjugpph9zRvP5Xq2x
- **Motor (código):** esta pasta, `/mnt/project-files/popdocs/motor/`
- **Vídeos:** `/mnt/project-files/popdocs/videos/<slug>/`

## Fluxo de um vídeo novo

1. **Tema.** Filipe diz o tema no chat do projeto.
2. **Pesquisa e roteiro.** Claude pesquisa e escreve o dossiê num Claude Doc, com todas as fontes. Fatos confirmados ficam separados de alegações, sempre com visão internacional. Filipe aprova.
3. **Montagem.** Claude cria a pasta do vídeo e as cenas, busca fotos públicas e gera a narração, depois envia tudo ao Estúdio.
4. **Ajustes.** Filipe mexe no Estúdio: texto, narração, foto, transição, ordem das cenas, thumbnail.
5. **Renderização.** Filipe toca em "Marcar para renderizar" e escreve "renderiza" no chat. Claude importa o Estúdio e roda o motor. O resultado (vídeo, legendas, thumbnail) vai para `saidas/` e as prévias do Estúdio são atualizadas.
6. **Publicação.** Claude escreve o título, a descrição com capítulos e o comentário fixado com as fontes.

## Pasta de um vídeo

| Arquivo | O que é |
|---|---|
| `video.json` | Título, textos de abertura e encerramento, voz, música, cores, thumbnail |
| `scenes.json` | As cenas em ordem: tipo, texto na tela, narração (`n`), foto (`bg`) |
| `transitions.json` | Uma transição por passagem de cena (`kind`, `dur`, `params`) |
| `fotos.json` + `img/` | Catálogo de fotos e vídeos com legenda, crédito, licença, origem e cor (`modo`) |
| `audio/` | Narração em cache, nomeada pelo texto. Só gera de novo, e gasta crédito, quando o texto muda |
| `musica/` | Trilha (fonte pública ou licença livre, com crédito) |
| `saidas/` | Vídeo final, legendas `.srt`, thumbnail |
| `historico/` | Cópia dos arquivos antes de cada importação do Estúdio |

### Tipos de cena

| Tipo | Campos |
|---|---|
| `headline` | Manchete: `outlet`, `head`, `mark` (trecho grifado), `url` |
| `quote` | Citação: `q`, `who`, `src` |
| `fact` | Fato: `kicker`, `big`, `sub`, `src` |
| `title` | Abertura, sem narração: `dur` |
| `chapter` | Capítulo: `num`, `name` |
| `timeline` | Linha do tempo: `kicker`, `ev` (pares data e texto), `cur` |
| `name` | Personagem: `name`, `role`, `src` |
| `status` | Situação: `rows` (pares assunto e situação), `src` |
| `cols` | Comparação: `cols` (pares título e texto), `src` |
| `photo` | Foto em tela cheia: `bg`, `cap`, `date`, `credit` |
| `end` | Encerramento com créditos |
| `clip` | Trecho de vídeo com o som original (citação): `bg` (vídeo em img/), `vin` (segundo de início), `dur` (duração), `cap` (o que mostra), `credit` ("Reprodução: TV X · data"), `date`, `tag` (padrão CITAÇÃO · TRECHO ORIGINAL), `som` (false desliga o som), `vol` (volume, 1 = normal) |

Qualquer cena (menos `photo`) pode receber `bg` para ganhar uma foto de fundo escurecida, com legenda e crédito no canto.

**Vídeo no lugar da foto.** Um arquivo `img/<chave>.mp4` (ou `.webm`, `.mov`) funciona como uma foto: a cena usa o vídeo como fundo, sem som, e repete se ele for mais curto que a cena. No `fotos.json` a entrada leva `"tipo": "video"`. O campo `vin` da cena diz em que segundo do vídeo começar. Só use vídeos de domínio público, com licença livre ou seus (Wikimedia Commons tem muitos, em `.webm`).

**Citação com som (`clip`).** O vídeo aparece numa janela com moldura, etiqueta, legenda e crédito. O som do próprio vídeo entra na mixagem e a música de fundo vai a zero durante o trecho (com rampa de 0,6 s). A cena não leva narração. Base legal: Lei 9.610/98, art. 46, III (citação para crítica ou análise, trecho curto, com autor e origem). Na prática: 3 a 8 segundos por trecho, poucos por vídeo, sempre comentados pela narração. O YouTube pode reivindicar a monetização pelo Content ID mesmo assim.

**Cor de cada foto.** `fotos.json` → `modo`: `pb` preto e branco, `cor` colorida, `tom` duas cores, ou vazio para seguir a opção do vídeo (`cores.fotos`).

### Transições

| Clássicas | Espionagem | Computador e arquivos |
|---|---|---|
| `zoom` avanço com escurecimento | `redact` tarja preta (censura) | `glitch` falha digital |
| `dissolve` dissolver | `stamp` carimbo CONFIDENCIAL | `terminal` terminal de busca |
| `cut` corte seco | `cctv` câmera de vigilância com mira | `decrypt` descriptografando |
| `scan` linha de scanner | `shred` fragmentadora de papel | `search` busca no banco de dados |
| `paper` folha de papel | `pixel` pixelado (identidade protegida) | `enhance` ampliar e melhorar imagem |
| `flash` flash de câmera | `fingerprint` impressão digital | `static` sinal perdido (chuvisco) |
| `whip` chicote com desfoque |  | `vhs` fita VHS rebobinando |

Padrão: pasta ou terminal na entrada dos capítulos, scanner na saída, papel nas manchetes, flash nas fotos e avanço no resto. Os textos de cada transição (`params`) aparecem como campos no Estúdio; vazio usa o padrão.

Cuidado editorial: transições como impressão digital, escuta e radar sugerem investigação. Use só onde o roteiro sustenta a ideia e escreva textos neutros (por exemplo "PERFIL EM ANÁLISE", nunca "ESPIÃO CONFIRMADO" sem prova).

`python3 previas_transicoes.py ../videos/<slug>` refaz os vídeos curtos de prévia (em `estudio_local/transicoes/`) com as cores do vídeo.

### Cores

`video.json` → `cores`: `fundo`, `texto`, `destaque` (faixas, linhas, carimbos, etiquetas), `papel` (manchetes e pastas) e `fotos` (`pb` preto e branco, `cor` cores originais, `tom` duas cores do fundo ao destaque). Valem para cenas, fotos, transições, legendas e thumbnail. O Estúdio tem 7 paletas prontas (Dossiê, Alerta vermelho, Arquivo sépia, Noite azul, Terminal verde, Ouro e preto, Cores originais). Mudar as cores refaz todas as cenas na próxima renderização, sem gastar narração.

## Comandos (para o Claude)

```bash
cd /mnt/project-files/popdocs/motor
python3 motor.py ../videos/<slug>                 # tudo: tts plan shots clips trans mix srt thumb
python3 motor.py ../videos/<slug> trans mix       # só alguns passos
python3 studio.py export ../videos/<slug> /tmp/estudio [assets.json]   # gera lotes para o Estúdio (ArtifactData batch)
python3 studio.py import ../videos/<slug> /tmp/dump                     # lê o Estúdio (ArtifactData list com out_dir)
```

Cada passo só refaz as cenas que mudaram. Os arquivos pesados ficam em `/tmp/popdocs-work/<slug>`. Esse diretório some quando o ambiente é reciclado, e aí a primeira renderização refaz tudo (cerca de 25 minutos para 12 minutos de vídeo).

Requisitos do ambiente: `ffmpeg`, Python com `opencv-python numpy soundfile`, Node com `playwright` (Chromium já instalado). Hosts liberados na rede: `api.elevenlabs.io`, `commons.wikimedia.org`, `upload.wikimedia.org`, `www.flickr.com`, `live.staticflickr.com`, `api.openverse.org` (busca de fotos livres; usar User-Agent honesto e nunca contornar bloqueios). A chave da ElevenLabs fica como segredo de rede do ambiente e nunca vai para o chat.

### Estúdio: banco de dados

- `videos/<slug>`: configurações do vídeo, `cores`, `render.requested`, `thumbUrl`
- `videos/<slug>/scenes/<id>`: `order`, `t`, `n`, `bg`, `f` (campos da tela), `trans` (para a próxima cena), `thumb`, `start`, `len`, `dirty`, `deleted`
- `videos/<slug>/fotos/<chave>`: `cap`, `credit`, `license`, `source`, `thumb`, `modo`, `tipo` (`foto` ou `video`); arquivos enviados pelo Filipe têm `origin: upload` e `asset` (baixar com Artifact read + `path` = asset id e salvar em `img/<chave>.jpg`, ou `img/<chave>.mp4` quando `tipo` é `video`; `studio.py import` lista o caminho certo)
- `config/studio`: `previews` (URL do vídeo curto de cada transição)

## Regras do canal

- Roteiro: checar tudo. Toda afirmação tem fonte, alegação é marcada como alegação e a visão é internacional.
- Imagens: só domínio público, licenças livres (CC0, CC BY, CC BY-SA) ou fotos do Filipe, sempre com crédito na tela e na descrição.
- Música: fonte pública ou licença livre, com crédito no encerramento e na descrição.
- Voz: ElevenLabs, voz Leonardo (`4XmhZ74tBbUVCXIYNMMo`), modelo `eleven_multilingual_v2`.
- Estilo visual: preto e branco, Oswald + IBM Plex Mono, ar de dossiê.


## Estúdio 2 (novembro de 2026)

O Estúdio foi refeito a partir das lições do Diesel e do vídeo da NVIDIA. As seções ficam na barra lateral:

- **Cenas.** Linha do tempo clicável com capítulos e trechos de música, busca e filtros (alteradas, sem foto, sem voz), player do áudio de cada cena e setas do teclado para andar entre cenas. O enquadramento da foto é feito na tela: clique no ponto que deve ficar visível e escolha "Preencher a tela" ou "Foto inteira". Marque "Só nesta cena" para não mudar as outras cenas que usam a mesma foto.
- **Mídia.** Galeria com filtros (em cena, sem uso, vídeos, sem crédito) e edição de legenda, crédito, licença, cor e enquadramento.
- **Música.** Trechos de música por cena (`musicas` no `video.json`), com a lista dos arquivos da pasta `musica/` e o volume.
- **Estilo.** Paletas lado a lado, modelos de transição aplicados a todas as cenas ("Documentário", "Sóbrio", "Dossiê tecnológico"), textos fixos e thumbnail.
- **Publicar.** Lista de pendências (checagem frase a frase, narração ainda sem áudio e quantos créditos vai gastar, fotos sem crédito, vídeo desatualizado), texto do YouTube, capítulos com os tempos e os três modos de renderização.

Modos de renderização (também pela linha de comando):

- `python motor/motor.py videos/<slug> --teste`: versão de teste com voz sintética grátis (pacote `edge-tts`), sem gastar créditos. Sai como `saidas/<slug>-TESTE.mp4` e usa pasta de trabalho e cache de voz próprios (`audio-teste/`, fora do Git). A voz de teste é `pt-BR-AntonioNeural`; troque com `"voz_teste"` no `video.json`.
- `python motor/motor.py videos/<slug>`: vídeo final, com a voz da ElevenLabs.
- `python motor/motor.py videos/<slug> celular`: cópia leve em 540p do vídeo final, `saidas/<slug>-celular.mp4`.

Mudar os créditos finais ou o título agora refaz só a cena de encerramento ou de abertura, e não o vídeo inteiro. Na primeira renderização depois desta atualização, todas as cenas são refeitas uma vez, porque a chave do cache mudou.

A checagem do roteiro fica em `"checagem": {"url": "...", "ok": true}` no `video.json`. O Estúdio avisa antes de gerar a voz se ela não estiver marcada como conferida.


## Ritmo (lições do vídeo de referência sobre o Diesel)

O estudo está em `pesquisa/referencias/fatos-mecanicos-diesel.md`. O que virou recurso:

- **Várias fotos na mesma cena.** No Estúdio, em Cenas → Fundo → "Mais fotos nesta cena". No `scenes.json` é o campo `"bgs": ["chave2", "chave3"]`. As fotos se revezam em partes iguais, com passagem suave, e cada uma mostra a própria legenda e o próprio crédito (da galeria).
- **Aviso de ritmo.** O topo mostra de quanto em quanto tempo a imagem troca. Cenas em que a mesma imagem passa de 9 segundos ganham o selo "parada", aparecem no filtro "Paradas", na linha do tempo e nas pendências de Publicar. A referência troca a cada 5,6 s.
- **Zoom no detalhe.** Em Fundo, marque "Zoom no detalhe" e clique no ponto. No `scenes.json`: `"zoom": "detalhe", "zp": [x, y]` (0 a 1, na tela).
- **Ambiente.** Em Estilo: luz viva (a luz oscila como num projetor antigo), ou luz viva e poeira no ar, sobre fotos e vídeos de fundo. No `video.json`: `"ambiente": "luz"` ou `"poeira"`. Grão de filme aleatório ficou de fora: medido numa cena real, ele mais que dobra o tamanho do arquivo final.
- **Velocidade da narração.** Em Estilo → Voz. No `video.json`: `"ritmo_voz": 1.15`. Acelera o áudio em cache sem mudar o tom e sem gastar créditos.
- **Gancho.** Lista de conferência dos dois primeiros minutos em Publicar (`"gancho"` no `video.json`).
- **Volume.** A narração agora sai em -14 LUFS, o padrão do YouTube (`"lufs"` no `video.json` muda isso).

Não entrou: imagem gerada por IA. O canal usa só material real com fonte, que é o que a referência não tem.
