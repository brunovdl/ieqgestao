"""
Módulo de Galeria de Fotos - VERSÃO RESPONSIVA (Mobile First)
Compatível com Flet 0.25.2 e o novo layout do app.py
"""
import flet as ft
from datetime import datetime
import uuid
import os
import asyncio

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

def gallery_view(page: ft.Page, db, current_user, show_success, show_error, show_warning, show_loading, hide_loading, readonly=False):
    """View principal da galeria de fotos - Totalmente Responsiva"""
    
    current_view = ft.Ref[ft.Column]()
    selected_album = {'id': None}
    current_album_photos_list = []
    
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
                    bg = ft.colors.GREY_300
                else:
                    cover = ft.Icon(ft.Icons.PHOTO_LIBRARY, size=40, color="white")
                    bg = "#1976D2"

                card = ft.Card(content=ft.Container(content=ft.Column([
                    ft.Container(content=cover, bgcolor=bg, height=140, alignment=ft.alignment.center, border_radius=ft.border_radius.only(top_left=10, top_right=10), clip_behavior=ft.ClipBehavior.HARD_EDGE),
                    ft.Container(content=ft.Column([
                        ft.Text(album['name'], weight="bold", size=16, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{count} fotos • {date_str}", size=12, color="grey"),
                        ft.Divider(height=10, color="transparent"),
                        ft.Row([
                            ft.OutlinedButton("Abrir", icon=ft.Icons.VISIBILITY, on_click=lambda e, x=album['id']: show_album_photos(x)),
                            ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda e, x=album['id'], n=album['name']: confirm_delete_album(x, n)) if not readonly else ft.Container()
                        ], alignment="spaceBetween")
                    ]), padding=15)
                ], spacing=0)), col={"sm": 12, "md": 6, "lg": 4, "xl": 3}, elevation=4)
                album_controls.append(card)
            content = ft.ResponsiveRow(album_controls)
        
        header = [ft.Text("Galeria", size=24, weight="bold", color="#1976D2")]
        if not readonly: header.append(ft.IconButton(ft.Icons.ADD, on_click=show_create_album_form, bgcolor="#1976D2", icon_color="white"))
        
        current_view.current.controls = [ft.Row(header, alignment="spaceBetween"), ft.Divider(), ft.Column([content], scroll="auto", expand=True)]
        page.update()

    def show_create_album_form(e=None):
        name = ft.TextField(label="Nome *", col=12)
        desc = ft.TextField(label="Descrição", multiline=True, col=12)
        date = ft.TextField(label="Data (AAAA-MM-DD)", col={"sm": 12, "md": 6})
        
        def save(e):
            if not name.value: show_warning(page, "Nome obrigatório!"); return
            loading = show_loading(page, "Criando...")
            if db.create_album(name.value, desc.value, date.value, current_user.get('user')):
                hide_loading(page, loading); show_success(page, "Criado!"); show_albums_list()
            else: hide_loading(page, loading); show_error(page, "Erro.")

        content = ft.Column([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list), ft.Text("Novo Álbum", size=20)]), ft.ResponsiveRow([name, desc, date]), ft.Button("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor="#1976D2", color="white"))], scroll="auto", expand=True)
        current_view.current.controls = [content]; page.update()

    def confirm_delete_album(aid, aname):
        def delete(e):
            page.close(dlg); loading = show_loading(page, "Deletando...")
            if db.delete_album(aid): hide_loading(page, loading); show_success(page, "Deletado!"); show_albums_list()
            else: hide_loading(page, loading); show_error(page, "Erro.")
        dlg = ft.AlertDialog(title=ft.Text("Excluir?"), content=ft.Text(f"Apagar '{aname}'?"), actions=[ft.TextButton("Não", on_click=lambda e: page.close(dlg)), ft.TextButton("Sim", on_click=delete)])
        page.open(dlg)

    def show_album_photos(album_id):
        selected_album['id'] = album_id
        album = db.get_album_by_id(album_id)
        photos = db.get_photos_by_album(album_id)
        current_album_photos_list.clear(); current_album_photos_list.extend(photos)
        
        photo_controls = []
        if not photos:
            content = ft.Container(content=ft.Column([ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=50, color="grey"), ft.Text("Sem fotos.", color="grey")]), alignment=ft.alignment.center, padding=20)
        else:
            for i, p in enumerate(photos):
                url = db.get_photo_url(p['storage_path'])
                img = ft.Container(content=ft.Image(src=url, fit="cover", repeat=ft.ImageRepeat.NO_REPEAT), aspect_ratio=1, border_radius=ft.border_radius.only(top_left=8, top_right=8), on_click=lambda e, idx=i: open_lightbox(idx), ink=True)
                actions = ft.Row([ft.IconButton(ft.Icons.DOWNLOAD, icon_color="blue", on_click=lambda e, u=url: page.launch_url(u)), ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda e, pid=p['id']: delete_photo(pid)) if not readonly else ft.Container()], alignment="spaceBetween")
                card = ft.Card(content=ft.Container(content=ft.Column([img, ft.Container(actions, padding=5)], spacing=0)))
                photo_controls.append(ft.Container(content=card, col={"sm": 6, "md": 4, "lg": 3, "xl": 2}, padding=2))
            content = ft.ResponsiveRow(photo_controls)

        header = [ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list), ft.Text(album['name'], size=18, weight="bold")]
        if not readonly: header.append(ft.IconButton(ft.Icons.ADD_PHOTO_ALTERNATE, on_click=lambda e: show_upload_form(album_id), bgcolor="#1976D2", icon_color="white"))
        
        current_view.current.controls = [ft.Row(header, alignment="spaceBetween"), ft.Divider(), ft.Column([content], scroll="auto", expand=True)]
        page.update()

    def delete_photo(pid):
        def conf(e):
            page.close(dlg); loading = show_loading(page, "Excluindo...")
            if db.delete_photo(pid): hide_loading(page, loading); show_success(page, "Excluída!"); show_album_photos(selected_album['id'])
            else: hide_loading(page, loading); show_error(page, "Erro.")
        dlg = ft.AlertDialog(title=ft.Text("Excluir Foto?"), content=ft.Text("Confirmar exclusão?"), actions=[ft.TextButton("Não", on_click=lambda e: page.close(dlg)), ft.TextButton("Sim", on_click=conf)])
        page.open(dlg)

    def show_upload_form(album_id):
        desc = ft.TextField(label="Descrição (Opcional)", col=12)
        status = ft.Text("Nenhum arquivo", col=12)
        prog = ft.ProgressBar(value=0, visible=False, col=12)
        stored_files = []
        
        def on_pick(e):
            if e.files: stored_files.extend(e.files); status.value = f"{len(stored_files)} arquivos"; btn_up.disabled=False; page.update()
        picker = ft.FilePicker(on_result=on_pick); page.overlay.append(picker); page.update()

        async def upload_task(d):
            prog.visible=True; btn_up.disabled=True; page.update(); count=0
            for f in stored_files:
                try:
                    with open(f.path, 'rb') as io: b=io.read()
                    res = db.upload_photo_to_storage(b, f.name, album_id)
                    if res: db.add_photo(album_id, f.name, res['public_url'], res['storage_path'], d, current_user.get('user'), len(b)); count+=1
                    prog.value = count/len(stored_files); page.update()
                except: pass
            show_success(page, f"{count} enviados!"); show_album_photos(album_id)

        btn_up = ft.Button("Enviar", disabled=True, on_click=lambda e: page.run_task(upload_task, desc.value), col=12, style=ft.ButtonStyle(bgcolor="green", color="white"))
        content = ft.Column([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_album_photos(album_id)), ft.Text("Upload", size=20)]), ft.ResponsiveRow([desc, ft.Button("Selecionar", on_click=lambda e: picker.pick_files(allow_multiple=True), col=12), status, prog, btn_up])], scroll="auto", expand=True)
        current_view.current.controls = [content]; page.update()

    def open_lightbox(idx):
        if not current_album_photos_list: return
        idx_ref = [idx]
        img = ft.Image(src=db.get_photo_url(current_album_photos_list[idx]['storage_path']), fit="contain", width=page.width, height=page.height)
        def nav(delta):
            n = idx_ref[0] + delta
            if 0 <= n < len(current_album_photos_list): idx_ref[0]=n; img.src=db.get_photo_url(current_album_photos_list[n]['storage_path']); img.update()
        stack = ft.Stack([ft.Container(bgcolor="black", opacity=0.95, on_click=lambda e: (page.overlay.remove(stack), page.update()), expand=True), ft.Container(content=img, alignment=ft.alignment.center), ft.Container(ft.IconButton(ft.Icons.CLOSE, icon_color="white", on_click=lambda e: (page.overlay.remove(stack), page.update())), top=20, right=20), ft.Container(ft.IconButton(ft.Icons.ARROW_BACK, icon_color="white", on_click=lambda e: nav(-1)), left=10, top=page.height/2), ft.Container(ft.IconButton(ft.Icons.ARROW_FORWARD, icon_color="white", on_click=lambda e: nav(1)), right=10, top=page.height/2)], expand=True)
        page.overlay.append(stack); page.update()

    col = ft.Column(expand=True, ref=current_view); show_albums_list(); return col