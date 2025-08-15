"""
RutIA Core - Módulos espaciales principales
"""

__version__ = "1.0.0"
__author__ = "GeoDojo"

# Funciones básicas para evitar errores de import
def log_info(message: str):
    """Logger básico"""
    print(f"🗺️ RutIA: {message}")

def get_version():
    """Obtener versión"""
    return __version__