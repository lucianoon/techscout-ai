"""Avaliação da extração de triplas por LLM contra o grafo curado.

`techscout.evaluation` mede recuperação sobre um grafo *correto*, isolando-a
da extração. Este módulo fecha a outra metade: **quão correto é o grafo que o
LLM produz?** — e, na sequência, **quanto o erro de extração custa na
recuperação**.

A comparação é feita em dois níveis, porque errar o rótulo da relação e não
enxergar a conexão são falhas de gravidade muito diferente:

- **estrito**: (sujeito, relação, objeto) precisa bater
- **por par**: basta ligar as duas entidades, qualquer que seja o rótulo

A distância entre os dois números diz quanto do erro é de vocabulário e
quanto é de percepção.

A extração é cacheada em `data/eval/extracted_<modelo>.json`. Sem isso, cada
execução gastaria API e devolveria números ligeiramente diferentes — o
benchmark deixaria de ser reproduzível.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from techscout.evaluation import (
    BM25Retriever,
    Caso,
    GraphRetriever,
    HybridRetriever,
    _data_dir,
    avaliar,
    carregar_casos,
    carregar_corpus,
    carregar_grafo,
    normalizar,
)
from techscout.graph_rag import GraphRAG
from techscout.logger import logger
from techscout.triple_extractor import VOCABULARIO_RELACOES, TripleExtractor

# Artigos e preposições que o LLM às vezes cola no nome da entidade
# ("a Nebula AI", "da OldTech"). Não são parte do nome.
_PREFIXOS = ("a ", "o ", "as ", "os ", "da ", "do ", "de ", "na ", "no ")


def normalizar_entidade(nome: str) -> str:
    """Forma canônica de uma entidade, para comparar extração com gabarito."""
    # Colapsa espaços antes de comparar prefixos: "a  da  Nebula" precisa
    # perder os dois, e um espaço duplo esconderia o segundo.
    texto = " ".join(normalizar(nome).strip(" .,;:\"'").split())
    mudou = True
    while mudou:
        mudou = False
        for prefixo in _PREFIXOS:
            if texto.startswith(prefixo):
                texto = texto[len(prefixo) :].lstrip()
                mudou = True
    return texto


def normalizar_relacao(relacao: str) -> str:
    return "_".join(normalizar(relacao).split())


Tripla = tuple[str, str, str]
Par = tuple[str, str]

# O que se compara com o gabarito: tripla completa ou par de entidades.
T = TypeVar("T")


def canonizar(tripla: dict[str, str]) -> Tripla:
    return (
        normalizar_entidade(tripla.get("sujeito", "")),
        normalizar_relacao(tripla.get("relacao", "")),
        normalizar_entidade(tripla.get("objeto", "")),
    )


def como_par(tripla: Tripla) -> Par:
    """Par de entidades sem direção — a aresta é não-direcionada no grafo."""
    sujeito, _, objeto = tripla
    return (min(sujeito, objeto), max(sujeito, objeto))


@dataclass(frozen=True)
class Metricas:
    nivel: str
    precisao: float
    revocacao: float
    f1: float
    corretos: int
    extraidos: int
    esperados: int


def _f1(precisao: float, revocacao: float) -> float:
    if precisao + revocacao == 0:
        return 0.0
    return 2 * precisao * revocacao / (precisao + revocacao)


def comparar(
    extraidas: set[T], esperadas: set[T], nivel: str
) -> Metricas:
    """Precisão, revocação e F1 de um conjunto contra o gabarito.

    Genérica no item comparado: serve tanto para triplas completas quanto
    para pares de entidades.
    """
    corretos = len(extraidas & esperadas)
    precisao = corretos / len(extraidas) if extraidas else 0.0
    revocacao = corretos / len(esperadas) if esperadas else 0.0
    return Metricas(
        nivel=nivel,
        precisao=precisao,
        revocacao=revocacao,
        f1=_f1(precisao, revocacao),
        corretos=corretos,
        extraidos=len(extraidas),
        esperados=len(esperadas),
    )


# --------------------------------------------------------------------------
# Extração com cache
# --------------------------------------------------------------------------


def caminho_cache(modelo: str) -> Path:
    return _data_dir() / f"extracted_{modelo.replace('/', '_')}.json"


def extrair_corpus(modelo: str, atualizar: bool = False) -> dict[str, list[dict]]:
    """Triplas extraídas por documento, do cache ou da API.

    Cada documento é extraído isoladamente, como acontece na ingestão real:
    é isso que torna o resultado comparável ao uso em produção.
    """
    cache = caminho_cache(modelo)
    if cache.exists() and not atualizar:
        return json.loads(cache.read_text(encoding="utf-8"))["por_documento"]

    extractor = TripleExtractor(model=modelo)
    por_documento: dict[str, list[dict]] = {}
    for doc in carregar_corpus():
        logger.info(f"Extraindo {doc.id}...")
        por_documento[doc.id] = extractor.extract(doc.conteudo)

    cache.write_text(
        json.dumps(
            {
                "modelo": modelo,
                "descricao": (
                    "Saída bruta da extração, cacheada para que o benchmark "
                    "seja reproduzível sem consumir API. Regerar com "
                    "--refresh."
                ),
                "por_documento": por_documento,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return por_documento


def gabarito_por_documento() -> dict[str, list[Tripla]]:
    dados = json.loads(
        (_data_dir() / "triples_v1.json").read_text(encoding="utf-8")
    )
    gabarito: dict[str, list[Tripla]] = {}
    for tripla in dados["triplas"]:
        gabarito.setdefault(tripla["fonte"], []).append(canonizar(tripla))
    return gabarito


# --------------------------------------------------------------------------
# Avaliação
# --------------------------------------------------------------------------


def avaliar_extracao(modelo: str, atualizar: bool = False) -> dict:
    extraidas_doc = extrair_corpus(modelo, atualizar=atualizar)
    gabarito_doc = gabarito_por_documento()

    todas_extraidas: set[Tripla] = set()
    todas_esperadas: set[Tripla] = set()
    for doc_id in {d.id for d in carregar_corpus()}:
        todas_extraidas.update(canonizar(t) for t in extraidas_doc.get(doc_id, []))
        todas_esperadas.update(gabarito_doc.get(doc_id, []))

    estrito = comparar(todas_extraidas, todas_esperadas, "estrito")
    por_par = comparar(
        {como_par(t) for t in todas_extraidas},
        {como_par(t) for t in todas_esperadas},
        "por par",
    )

    faltantes = sorted(todas_esperadas - todas_extraidas)
    espurias = sorted(todas_extraidas - todas_esperadas)

    return {
        "modelo": modelo,
        "metricas": [estrito, por_par],
        "conformidade": conformidade(todas_extraidas),
        "faltantes": faltantes,
        "espurias": espurias,
        "extraidas_por_documento": extraidas_doc,
    }


# Objeto com mais que isto raramente é nome de entidade; costuma ser um
# sintagma ("expandir a equipe de pesquisa") que o modelo colou no lugar.
_MAX_PALAVRAS_ENTIDADE = 3


def conformidade(extraidas: set[Tripla]) -> dict[str, float | int]:
    """Quanto da saída respeita o contrato que o prompt anuncia.

    Separa *não entender o texto* de *não seguir a instrução* — falhas com
    causas e correções completamente diferentes.
    """
    if not extraidas:
        return {
            "n": 0,
            "relacao_no_vocabulario": 0.0,
            "objeto_e_entidade": 0.0,
            "relacoes_inventadas": 0,
        }

    no_vocabulario = [t for t in extraidas if t[1] in VOCABULARIO_RELACOES]
    objeto_curto = [
        t for t in extraidas if len(t[2].split()) <= _MAX_PALAVRAS_ENTIDADE
    ]
    inventadas = {t[1] for t in extraidas} - VOCABULARIO_RELACOES

    return {
        "n": len(extraidas),
        "relacao_no_vocabulario": len(no_vocabulario) / len(extraidas),
        "objeto_e_entidade": len(objeto_curto) / len(extraidas),
        "relacoes_inventadas": len(inventadas),
    }


def grafo_extraido(extraidas_doc: dict[str, list[dict]]) -> GraphRAG:
    """Monta o grafo como a ingestão faria, preservando a proveniência."""
    grafo = GraphRAG()
    for doc_id, triplas in extraidas_doc.items():
        for t in triplas:
            grafo.add_triple(
                t.get("sujeito", ""),
                t.get("relacao", ""),
                t.get("objeto", ""),
                fonte=doc_id,
            )
    return grafo


def custo_na_recuperacao(
    extraidas_doc: dict[str, list[dict]], k: int = 5
) -> list[dict]:
    """Quanto o erro de extração custa em Recall@K e MRR.

    Roda o mesmo benchmark de recuperação duas vezes — sobre o grafo curado e
    sobre o extraído — e devolve a diferença. É a resposta ponta a ponta que
    nenhum dos dois módulos dá sozinho.
    """
    corpus = carregar_corpus()
    casos: list[Caso] = [c for c in carregar_casos() if c.tipo.startswith("relacional")]
    lexical = BM25Retriever(corpus)

    linhas = []
    for rotulo, grafo in (
        ("curado", carregar_grafo()),
        ("extraido", grafo_extraido(extraidas_doc)),
    ):
        graph_retriever = GraphRetriever(grafo)
        for retriever in (graph_retriever, HybridRetriever(graph_retriever, lexical)):
            resultado = avaliar(retriever, casos, k)
            linhas.append(
                {
                    "grafo": rotulo,
                    "recuperador": retriever.nome,
                    "recall": resultado.recall_at_k,
                    "mrr": resultado.mrr,
                }
            )
    return linhas


def formatar(relatorio: dict, custos: list[dict], k: int) -> str:
    linhas = [
        f"Extração por LLM vs grafo curado — modelo: {relatorio['modelo']}",
        "",
        f"{'nível':<10} {'precisão':>9} {'revocação':>10} {'F1':>7} "
        f"{'ok':>4} {'extr':>5} {'gab':>4}",
        "-" * 56,
    ]
    for m in relatorio["metricas"]:
        linhas.append(
            f"{m.nivel:<10} {m.precisao:>9.3f} {m.revocacao:>10.3f} {m.f1:>7.3f} "
            f"{m.corretos:>4} {m.extraidos:>5} {m.esperados:>4}"
        )

    c = relatorio["conformidade"]
    linhas += [
        "",
        "Aderência ao contrato do prompt",
        f"  relação dentro do vocabulário fechado : {c['relacao_no_vocabulario']:.1%}",
        f"  objeto parece entidade (<= 3 palavras): {c['objeto_e_entidade']:.1%}",
        f"  rótulos de relação inventados         : {c['relacoes_inventadas']}",
    ]

    linhas += ["", f"Custo na recuperação (perguntas relacionais, k={k})", ""]
    linhas.append(f"{'grafo':<10} {'recuperador':<12} {'Recall':>8} {'MRR':>8}")
    linhas.append("-" * 42)
    for linha in custos:
        linhas.append(
            f"{linha['grafo']:<10} {linha['recuperador']:<12} "
            f"{linha['recall']:>8.3f} {linha['mrr']:>8.3f}"
        )

    if relatorio["faltantes"]:
        linhas += ["", f"Não extraídas ({len(relatorio['faltantes'])}):"]
        linhas += [f"  {s} --[{r}]--> {o}" for s, r, o in relatorio["faltantes"]]
    if relatorio["espurias"]:
        linhas += ["", f"Extraídas fora do gabarito ({len(relatorio['espurias'])}):"]
        linhas += [f"  {s} --[{r}]--> {o}" for s, r, o in relatorio["espurias"]]

    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mede a extração de triplas por LLM contra o grafo curado."
    )
    parser.add_argument("--model", default="gpt-3.5-turbo", help="modelo a avaliar")
    parser.add_argument("-k", type=int, default=5, help="corte do ranking")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="reextrai chamando a API em vez de usar o cache (consome créditos)",
    )
    parser.add_argument("--json", action="store_true", help="emite JSON")
    args = parser.parse_args(argv)

    relatorio = avaliar_extracao(args.model, atualizar=args.refresh)
    custos = custo_na_recuperacao(relatorio["extraidas_por_documento"], k=args.k)

    if args.json:
        print(
            json.dumps(
                {
                    "modelo": relatorio["modelo"],
                    "metricas": [vars(m) for m in relatorio["metricas"]],
                    "custo_na_recuperacao": custos,
                    "faltantes": relatorio["faltantes"],
                    "espurias": relatorio["espurias"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(formatar(relatorio, custos, args.k))
    return 0


if __name__ == "__main__":
    sys.exit(main())
