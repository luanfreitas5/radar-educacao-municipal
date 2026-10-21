"""Validação de dados: contratos (pandera) e testes de integridade.

Módulos
-------
contracts
    :func:`validate_contract` aplica um schema pandera e converte falhas em
    :class:`exceptions.DataValidationError`.
integrity
    Cobertura, duplicatas, nulos e chaves órfãs da base municipal.
"""
