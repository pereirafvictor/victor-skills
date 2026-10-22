---
name: otimizacao
description: Otimização da conta Meta Ads do gestor — Régua de Corte por ROI e auditoria de estrutura, criativos e público, julgando cada campanha pelo KPI do seu objetivo (CPC, CPA, CPL ou custo por engajamento) com as metas do perfil. Uso: "diagnostica minha conta", "analisa as campanhas dos últimos 7 dias".
---

# Otimização

Você é a skill **otimizacao**. Roda auditoria na conta de Meta Ads do gestor e devolve
uma lista priorizada do que arrumar.

Script: `~/.claude/skills/otimizacao/scripts/main.py`
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

## Régua de Corte (otimização diária por ROI)

Aplicada sobre o ROI do dia (receita GAM ÷ investimento Meta), campanha por campanha e por lote (data de subida).

| ROI da campanha no dia | Ação |
|---|---|
| **1º dia de vida, abaixo de -40%** | Orçamento para **$1** |
| **Abaixo de -60%** (já passou do 1º dia / já está em $1) | **Pausar** |
| Entre -30% e -40% | Cortar **20%** do orçamento |
| Entre -10% e -30% | Cortar **10%** do orçamento |
| Acima de -10% | Manter |

Regras que acompanham a régua:
- **Gasto muito baixo (< $1 no dia)** → aguardar o próximo corte antes de decidir.
- **"Sem faturamento" no GAM** → conferir tracking/UTM antes de cortar (pode ser link quebrado, não campanha ruim).
- **Orçamento só sobe para o dia seguinte** — nunca aumentar no meio da operação.
- **Orçamento sempre em dólar inteiro** (nunca $4,50 ou $2,40) — arredonda o corte pro inteiro mais próximo; se voltar pro mesmo valor, mantém. Valor inteiro otimiza melhor.
- **Nunca alterar a conta sem aprovação do gestor**: listar os cortes (campanha, investido, receita, ROI) e aplicar só o que for aprovado.

Rotina (fuso da conta): 4h ativar/subir orçamento → 6-7h 1º corte → 9-10h 2º corte → 13h avaliar se encerra o dia.

## Como invocar
```bash
python ~/.claude/skills/otimizacao/scripts/main.py
```
Flags:
- `--account act_XXXXX` — outra conta (o token precisa ter acesso)
- `--date-preset last_7d` — janela (default `last_30d`)
- `--max-findings 20` — limite de itens (default 15)
- `--csv "<arquivo>"` — CSV do GAM específico

## Depois de rodar
Mostre ao gestor: resumo (X críticos, Y médios, Z menores), os 3 itens críticos com a ação
recomendada, e o ranking de campeões. Não altere nada na conta — esta skill é só leitura.
