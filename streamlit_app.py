"""Ponto de entrada do Streamlit.

Mantido fino de propósito: a aplicação vive em ``techscout.app_streamlit``.
Este arquivo apenas garante que o pacote seja importável quando o repositório
é executado da raiz sem `pip install -e .`.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    from techscout.app_streamlit import main
except ImportError as exc:  # pragma: no cover - caminho de diagnóstico
    sys.exit(
        f"Erro ao importar a aplicação: {exc}\n\n"
        "Instale o pacote e suas dependências com:\n"
        "    pip install -e .\n"
    )

main()
