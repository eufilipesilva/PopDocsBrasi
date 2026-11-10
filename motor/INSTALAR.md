# Como rodar o PopDocs no seu computador, sem o Claude

Com isto você edita os vídeos no Estúdio e gera o vídeo final no seu próprio computador. Não precisa de assinatura do Claude. Precisa de internet, para as fontes das letras e para a narração da ElevenLabs.

## O que vem no pacote

```
PopDocs/
  motor/        o programa que monta os vídeos e o Estúdio local
  videos/       uma pasta por vídeo (cenas, fotos, narração, música, resultado)
```

## Instalação (uma vez só)

### Windows

1. **Python.** Baixe em python.org/downloads e instale. Na primeira tela, marque **Add python.exe to PATH**.
2. **Node.js.** Baixe a versão LTS em nodejs.org e instale com as opções padrão.
3. **ffmpeg.** Abra o menu Iniciar, digite `cmd`, abra o Prompt de Comando e rode:
   `winget install Gyan.FFmpeg`
   Feche e abra o Prompt de novo depois.
4. **Dependências do motor.** Na pasta `PopDocs\motor`, dê dois cliques em `instalar.bat`. Leva alguns minutos.

### Mac

1. **Homebrew.** Abra o Terminal e cole o comando que aparece em brew.sh.
2. **Python, Node e ffmpeg.** No Terminal, rode:
   `brew install python node ffmpeg`
3. **Dependências do motor.** Na pasta `PopDocs/motor`, clique com o botão direito em `instalar.command` e escolha **Abrir**. Na primeira vez, o Mac pergunta se você confia no arquivo.

## Chave da ElevenLabs

A narração usa a sua conta da ElevenLabs. A chave fica só no seu computador:

1. Na ElevenLabs, vá em **Developers → API Keys** e crie uma chave com permissão de **Text to Speech**. Ela começa com `sk_`.
2. Crie uma pasta chamada `.popdocs` dentro da sua pasta de usuário:
   - Windows: `C:\Users\SEU_NOME\.popdocs\`
   - Mac: `/Users/SEU_NOME/.popdocs/` (no Finder, aperte Cmd+Shift+. para ver pastas que começam com ponto)
3. Dentro dela, crie um arquivo de texto `elevenlabs.txt` com a chave numa única linha.

A narração só é gerada quando um texto é novo ou mudou. As narrações já feitas ficam em `videos/<vídeo>/audio/` e não gastam créditos de novo.

## Usar o Estúdio

- **Windows:** dois cliques em `motor\iniciar-estudio.bat`
- **Mac:** dois cliques em `motor/iniciar-estudio.command`

O navegador abre em `http://localhost:8765` com a mesma tela do Estúdio do Claude. Tudo o que você muda é salvo na pasta do vídeo, e uma cópia da versão anterior fica em `historico/`.

O botão **Renderizar vídeo** gera o vídeo. Um painel no canto mostra o andamento. No fim, o resultado fica em `videos/<vídeo>/saidas/`:

- `<vídeo>.mp4`: o vídeo final, em 1080p, pronto para o YouTube
- `<vídeo>-legendas.srt`: as legendas, para enviar ao YouTube
- `<vídeo>-thumbnail.jpg`: a thumbnail, em 1280x720

A primeira renderização de um vídeo leva de 20 a 40 minutos para 12 minutos de vídeo, dependendo do computador. Depois, só as cenas que mudaram são refeitas.

Para fechar o Estúdio, feche a janela preta do Prompt ou do Terminal.

## Começar um vídeo novo sem o Claude

1. Copie a pasta de um vídeo pronto (por exemplo `videos/jensanity`) e dê um nome novo, só com letras minúsculas, números e `-`.
2. Na pasta nova, apague `audio/`, `previas/`, `saidas/`, `historico/` e as fotos de `img/`. Apague também `transitions.json`, que é recriado com as transições padrão.
3. Abra `video.json` num editor de texto (Bloco de Notas ou TextEdit) e troque `slug` pelo nome novo da pasta, além dos títulos e textos.
4. Coloque as fotos em `img/` (formato `.jpg`) e descreva cada uma em `fotos.json`, com legenda, crédito e licença.
5. Escreva as cenas em `scenes.json`. O `LEIA-ME.md` explica cada tipo de cena e seus campos. Dica: comece editando as cenas do vídeo copiado no próprio Estúdio.
6. Abra o Estúdio, ajuste o que quiser e renderize.

## Se algo der errado

| Mensagem | O que fazer |
|---|---|
| `python` não é reconhecido | Reinstale o Python marcando **Add python.exe to PATH** |
| `ffmpeg` não encontrado | Rode a instalação do ffmpeg de novo e reabra o Prompt ou Terminal |
| `Cannot find module 'playwright'` | Rode `instalar.bat` ou `instalar.command` de novo |
| Erro 401 da ElevenLabs | A chave em `elevenlabs.txt` está errada ou sem permissão de Text to Speech |
| Foto "não encontrada" | O arquivo precisa estar em `img/` com o mesmo nome da chave e terminar em `.jpg` |

O painel de renderização mostra as últimas linhas do registro. O registro completo fica em `saidas/renderizacao.log`.
