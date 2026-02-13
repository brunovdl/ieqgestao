import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

class Config:
    APP_TITLE = "IEQ - Jd Portugal"
    THEME_COLOR = "#1976D2"
    
    # Credenciais
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
    
    # Ambiente
    ENV = os.getenv("APP_ENV", "local")