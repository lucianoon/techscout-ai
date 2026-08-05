"""
Módulo de extração de triplas (sujeito-relação-objeto) usando LLM
"""
import json
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from techscout.logger import logger
from techscout.settings import settings


class TripleExtractor:
    """Extrai triplas de conhecimento de textos usando LLM"""
    
    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        llm: BaseChatModel | None = None,
    ):
        """
        Inicializa o extrator de triplas.

        O cliente LLM é construído sob demanda (ver ``self.llm``), de modo que
        instanciar esta classe não exija ``OPENAI_API_KEY``. Isso mantém o
        parsing e a validação de triplas testáveis offline.

        Args:
            model: Modelo OpenAI a usar
            temperature: Temperatura do modelo
            llm: Cliente já construído; injetado em testes para evitar rede
        """
        self._model = model or settings.OPENAI_MODEL
        self._temperature = (
            temperature if temperature is not None else settings.OPENAI_TEMPERATURE
        )
        self._llm = llm
        self.logger = logger

    @property
    def llm(self) -> BaseChatModel:
        """Cliente LLM, construído na primeira utilização."""
        if self._llm is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY não configurada. "
                    "Defina a variável de ambiente ou crie um arquivo .env"
                )
            self._llm = ChatOpenAI(
                model=self._model,
                temperature=self._temperature,
                api_key=SecretStr(settings.OPENAI_API_KEY),
                timeout=settings.OPENAI_TIMEOUT_SECONDS,
                max_retries=settings.OPENAI_MAX_RETRIES,
            )
        return self._llm


    def extract(self, text: str) -> list[dict[str, str]]:
        """
        Extrai triplas de um texto
        
        Args:
            text: Texto para análise
            
        Returns:
            Lista de dicionários com chaves 'sujeito', 'relacao', 'objeto'
        """
        if not text or not text.strip():
            self.logger.warning("Texto vazio fornecido para extração")
            return []
        
        prompt = self._build_prompt(text)
        
        try:
            response = self.llm.invoke(prompt)
            # `content` pode vir como lista de blocos em modelos multimodais;
            # o parser trabalha sobre texto.
            conteudo = response.content
            if not isinstance(conteudo, str):
                conteudo = "".join(str(bloco) for bloco in conteudo)
            triples = self._parse_response(conteudo)
            self.logger.debug(f"Extraídas {len(triples)} triplas do texto")
            return triples
        except Exception as e:
            self.logger.error(f"Erro ao extrair triplas: {e}")
            return []
    
    def _build_prompt(self, text: str) -> str:
        """Constrói o prompt para o LLM"""
        return f"""
Analise o texto e extraia relações estruturadas no formato JSON estrito.
Extraia apenas relações factuais e explícitas.

Formato esperado:
[
  {{"sujeito": "Entidade1", "relacao": "verbo", "objeto": "Entidade2"}},
  {{"sujeito": "Entidade3", "relacao": "verbo", "objeto": "Entidade4"}}
]

Tipos de relação aceitos:
- fundou, trabalhou_em, investiu_em, consultor_de
- liderou, adquiriu, vendeu, parceiro_de
- especialista_em, ex_funcionario_de

Regras:
1. Use apenas relações claramente mencionadas no texto
2. Mantenha nomes de entidades exatamente como aparecem
3. Use relações curtas e descritivas
4. Retorne array vazio [] se nenhuma relação for encontrada

Texto:
{text}

JSON:
"""
    
    def _parse_response(self, content: str) -> list[dict[str, str]]:
        """
        Faz parse da resposta do LLM e valida triplas
        
        Args:
            content: Conteúdo da resposta do LLM
            
        Returns:
            Lista de triplas validadas
        """
        try:
            # Limpa markdown code blocks
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
            
            # Tenta encontrar JSON no conteúdo
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            triples = json.loads(content)
            
            # Validação
            if not isinstance(triples, list):
                self.logger.warning(f"Resposta não é uma lista: {type(triples)}")
                return []
            
            validated = []
            for t in triples:
                if self._validate_triple(t):
                    validated.append({
                        'sujeito': t['sujeito'].strip(),
                        'relacao': t['relacao'].strip(),
                        'objeto': t['objeto'].strip()
                    })
                else:
                    self.logger.debug(f"Tripla inválida ignorada: {t}")
            
            return validated
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Erro ao fazer parse do JSON: {e}")
            self.logger.debug(f"Conteúdo recebido: {content[:200]}...")
            return []
        except Exception as e:
            self.logger.error(f"Erro inesperado ao processar resposta: {e}")
            return []
    
    def _validate_triple(self, triple: dict) -> bool:
        """
        Valida se uma tripla tem estrutura correta
        
        Args:
            triple: Dicionário com a tripla
            
        Returns:
            True se válida
        """
        if not isinstance(triple, dict):
            return False
        
        required_keys = ['sujeito', 'relacao', 'objeto']
        if not all(k in triple for k in required_keys):
            return False
        
        # Valida que valores não estão vazios
        return all(
            isinstance(triple[k], str) and triple[k].strip()
            for k in required_keys
        )

