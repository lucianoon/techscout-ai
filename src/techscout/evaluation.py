"""Avaliação de recuperação: Recall@K e MRR sobre um dataset rotulado.

A pergunta que este módulo responde é a do README: **um grafo de conhecimento
recupera melhor que busca por passagem em perguntas relacionais?**

Para que a comparação seja justa, os dois lados devolvem a mesma coisa — uma
lista ordenada de ids de documento — e são medidos pelo mesmo rótulo. O grafo
chega lá pela proveniência das arestas (`GraphRAG.retrieve_documents`); o
baseline lexical, por BM25 sobre os textos.

O grafo usado na avaliação é fixo (`data/eval/triples_v1.json`), curado à mão.
Isso é deliberado: isola a qualidade da **recuperação** da qualidade da
**extração** por LLM, que varia entre modelos e execuções. Um número que
misturasse as duas não diria qual das partes é boa ou ruim.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from techscout.graph_rag import GraphRAG

# --------------------------------------------------------------------------
# Tokenização
# --------------------------------------------------------------------------

# Termos de até 2 caracteres são descartados, mesma regra da busca no grafo,
# para que os dois lados enxerguem a consulta do mesmo jeito.
_MIN_TOKEN = 3

# Stopwords que, no domínio de notícias de mercado, aparecem em quase todo
# documento e por isso não discriminam.
_STOPWORDS = frozenset(
    # fmt: off
    (
        "que", "quem", "qual", "quais", "como", "onde", "quando",
        "por", "para", "com", "sem", "sobre", "entre",
        "uma", "umas", "uns", "dos", "das", "nos", "nas",
        "pelo", "pela", "pelos", "pelas",
        "ele", "ela", "eles", "elas", "seu", "sua", "seus", "suas",
        "este", "esta", "estes", "estas", "esse", "essa", "isso", "aquilo",
        "the", "and", "for", "from", "with",
    )
    # fmt: on
)


def normalizar(texto: str) -> str:
    """Minúsculas sem acento, para que 'Órbita' e 'orbita' casem."""
    decomposto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def tokenizar(texto: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", normalizar(texto))
    return [t for t in tokens if len(t) >= _MIN_TOKEN and t not in _STOPWORDS]


# --------------------------------------------------------------------------
# Métricas
# --------------------------------------------------------------------------


def recall_at_k(recuperados: list[str], relevantes: set[str], k: int) -> float:
    """Fração dos documentos relevantes que apareceu nos k primeiros.

    Com múltiplos relevantes por pergunta, o denominador é o total de
    relevantes — não 1 — para que responder metade da pergunta valha metade
    do ponto.
    """
    if not relevantes:
        return 0.0
    encontrados = set(recuperados[:k]) & relevantes
    return len(encontrados) / len(relevantes)


def reciprocal_rank(recuperados: list[str], relevantes: set[str]) -> float:
    """Inverso da posição do primeiro documento relevante (0 se nenhum)."""
    for posicao, doc_id in enumerate(recuperados, start=1):
        if doc_id in relevantes:
            return 1.0 / posicao
    return 0.0


# --------------------------------------------------------------------------
# Recuperadores
# --------------------------------------------------------------------------


class Retriever(Protocol):
    nome: str

    def retrieve(self, query: str, k: int) -> list[str]:
        """Ids de documento, do mais para o menos relevante."""


@dataclass
class Documento:
    id: str
    titulo: str
    texto: str

    @property
    def conteudo(self) -> str:
        return f"{self.titulo} {self.texto}"


class BM25Retriever:
    """Busca por passagem com BM25 — o baseline padrão da área.

    Determinístico e sem dependência externa, o que permite medi-lo na CI.
    """

    nome = "bm25"

    def __init__(self, documentos: list[Documento], k1: float = 1.5, b: float = 0.75):
        self.documentos = documentos
        self.k1 = k1
        self.b = b

        self._tokens = {d.id: tokenizar(d.conteudo) for d in documentos}
        self._freq = {doc_id: Counter(toks) for doc_id, toks in self._tokens.items()}
        tamanhos = [len(t) for t in self._tokens.values()]
        self._tam_medio = sum(tamanhos) / len(tamanhos) if tamanhos else 0.0

        total = len(documentos)
        ocorrencias: Counter[str] = Counter()
        for toks in self._tokens.values():
            ocorrencias.update(set(toks))
        self._idf = {
            termo: math.log(1 + (total - n + 0.5) / (n + 0.5))
            for termo, n in ocorrencias.items()
        }

    def _score(self, doc_id: str, termos: list[str]) -> float:
        freq = self._freq[doc_id]
        tamanho = len(self._tokens[doc_id])
        total = 0.0
        for termo in termos:
            f = freq.get(termo, 0)
            if not f:
                continue
            denominador = f + self.k1 * (
                1 - self.b + self.b * tamanho / (self._tam_medio or 1)
            )
            total += self._idf.get(termo, 0.0) * f * (self.k1 + 1) / denominador
        return total

    def retrieve(self, query: str, k: int) -> list[str]:
        termos = tokenizar(query)
        if not termos:
            return []
        pontuados = [(d.id, self._score(d.id, termos)) for d in self.documentos]
        # Desempate pelo id mantém o ranking reprodutível.
        pontuados.sort(key=lambda par: (-par[1], par[0]))
        return [doc_id for doc_id, score in pontuados[:k] if score > 0]


class GraphRetriever:
    """Recuperação pela proveniência das arestas do grafo."""

    nome = "grafo"

    def __init__(self, graph_rag: GraphRAG, expansion_depth: int = 1):
        self.graph_rag = graph_rag
        self.expansion_depth = expansion_depth

    def retrieve(self, query: str, k: int) -> list[str]:
        return self.graph_rag.retrieve_documents(
            query, k=k, expansion_depth=self.expansion_depth
        )


class HybridRetriever:
    """Funde grafo e BM25 por reciprocal rank fusion.

    RRF soma 1/(c + posição) de cada lista, o que dispensa normalizar scores
    de escalas diferentes — problema real aqui, já que a pontuação do grafo
    conta arestas e a do BM25 é uma soma de IDF.
    """

    nome = "hibrido"

    def __init__(self, grafo: GraphRetriever, lexical: BM25Retriever, c: int = 60):
        self.grafo = grafo
        self.lexical = lexical
        self.c = c

    def retrieve(self, query: str, k: int) -> list[str]:
        pontuacao: dict[str, float] = {}
        # Busca uma janela maior que k em cada lado: um documento pode estar
        # fora do topo dos dois e ainda assim vencer pela soma.
        janela = max(k * 2, 10)
        for retriever in (self.grafo, self.lexical):
            for posicao, doc_id in enumerate(retriever.retrieve(query, janela), 1):
                pontuacao[doc_id] = pontuacao.get(doc_id, 0.0) + 1.0 / (
                    self.c + posicao
                )
        ordenados = sorted(pontuacao.items(), key=lambda par: (-par[1], par[0]))
        return [doc_id for doc_id, _ in ordenados[:k]]


# --------------------------------------------------------------------------
# Dataset e execução
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Caso:
    id: str
    tipo: str
    pergunta: str
    documentos_relevantes: frozenset[str]


@dataclass(frozen=True)
class Resultado:
    retriever: str
    tipo: str
    n_casos: int
    recall_at_k: float
    mrr: float


def _data_dir() -> Path:
    """Localiza `data/eval`, que acompanha o repositório e não o pacote.

    Em instalação editável o caminho relativo ao módulo resolve; a partir de
    um wheel, não — daí o recuo para o diretório de trabalho.
    """
    do_repo = Path(__file__).resolve().parents[2] / "data" / "eval"
    if do_repo.is_dir():
        return do_repo
    do_cwd = Path.cwd() / "data" / "eval"
    if do_cwd.is_dir():
        return do_cwd
    raise FileNotFoundError(
        "Diretório data/eval não encontrado. O dataset acompanha o "
        "repositório: rode a avaliação a partir da raiz do projeto."
    )


def carregar_corpus(caminho: Path | None = None) -> list[Documento]:
    dados = json.loads(
        (caminho or _data_dir() / "corpus_v1.json").read_text(encoding="utf-8")
    )
    return [Documento(**d) for d in dados["documentos"]]


def carregar_grafo(caminho: Path | None = None) -> GraphRAG:
    dados = json.loads(
        (caminho or _data_dir() / "triples_v1.json").read_text(encoding="utf-8")
    )
    grafo = GraphRAG()
    grafo.add_triples(dados["triplas"])
    return grafo


def carregar_casos(caminho: Path | None = None) -> list[Caso]:
    texto = (caminho or _data_dir() / "relational_v1.jsonl").read_text(encoding="utf-8")
    casos = []
    for linha in texto.splitlines():
        if not linha.strip():
            continue
        registro = json.loads(linha)
        casos.append(
            Caso(
                id=registro["id"],
                tipo=registro["tipo"],
                pergunta=registro["pergunta"],
                documentos_relevantes=frozenset(registro["documentos_relevantes"]),
            )
        )
    return casos


def avaliar(retriever: Retriever, casos: list[Caso], k: int = 5) -> Resultado:
    """Média de Recall@K e MRR sobre os casos informados."""
    if not casos:
        return Resultado(retriever.nome, "vazio", 0, 0.0, 0.0)

    recalls, rrs = [], []
    for caso in casos:
        recuperados = retriever.retrieve(caso.pergunta, k)
        relevantes = set(caso.documentos_relevantes)
        recalls.append(recall_at_k(recuperados, relevantes, k))
        rrs.append(reciprocal_rank(recuperados, relevantes))

    tipos = {c.tipo for c in casos}
    return Resultado(
        retriever=retriever.nome,
        tipo=tipos.pop() if len(tipos) == 1 else "todos",
        n_casos=len(casos),
        recall_at_k=sum(recalls) / len(recalls),
        mrr=sum(rrs) / len(rrs),
    )


def executar(k: int = 5, expansion_depth: int = 1) -> list[Resultado]:
    """Roda os três recuperadores sobre o dataset, global e por tipo."""
    corpus = carregar_corpus()
    grafo = carregar_grafo()
    casos = carregar_casos()

    lexical = BM25Retriever(corpus)
    graph = GraphRetriever(grafo, expansion_depth=expansion_depth)
    retrievers: list[Retriever] = [lexical, graph, HybridRetriever(graph, lexical)]

    resultados = []
    grupos: list[tuple[str, list[Caso]]] = [("todos", casos)]
    for tipo in sorted({c.tipo for c in casos}):
        grupos.append((tipo, [c for c in casos if c.tipo == tipo]))

    for rotulo, subconjunto in grupos:
        for retriever in retrievers:
            resultado = avaliar(retriever, subconjunto, k)
            resultados.append(
                Resultado(
                    retriever=resultado.retriever,
                    tipo=rotulo,
                    n_casos=resultado.n_casos,
                    recall_at_k=resultado.recall_at_k,
                    mrr=resultado.mrr,
                )
            )
    return resultados


def formatar(resultados: list[Resultado], k: int) -> str:
    linhas = [
        f"{'grupo':<22} {'recuperador':<12} {'n':>3} "
        f"{'Recall@' + str(k):>10} {'MRR':>8}",
        "-" * 60,
    ]
    grupo_anterior = None
    for r in resultados:
        if grupo_anterior is not None and r.tipo != grupo_anterior:
            linhas.append("")
        linhas.append(
            f"{r.tipo:<22} {r.retriever:<12} {r.n_casos:>3} "
            f"{r.recall_at_k:>10.3f} {r.mrr:>8.3f}"
        )
        grupo_anterior = r.tipo
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mede Recall@K e MRR do grafo, do BM25 e da fusão dos dois."
    )
    parser.add_argument("-k", type=int, default=5, help="corte do ranking (padrão: 5)")
    parser.add_argument(
        "--expansion-depth",
        type=int,
        default=1,
        help="graus de separação percorridos no grafo (padrão: 1)",
    )
    parser.add_argument(
        "--json", action="store_true", help="emite os resultados em JSON"
    )
    args = parser.parse_args(argv)

    resultados = executar(k=args.k, expansion_depth=args.expansion_depth)

    if args.json:
        print(
            json.dumps(
                {
                    "k": args.k,
                    "expansion_depth": args.expansion_depth,
                    "resultados": [vars(r) for r in resultados],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(formatar(resultados, args.k))
    return 0


if __name__ == "__main__":
    sys.exit(main())
