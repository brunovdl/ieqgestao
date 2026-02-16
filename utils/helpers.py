import flet as ft
import time
import threading
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Optional, Dict

# --- UI FEEDBACK ---

def show_top_message(page, message, color, icon):
    snack_content = ft.Container(
        content=ft.Row([
            ft.Icon(icon, color="white"),
            ft.Text(message, color="white", weight="bold", size=14, expand=True)
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=color, padding=15, border_radius=10,
        shadow=ft.BoxShadow(blur_radius=15, color="black26"),
        left=10, right=10, top=-100, opacity=0,
        animate_position=ft.animation.Animation(500, ft.AnimationCurve.ELASTIC_OUT),
        animate_opacity=ft.animation.Animation(300, ft.AnimationCurve.EASE_IN),
        on_click=lambda e: close_snack(page, e.control)
    )
    page.overlay.append(snack_content)
    page.update()
    snack_content.top = 10; snack_content.opacity = 1; page.update()
    
    def auto_close():
        time.sleep(4)
        try: close_snack(page, snack_content)
        except: pass
    threading.Thread(target=auto_close, daemon=True).start()

def close_snack(page, container):
    try:
        container.top = -100; container.opacity = 0; page.update()
        time.sleep(0.5)
        if container in page.overlay: page.overlay.remove(container); page.update()
    except: pass

def show_success(page, message): show_top_message(page, message, "green", ft.Icons.CHECK_CIRCLE)
def show_error(page, message): show_top_message(page, message, "red", ft.Icons.ERROR)
def show_warning(page, message): show_top_message(page, message, "orange", ft.Icons.WARNING)

def show_loading(page, message="Processando..."):
    loading = ft.Container(
        content=ft.Column([ft.ProgressRing(), ft.Text(message, color="white")], horizontal_alignment="center", alignment="center"), 
        bgcolor="black54", expand=True, alignment=ft.alignment.center
    )
    page.overlay.append(loading); page.update(); return loading

def hide_loading(page, loading):
    if loading in page.overlay: page.overlay.remove(loading); page.update()

# --- INTEGRAÇÕES ---

def get_youtube_thumbnail(channel_id):
    if not channel_id: return None
    clean_id = channel_id.strip().replace('"', '').replace("'", "")
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={clean_id}"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            ns = {'yt': 'http://www.youtube.com/xml/schemas/2015', 'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', ns)
            if entry is not None:
                vid = entry.find('yt:videoId', ns).text
                return f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"
    except: pass
    return None

def get_latest_video_id(channel_id):
    if not channel_id: return None
    clean_id = channel_id.strip().replace('"', '').replace("'", "")
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={clean_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # Namespaces do XML do YouTube
            ns = {'yt': 'http://www.youtube.com/xml/schemas/2015', 'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', ns)
            if entry is not None:
                video_id = entry.find('yt:videoId', ns).text
                return video_id
    except Exception as e:
        print(f"Erro ao buscar vídeo do YouTube: {e}")
    return None

def open_whatsapp(phone, name, custom_msg=None):
    if not phone: return ""
    clean = ''.join(filter(str.isdigit, phone))
    if len(clean) <= 11 and not clean.startswith("55"): clean = "55" + clean
    
    # Se custom_msg é None, usa mensagem padrão. Se é string vazia, abre sem mensagem.
    if custom_msg is None:
        msg = urllib.parse.quote_plus(f"Olá {name}, paz! Sou da IEQ.")
        return f"https://api.whatsapp.com/send?phone={clean}&text={msg}"
    elif custom_msg == "":
        return f"https://api.whatsapp.com/send?phone={clean}"
    else:
        msg = urllib.parse.quote_plus(custom_msg)
        return f"https://api.whatsapp.com/send?phone={clean}&text={msg}"

# --- UI COMPONENTS ---

def get_logo(size=80, theme_color="#1976D2"):
    return ft.Container(
        content=ft.Image(src="logoieq.png", fit="cover", width=size, height=size, error_content=ft.Icon(ft.Icons.CHURCH, size=size*0.6, color="white")),
        width=size, height=size, border_radius=size//2, bgcolor=theme_color,
        shadow=ft.BoxShadow(blur_radius=10, color="black26"), clip_behavior=ft.ClipBehavior.HARD_EDGE
    )

# --- CEP HELPER ---

class ViaCEPService:
    BASE_URL = "https://viacep.com.br/ws"
    @staticmethod
    def clean_cep(cep: str) -> str: return ''.join(filter(str.isdigit, cep)) if cep else ""
    @staticmethod
    def format_cep(cep: str) -> str:
        clean = ViaCEPService.clean_cep(cep)
        return f"{clean[:5]}-{clean[5:]}" if len(clean) == 8 else cep
    @staticmethod
    def search_by_cep(cep: str):
        try:
            clean = ViaCEPService.clean_cep(cep)
            if len(clean) != 8: return None
            response = requests.get(f"{ViaCEPService.BASE_URL}/{clean}/json/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data if 'erro' not in data else None
            return None
        except: return None

# --- FORMULÁRIO DE ENDEREÇO (REINSERIDO) ---

def address_form_fields(page):
    cep = ft.TextField(label="CEP", keyboard_type=ft.KeyboardType.NUMBER, max_length=9, col={"sm": 6, "md": 3})
    status = ft.Text("", size=12, col={"sm": 6, "md": 9})
    logra = ft.TextField(label="Logradouro", col={"sm": 12, "md": 8})
    num = ft.TextField(label="Nº", col={"sm": 12, "md": 4})
    bairro = ft.TextField(label="Bairro", col={"sm": 12, "md": 4})
    cid = ft.TextField(label="Cidade", col={"sm": 8, "md": 6})
    uf = ft.TextField(label="UF", col={"sm": 4, "md": 2})

    def on_cep_change(e):
        if len(ViaCEPService.clean_cep(cep.value)) < 8: return
        status.value = "Buscando..."; status.color = "blue"; page.update()
        data = ViaCEPService.search_by_cep(cep.value)
        if data:
            logra.value, bairro.value, cid.value, uf.value = data.get('logradouro',''), data.get('bairro',''), data.get('localidade',''), data.get('uf','')
            cep.value = ViaCEPService.format_cep(cep.value)
            status.value = "✓ Encontrado!"; status.color = "green"
        else: status.value = "✗ Inválido"; status.color = "red"
        page.update()

    cep.on_change = on_cep_change
    ui = ft.ResponsiveRow([cep, status, logra, num, bairro, cid, uf], vertical_alignment=ft.CrossAxisAlignment.CENTER)
    return {
        "ui": ui, 
        "get_full_address": lambda: f"{logra.value}, {num.value} - {bairro.value}, {cid.value}/{uf.value} CEP: {cep.value}", 
        "cep": cep, 
        "logradouro": logra, 
        "numero": num, 
        "bairro": bairro, 
        "cidade": cid, 
        "uf": uf, 
        "status": status
    }

# --- GROQ AI SERVICE ---

class GroqAIService:
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    @staticmethod
    def _call_groq(api_key, system_msg, user_prompt, max_tokens=250):
        """Chamada genérica à API Groq."""
        if not api_key:
            return None, "Chave da API Groq não configurada."
        try:
            response = requests.post(
                GroqAIService.BASE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": max_tokens
                },
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                message = data["choices"][0]["message"]["content"].strip()
                return message, None
            else:
                return None, f"Erro da API: {response.status_code}"
        except requests.exceptions.Timeout:
            return None, "Timeout ao conectar com a IA."
        except Exception as ex:
            return None, f"Erro: {str(ex)}"
    
    @staticmethod
    def generate_greeting(api_key, visitor_name, church_name="IEQ Jd Portugal"):
        """Gera uma mensagem de saudacao personalizada para um visitante."""
        first_name = visitor_name.split()[0].capitalize() if visitor_name else "Visitante"
        
        system_msg = (
            "Voce e um assistente de uma igreja evangelica. Gere mensagens acolhedoras e breves. "
            "USE emojis moderadamente."
        )
        prompt = (
            f"Gere uma mensagem curta e acolhedora de saudacao em portugues do Brasil para '{first_name}', "
            f"que visitou a igreja '{church_name}'. "
            f"A mensagem deve ser calorosa, convidativa para retornar, e mencionar que ficamos felizes com a visita. "
            f"Se colocando a disposição da pessoa se precisar de alguma coisa. "
            f"Maximo 3 frases. Comece com 'Ola {first_name}'. Use Emojis moderadamente."
        )
        return GroqAIService._call_groq(api_key, system_msg, prompt, 200)
    
    @staticmethod
    def generate_event_post(api_key, title, description, date_str, time_str, location, church_name="IEQ Jd Portugal"):
        """Gera um post de divulgacao de evento para compartilhar no WhatsApp."""
        system_msg = (
            "Voce e um assistente de comunicacao de uma igreja evangelica. Crie posts de divulgacao de eventos "
            "formatados para WhatsApp. USE Emojis moderadamente. "
            "Use negrito do WhatsApp e italico"
        )
        prompt = (
            f"Crie um post de divulgacao para WhatsApp do evento da igreja '{church_name}':\n"
            f"- Titulo: {title}\n"
            f"- Descricao: {description or 'Nao informada'}\n"
            f"- Data: {date_str}\n"
            f"- Horario: {time_str}\n"
            f"- Local: {location or church_name}\n\n"
            f"O post deve ser chamativo, convidativo e bem formatado para WhatsApp. "
            f"USE Emojis moderadamente. Utilize formatacao do WhatsApp (negrito e italico). "
            f"Inclua uma chamada final convidando as pessoas. Maximo 8 linhas."
        )
        return GroqAIService._call_groq(api_key, system_msg, prompt, 300)