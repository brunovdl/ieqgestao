"""
Módulo de Views
"""
from .login_view import login_view
from .dashboard_view import dashboard_view
from .visitors_view import visitors_view
from .users_view import users_view
from .collaborators_view import collaborators_view
from .components import rounded_logo, header_logo

__all__ = [
    'login_view', 
    'dashboard_view', 
    'visitors_view', 
    'users_view',
    'collaborators_view',
    'rounded_logo', 
    'header_logo'
]