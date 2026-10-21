"""Exceções customizadas do projeto.

Todas herdam de :class:`RadarError`, permitindo capturar qualquer falha
esperada do pipeline sem mascarar erros de programação.

Classes
-------
RadarError
    Base de todas as exceções do projeto.
ConfigurationError
    Configuração YAML ausente ou inválida.
IngestionError
    Falha ao baixar ou registrar uma fonte de dados.
DataValidationError
    Violação de contrato de dados (schema) ou dado de entrada inesperado.
IntegrityError
    Falha nos testes de integridade da base municipal.
"""


class RadarError(Exception):
    """Base de todas as exceções do projeto."""


class ConfigurationError(RadarError):
    """Configuração ausente ou inválida."""


class IngestionError(RadarError):
    """Falha na ingestão de uma fonte de dados."""


class DataValidationError(RadarError):
    """Dado de entrada inconsistente com o contrato esperado."""


class IntegrityError(RadarError):
    """Teste de integridade da base municipal reprovado."""
