---
name: subir-campanha
description: Sobe campanha no Meta Ads (tráfego, vendas, leads ou engajamento) usando o perfil do gestor — página, pixel, destino e público dele. Sempre PAUSED e sempre com dry-run antes. Uso: "sobe campanha de vendas pro site-br com 50 reais na página loja".
---

# Subir Campanha

Você é a skill **subir-campanha**. Ela é implementada em Python — você invoca via Bash, não escreve código.

Script: `~/.claude/skills/subir-campanha/scripts/main.py`
Configuração do gestor: `~/.meta-ads/perfil.json` (páginas, destinos, pixel, público, objetivo padrão).

## 0. Perfil
Se o script sair com código 3 ("Perfil não encontrado"), rode a skill **configurar-meta-ads** antes.
Leia `~/.meta-ads/perfil.json` para saber os apelidos de páginas e destinos — **nunca mostre o `.env`**.

## 1. Inputs
Pegue da frase do gestor e pergunte só o que faltar:

| Input | Flag | Obrigatório |
|---|---|---|
| Budget diário por conjunto (moeda da conta) | `--budget 50` | sim |
| Objetivo: `trafego`, `vendas`, `leads`, `engajamento` | `--objetivo` | não (usa `objetivo_padrao`) |
| Página (apelido, nome ou ID) | `--pagina loja` | se o perfil tiver mais de uma |
| Destino (apelido do perfil) ou URL avulsa | `--destino site-br` / `--url https://...` | se tiver mais de um |
| Pasta de criativos (.mp4/.mov/.jpg/.png) | `--criativos "C:\pasta"` | sim (no real) |
| País(es) | `--pais BR` ou `--pais ES,PT` | não (vem do destino) |
| Evento de conversão | `--evento LEAD` | não (vendas=perfil, leads=LEAD) |
| Texto do anúncio | `--texto "..."` | não (vem do perfil por idioma) |
| Conjuntos / anúncios por conjunto | `--conjuntos 2 --anuncios 3` | não (vem do perfil) |
| Otimização específica | `--otimizacao LANDING_PAGE_VIEWS` | não |
| Público e posicionamentos automáticos | `--advantage-plus` | não |
| Prefixo do nome | `--nome black-friday` | não |

Mapa dos objetivos:
- **trafego** → OUTCOME_TRAFFIC, otimiza cliques no link
- **vendas** → OUTCOME_SALES, otimiza conversão do pixel (evento do perfil) — precisa de pixel
- **leads** → OUTCOME_LEADS, otimiza evento LEAD do pixel — precisa de pixel
- **engajamento** → OUTCOME_ENGAGEMENT, otimiza engajamento com a publicação

## 2. Dry-run (sempre)
```bash
python ~/.claude/skills/subir-campanha/scripts/main.py --budget <valor> --objetivo <obj> --pagina <pagina> --destino <destino> --criativos "<pasta>" --dry-run
```

## 3. Confirmação
Mostre o resumo do dry-run e pergunte, por exemplo:
> "Vou criar 1 conjunto de R$50/dia com 3 anúncios, objetivo VENDAS (pixel 123 / PURCHASE), página Loja, destino meusite.com.br, tudo PAUSED. Confirma?"

Se o script recusar por passar do teto (`orcamento_max_diario`), avise e só use `--forcar` se o gestor confirmar o valor.

## 4. Subir
Após o "sim", rode o mesmo comando **sem** `--dry-run`. Mostre o link do Ads Manager impresso no final.

## Convenções
- Sempre **PAUSED** — o gestor ativa no Ads Manager
- Sempre **dry-run antes**
- Nome: `<destino> · <OBJETIVO> · AAAA-MM-DD` / conjunto `<países> · <idade> · <posicionamentos>` / anúncios `anuncio-NN`
- Países da UE recebem DSA automaticamente (`dsa_beneficiario` do perfil ou nome da página)
- Erro da API: mostre a mensagem do Meta ao gestor em linguagem simples e sugira a correção
