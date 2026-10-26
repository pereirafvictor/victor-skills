# subir-campanha

Sobe campanhas do modelo **direto** no Meta Ads em lote, a partir de um plano JSON.
Todo conjunto sai com **Estratégia de ciclo de vida do cliente = Obter conversões de todos os públicos**
(`ad_set_goal: {"type": 0}`) e Advantage+ Audience ligado.

## Instalação

1. Dependências:
   ```bash
   pip install requests python-dotenv
   ```
2. Token: copie `.env.example` → `.env` e coloque o seu `META_ACCESS_TOKEN` (com `ads_management`).
3. Sua conta: copie `config.example.json` → `config.json` e preencha conta, página, pixel, site, funis e países.
   `.env` e `config.json` ficam fora do git.

## Uso

```bash
python scripts/subir_direto.py plano.json --dry-run
python scripts/subir_direto.py plano.json
python scripts/subir_direto.py plano.json --conferir
```

Formato do plano, do config e regras: ver [SKILL.md](SKILL.md).
