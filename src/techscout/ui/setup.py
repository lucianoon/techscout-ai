"""
Configuração inicial do ambiente Streamlit
"""
import logging
import sys
import warnings

# Suprime avisos do Streamlit ANTES de importar
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")
logging.getLogger("streamlit.runtime.scriptrunner_utils").setLevel(logging.ERROR)

# Correção para SQLite no Streamlit Cloud (se necessário)
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

def setup_streamlit_environment():
    """
    Configura o ambiente Streamlit (warnings, paths, etc.)
    Deve ser chamado antes de qualquer import do Streamlit
    """
    # Configuração já feita no nível do módulo
    pass

