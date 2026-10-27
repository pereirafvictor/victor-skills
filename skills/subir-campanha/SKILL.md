---
name: subir-campanha
description: Sobe campanhas no Meta Ads em lote a partir de um plano, nos dois modelos — DIRETO (tráfego pro site, conversão no pixel; vários países, funis e eventos, numeração contínua) e CHATBOT (anúncio abre o Messenger da página, 1 campanha por página, boas-vindas com ice breakers, UTM da página). Sempre com "Estratégia de ciclo de vida do cliente" = Obter conversões de todos os públicos. Uso: "sobe 30 campanhas em francês com ad_click", "sobe chatbot nas páginas da França".
---

# Subir Campanha (modelo direto e chatbot)

Você é a skill **subir-campanha**. Primeiro descubra o **modelo**:

| Modelo | Quando | Script | Config |
|---|---|---|---|
| **Direto** | anúncio leva pro site (quiz/chat), conversão no pixel | `scripts/subir_direto.py` | `config.json` |
| **Chatbot** | anúncio abre o **Messenger** da página | `scripts/subir_chatbot.py` | `config.chatbot.json` |

Na dúvida, pergunte. Os dois são bem diferentes — **nunca** suba chatbot com o script do direto nem o contrário.
O chatbot está na seção [Modelo chatbot](#modelo-chatbot); o resto deste arquivo é o direto.

A subida é feita pelo script — você monta o **plano JSON** e roda o script via Bash; não escreva chamadas de API na mão.

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

---

# Modelo chatbot

O anúncio abre o **Messenger da página**; o bot faz o reengajamento (LTV). Script: `scripts/subir_chatbot.py`.

```bash
cd <pasta da skill>
python -I -X utf8 scripts/subir_chatbot.py <plano.json> --dry-run   # sempre primeiro
python -I -X utf8 scripts/subir_chatbot.py <plano.json>             # cria (rodar em background: tem pausas)
python -I -X utf8 scripts/subir_chatbot.py <plano.json> --conferir  # confere/corrige as já criadas
```

Mesmo esquema de log do direto (`<plano>.log.json`, retoma de onde parou).

## Regras do chatbot (diferente do direto)

- **1 campanha por página** — nunca 2 campanhas da mesma página no mesmo plano. Quer testar mais criativo? Outra página.
- **UTM é da página, não da campanha**: `utm_source=facebook&utm_campaign=udl-shein-{idioma}-{pais}-{pagina}-chatbot`, no campo **url_tags** de cada anúncio (o GAM soma por página).
- **Nome da campanha**: `[DD/MM][udl][shein][Franca|Espanha|Belgica|canada][pagina][chatbot] - 1`. O conjunto leva o mesmo nome.
- **Nome do anúncio**: `{criativo} - {Nome da Página}` (ex. `Colete Nike - Zoe Mitchell`).
- **Mensagem de boas-vindas** obrigatória em todo anúncio: texto + 3 ice breakers, sem resposta (o bot responde).

## Configuração fixa de toda campanha de chatbot

| Nível | Configuração |
|---|---|
| Campanha | OUTCOME_SALES, orçamento na campanha, LOWEST_COST_WITHOUT_CAP |
| Conjunto | OFFSITE_CONVERSIONS / IMPRESSIONS / **MESSENGER**, pixel + evento padrão (`SEARCH`) + `page_id` da página |
| **Ciclo de vida** | **`ad_set_goal: {"type": 0}`** — Obter conversões de todos os públicos |
| Público | 18-65, aberto, `advantage_audience: 1`, celular + desktop — copia o último conjunto de chatbot do país |
| Posicionamentos | **SÓ Facebook (feed, story, reels) + Messenger (home)** — sem Instagram, sem Threads (o script força) |
| Início | `amanha` = ACTIVE agendado 00:01 no fuso da conta (padrão) |
| DSA | beneficiário/pagador do config nos países com `"ue": true` |
| Anúncio | vídeo + thumbnail, CTA **MESSAGE_PAGE** (Messenger), boas-vindas, UTM da página em `url_tags`, melhorias automáticas OPT_OUT |

## Config (`config.chatbot.json`, fora do git)

Copie `config.chatbot.example.json` → `config.chatbot.json`. Campos: `conta`, `pixel`, `dsa_beneficiario`, `site`/`oferta`/`utm_prefixo` (blocos do nome e da UTM), `evento_padrao`, `orcamento_padrao`, `fuso` da conta, `descricao_padrao` (linha abaixo do título), `paises` (`idioma`, `bloco` do nome, `ue`) e **`paginas`** (`slug`: `id`, `nome` exibido no anúncio, `pais`).

Página nova? Cadastre em `paginas` antes de subir.

## Plano JSON (chatbot)

```json
{
  "orcamento": 5,
  "inicio": "amanha",
  "campanhas": [
    {"pagina": "zoemitchell", "criativos": ["Colete Nike", "Pulseira Pandora"]},
    {"pagina": "dianavieira", "orcamento": 3, "criativos": [
      {"video": "C:\pasta\chaleco.mp4", "nome": "Chaleco Nike",
       "titulo": "CHALECO GRATIS",
       "texto": "➡ ¡Recibe tu chaleco GRATIS! ✅ ¡Envío gratis!",
       "descricao": "Oferta por tiempo limitado",
       "boas_vindas": {"texto": "¡Hola {{user_first_name}}! 😊 Elige el producto que quieres probar gratis:",
                       "botoes": ["🧥 Quiero probar el CHALECO GRATIS", "👗 Quiero probar ROPA GRATIS", "🎁 Quiero elegir OTRO PRODUCTO"]}}
    ]}
  ]
}
```

| Campo | Valores | Padrão |
|---|---|---|
| `pagina` | slug cadastrado em `paginas` | — |
| `orcamento` | dólares/dia (no plano ou por campanha) — **dólar inteiro** | `orcamento_padrao` |
| `inicio` | `amanha` (00:01 do dia seguinte) · `agora` · `pausada` | `amanha` |
| `evento` | evento padrão do pixel | `evento_padrao` (`SEARCH`) |
| `criativos` | **string** = criativo que já roda em chatbot do mesmo idioma (nome antes de ` - Página`; reaproveita vídeo, texto e boas-vindas) · **objeto** = vídeo novo com `boas_vindas` | — |

## Fluxo (chatbot)

1. Entender o pedido — quais páginas, orçamento e criativos. Página sem `paginas` no config → cadastrar.
2. Montar o plano e rodar o **dry-run**; mostrar nome, anúncios e UTM de cada página.
3. Após o "sim", rodar sem `--dry-run` em background.
4. Ao terminar: resumo da conferência (destino Messenger, só FB+Messenger, UTM em todo anúncio, CTA, ciclo de vida) e **o nome de uma campanha** pra conferir no Ads Manager.
