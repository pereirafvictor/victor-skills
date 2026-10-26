---
name: subir-campanha
description: Sobe campanhas do modelo DIRETO no Meta Ads (tráfego pro site, conversão no pixel) em lote a partir de um plano — vários países, funis e eventos, numeração contínua, sempre com "Estratégia de ciclo de vida do cliente" = Obter conversões de todos os públicos. Usa a conta, página e pixel do config.json de quem usa. Uso: "sobe 30 campanhas em francês com ad_click".
---

# Subir Campanha (modelo direto)

Você é a skill **subir-campanha**. A subida é feita pelo script `scripts/subir_direto.py` — você monta o **plano JSON** e roda o script via Bash; não escreva chamadas de API na mão.

```bash
cd <pasta da skill>
python -I -X utf8 scripts/subir_direto.py <plano.json> --dry-run   # sempre primeiro
python -I -X utf8 scripts/subir_direto.py <plano.json>             # cria (rodar em background: tem pausas)
python -I -X utf8 scripts/subir_direto.py <plano.json> --conferir  # confere/corrige as já criadas
```

O script grava o log ao lado do plano (`<plano>.log.json`) e **retoma de onde parou** se cair ou for interrompido — nunca apague o log no meio de uma subida.

## 0. Configuração (uma vez por pessoa)

Tudo que é da conta de quem usa fica fora do código:

| Arquivo | O que tem | Vai pro git? |
|---|---|---|
| `.env` | `META_ACCESS_TOKEN` (token com `ads_management`) | não |
| `config.json` | conta, página, pixel, site, funis, países, padrão de nome/UTM | não |
| `config.example.json` | modelo pra copiar | sim |

Se o script disser "Config não encontrado" ou "Faltam no config", ajude a pessoa a copiar `config.example.json` → `config.json` e preencher:

| Campo | Exemplo | Pra que serve |
|---|---|---|
| `conta` | `act_123...` | conta de anúncios |
| `pagina_id` / `pagina_slug` | `123...` / `minhapagina` | página dos anúncios; o slug entra no nome e na UTM |
| `pixel` | `123...` | pixel do evento de conversão |
| `dsa_beneficiario` | `Minha Empresa LTDA` | opcional; exigido em país da UE se a conta não tiver padrão |
| `site` / `utm_prefixo` | `meusite` / `meusite-oferta` | bloco do site no nome / começo da UTM |
| `evento_padrao` | `ad_click` | evento custom do pixel usado na otimização |
| `funis` | `{"quiz": "https://meusite.com/{idioma}/quiz/"}` | links por funil; `{idioma}` vira `fr`, `es`… |
| `bloco_funil` | `{"chat": "chat"}` | bloco extra no nome quando usar aquele funil |
| `paises` | `{"CA": {"idioma":"fr","continente":"América do Norte","conjunto":"Canadá","primeira_linha":"..."}}` | países liberados, nome do conjunto e 1ª linha do texto por país |
| `nome` / `utm` | ver exemplo | padrão do nome da campanha e da UTM (opcional) |

**Nunca mostre o `.env` nem cole o token na conversa.**

## Configuração fixa de toda campanha

| Nível | Configuração |
|---|---|
| Campanha | OUTCOME_SALES, orçamento na campanha (padrão do config), LOWEST_COST_WITHOUT_CAP |
| Conjunto | OFFSITE_CONVERSIONS / IMPRESSIONS / WEBSITE, pixel do config, evento custom do plano |
| **Ciclo de vida** | **`ad_set_goal: {"type": 0}`** → "Estratégia de ciclo de vida do cliente" = **Obter conversões de todos os públicos** |
| Público | `targeting_automation: {"advantage_audience": 1}` + público do último conjunto do país na conta (país novo: 18-65, celular, FB+IG) |
| Anúncio | vídeo, CTA LEARN_MORE, link com UTM, display link sem UTM, melhorias automáticas OPT_OUT |

> ⚠️ **Ciclo de vida:** sem o `ad_set_goal` o dropdown "Estratégia de ciclo de vida do cliente" fica **vazio** no Ads Manager. O `advantage_audience` sozinho **não** preenche esse dropdown. Tipos: `0` = todos os públicos, `1` = excluir clientes existentes e engajados, `2` = excluir clientes existentes. O Ads Manager só mostra o valor **depois de recarregar a página**.

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
    {"pais": "CA", "nicho": "Mix", "criativos": ["Nome de um anúncio que já existe", "Outro anúncio", "Mais um"]},
    {"pais": "US", "nicho": "Acessorios", "criativos": [
      {"video": "C:\\pasta\\relogio.mp4", "nome": "ES-NEW-09",
       "titulo": "Relojes para probar", "texto": "🎁 ¡Recibe RELOJES GRATIS + REGALOS!\n✅ ¡Sin costo de envío!"}
    ]}
  ]
}
```

| Campo | Valores | Padrão |
|---|---|---|
| `evento` | evento custom do pixel (ex. `ad_click`, `pv2`) | `evento_padrao` do config |
| `funil` | uma chave de `funis` do config | o primeiro funil do config |
| `url` | URL avulsa (substitui o funil) | — |
| `orcamento` | dólares por campanha/dia | `orcamento_padrao` do config |
| `inicio` | `agora` = ACTIVE na hora · `amanha` = ACTIVE agendado pra 00:01 do dia seguinte | `agora` |
| `blocos` | blocos extras no nome, ex. `["pv2"]` | `[]` |
| `permitir_repetir` | `true` deixa o mesmo criativo em 2 campanhas do mesmo país | `false` |
| `criativos` | **string** = nome de um anúncio que já existe na conta (reaproveita vídeo e texto de uma campanha do mesmo idioma) · **objeto** = vídeo novo (`video`, `titulo`, `texto`, `nome` opcional) | — |
| `fase` (por campanha) | `teste`, `escala` ou `null` | `teste`; `Mix` vai sem fase |

O script faz sozinho:
- **Numeração**: pega o maior número já usado no país na conta (fim do nome `- NN`) e continua dele — nome e UTM, sem duplicar.
- **Nome**: padrão `nome` do config, ex. `[DD/MM][direto][fase][Continente][PAÍS][idioma][Nicho][site][pagina] - NN`; conjunto `Aberto - {País}`; anúncio = nome do criativo.
- **UTM**: `?utm_source=facebook&utm_campaign=` + padrão `utm` do config.
- **1ª linha do texto**: se começar com a `primeira_linha` de algum país do config, troca pela do país da campanha.
- **Vídeo novo**: sobe, espera `ready` e usa a thumbnail.
- **Limite de API da Meta**: lotes de 5 com pausa de 5 min; se a conta bloquear, espera e tenta de novo sozinho.
- **Conferência no final**: status, evento, Advantage+ e ciclo de vida de cada conjunto — corrige o ciclo de vida se vier vazio — e imprime o nome de uma campanha.

## Fluxo

1. **Entender o pedido** — quantas campanhas, países, evento, funil, criativos. Pergunte só o que faltar.
2. **Escolher criativos com dado** — se tiver relatório de receita por campanha, cruzar com os anúncios da conta (ROI do criativo rateado pelos cliques do anúncio dentro da campanha).
3. **Montar o plano** e rodar o **dry-run**. Mostrar a matriz (país × qtd × pacote) e a numeração.
4. **Após o "sim"**, rodar sem `--dry-run` **em background** (50 campanhas ≈ 50-60 min por causa das pausas).
5. **Ao terminar**: mandar o resumo da conferência e **o nome de uma campanha** pra conferir no Ads Manager (lembrar de recarregar a página).

## Corrigir campanhas já criadas sem ciclo de vida

`--conferir` com o log da subida corrige automaticamente. Pra conjuntos de outra origem: `POST /{adset_id}` com `ad_set_goal={"type":0}` (só esse campo — não mexe no público).
