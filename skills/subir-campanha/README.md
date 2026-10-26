# subir-campanha

Sobe campanhas do modelo **direto** no Meta Ads em lote, a partir de um plano JSON.
Todo conjunto sai com **Estratégia de ciclo de vida do cliente = Obter conversões de todos os públicos**
(`ad_set_goal: {"type": 0}`) e Advantage+ Audience ligado.

## Instalação

1. Configura o token no `.env` (copie o `.env.example`):
   ```env
   META_ACCESS_TOKEN=EAAxxxx...
   ```
2. Dependências:
   ```bash
   pip install requests python-dotenv
   ```

## Uso

```bash
python scripts/subir_direto.py plano.json --dry-run
python scripts/subir_direto.py plano.json
python scripts/subir_direto.py plano.json --conferir
```

Formato do plano e regras: ver [SKILL.md](SKILL.md).
