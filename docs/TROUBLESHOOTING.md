# 🔧 Guia de Troubleshooting

## Problemas Comuns e Soluções

### 1. "OPENAI_API_KEY não configurada"

**Solução:**
```powershell
# Windows PowerShell
$env:OPENAI_API_KEY="sk-sua-chave-aqui"

# Ou crie arquivo .env na raiz do projeto
OPENAI_API_KEY=sk-sua-chave-aqui
```

### 2. "Erro de importação" ou "ModuleNotFoundError"

**Solução:**
```bash
# Instale todas as dependências
pip install -e ".[dev]"

# Verifique se está na raiz do projeto
cd "TechScout AI"
```

### 3. "Dados não encontrados" no Streamlit

**Solução:**
```bash
# Execute a ingestão primeiro
python scripts/ingest.py

# Ou
python scripts/ingest.py
```

### 4. Erro ao executar scripts

**Use as versões simplificadas:**
```bash
# Ingestão
python scripts/ingest.py

# App Streamlit
streamlit run src/techscout/app_streamlit.py
```

### 5. Problemas de Path/Import no Windows

**Solução:**
- Certifique-se de estar na raiz do projeto
- Use os scripts simplificados (`scripts/ingest.py`)
- Verifique se todas as pastas existem: `src/techscout/`, `config/`, `data/`

### 6. Streamlit não abre

**Solução:**
```bash
# Verifique se Streamlit está instalado
pip install streamlit

# Execute diretamente
streamlit run src/techscout/app_streamlit.py
```

## Verificação Rápida

Execute estes comandos para verificar se está tudo OK:

```bash
# 1. Verificar Python
python --version  # Deve ser 3.11+

# 2. Verificar dependências
pip list | findstr streamlit
pip list | findstr langchain

# 3. Verificar estrutura
dir src\techscout
dir config

# 4. Testar imports
python -c "from config import settings; print('OK')"
```

## Ordem Correta de Execução

1. **Instalar dependências:**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Configurar API Key:**
   ```powershell
   $env:OPENAI_API_KEY="sk-..."
   ```

3. **Processar dados:**
   ```bash
   python scripts/ingest.py
   ```

4. **Executar app:**
   ```bash
   streamlit run src/techscout/app_streamlit.py
   ```

## Se Nada Funcionar

1. Verifique se está na pasta correta
2. Verifique se a API key está configurada
3. Verifique se as dependências estão instaladas
4. Tente usar os scripts simplificados (`scripts/ingest.py`)
5. Verifique os logs em `logs/techscout.log`

## Logs

Os logs estão em: `logs/techscout.log`

Para ver em tempo real:
```bash
# Windows PowerShell
Get-Content logs\techscout.log -Wait -Tail 50
```

