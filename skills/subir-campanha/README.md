# subir-campanha

Skill que sobe campanha de tráfego no Meta Ads via 1 frase no Claude Code.
Objetivo: CPC baixo para blogs monetizados com Google Ad Manager.

## Instalação

1. Copia esta pasta pro diretório de skills do Claude Code:
   ```bash
   cp -r subir-campanha ~/.claude/skills/
   ```

2. Configura as variáveis no `.env` (copie o `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Preencha:
   ```env
   META_ACCESS_TOKEN=EAAxxxx...
   META_AD_ACCOUNT_ID=act_1234567890
   ```

3. Instala dependências Python:
   ```bash
   pip install requests python-dotenv
   ```

## Uso

No Claude Code:
```
sobe campanha do portaldoplayer com 50 reais
```
ou
```
sobe campanha do universodolook com 80 reais usando a página ID 123456789
```

A skill pede o que faltar, mostra o dry-run e só sobe depois da sua confirmação.

## Como obter o token Meta

1. Acesse [developers.facebook.com](https://developers.facebook.com) → crie um app (tipo: Business)
2. Marketing API → gere token com permissão `ads_management`
3. Pegue o `act_id` em [adsmanager.facebook.com](https://adsmanager.facebook.com) → URL da conta

## Blogs suportados

| Alias | Domínio |
|-------|---------|
| portaldoplayer | portaldoplayer.com |
| universodolook | universodolook.com |
