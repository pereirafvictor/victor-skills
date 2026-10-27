---
name: subir-campanha
description: Sobe campanha no Meta Ads em dois modelos — DIRETO/site (tráfego, vendas, leads ou engajamento, com o perfil do gestor) e CHATBOT (anúncio abre o Messenger da página, 1 campanha por página, boas-vindas com ice breakers, UTM da página). Sempre com dry-run antes. Uso: "sobe campanha de vendas pro site-br com 50 reais na página loja", "sobe chatbot nas páginas da França".
---

# Subir Campanha

Você é a skill **subir-campanha**. Ela é implementada em Python — você invoca via Bash, não escreve código.

**Primeiro descubra o modelo:**
- **Direto / site** — anúncio leva pra um site → seções 0 a 4 abaixo (`scripts/main.py`).
- **Chatbot** — anúncio abre o **Messenger** da página → seção [Modelo chatbot](#modelo-chatbot) (`scripts/subir_chatbot.py`).

Na dúvida, pergunte. Nunca suba chatbot pelo `main.py`.

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

---

# Modelo chatbot

O anúncio abre o **Messenger da página**; o bot faz o reengajamento (LTV). Script: `scripts/subir_chatbot.py`.

```bash
python -X utf8 ~/.claude/skills/subir-campanha/scripts/subir_chatbot.py <plano.json> --dry-run   # sempre primeiro
python -X utf8 ~/.claude/skills/subir-campanha/scripts/subir_chatbot.py <plano.json>             # cria (rodar em background: tem pausas)
python -X utf8 ~/.claude/skills/subir-campanha/scripts/subir_chatbot.py <plano.json> --conferir  # confere/corrige as já criadas
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

## Config (`~/.meta-ads/config.chatbot.json`)

Token: o mesmo `~/.meta-ads/.env` das outras skills. Na primeira vez, copie `~/.claude/skills/subir-campanha/config.chatbot.example.json` → `~/.meta-ads/config.chatbot.json` e preencha com o gestor (fica fora da pasta da skill pra não ser apagado quando reinstalar). Campos: `conta`, `pixel`, `dsa_beneficiario`, `site`/`oferta`/`utm_prefixo` (blocos do nome e da UTM), `evento_padrao`, `orcamento_padrao`, `fuso` da conta, `descricao_padrao` (linha abaixo do título), `paises` (`idioma`, `bloco` do nome, `ue`) e **`paginas`** (`slug`: `id`, `nome` exibido no anúncio, `pais`).

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
