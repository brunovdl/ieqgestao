"""
Módulo de utilitários
"""
from .config import *
from .viacep_service import ViaCEPService

__all__ = [
    'WINDOW_WIDTH',
    'WINDOW_HEIGHT',
    'APP_TITLE',
    'DB_NAME',
    'ROUTE_LOGIN',
    'ROUTE_DASHBOARD',
    'DEFAULT_USERNAME',
    'DEFAULT_PASSWORD',
    'ViaCEPService'
]
