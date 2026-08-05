# 📰 Como Buscar Dados da Internet para Ingestão

## 🎯 Opções Disponíveis

### Opção 1: Feeds RSS (Gratuito, Sem API Key)

Feeds RSS de tecnologia em português:
- Tecnoblog
- TecMundo
- CanalTech
- Olhar Digital

**Vantagens:**
- ✅ Gratuito
- ✅ Não precisa de API key
- ✅ Sempre atualizado
- ✅ Fácil de usar

**Como usar:**
```bash
python scripts/ingest_quick.py
```

### Opção 2: NewsAPI (Requer API Key)

API profissional de notícias com milhões de artigos.

**Vantagens:**
- ✅ Muitos artigos
- ✅ Busca por palavras-chave
- ✅ Filtros avançados
- ✅ Dados estruturados

**Como obter API Key:**
1. Acesse: https://newsapi.org/
2. Crie uma conta gratuita
3. Copie sua API key
4. Adicione no `.env`:
   ```env
   NEWSAPI_KEY=sua-chave-aqui
   ```

**Como usar:**
```bash
python scripts/ingest_online.py
```

### Opção 3: Script Interativo

Script completo com opções:

```bash
python scripts/ingest_online.py
```

Você pode escolher:
- Apenas RSS
- Apenas NewsAPI
- Ambos

## 🚀 Uso Rápido

### Método Mais Simples (RSS apenas)

```bash
python scripts/ingest_quick.py
```

Isso vai:
1. ✅ Coletar notícias de feeds RSS
2. ✅ Processar e extrair triplas
3. ✅ Criar grafo e índices vetoriais
4. ✅ Pronto para usar!

### Método Completo (com NewsAPI)

1. **Configure NewsAPI key** (opcional):
   ```env
   # No arquivo .env
   NEWSAPI_KEY=sua-chave-newsapi
   ```

2. **Execute:**
   ```bash
   python scripts/ingest_online.py
   ```

3. **Escolha as opções:**
   - Fonte de dados (RSS, NewsAPI ou ambos)
   - Quantidade de artigos

## 📊 Quantidade de Dados

### Recomendações:

- **Desenvolvimento/Teste:** 10-20 artigos
- **Uso Normal:** 30-50 artigos
- **Produção:** 50-100+ artigos

⚠️ **Atenção:** Mais artigos = mais tempo de processamento e mais custo com OpenAI

## 🔧 Configuração Avançada

### Adicionar Novos Feeds RSS

Edite `src/techscout/data_sources.py`:

```python
RSS_FEEDS = [
    "https://rss.tecnoblog.net/feed/",
    "https://seu-feed-aqui.com/feed/",  # Adicione aqui
]
```

### Personalizar Queries da NewsAPI

Edite `scripts/ingest_online.py` ou use diretamente:

```python
from src.techscout.data_sources import TechNewsCollector

collector = TechNewsCollector(newsapi_key="sua-chave")
texts = collector.collect_from_newsapi(
    queries=["startup", "IA", "investimento"],
    max_articles=50
)
```

## 💡 Dicas

1. **Primeira vez:** Use `ingest_quick.py` para testar
2. **Produção:** Use `ingest_online.py` com NewsAPI
3. **Atualização:** Execute periodicamente para dados frescos
4. **Custo:** RSS é gratuito, NewsAPI tem limite no plano free

## 📝 Exemplo Completo

```bash
# 1. Configure .env
OPENAI_API_KEY=sk-...
NEWSAPI_KEY=sua-chave-newsapi  # Opcional

# 2. Execute ingestão rápida (RSS)
python scripts/ingest_quick.py

# Ou ingestão completa
python scripts/ingest_online.py

# 3. Execute o app
streamlit run src/techscout/app_streamlit.py
```

## 🔍 Verificar Dados Coletados

Após a ingestão, você pode verificar:

```python
from src.techscout.graph_rag import GraphRAG

graph = GraphRAG.load()
if graph:
    stats = graph.get_stats()
    print(f"Nós: {stats['nodes']}")
    print(f"Arestas: {stats['edges']}")
```

## ❓ Problemas Comuns

### "Nenhum texto coletado"

**Solução:**
- Verifique sua conexão com internet
- Tente feeds RSS primeiro (mais confiável)
- Verifique se os feeds ainda estão ativos

### "NewsAPI rate limit"

**Solução:**
- Plano free tem limite de 100 requests/dia
- Use feeds RSS como alternativa
- Aguarde 24h ou faça upgrade

### "Erro ao processar"

**Solução:**
- Verifique se OPENAI_API_KEY está configurada
- Verifique se tem créditos na conta OpenAI
- Tente com menos artigos primeiro

## 🎯 Próximos Passos

Após coletar dados:

1. ✅ Execute a ingestão
2. ✅ Verifique os logs em `logs/techscout.log`
3. ✅ Execute o app: `streamlit run src/techscout/app_streamlit.py`
4. ✅ Faça perguntas sobre os dados coletados!

