---
name: subir-campanha
description: Sobe campanhas do modelo DIRETO no Meta Ads (Rocket 02, página Diana Dantas, minrule) em lote a partir de um plano — quiz do portaldoplayer ou chat, evento ad_click ou pv2, sempre com "Estratégia de ciclo de vida do cliente" = Obter conversões de todos os públicos. Uso: "sobe 30 campanhas em francês com ad_click".
---

# Subir Campanha (modelo direto)

Você é a skill **subir-campanha**. A subida é feita pelo script `scripts/subir_direto.py` — você monta o **plano JSON** e roda o script via Bash; não escreva chamadas de API na mão.

```bash
cd "C:\Users\Administrador\Documents\OASIS\victor-skills\skills\subir-campanha"
python -I -X utf8 scripts/subir_direto.py <plano.json> --dry-run   # sempre primeiro
python -I -X utf8 scripts/subir_direto.py <plano.json>             # cria (rodar em background: tem pausas)
python -I -X utf8 scripts/subir_direto.py <plano.json> --conferir  # confere/corrige as já criadas
```

Salve o plano em `C:\Users\Administrador\Documents\OASIS\operacao\subidas\<nome>.json`. O script grava o log ao lado (`<nome>.log.json`) e **retoma de onde parou** se cair ou for interrompido — nunca apague o log no meio de uma subida.

## Configuração fixa de toda campanha

| Nível | Configuração |
|---|---|
| Conta | Rocket 02 (`act_1414802330033520`) — o `.env` da skill só fornece o token |
| Página | Diana Dantas (`1278207382032588`) |
| Campanha | OUTCOME_SALES, orçamento na campanha (padrão **$5**), LOWEST_COST_WITHOUT_CAP |
| Conjunto | OFFSITE_CONVERSIONS / IMPRESSIONS / WEBSITE, pixel `2285334382219676`, evento `ad_click` (padrão) ou `pv2` |
| **Ciclo de vida** | **`ad_set_goal: {"type": 0}`** → "Estratégia de ciclo de vida do cliente" = **Obter conversões de todos os públicos** |
| Público | `targeting_automation: {"advantage_audience": 1}` + público do último conjunto direto do país (CA = Quebec + locales FR) |
| Anúncio | vídeo, CTA LEARN_MORE, link com UTM, display link sem UTM, melhorias automáticas OPT_OUT |

> ⚠️ **Ciclo de vida:** sem o `ad_set_goal` o dropdown "Estratégia de ciclo de vida do cliente" fica **vazio** no Ads Manager. O `advantage_audience` sozinho **não** preenche esse dropdown. Tipos: `0` = todos os públicos, `1` = excluir clientes existentes e engajados, `2` = excluir clientes existentes. Depois de criar, o Ads Manager só mostra o valor **depois de recarregar a página**.

## Plano JSON

```json
{
  "evento": "ad_click",
  "funil": "quiz",
  "orcamento": 5,
  "inicio": "agora",
  "blocos": [],
  "permitir_repetir": false,
  "campanhas": [
    {"pais": "CA", "nicho": "Mix", "criativos": ["Pulseira Pandora", "Moletom Nike", "Terço"]},
    {"pais": "US", "nicho": "Acessorios", "criativos": [
      {"video": "C:\\Users\\Administrador\\Downloads\\espanhol\\relogio.mp4", "nome": "ES-NEW-09",
       "titulo": "Relojes para probar", "texto": "🎁 ¡Recibe RELOJES GRATIS + REGALOS!\n✅ ¡Sin costo de envío!"}
    ]}
  ]
}
```

| Campo | Valores | Padrão |
|---|---|---|
| `evento` | `ad_click` ou `pv2` (lead que paginou) | `ad_click` |
| `funil` | `quiz` → `portaldoplayer.com/{idioma}/quiz-mrl1-2/` · `chat` → `chat.minrule.com/{idioma}/moda-shein` | `quiz` |
| `url` | URL avulsa (substitui o funil) | — |
| `orcamento` | dólares por campanha/dia | `5` |
| `inicio` | `agora` = ACTIVE na hora · `amanha` = ACTIVE agendado pra 00:01 do dia seguinte | `agora` |
| `blocos` | blocos extras no nome, ex. `["pv2"]` | `[]` |
| `permitir_repetir` | `true` deixa o mesmo criativo em 2 campanhas do mesmo país | `false` |
| `criativos` | **string** = nome de um anúncio que já existe na conta (reaproveita o vídeo e o texto da campanha do mesmo idioma) · **objeto** = vídeo novo (`video`, `titulo`, `texto`, `nome` opcional) | — |
| `fase` (por campanha) | `teste`, `escala` ou `null` | `teste`; `Mix` vai sem fase |

O script faz sozinho:
- **Numeração**: pega o maior número já usado no país na conta e continua dele (nome e UTM) — evita duplicar.
- **Nome**: `[DD/MM][direto][chat?][fase][blocos][Continente][PAÍS][idioma][Nicho][mrl][dianadantas] - NN`; conjunto `Aberto - {País}`; anúncio = nome do criativo.
- **UTM**: `?utm_source=facebook&utm_campaign=mrl-shein-{idioma}-{pais}-dianadantas-NN`.
- **1ª linha do texto** troca o país ("Nous recherchons des testeuses au Québec." / "Buscamos probadoras en Chile.").
- **Vídeo novo**: sobe, espera `ready` e usa a thumbnail.
- **Limite de API da Meta**: lotes de 5 com pausa de 5 min; se a conta bloquear, espera e tenta de novo sozinho.
- **Conferência no final**: status, evento, Advantage+ e ciclo de vida de cada conjunto — corrige o ciclo de vida se vier vazio — e imprime o nome de uma campanha.

Países cadastrados: CA, CH, BE, LU, FR (fr) · US, ES, MX, CL, CO, AR (es). País novo → adicionar em `PAISES` no script.

## Fluxo

1. **Entender o pedido** — quantas campanhas, países, evento, funil, criativos. Pergunte só o que faltar.
2. **Escolher criativos com dado** — cruzar a planilha do GAM (`Downloads/campanhas_*.csv`) com os anúncios da conta; o ROI de criativo é rateado pelos cliques do anúncio dentro da campanha.
3. **Montar o plano** e rodar o **dry-run**. Mostrar ao Majo a matriz (país × qtd × pacote) e a numeração.
4. **Após o "sim"**, rodar sem `--dry-run` **em background** (50 campanhas ≈ 50-60 min por causa das pausas).
5. **Ao terminar**: mandar o resumo da conferência e **o nome de uma campanha** pra ele conferir no Ads Manager (lembrar de recarregar a página).

## Corrigir campanhas já criadas sem ciclo de vida

`--conferir` com o log da subida corrige automaticamente. Pra conjuntos de outra origem: `POST /{adset_id}` com `ad_set_goal={"type":0}` (só esse campo — não mexe no público).

## Legado

`scripts/main.py` é o modelo antigo (OUTCOME_TRAFFIC, PAUSED, sem ciclo de vida) — **não usar** pro direto.
