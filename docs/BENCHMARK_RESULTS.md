# Baseline de recuperação — resultados medidos

## O que está sendo medido

A hipótese do projeto é que **um grafo de conhecimento recupera melhor que
busca por passagem em perguntas relacionais** — aquelas cuja resposta não está
em nenhum documento isolado.

Para testá-la, os dois lados devolvem a mesma coisa: uma lista ordenada de ids
de documento, avaliada pelo mesmo rótulo.

| Recuperador | Como chega ao ranking |
|---|---|
| `bm25` | BM25 clássico sobre título + texto |
| `grafo` | Proveniência das arestas: cada fato aponta para os documentos que o afirmaram |
| `hibrido` | Fusão dos dois por reciprocal rank fusion (k=60) |

**O grafo é fixo e curado à mão** (`data/eval/triples_v1.json`). Isso isola a
qualidade da *recuperação* da qualidade da *extração* por LLM, que varia entre
modelos e execuções. Um número que misturasse as duas não diria qual das
partes é boa.

## Como reproduzir

```bash
pip install -e ".[dev]"
python -m techscout.evaluation -k 5
```

Sem chave de API e sem rede: todos os três recuperadores são determinísticos.

## Procedência

| Item | Valor |
|---|---|
| Data da medição | 5 de agosto de 2026 |
| Commit base | `9b772ac` |
| Python | 3.11 |
| Corpus | `corpus_v1` — 15 documentos |
| Grafo | `triples_v1` — 13 nós, 15 arestas, densidade 0,192 |
| Dataset | `relational_v1` — 15 perguntas rotuladas |
| Comando | `python -m techscout.evaluation -k 5` |

## Resultados (k = 5)

| Grupo | n | Recuperador | Recall@5 | MRR |
|---|---:|---|---:|---:|
| **todos** | 15 | bm25 | 0,789 | **0,844** |
| | | grafo | 0,822 | 0,722 |
| | | híbrido | **0,844** | **0,856** |
| **relacional** | 10 | bm25 | 0,750 | 0,767 |
| | | grafo | **0,800** | 0,708 |
| | | híbrido | **0,800** | **0,850** |
| **relacional profunda** | 2 | bm25 | 0,667 | **1,000** |
| | | grafo | 0,667 | 0,625 |
| | | híbrido | **0,833** | 0,667 |
| **factual** (controle) | 3 | bm25 | **1,000** | **1,000** |
| | | grafo | **1,000** | 0,833 |
| | | híbrido | **1,000** | **1,000** |

## Leitura honesta

**1. A hipótese original só se confirma em parte.** Em k=5, o grafo recupera
mais documentos relevantes que o BM25 nas perguntas relacionais (0,800 contra
0,750). Mas ele *ordena pior*: MRR de 0,708 contra 0,767. Ele encontra o que
importa e falha em colocá-lo em primeiro.

**2. A vantagem de recall do grafo não é estável.** Variando o corte:

| k | bm25 | grafo | híbrido |
|---:|---:|---:|---:|
| 2 | 0,611 | 0,678 | **0,711** |
| 3 | **0,756** | 0,711 | **0,767** |
| 5 | 0,789 | 0,822 | **0,844** |

O grafo ganha em k=2 e k=5 e **perde em k=3**. Com 15 perguntas, uma inversão
dessas é ruído, não sinal. **Não é possível afirmar, com este dataset, que o
grafo supera o BM25 em recall.**

**3. O achado que se sustenta é a fusão.** O híbrido é igual ou melhor que
ambos em *todos* os cortes de k e em *ambas* as métricas. Esse é o único
resultado que não inverte, e é o que justifica manter as duas estruturas em
vez de escolher uma.

**4. O controle se comportou como previsto.** Nas perguntas factuais, o BM25
acerta tudo (Recall e MRR = 1,000) e o grafo fica atrás no MRR. Era a
expectativa — a resposta está literalmente em um trecho — e serve como
sanidade do arranjo: se o grafo tivesse vencido aqui, o dataset estaria
enviesado.

## Limitações

Estas condicionam qualquer uso dos números acima:

1. **n = 15 perguntas, 15 documentos.** Pequeno demais para significância.
   Uma pergunta a mais ou a menos move o Recall em ~0,07. Trate as diferenças
   abaixo de ~0,10 como indistinguíveis.
2. **Corpus sintético.** Escrito para que perguntas relacionais exijam dois ou
   mais documentos. Isso torna o teste limpo e o afasta de texto real, onde
   redundância e ruído mudam o equilíbrio.
3. **O grafo é curado, não extraído.** Mede-se recuperação sobre um grafo
   correto. Num grafo extraído por LLM, erros de extração se somariam — e não
   estão contabilizados aqui.
4. **Rótulos de documento, não de resposta.** Mede-se se os textos certos
   foram recuperados, não se a resposta final estava correta. Fidelidade da
   síntese não é avaliada.
5. **Uma única execução.** Determinística, então repetir dá o mesmo resultado
   — o que também significa que não há variância medida para comparar.

## O que tornaria isso conclusivo

Em ordem de retorno:

1. Ampliar para ~100 perguntas sobre um corpus real de notícias, o suficiente
   para intervalos de confiança.
2. Avaliar sobre grafo extraído por LLM, medindo separadamente o erro de
   extração para saber quanto ele custa.
3. Corrigir o ranqueamento do grafo, que hoje é a fraqueza clara: o recall
   mostra que a informação é alcançada, o MRR mostra que ela não sobe ao topo.
