# Política de segurança

## Versões suportadas

O branch `main` recebe correções de segurança. Releases e commits antigos não
recebem backports garantidos.

## Reportar uma vulnerabilidade

Não abra uma issue pública. Use **Security → Report a vulnerability** neste
repositório para enviar o relato de forma privada.

Inclua o commit afetado, impacto, passos mínimos para reprodução e, se
possível, uma mitigação. O objetivo é confirmar o recebimento em até 3 dias
úteis e publicar uma avaliação inicial em até 7 dias úteis.

## Escopo sensível

Este projeto ingere texto de fontes externas (feeds RSS, APIs de notícias) e o
envia a um LLM para extração de relações. Isso torna especialmente relevantes
os relatos sobre:

- **Prompt injection via documento ingerido** — um artigo hostil que faça o
  extrator emitir triplas forjadas, envenenando o grafo de conhecimento.
- **Envenenamento do grafo** — inserção de relações falsas que se propaguem
  para as respostas por meio da expansão de vizinhança.
- **Desserialização insegura** — o carregamento de grafos em formato pickle
  legado executa código arbitrário do arquivo. Por isso é desabilitado por
  padrão e só ocorre com `ALLOW_PICKLE_GRAPH_LOAD=1`. Trate qualquer caminho
  que contorne esse opt-in como vulnerabilidade.
- **Exposição de chaves** — vazamento de `OPENAI_API_KEY` ou `NEWSAPI_KEY` em
  logs, mensagens de erro, estado do Streamlit ou artefatos persistidos.
- **Indisponibilidade por entrada adversarial** — documentos que provoquem
  consumo desproporcional de tokens ou expansão explosiva do grafo.

Não inclua documentos privados, dados pessoais, chaves ou segredos reais no
relato.

## Fora de escopo

- Custo de chamadas à API decorrente de uso legítimo.
- Qualidade ou correção factual das triplas extraídas pelo LLM: é limitação
  conhecida do método, documentada no README, não uma falha de segurança.
