# subir-campanha

Sobe campanhas no Meta Ads em lote, a partir de um plano JSON, em dois modelos:

| Modelo | Script | Config |
|---|---|---|
| **Direto** — anúncio leva pro site, conversão no pixel | `scripts/subir_direto.py` | `config.json` |
| **Chatbot** — anúncio abre o Messenger da página, 1 campanha por página | `scripts/subir_chatbot.py` | `config.chatbot.json` |

Todo conjunto sai com **Estratégia de ciclo de vida do cliente = Obter conversões de todos os públicos**
(`ad_set_goal: {"type": 0}`) e Advantage+ Audience ligado.

## Instalação

1. Dependências:
   ```bash
   pip install requests python-dotenv
   ```
2. Token: copie `.env.example` → `.env` e coloque o seu `META_ACCESS_TOKEN` (com `ads_management`).
3. Sua conta:
   - direto: copie `config.example.json` → `config.json`
   - chatbot: copie `config.chatbot.example.json` → `config.chatbot.json` e cadastre as páginas

   `.env`, `config.json` e `config.chatbot.json` ficam fora do git.

## Uso

```bash
python scripts/subir_direto.py plano.json --dry-run      # direto
python scripts/subir_chatbot.py plano.json --dry-run     # chatbot
python scripts/subir_chatbot.py plano.json               # cria
python scripts/subir_chatbot.py plano.json --conferir    # confere as já criadas
```

Formato dos planos, dos configs e regras de cada modelo: ver [SKILL.md](SKILL.md).
