# 📖 Como Usar o TechScout AI

## ✅ Verificação Inicial

Primeiro, verifique se tudo está OK:

```bash
python test_setup.py
```

Este script verifica:
- ✅ Versão do Python
- ✅ Estrutura de pastas
- ✅ Imports funcionando
- ✅ Dependências instaladas
- ⚠️ Configuração da API Key

## 🚀 Passo a Passo Completo

### Passo 1: Instalar Dependências

```bash
uv sync --extra dev --locked
```

### Passo 2: Configurar API Key

**Opção A - Variável de Ambiente (Recomendado):**
```powershell
# Windows PowerShell
$env:OPENAI_API_KEY="sk-sua-chave-aqui"
```

```bash
# Linux/Mac
export OPENAI_API_KEY="sk-sua-chave-aqui"
```

**Opção B - Arquivo .env:**
1. Copie `.env.example` para `.env`
2. Edite e adicione sua chave:
```
OPENAI_API_KEY=sk-sua-chave-aqui
```

### Passo 3: Processar Dados

```bash
# Versão simplificada (recomendada)
python scripts/ingest.py

# Ou versão completa
python scripts/ingest.py
```

Isso vai:
- Ler os dados de `data/samples/noticias_exemplo.py`
- Extrair triplas usando GPT-3.5-turbo
- Criar o grafo de conhecimento
- Indexar documentos no ChromaDB
- Salvar em `data/graph_data.json` e `data/chroma_db/`

### Passo 4: Executar a Aplicação

```bash
streamlit run src/techscout/app_streamlit.py
```

Ou usando o entry point:

```bash
streamlit run streamlit_app.py
```

A aplicação abrirá automaticamente no navegador em `http://localhost:8501`

## 🎯 Uso da Interface

1. **Digite uma pergunta** na caixa de texto
   - Exemplo: "Quem é a Ana Souza e em que ela está envolvida?"

2. **Configure o modelo** na barra lateral
   - GPT-4: Mais preciso, mais caro
   - GPT-3.5-turbo: Mais barato, rápido

3. **Ajuste o número de resultados** (opcional)
   - Quantos documentos buscar no vector store

4. **Clique em "🔍 Investigar Mercado"**

5. **Veja os resultados:**
   - Resposta sintetizada pelo LLM
   - Visualização interativa do grafo
   - Contexto recuperado (expandir para ver)

## 📝 Adicionar Seus Próprios Dados

### Método 1: Editar data/samples/noticias_exemplo.py

```python
noticias = [
    "Seu texto 1 aqui...",
    "Seu texto 2 aqui...",
]
```

### Método 2: Criar novo arquivo

```python
# meus_dados.py
texts = [
    "Texto sobre startup X...",
    "Notícia sobre investimento Y...",
]
```

Depois execute:
```bash
python scripts/ingest.py meus_dados.py
```

## 🔍 Comandos Úteis

```bash
# Verificar setup
python test_setup.py

# Processar dados
python scripts/ingest.py

# Executar app
streamlit run src/techscout/app_streamlit.py

# Ver logs
# Windows
Get-Content logs\techscout.log -Tail 50

# Linux/Mac
tail -f logs/techscout.log
```

## ❓ Problemas?

Veja o arquivo [TROUBLESHOOTING.md](TROUBLESHOOTING.md) para soluções comuns.

## 📊 Estrutura de Dados

Os dados processados ficam em:
- `data/graph_data.pkl` - Grafo de conhecimento
- `data/chroma_db/` - Índices vetoriais
- `logs/techscout.log` - Logs da aplicação

## 🎨 Personalização

### Mudar modelo padrão

Edite `config/config.py` ou defina:
```bash
$env:OPENAI_MODEL="gpt-3.5-turbo"
```

### Ajustar busca

Edite `config/config.py`:
```python
VECTOR_SEARCH_K=5  # Mais resultados
GRAPH_EXPANSION_DEPTH=2  # Mais profundidade no grafo
```

### Customizar extração de triplas

Edite `src/techscout/triple_extractor.py` - método `_build_prompt()`

## 🚀 Pronto para Produção

O projeto está configurado e pronto para uso! Basta:
1. ✅ Configurar API Key
2. ✅ Processar dados
3. ✅ Executar app
4. ✅ Fazer perguntas!

