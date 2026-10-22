---
name: otimizacao
description: Otimização da conta Meta Ads para arbitragem de mídia programática — Régua de Corte por ROI (GAM), auditoria de estrutura, criativos e público. Uso: "faz a otimização", "aplica a régua de corte", "diagnostica a conta".
---

# Otimização

Você é a skill **otimizacao**. Roda auditoria automatizada na conta de Meta Ads do usuário, focada em **arbitragem de mídia programática** (Meta Ads → blogs → Google Ad Manager).

## KPI principal

**CPC** — quanto menor o CPC, maior a margem sobre o RPM do Ad Manager.

| CPC | Classificação |
|-----|--------------|
| < R$0,10 | Excelente (campeão) |
| R$0,10 – R$0,15 | Bom |
| R$0,15 – R$0,25 | Medíocre |
| > R$0,25 | Ruim — pausar |

## Modelo esperado

**1 campanha × 1 conjunto × 3 anúncios** (escala). Não existe teste/pré-escala como estrutura separada.

## 3 frentes de auditoria

1. **Estrutura** — valida modelo escala, detecta campanhas com conjuntos demais, campanhas duplicadas
2. **Criativo** — detecta fadiga, CPC alto, CTR baixo, falta de variação
3. **Público** — overlap entre conjuntos, idade ampla sem segmentação, lookalikes velhos

Não roda audit de LP (blogs WordPress, fora do escopo).

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
- **Nunca alterar a conta sem aprovação do gestor**: listar os cortes (campanha, investido, receita, ROI) e aplicar só o que for aprovado.

Rotina (fuso da conta): 4h ativar/subir orçamento → 6-7h 1º corte → 9-10h 2º corte → 13h avaliar se encerra o dia.

## Como invocar

Quando o usuário pedir algo como "diagnostica a conta" ou "roda diagnóstico":

1. **Identifica a conta** — usa a do `.env` ou aceita `--account act_XXXXX`
2. **Roda o script**:
   ```bash
   cd "C:\Users\Administrador\Documents\OASIS\victor-skills\skills\otimizacao" && "C:\Users\Administrador\AppData\Local\Programs\Python\Python312\python.exe" scripts/main.py
   ```
   Flags opcionais:
   - `--account act_XXXXX` — conta diferente da do `.env`
   - `--date-preset last_7d` — janela de insights (default: last_30d)
   - `--max-findings 20` — limite de findings (default: 15)

3. **Mostra o resultado** formatado no terminal

## Variáveis de ambiente (.env)

Usa o mesmo `.env` da skill `subir-campanha`:
- `META_ACCESS_TOKEN` — token com `ads_read`
- `META_AD_ACCOUNT_ID` — conta no formato `act_XXXXX`
