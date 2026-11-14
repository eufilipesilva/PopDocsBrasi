# PopDocsBrasil

Canal de documentários no YouTube, estilo dossiê, sem rosto. Um vídeo por semana. Narração com a voz Leonardo da ElevenLabs.

- O motor e o Estúdio estão em `motor/`. O manual completo está em `motor/LEIA-ME.md`, e a instalação em `motor/INSTALAR.md`.
- Cada vídeo tem uma pasta em `videos/<slug>/` (cenas, fotos, transições, cores, narração em cache, saídas).
- Renderizar: `python motor/motor.py videos/<slug>`. Estúdio local: `python motor/estudio_local/servidor.py`.

## Regras

- Roteiro: checar tudo. Cada fato precisa de fonte confiável, e alegações sem prova aparecem como alegações.
- Roteiro: só escrever o que a fonte diz. Nada de detalhe inventado ou inferido (cômodo, gesto, diálogo, causa) sem fonte; se for inferência, marcar como tal. Entregar com planilha de checagem frase a frase (fonte e link por frase).
- A planilha de checagem vem antes de gerar a voz e tem, por frase: o link da fonte (abrindo no trecho, quando der), o trecho original que sustenta a frase, a situação (Confirmado, Atribuído à fonte, Hipótese, Interpretação, Texto autoral, Precisa corrigir) e uma caixa "Conferido" para o Filipe. Modelo: Eastman, https://claude.ai/artifact/VpxHMjydddSVpVm21k6YGQ
- Em relatórios e resumos para o Filipe, toda afirmação leva o link da fonte, conferido antes de enviar.
- Imagens e vídeos só de domínio público, licença livre ou do próprio canal, sempre com crédito e licença em `fotos.json`.
- A chave da ElevenLabs fica só em `~/.popdocs/elevenlabs.txt`. Nunca pedir, mostrar ou copiar a chave.
- Narração gasta créditos: só mudar o texto `n` de uma cena quando for preciso.
- Orçamento do canal: R$200 por mês.

## Sincronização

- Este repositório no GitHub é a fonte comum entre o Claude na nuvem e o Claude Code no computador. Antes de trabalhar, `git pull`; ao terminar, commit e `git push`.
- Os vídeos finais (`saidas/*.mp4`), o histórico e a chave não vão para o Git (ver `.gitignore`).
