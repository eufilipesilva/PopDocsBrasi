# Criar o canal PopDocsBrasil no YouTube

Tudo o que está aqui foi preparado com o nome **PopDocsBrasil**, o mesmo que já aparece nos vídeos. Se o nome mudar, o banner e a foto são refeitos em minutos (`node render-arte.js` depois de editar `arte.html`).

## 1. Que conta usar (sem associar a sua conta pessoal)

| Opção | Como fica | Prós | Contras |
|---|---|---|---|
| **A. Conta Google nova só do canal** (recomendada) | Um Gmail novo, por exemplo `popdocsbrasil@gmail.com`, dono do canal | Separação total da sua conta pessoal. Serve também para ElevenLabs, AdSense e e-mail de contato do canal. Fácil de passar para um sócio ou vender no futuro | Mais um login para guardar. O Google pede um número de celular na criação (pode ser o seu; ele não aparece em lugar nenhum) |
| B. Conta de marca dentro da sua conta pessoal | O canal tem nome próprio, mas o dono é a sua conta Google | Não precisa de outro login, troca de conta com um clique | O canal fica preso à sua conta pessoal. Se ela tiver problema (bloqueio, invasão), o canal vai junto |

Em nenhuma das duas o seu nome aparece para o público. A diferença é o vínculo por trás. Como você não quer associar, a **opção A** é a certa.

Dica: ative a verificação em duas etapas na conta nova logo no primeiro dia e guarde os códigos de recuperação.

## 2. Passo a passo

1. Abra uma **janela anônima** no navegador (Ctrl+Shift+N no Chrome), para não misturar com a sua conta pessoal.
2. Vá em `accounts.google.com/signup` e crie a conta: nome **PopDocs**, sobrenome **Brasil**, e-mail `popdocsbrasil@gmail.com` (ou a alternativa que estiver livre).
3. Com a conta nova, entre em `youtube.com`, clique na foto do canto superior direito e em **Criar um canal**.
4. Nome: **PopDocsBrasil**. Identificador (@): **@PopDocsBrasil**. Se estiver ocupado, use na ordem: `@PopDocsBR`, `@PopDocsBrasilOficial`, `@DossiePopDocs`.
5. Entre no **YouTube Studio** (`studio.youtube.com`) → **Personalização**:
   - **Branding:** foto do perfil = `foto-perfil.png`; banner = `banner.png`; marca-d'água (opcional) = `foto-perfil.png`.
   - **Informações básicas:** cole a descrição da seção 3, os links e o e-mail de contato (o da conta nova).
6. **Configurações → Canal → Informações básicas:** país **Brasil**, palavras-chave da seção 4.
7. **Configurações → Canal → Configurações avançadas:** público = "Não, este canal não é para crianças".
8. **Verifique o canal por telefone** em `youtube.com/verify`. Isso libera vídeos com mais de 15 minutos, thumbnails personalizadas e o comentário fixado com as fontes. Faça isso antes de subir o Diesel.
9. **Configurações → Padrões de envio:** idioma do vídeo Português (Brasil), categoria **Educação**, e cole no campo de descrição padrão o rodapé da seção 5.
10. Ao subir cada vídeo, marque **"Conteúdo alterado ou sintético" → Sim** se o YouTube perguntar (a narração é voz sintética da ElevenLabs).

## 3. Descrição do canal (cole em Personalização → Informações básicas)

> Dossiês em vídeo sobre pessoas que marcaram a história: inventores, empresários, artistas e personagens que viraram mistério. Cada episódio reconstrói uma vida inteira, do começo ao fim, com fatos checados, fontes citadas e imagens de arquivo.
>
> Aqui, o que tem prova é tratado como fato, e o que não tem aparece como hipótese. As fontes de cada vídeo ficam no comentário fixado.
>
> Novo dossiê toda semana. Inscreva-se e ative o sininho para não perder o próximo arquivo.

## 4. Palavras-chave do canal

```
documentário, dossiê, documentário em português, biografia, história, histórias reais, mistérios da história, personalidades, inventores, empresários, história da tecnologia, curiosidades históricas, PopDocsBrasil
```

## 5. Rodapé padrão para todo vídeo

```
📁 PopDocsBrasil: dossiês sobre vidas que marcaram a história.
Fontes completas no comentário fixado.
Narração: voz sintética (ElevenLabs). Imagens de arquivo em domínio público ou licença livre, com créditos.
#PopDocsBrasil #Documentário #Dossiê
```

## 6. Arquivos desta pasta

- `banner.png`: 2560x1440. O texto fica dentro da área segura de 1546x423, então aparece inteiro no celular, no PC e na TV.
- `foto-perfil.png`: 800x800, monograma **PD** com o círculo dourado. Funciona recortada em círculo.
- `arte.html` e `render-arte.js`: a fonte das duas imagens, na mesma paleta sépia dos vídeos (#15110C, #F1E6D0, #D2A85A).
