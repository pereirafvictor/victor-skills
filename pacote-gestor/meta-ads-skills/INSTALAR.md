# Skills de Meta Ads para Claude Code

Três skills que funcionam juntas:

| Skill | O que faz | Exemplo de frase |
|---|---|---|
| `configurar-meta-ads` | Cadastra seu token, conta, pixel, páginas, URLs, objetivo e metas | "configura meu meta ads" |
| `subir-campanha` | Sobe campanha de site (tráfego, vendas, leads ou engajamento) ou de **chatbot** (Messenger, 1 campanha por página) | "sobe campanha de vendas pro site-br com 50 reais" / "sobe chatbot nas páginas da França" |
| `otimizacao` | Otimiza a conta: Régua de Corte por ROI e o que pausar, trocar e escalar | "diagnostica minha conta dos últimos 7 dias" |

Nada vem configurado com dados de outra pessoa: **você usa seu próprio pixel, páginas e domínios.**

---

## Baixar

- **Sem git:** abra [github.com/pereirafvictor/victor-skills](https://github.com/pereirafvictor/victor-skills) → botão verde **Code** → **Download ZIP** → descompacte e entre em `pacote-gestor/meta-ads-skills`.
- **Com git:**
  ```bash
  git clone https://github.com/pereirafvictor/victor-skills.git
  cd victor-skills/pacote-gestor/meta-ads-skills
  ```

Para atualizar depois: baixe de novo (ou `git pull`) e rode o instalador outra vez — seu perfil e token não são apagados.

---

## Jeito mais fácil: deixar o Claude instalar

1. Baixe e entre na pasta `meta-ads-skills` (veja acima).
2. Abra o Claude Code **nessa pasta** e cole:

   > Leia o INSTALAR.md desta pasta e instale as skills de Meta Ads pra mim. Depois me ajude a configurar.

Pronto: ele roda o instalador e depois te faz as perguntas da configuração.

---

## Instalação manual

**Pré-requisitos:** [Claude Code](https://claude.com/claude-code) e [Python 3.10+](https://www.python.org/downloads/) (no Windows, marque "Add Python to PATH").

**Windows** — na pasta descompactada:
```powershell
powershell -ExecutionPolicy Bypass -File instalar.ps1
```

**Mac / Linux:**
```bash
bash instalar.sh
```

O instalador:
- copia as 3 skills para `~/.claude/skills/`
- instala as dependências Python (`requests`, `python-dotenv`)
- cria `~/.meta-ads/.env`, onde vai o seu token

Depois abra o Claude Code (em qualquer pasta) e diga: **"configura meu meta ads"**.

---

## Gerar o token do Meta (uma vez)

Use um **usuário do sistema** — o token não expira:

1. [business.facebook.com](https://business.facebook.com) → **Configurações do negócio** → **Usuários** → **Usuários do sistema** → **Adicionar** (função Admin)
2. **Atribuir ativos**: sua conta de anúncios, suas páginas e seu pixel (controle total)
3. **Gerar novo token** → escolha um app do seu Business → marque:
   `ads_management`, `ads_read`, `pages_show_list`, `pages_read_engagement`, `business_management`
4. Cole o token em `~/.meta-ads/.env`:
   ```
   META_ACCESS_TOKEN=EAAxxxx...
   ```
   (Windows: `C:\Users\<seu usuário>\.meta-ads\.env`)

**Não mande o token no chat nem para ninguém.** Ele dá acesso à sua conta de anúncios.

---

## O que fica configurado no seu perfil

`~/.meta-ads/perfil.json` — o Claude monta pra você, mas dá pra editar à mão (modelo em `skills/configurar-meta-ads/perfil.exemplo.json`):

- conta de anúncios e moeda
- **objetivo padrão** (tráfego, vendas, leads ou engajamento) — dá pra trocar em cada campanha
- pixel e evento de conversão
- páginas e destinos (URLs, país, idioma), com apelidos
- público padrão (idade, Advantage+, posicionamentos)
- estrutura padrão (conjuntos × anúncios)
- UTM, CTA e textos padrão
- **teto de orçamento diário** (trava contra erro de digitação)
- metas de KPI (CPC, CPA, CPL, custo/engajamento) usadas no diagnóstico

Atualizar as skills (rodar o instalador de novo) **não apaga** o seu perfil nem o token.

---

## Segurança
- Toda campanha sobe **pausada**: você revisa e ativa no Ads Manager.
- Antes de subir, o Claude sempre mostra uma simulação (dry-run) e pede confirmação.
- O diagnóstico só lê dados, não altera nada.
