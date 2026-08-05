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

---

# Parte 2 — Extração por LLM contra o grafo curado

A Parte 1 mede recuperação sobre um grafo *correto*. Esta mede quão correto é
o grafo que o LLM produz, e quanto o erro custa lá na ponta.

```bash
make eval-extraction            # usa o cache versionado, não chama API
make eval-extraction-refresh    # reextrai (consome créditos)
```

A saída bruta fica em `data/eval/extracted_gpt-3.5-turbo.json`, versionada
para que o número seja reproduzível sem gastar API — e para que a CI possa
verificá-lo a cada push.

## O que a primeira medição revelou

Modelo `gpt-3.5-turbo`, 15 documentos, gabarito de 15 triplas:

| Nível | Precisão | Revocação | F1 |
|---|---:|---:|---:|
| Estrito (sujeito, relação, objeto) | 0,345 | 0,667 | 0,455 |
| Por par (ignora o rótulo) | 0,444 | 0,800 | 0,571 |

O modelo extraiu **29 triplas onde o gabarito tem 15**. E o diagnóstico não
era compreensão, era desobediência:

| Aderência ao contrato do prompt | |
|---|---:|
| Relação dentro do vocabulário fechado | **41,4%** |
| Objeto parece entidade (≤ 3 palavras) | 69,0% |
| Rótulos de relação inventados | **15** |

O prompt lista 10 relações permitidas. O modelo inventou outras 15
(`assumiu_como`, `promovida_a`, `a_frente_da`…) e usou sintagmas inteiros como
objeto ("expandir a equipe de pesquisa").

**Causa-raiz:** a regra 3 do prompt dizia *"use relações curtas e
descritivas"* — instrução que contradiz frontalmente um vocabulário fechado.
O modelo obedeceu à regra errada.

## Depois de corrigir o prompt

Regras reescritas: descartar o que não couber no vocabulário em vez de
adaptar, e exigir nome próprio como sujeito e objeto.

| Métrica | Prompt v1 | Prompt v2 | |
|---|---:|---:|---|
| F1 estrito | 0,455 | **0,579** | +27% |
| F1 por par | 0,571 | **0,857** | +50% |
| **Revocação por par** | 0,800 | **1,000** | +25% |
| Aderência ao vocabulário | 41,4% | **87,0%** | +110% |
| Objeto é entidade | 69,0% | **95,7%** | +39% |
| Rótulos inventados | 15 | **3** | −80% |

**Revocação por par de 1,000**: o modelo passou a encontrar *todas* as
conexões do gabarito. Todo o erro residual é de rótulo ou de direção — e como
o grafo é não-direcionado, direção não afeta a recuperação.

Os erros que sobraram são quase todos inversões:

| Gabarito | Extraído |
|---|---|
| `Pedro Santos --[consultor_de]--> Nebula AI` | `Nebula AI --[consultor_de]--> Pedro Santos` |
| `Marina Klein --[trabalhou_em]--> Horizon Ventures` | `Horizon Ventures --[liderou]--> Marina Klein` |
| `Horizon Ventures --[investiu_em]--> Nebula AI` | `Nebula AI --[liderada_por]--> Horizon Ventures` |

## Quanto o erro de extração custa na recuperação

Mesmo benchmark da Parte 1, rodado duas vezes — sobre o grafo curado e sobre
o extraído (perguntas relacionais + profundas, n=12, k=5):

| Grafo | Recuperador | Recall@5 | MRR |
|---|---|---:|---:|
| curado | grafo | 0,778 | 0,694 |
| extraído (v1) | grafo | 0,722 | 0,729 |
| extraído (v2) | grafo | **0,778** | **0,799** |
| curado | híbrido | 0,806 | 0,819 |
| extraído (v1) | híbrido | 0,806 | 0,819 |
| extraído (v2) | híbrido | **0,806** | **0,875** |

Três leituras, em ordem de importância:

**1. O custo da extração é surpreendentemente baixo.** Mesmo com o prompt v1
— F1 estrito de 0,455 — a recuperação caiu só 0,056 em Recall e *subiu* em
MRR. Recuperação depende da **proveniência**, não do rótulo: uma tripla com
relação errada ainda aponta para o documento certo.

**2. O híbrido absorve o erro por completo.** Recall idêntico (0,806) nas três
condições. É a terceira vez neste benchmark que a fusão se mostra o
componente robusto.

**3. O grafo extraído supera o curado em MRR** (0,799 vs 0,694). Não é mágica:
o modelo extrai fatos verdadeiros que meu gabarito omitiu — `Ana Souza
--[trabalhou_em]--> Google`, `Pedro Santos --[trabalhou_em]--> OldTech` — e
essas arestas a mais ajudam a ranquear. O gabarito foi curado a partir das
perguntas, não do texto completo.

## Limitações desta parte

Somam-se às da Parte 1:

1. **O prompt foi ajustado depois de ver os erros nestes mesmos 15
   documentos.** É *overfitting* de manual: os números do v2 são otimistas e
   não devem ser lidos como desempenho em texto novo. O A/B é honesto quanto
   à direção da melhora, não quanto à magnitude.
2. **A precisão está subestimada.** O gabarito cobre apenas os fatos
   necessários para responder às 15 perguntas, então extrações corretas mas
   fora do escopo contam como falso positivo. A revocação não sofre desse
   problema — e é por isso que a revocação por par é a métrica mais confiável
   aqui.
3. **Um modelo, uma execução.** Só `gpt-3.5-turbo`, temperatura 0. Sem
   variância medida e sem comparação entre modelos.
4. **A direção da relação não é avaliada de fato.** O grafo é não-direcionado,
   então inversões passam sem punição na recuperação — mas seriam erros graves
   num grafo direcionado.

## O que tornaria tudo isso conclusivo

Em ordem de retorno:

1. **Corpus de validação separado**, não usado para ajustar prompt nem
   ranqueador. Sem isso, os ganhos do v2 permanecem não verificados.
2. Ampliar para ~100 perguntas sobre notícias reais, o suficiente para
   intervalos de confiança.
3. Comparar modelos (gpt-4o, Claude) sobre o mesmo gabarito, já que a
   infraestrutura de medição agora existe.
4. Migrar para `MultiDiGraph` e passar a punir inversão de direção.
5. Corrigir o ranqueamento do grafo: o recall mostra que a informação é
   alcançada, o MRR mostra que ela não sobe ao topo.
