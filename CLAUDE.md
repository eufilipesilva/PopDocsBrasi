# PopDocsBrasil

Canal de documentários no YouTube, estilo dossiê, sem rosto. Um vídeo por semana. Narração com a voz Leonardo da ElevenLabs.

- O motor e o Estúdio estão em `motor/`. O manual completo está em `motor/LEIA-ME.md`, e a instalação em `motor/INSTALAR.md`.
- Cada vídeo tem uma pasta em `videos/<slug>/` (cenas, fotos, transições, cores, narração em cache, saídas).
- Renderizar: `python motor/motor.py videos/<slug>`. Estúdio local: `python motor/estudio_local/servidor.py`.

## Regras

- Roteiro: checar tudo. Cada fato precisa de fonte confiável, e alegações sem prova aparecem como alegações.
- Imagens e vídeos só de domínio público, licença livre ou do próprio canal, sempre com crédito e licença em `fotos.json`.
- A chave da ElevenLabs fica só em `~/.popdocs/elevenlabs.txt`. Nunca pedir, mostrar ou copiar a chave.
- Narração gasta créditos: só mudar o texto `n` de uma cena quando for preciso.
- Orçamento do canal: R$200 por mês.
