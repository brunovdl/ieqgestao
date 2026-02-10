"""
Módulo de Galeria de Fotos - VERSÃO RESPONSIVA (Clean Layout)
Compatível com Flet 0.25.2 e App.py Moderno
"""
import flet as ft
from datetime import datetime
import uuid
import os
import asyncio

THEME_COLOR = "#1976D2"

# ==============================================================================
# FUNÇÕES DE BANCO DE DADOS
# ==============================================================================

def add_gallery_methods_to_database(db_class):
    """Adiciona métodos de galeria à classe Database"""
    
    def create_album(self, name, description, event_date, created_by):
        try:
            data = {'name': name, 'description': description, 'event_date': event_date, 'created_by': created_by}
            response = self.supabase.table('albums').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e: return None
    
    def get_all_albums(self):
        try: return self.supabase.table('albums').select('*').order('event_date', desc=True).execute().data or []
        except: return []
    
    def get_album_by_id(self, album_id):
        try: return self.supabase.table('albums').select('*').eq('id', album_id).execute().data[0]
        except: return None
    
    def delete_album(self, album_id):
        try:
            photos = self.get_photos_by_album(album_id)
            for photo in photos:
                try: self.supabase.storage.from_('gallery').remove([photo['storage_path']])
                except: pass
            self.supabase.table('albums').delete().eq('id', album_id).execute()
            return True
        except: return False
    
    def add_photo(self, album_id, file_name, file_path, storage_path, description, uploaded_by, file_size):
        try:
            data = {'album_id': album_id, 'file_name': file_name, 'file_path': file_path, 'storage_path': storage_path, 'description': description, 'uploaded_by': uploaded_by, 'file_size': file_size}
            self.supabase.table('photos').insert(data).execute()
            return True
        except: return False
    
    def get_photos_by_album(self, album_id):
        try: return self.supabase.table('photos').select('*').eq('album_id', album_id).order('created_at', desc=True).execute().data or []
        except: return []
    
    def delete_photo(self, photo_id):
        try:
            res = self.supabase.table('photos').select('*').eq('id', photo_id).execute()
            if res.data:
                photo = res.data[0]
                try: self.supabase.storage.from_('gallery').remove([photo['storage_path']])
                except: pass
                self.supabase.table('photos').delete().eq('id', photo_id).execute()
                return True
            return False
        except: return False
    
    def upload_photo_to_storage(self, file_bytes, file_name, album_id):
        try:
            unique_name = f"{album_id}/{uuid.uuid4()}_{file_name}"
            self.supabase.storage.from_('gallery').upload(unique_name, file_bytes, file_options={"content-type": "image/jpeg"})
            url = self.supabase.storage.from_('gallery').get_public_url(unique_name)
            return {'storage_path': unique_name, 'public_url': url}
        except: return None
    
    def get_photo_url(self, storage_path):
        try: return self.supabase.storage.from_('gallery').get_public_url(storage_path)
        except: return None

    # Injeta os métodos na classe
    db_class.create_album = create_album
    db_class.get_all_albums = get_all_albums
    db_class.get_album_by_id = get_album_by_id
    db_class.delete_album = delete_album
    db_class.add_photo = add_photo
    db_class.get_photos_by_album = get_photos_by_album
    db_class.delete_photo = delete_photo
    db_class.upload_photo_to_storage = upload_photo_to_storage
    db_class.get_photo_url = get_photo_url

# ==============================================================================
# VIEW DE GALERIA RESPONSIVA
# ==============================================================================

def gallery_view(page: ft.Page, db, user_state, show_success, show_error, show_warning, show_loading, hide_loading, readonly=False):
    """View principal da galeria de fotos - Totalmente Responsiva"""
    
    current_view = ft.Ref[ft.Column]()
    selected_album = {'id': None}
    current_album_photos_list = []
    
    # Função auxiliar para extrair o usuário do state
    def get_current_user():
        return user_state.get('user')

    def show_albums_list(e=None):
        """Mostra lista de álbuns com capa"""
        albums = db.get_all_albums()
        
        if not albums:
            content = ft.Container(content=ft.Column([ft.Icon(ft.Icons.PHOTO_ALBUM, size=50, color="grey"), ft.Text("Nenhum álbum.", color="grey")], horizontal_alignment="center"), padding=20, alignment=ft.alignment.center)
        else:
            album_controls = []
            for album in albums:
                photos = db.get_photos_by_album(album['id'])
                count = len(photos)
                date_str = datetime.fromisoformat(str(album['event_date'])).strftime("%d/%m/%Y") if album.get('event_date') else ""
                
                # Capa
                if photos:
                    cover = ft.Image(src=db.get_photo_url(photos[0]['storage_path']), fit=ft.ImageFit.COVER, width=float("inf"), height=140, repeat=ft.ImageRepeat.NO_REPEAT, gapless_playback=True)
                    bg_color = ft.colors.GREY_300
                else:
                    cover = ft.Icon(ft.Icons.PHOTO_LIBRARY, size=40, color="white")
                    bg_color = THEME_COLOR

                # Card do Álbum
                card_content = ft.Column([
                    ft.Container(content=cover, bgcolor=bg_color, height=140, alignment=ft.alignment.center, border_radius=ft.border_radius.only(top_left=10, top_right=10), clip_behavior=ft.ClipBehavior.HARD_EDGE),
                    ft.Container(content=ft.Column([
                        ft.Text(album['name'], weight="bold", size=16, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{count} fotos • {date_str}", size=12, color="grey"),
                        ft.Divider(height=10, color="transparent"),
                        ft.Row([
                            ft.OutlinedButton("Abrir", icon=ft.Icons.VISIBILITY, on_click=lambda e, x=album['id']: show_album_photos(x), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))),
                            ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Excluir Álbum", on_click=lambda e, x=album['id'], n=album['name']: confirm_delete_album(x, n)) if not readonly else ft.Container()
                        ], alignment="spaceBetween")
                    ]), padding=15)
                ], spacing=0)

                card = ft.Card(content=ft.Container(content=card_content), elevation=4)
                album_controls.append(ft.Container(content=card, col={"sm": 12, "md": 6, "lg": 4, "xl": 3}))
            
            content = ft.ResponsiveRow(album_controls)
        
        # LAYOUT LIMPO: Título removido (está no header). Apenas botão ADD à direita.
        toolbar = ft.Row([
            ft.IconButton(ft.Icons.ADD, on_click=show_create_album_form, bgcolor=THEME_COLOR, icon_color="white", tooltip="Novo Álbum") if not readonly else ft.Container()
        ], alignment=ft.MainAxisAlignment.END)
        
        current_view.current.controls = [toolbar, ft.Divider(), ft.Column([content], scroll="auto", expand=True)]
        page.update()

    def show_create_album_form(e=None):
        name = ft.TextField(label="Nome do Álbum *", col=12)
        desc = ft.TextField(label="Descrição", multiline=True, col=12)
        date = ft.TextField(label="Data (AAAA-MM-DD)", col={"sm": 12, "md": 6}, value=datetime.now().strftime("%Y-%m-%d"))
        
        def save(e):
            if not name.value: show_warning(page, "Nome obrigatório!"); return
            loading = show_loading(page, "Criando álbum...")
            if db.create_album(name.value, desc.value, date.value, get_current_user()):
                hide_loading(page, loading); show_success(page, "Álbum criado!"); show_albums_list()
            else: hide_loading(page, loading); show_error(page, "Erro ao criar álbum.")

        header = ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list), ft.Text("Novo Álbum", size=20, weight="bold")])
        
        form = ft.Column([
            header, 
            ft.Divider(),
            ft.ResponsiveRow([name, desc, date], spacing=20),
            ft.Container(ft.Button("Salvar Álbum", on_click=save, icon=ft.Icons.SAVE, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"), height=50), padding=20, alignment=ft.alignment.center)
        ], scroll="auto", expand=True) # Scroll importantíssimo aqui
        
        current_view.current.controls = [form]; page.update()

    def confirm_delete_album(aid, aname):
        def delete(e):
            page.close(dlg); loading = show_loading(page, "Deletando álbum...")
            if db.delete_album(aid): hide_loading(page, loading); show_success(page, "Álbum deletado!"); show_albums_list()
            else: hide_loading(page, loading); show_error(page, "Erro ao deletar.")
        dlg = ft.AlertDialog(title=ft.Text("Excluir Álbum?"), content=ft.Text(f"Tem certeza que deseja apagar '{aname}' e todas as suas fotos?"), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)), ft.TextButton("Apagar", on_click=delete, style=ft.ButtonStyle(color="red"))])
        page.open(dlg)

    def show_album_photos(album_id):
        selected_album['id'] = album_id
        album = db.get_album_by_id(album_id)
        photos = db.get_photos_by_album(album_id)
        current_album_photos_list.clear(); current_album_photos_list.extend(photos)
        
        photo_controls = []
        if not photos:
            content = ft.Container(content=ft.Column([ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=50, color="grey"), ft.Text("Este álbum está vazio.", color="grey")], horizontal_alignment="center"), alignment=ft.alignment.center, padding=20, expand=True)
        else:
            for i, p in enumerate(photos):
                url = db.get_photo_url(p['storage_path'])
                # Imagem Quadrada (Aspect Ratio 1)
                img = ft.Container(content=ft.Image(src=url, fit=ft.ImageFit.COVER, repeat=ft.ImageRepeat.NO_REPEAT), aspect_ratio=1, border_radius=8, on_click=lambda e, idx=i: open_lightbox(idx), ink=True, clip_behavior=ft.ClipBehavior.HARD_EDGE)
                
                # Botões de ação pequenos abaixo da foto
                actions = ft.Row([
                    ft.IconButton(ft.Icons.DOWNLOAD, icon_color="blue", icon_size=20, tooltip="Baixar", on_click=lambda e, u=url: page.launch_url(u)),
                    ft.IconButton(ft.Icons.DELETE, icon_color="red", icon_size=20, tooltip="Excluir", on_click=lambda e, pid=p['id']: delete_photo(pid)) if not readonly else ft.Container()
                ], alignment="spaceBetween")
                
                # Card da Foto
                card = ft.Container(content=ft.Column([img, actions], spacing=0), bgcolor="white", padding=5, border_radius=8, shadow=ft.BoxShadow(blur_radius=2, color="black12"))
                photo_controls.append(ft.Container(content=card, col={"xs": 6, "sm": 4, "md": 3, "lg": 2, "xl": 2}, padding=5))
            
            content = ft.Column([ft.ResponsiveRow(photo_controls)], scroll="auto", expand=True)

        # Header do Álbum: Botão voltar + Título + Botão Upload (se permitido)
        header_row = ft.Row([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list), ft.Text(album['name'], size=18, weight="bold", no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)]),
            ft.IconButton(ft.Icons.ADD_PHOTO_ALTERNATE, on_click=lambda e: show_upload_form(album_id), bgcolor=THEME_COLOR, icon_color="white", tooltip="Adicionar Fotos") if not readonly else ft.Container()
        ], alignment="spaceBetween")
        
        current_view.current.controls = [header_row, ft.Divider(), content]
        page.update()

    def delete_photo(pid):
        def conf(e):
            page.close(dlg); loading = show_loading(page, "Excluindo foto...")
            if db.delete_photo(pid): hide_loading(page, loading); show_success(page, "Foto excluída!"); show_album_photos(selected_album['id'])
            else: hide_loading(page, loading); show_error(page, "Erro ao excluir.")
        dlg = ft.AlertDialog(title=ft.Text("Excluir Foto?"), content=ft.Text("Essa ação não pode ser desfeita."), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)), ft.TextButton("Sim", on_click=conf, style=ft.ButtonStyle(color="red"))])
        page.open(dlg)

    def show_upload_form(album_id):
        desc = ft.TextField(label="Descrição das fotos (Opcional)", col=12)
        status = ft.Text("Nenhum arquivo selecionado", col=12, italic=True)
        prog = ft.ProgressBar(value=0, visible=False, col=12, color=THEME_COLOR)
        stored_files = []
        
        def on_pick(e):
            if e.files:
                stored_files.extend(e.files)
                status.value = f"{len(stored_files)} arquivo(s) pronto(s) para envio."; status.color = "blue"
                btn_up.disabled = False
                page.update()
        
        picker = ft.FilePicker(on_result=on_pick)
        page.overlay.append(picker)
        page.update()

        # Task assíncrona para upload
        async def upload_task(d):
            prog.visible = True; btn_up.disabled = True; page.update()
            count = 0
            total = len(stored_files)
            for f in stored_files:
                try:
                    with open(f.path, 'rb') as io: b = io.read()
                    res = db.upload_photo_to_storage(b, f.name, album_id)
                    if res:
                        db.add_photo(album_id, f.name, res['public_url'], res['storage_path'], d, get_current_user(), len(b))
                        count += 1
                    prog.value = count / total
                    page.update()
                except: pass
            
            show_success(page, f"{count} fotos enviadas com sucesso!");
            show_album_photos(album_id)

        btn_up = ft.Button("Iniciar Upload", icon=ft.Icons.CLOUD_UPLOAD, disabled=True, on_click=lambda e: page.run_task(upload_task, desc.value), col=12, style=ft.ButtonStyle(bgcolor="green", color="white"), height=50)
        
        header = ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_album_photos(album_id)), ft.Text("Adicionar Fotos", size=20, weight="bold")])
        
        content = ft.Column([
            header, ft.Divider(),
            ft.ResponsiveRow([
                desc,
                ft.Container(ft.OutlinedButton("Selecionar Arquivos", icon=ft.Icons.FILE_UPLOAD, on_click=lambda e: picker.pick_files(allow_multiple=True), height=50), col=12),
                status, prog, btn_up
            ], spacing=20)
        ], scroll="auto", expand=True)
        
        current_view.current.controls = [content]; page.update()

    def open_lightbox(idx):
        if not current_album_photos_list: return
        idx_ref = [idx]
        
        # Imagem em tela cheia
        img = ft.Image(src=db.get_photo_url(current_album_photos_list[idx]['storage_path']), fit=ft.ImageFit.CONTAIN, width=page.width, height=page.height)
        
        def nav(delta):
            n = idx_ref[0] + delta
            if 0 <= n < len(current_album_photos_list):
                idx_ref[0] = n
                img.src = db.get_photo_url(current_album_photos_list[n]['storage_path'])
                img.update()
        
        stack = ft.Stack([
            ft.Container(bgcolor="black", opacity=0.95, on_click=lambda e: (page.overlay.remove(stack), page.update()), expand=True),
            ft.Container(content=img, alignment=ft.alignment.center),
            # Controles
            ft.Container(ft.IconButton(ft.Icons.CLOSE, icon_color="white", icon_size=30, on_click=lambda e: (page.overlay.remove(stack), page.update())), top=20, right=20),
            ft.Container(ft.IconButton(ft.Icons.ARROW_BACK, icon_color="white", icon_size=40, on_click=lambda e: nav(-1)), left=10, top=page.height/2 - 20),
            ft.Container(ft.IconButton(ft.Icons.ARROW_FORWARD, icon_color="white", icon_size=40, on_click=lambda e: nav(1)), right=10, top=page.height/2 - 20)
        ], expand=True)
        
        page.overlay.append(stack); page.update()

    col = ft.Column(expand=True, ref=current_view)
    show_albums_list()
    return col