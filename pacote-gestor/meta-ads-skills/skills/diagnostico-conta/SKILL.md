---
name: diagnostico-conta
description: Auditoria automatizada da conta Meta Ads do gestor — estrutura, criativos e público, julgando cada campanha pelo KPI do seu objetivo (CPC, CPA, CPL ou custo por engajamento) com as metas do perfil. Uso: "diagnostica minha conta", "analisa as campanhas dos últimos 7 dias".
---

# Diagnóstico de Conta

Você é a skill **diagnostico-conta**. Roda auditoria na conta de Meta Ads do gestor e devolve
uma lista priorizada do que arrumar.

Script: `~/.claude/skills/diagnostico-conta/scripts/main.py`
Configuração: `~/.meta-ads/perfil.json` (conta, estrutura padrão e metas de KPI). Se não existir,
o script roda com limites padrão — sugira rodar **configurar-meta-ads** para ajustar as metas.

## KPI por objetivo
| Objetivo da campanha | Métrica | Limites |
|---|---|---|
| Tráfego | CPC | `kpis.trafego` |
| Vendas | CPA (compra do pixel) | `kpis.vendas` |
| Leads | CPL | `kpis.leads` |
| Engajamento | custo por engajamento | `kpis.engajamento` |

## Frentes
1. **Estrutura** — conjuntos/anúncios fora do padrão do perfil, campanhas duplicadas, conjuntos parados, objetivo fora de `objetivos_permitidos`
2. **Criativo** — custo por resultado acima da meta, gasto sem resultado, fadiga, pouca variação, CTR baixo, ranking com campeão por objetivo
3. **Público** — overlap entre conjuntos, idade ampla sem segmentação, lookalikes velhos
4. **ROI (GAM)** — só se `gam_csv_dir` estiver no perfil ou passar `--csv`

## Como invocar
```bash
python ~/.claude/skills/diagnostico-conta/scripts/main.py
```
Flags:
- `--account act_XXXXX` — outra conta (o token precisa ter acesso)
- `--date-preset last_7d` — janela (default `last_30d`)
- `--max-findings 20` — limite de itens (default 15)
- `--csv "<arquivo>"` — CSV do GAM específico

## Depois de rodar
Mostre ao gestor: resumo (X críticos, Y médios, Z menores), os 3 itens críticos com a ação
recomendada, e o ranking de campeões. Não altere nada na conta — esta skill é só leitura.
