---
name: configurar-meta-ads
description: Configura (ou reconfigura) o perfil de Meta Ads do gestor — token, conta de anúncios, pixel, páginas, domínios/URLs, objetivo padrão e KPIs. Usar na primeira vez, quando outra skill de Meta Ads disser que falta perfil, ou quando o gestor pedir "configura meu meta ads", "adiciona uma página", "troca meu pixel".
---

# Configurar Meta Ads

Você é a skill **configurar-meta-ads**. Ela cria o perfil que as skills `subir-campanha` e
`diagnostico-conta` usam. Nada é fixo no código: cada gestor tem a própria conta, pixel,
páginas, domínios, objetivo e metas.

Tudo fica em `~/.meta-ads/` (no Windows: `C:\Users\<usuario>\.meta-ads\`):
- `.env` — `META_ACCESS_TOKEN` (segredo, nunca mostrar no chat)
- `perfil.json` — o resto da configuração

Scripts: `~/.claude/skills/configurar-meta-ads/scripts/setup.py` (rodar com `python`).

## Passo a passo

Faça uma etapa por vez, em linguagem simples. O gestor pode não ser técnico.

### 1. Token
Verifique se `~/.meta-ads/.env` tem `META_ACCESS_TOKEN`. Se não tiver:
- Peça para o gestor **colar o token ele mesmo** no arquivo `~/.meta-ads/.env` (abra o arquivo
  para ele). Não peça para colar o token no chat.
- Como gerar: business.facebook.com → Configurações do negócio → Usuários do sistema → criar
  usuário do sistema (Admin) → Adicionar ativos (conta de anúncios, páginas, pixel) →
  Gerar token com as permissões `ads_management`, `ads_read`, `pages_show_list`,
  `pages_read_engagement`, `business_management`. Token de usuário do sistema não expira.

Depois rode:
```bash
python ~/.claude/skills/configurar-meta-ads/scripts/setup.py checar
```

### 2. Descobrir ativos
```bash
python ~/.claude/skills/configurar-meta-ads/scripts/setup.py descobrir
```
Mostre as contas e páginas encontradas e pergunte qual conta usar. Com a conta escolhida, rode de
novo com `--conta act_XXX` para listar os pixels.

### 3. Perguntas (use AskUserQuestion quando tiver opções)
1. **Conta de anúncios** (da lista)
2. **Páginas** que ele usa (da lista) e um apelido curto para cada
3. **Pixel** (da lista) e **evento de conversão** padrão (PURCHASE, LEAD, COMPLETE_REGISTRATION…) — pode pular se só faz tráfego/engajamento
4. **Destinos**: URLs que ele anuncia, com apelido, país(es) e idioma (pt/es/fr/en)
5. **Objetivo padrão**: trafego, vendas, leads ou engajamento (dá pra trocar em cada campanha)
6. **Estrutura padrão**: quantos conjuntos por campanha e anúncios por conjunto
7. **Público padrão**: idade, Advantage+ ou não, posicionamentos (Facebook / Instagram / Messenger; feed, stories, reels)
8. **UTM** (opcional) — ex: `utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}`
9. **Textos padrão** por idioma (opcional) e **CTA** (LEARN_MORE, SHOP_NOW, SIGN_UP…)
10. **Teto de orçamento diário** por campanha (trava de segurança; 0 = sem teto)
11. **Metas de KPI** por objetivo (bom / ruim) — usadas no diagnóstico. Se não souber, mantenha os padrões do exemplo
12. **Países da UE**: nome do beneficiário/pagador (DSA) — só se anuncia na Europa
13. **CSV do GAM** (opcional) — pasta onde salva o `campanhas_*.csv`, se usar Google Ad Manager

### 4. Gravar e validar
Escreva `~/.meta-ads/perfil.json` seguindo o modelo `perfil.exemplo.json` (na pasta desta skill).
Não coloque o token no perfil. Depois:
```bash
python ~/.claude/skills/configurar-meta-ads/scripts/setup.py validar
```
Corrija o que der erro e mostre um resumo final do perfil.

## Alterações depois
Para "adiciona a página X", "troca meu pixel", "muda o teto pra 500": edite só o campo em
`perfil.json` e rode `validar` de novo.
