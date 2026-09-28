---
name: subir-campanha
description: Sobe campanha de tráfego no Meta Ads para blogs de arbitragem monetizados com Google Ad Manager. Foco em CPC baixo. Uso: "sobe campanha do portaldoplayer com 50 reais".
---

# Subir Campanha

Você é a skill **subir-campanha**. A skill está implementada em Python — você invoca via Bash, não escreve código.

## Contexto da operação

Arbitragem de mídia programática: tráfego comprado no Meta Ads → blogs monetizados via Google Ad Manager.
O KPI principal é **CPC baixo** — quanto mais barato o clique, maior a margem sobre o RPM do Ad Manager.

Blogs conhecidos:
- `portaldoplayer` → portaldoplayer.com
- `universodolook` → universodolook.com

## Como invocar

Quando o usuário pedir algo como "sobe campanha do portaldoplayer com X reais":

1. **Identifica os inputs** — peça os que faltarem:
   - **Blog** (`portaldoplayer` ou `universodolook`)
   - **Budget** diário em reais (ex: `50`)
   - **Página do Facebook** a usar — ID ou nome (opcional: usa a padrão do blog se omitido)
   - **Modo** — `--abo` (default) ou `--cbo`

2. **Roda dry-run primeiro** (sempre):
   ```bash
   cd ~/.claude/skills/subir-campanha && python scripts/main.py --blog "<blog>" --budget <valor> --dry-run
   ```

3. **Se imprimir "✗ Variáveis ausentes no .env"**, oriente o usuário a preencher o `.env` e tente de novo.

4. **Mostra o resumo do dry-run** e **pede confirmação** antes de subir. Exemplo:
   > "Vou criar essa campanha PAUSED com R$50/dia para portaldoplayer.com. Confirma?"

5. **Após confirmação**, roda sem `--dry-run`:
   ```bash
   cd ~/.claude/skills/subir-campanha && python scripts/main.py --blog "<blog>" --budget <valor>
   ```

6. **Mostra o link do Ads Manager** impresso no final para o usuário revisar e ativar.

## O que o script cria

Estrutura padrão de arbitragem:
```
Campanha: [Blog] · TRAFFIC · [Data]
  └── Conjunto: Feed+Stories · BR · 25-55 · [Interesses]
        └── Anúncio: [creative_id ou placeholder]
```

## Convenções

- **Sempre subir PAUSED** — o usuário ativa manualmente no Ads Manager
- **Objetivo fixo: TRAFFIC** — o KPI é volume de cliques com CPC baixo
- **Sempre dry-run antes** — mostrar estrutura e custo estimado antes de subir
- **Nomenclatura padrão:**
  ```
  Campanha: [Blog] · TRAFFIC · AAAA-MM-DD
  Conjunto:  BR · 25-55 · Feed+Stories
  Anúncio:   [creative_id]
  ```

## Variáveis de ambiente (.env)

- `META_ACCESS_TOKEN` — token long-lived com `ads_management`
- `META_AD_ACCOUNT_ID` — conta no formato `act_XXXXX`

## Limitações

- Só Meta Ads (objetivo TRAFFIC)
- Não cria criativos — usa `creative_id` já existente na conta; sem ele, o anúncio sobe sem criativo e o usuário anexa no Ads Manager
- Targeting default: Brasil, 25-55 anos, Feed + Stories — refine no Ads Manager depois
- Não valida RPM nem acessa o Google Ad Manager
