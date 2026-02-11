import flet as ft
from datetime import datetime
import os
import time

THEME_COLOR = "#1976D2"

# ==============================================================================
# 1. MÉTODOS DE BANCO DE DADOS (INJEÇÃO)
# ==============================================================================

def add_gallery_methods_to_database(db_class):
    """Adiciona métodos de galeria à classe Database principal"""
    
    def create_album(self, name, description, event_date, created_by):
        try:
            data = {'name': name, 'description': description, 'event_date': event_date, 'created_by': created_by}
            response = self.supabase.table('albums').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e: 
            print(f"Erro create_album: {e}")
            return None
    
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
            data = {
                'album_id': album_id, 
                'file_name': file_name, 
                'file_path': file_path, 
                'storage_path': storage_path, 
                'description': description, 
                'uploaded_by': uploaded_by, 
                'file_size': file_size
            }
            self.supabase.table('photos').insert(data).execute()
            return True
        except Exception as e: 
            print(f"Erro add_photo: {e}")
            return False
    
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
    
    # --- UPLOAD FÍSICO (DO SERVIDOR LOCAL PARA O SUPABASE) ---
    def upload_photo_to_storage(self, local_file_path, file_name, album_id):
        try:
            # Cria nome único: ID_ALBUM / TIMESTAMP_NOME
            unique_name = f"{album_id}/{int(time.time())}_{file_name}"
            
            print(f"DEBUG DB: Lendo arquivo de {local_file_path}")
            
            with open(local_file_path, "rb") as f:
                file_bytes = f.read()
                # Define Content-Type para garantir que o navegador exiba e não baixe
                self.supabase.storage.from_('gallery').upload(unique_name, file_bytes, file_options={"content-type": "image/jpeg"})
            
            # Pega URL pública
            res_url = self.supabase.storage.from_('gallery').get_public_url(unique_name)
            
            # Tratamento para diferentes versões da lib supabase
            public_url = res_url if isinstance(res_url, str) else res_url.public_url
            
            print(f"DEBUG DB: Upload Sucesso! URL: {public_url}")
            return {'storage_path': unique_name, 'public_url': public_url, 'size': len(file_bytes)}
        except Exception as e: 
            print(f"ERRO DB Upload: {e}")
            return None
    
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
# 2. VIEW DA GALERIA (UI)
# ==============================================================================

def gallery_view(page: ft.Page, db, user_state, show_success, show_error, show_warning, show_loading, hide_loading, readonly=False):
    current_view = ft.Ref[ft.Column]()
    selected_album = {'id': None}
    files_to_upload_list = []
    
    def get_current_user(): return user_state.get('user')

    # --- LISTA DE ÁLBUNS ---
    def show_albums_list(e=None):
        albums = db.get_all_albums()
        if not albums:
            content = ft.Container(content=ft.Column([ft.Icon(ft.Icons.PHOTO_ALBUM, size=50, color="grey"), ft.Text("Nenhum álbum.", color="grey")], horizontal_alignment="center"), padding=20, alignment=ft.alignment.center)
        else:
            album_controls = []
            for album in albums:
                photos = db.get_photos_by_album(album['id'])
                count = len(photos)
                date_str = datetime.fromisoformat(str(album['event_date'])).strftime("%d/%m/%Y") if album.get('event_date') else ""
                
                # Capa do Álbum
                if photos:
                    try: 
                        url_capa = photos[0]['file_path'] or db.get_photo_url(photos[0]['storage_path'])
                        cover = ft.Image(src=url_capa, fit=ft.ImageFit.COVER, width=float("inf"), height=140, repeat=ft.ImageRepeat.NO_REPEAT, gapless_playback=True)
                        bg_color = ft.colors.GREY_300
                    except:
                        cover = ft.Icon(ft.Icons.IMAGE, size=40, color="white"); bg_color = THEME_COLOR
                else:
                    cover = ft.Icon(ft.Icons.PHOTO_LIBRARY, size=40, color="white"); bg_color = THEME_COLOR

                # Card
                card_content = ft.Column([
                    ft.Container(content=cover, bgcolor=bg_color, height=140, alignment=ft.alignment.center, border_radius=ft.border_radius.only(top_left=10, top_right=10), clip_behavior=ft.ClipBehavior.HARD_EDGE),
                    ft.Container(content=ft.Column([
                        ft.Text(album['name'], weight="bold", size=16, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{count} fotos • {date_str}", size=12, color="grey"),
                        ft.Divider(height=10, color="transparent"),
                        ft.Row([
                            ft.OutlinedButton("Abrir", icon=ft.Icons.VISIBILITY, on_click=lambda e, x=album['id']: show_album_photos(x), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))),
                            ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Excluir", on_click=lambda e, x=album['id'], n=album['name']: confirm_delete_album(x, n)) if not readonly else ft.Container()
                        ], alignment="spaceBetween")
                    ]), padding=15)
                ], spacing=0)
                album_controls.append(ft.Container(content=ft.Card(content=ft.Container(content=card_content), elevation=4), col={"sm": 12, "md": 6, "lg": 4, "xl": 3}))
            
            content = ft.ResponsiveRow(album_controls)
        
        toolbar = ft.Row([ft.IconButton(ft.Icons.ADD, on_click=show_create_album_form, bgcolor=THEME_COLOR, icon_color="white", tooltip="Novo Álbum") if not readonly else ft.Container()], alignment=ft.MainAxisAlignment.END)
        current_view.current.controls = [toolbar, ft.Divider(), ft.Column([content], scroll="auto", expand=True)]; page.update()

    # --- CRIAR ÁLBUM ---
    def show_create_album_form(e=None):
        name, desc, date = ft.TextField(label="Nome *", col=12), ft.TextField(label="Descrição", col=12), ft.TextField(label="Data", col={"sm": 12, "md": 6}, value=datetime.now().strftime("%Y-%m-%d"))
        
        def save(e):
            if not name.value: show_warning(page, "Nome obrigatório!"); return
            if db.create_album(name.value, desc.value, date.value, get_current_user()): show_success(page, "Criado!"); show_albums_list()
            else: show_error(page, "Erro.")

        current_view.current.controls = [
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list), ft.Text("Novo Álbum", size=20, weight="bold")]), 
            ft.Divider(), 
            ft.ResponsiveRow([name, desc, date]), 
            ft.Container(ft.Button("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")), padding=20)
        ]
        page.update()

    # --- DELETAR ÁLBUM ---
    def confirm_delete_album(aid, aname):
        def delete(e):
            page.close(dlg); 
            if db.delete_album(aid): show_success(page, "Deletado!"); show_albums_list()
            else: show_error(page, "Erro.")
        dlg = ft.AlertDialog(title=ft.Text("Excluir?"), content=ft.Text(f"Apagar '{aname}'?"), actions=[ft.TextButton("Não", on_click=lambda e: page.close(dlg)), ft.TextButton("Sim", on_click=delete, style=ft.ButtonStyle(color="red"))]); page.open(dlg)

    # --- VISUALIZAR FOTOS DO ÁLBUM ---
    def show_album_photos(album_id):
        selected_album['id'] = album_id
        album = db.get_album_by_id(album_id)
        photos = db.get_photos_by_album(album_id)
        
        photo_controls = []
        if not photos:
            content = ft.Container(content=ft.Column([ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=50, color="grey"), ft.Text("Vazio.", color="grey")], horizontal_alignment="center"), alignment=ft.alignment.center, padding=20, expand=True)
        else:
            for p in photos:
                url = p.get('file_path') or db.get_photo_url(p['storage_path'])
                img = ft.Container(content=ft.Image(src=url, fit=ft.ImageFit.COVER), aspect_ratio=1, border_radius=8, on_click=lambda e, u=url: page.launch_url(u))
                actions = ft.Row([ft.IconButton(ft.Icons.DELETE, icon_color="red", icon_size=20, on_click=lambda e, pid=p['id']: delete_photo(pid)) if not readonly else ft.Container()], alignment="end")
                photo_controls.append(ft.Container(content=ft.Container(content=ft.Column([img, actions], spacing=0), bgcolor="white", padding=5, border_radius=8, shadow=ft.BoxShadow(blur_radius=2, color="black12")), col={"xs": 6, "sm": 4, "md": 3, "lg": 2}))
            content = ft.Column([ft.ResponsiveRow(photo_controls)], scroll="auto", expand=True)

        header = ft.Row([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list), ft.Text(album['name'], size=18, weight="bold")]),
            ft.IconButton(ft.Icons.ADD_PHOTO_ALTERNATE, on_click=lambda e: show_upload_form(album_id), bgcolor=THEME_COLOR, icon_color="white") if not readonly else ft.Container()
        ], alignment="spaceBetween")
        current_view.current.controls = [header, ft.Divider(), content]; page.update()

    def delete_photo(pid):
        if db.delete_photo(pid): show_success(page, "Apagado!"); show_album_photos(selected_album['id'])
        else: show_error(page, "Erro.")

    # --- FORMULÁRIO DE UPLOAD (CRÍTICO) ---
    def show_upload_form(album_id):
        print(f"DEBUG: Abrindo form de upload para album {album_id}")
        
        status_txt = ft.Text("Selecione os arquivos...", italic=True)
        prog_bar = ft.ProgressBar(value=0, visible=False, color=THEME_COLOR)
        btn_start_upload = ft.Button("Enviar", icon=ft.Icons.CLOUD_UPLOAD, disabled=True)
        
        # 1. Callback da Seleção de Arquivos
        def on_files_selected(e: ft.FilePickerResultEvent):
            if e.files:
                files_to_upload_list.clear()
                files_to_upload_list.extend(e.files)
                status_txt.value = f"{len(e.files)} arquivos prontos."
                status_txt.color = "blue"
                btn_start_upload.disabled = False
                print(f"DEBUG: {len(e.files)} arquivos selecionados.")
                page.update()

        # 2. Callback de Upload Concluído (Do Browser -> Servidor)
        def on_upload_complete(e: ft.FilePickerUploadEvent):
            if e.progress is None: 
                print(f"DEBUG: Handshake... (Aguardando)")
                return
            
            if e.error:
                print(f"ERRO FLET: {e.error}")
                status_txt.value = f"Erro: {e.error}"
                status_txt.color = "red"
                page.update()
                return

            print(f"DEBUG: Progresso: {e.progress}")

            if e.progress == 1.0:
                # 1. Procura o arquivo na pasta TEMPORÁRIA
                # Nota: "temp_uploads" deve bater com o nome criado no app.py
                temp_path = os.path.join(os.getcwd(), "temp_uploads", e.file_name)
                
                print(f"DEBUG: Buscando em {temp_path}")
                
                if os.path.exists(temp_path):
                    print(f"DEBUG: Arquivo recebido! Enviando para nuvem...")
                    
                    # 2. Envia para o Supabase
                    res = db.upload_photo_to_storage(temp_path, e.file_name, album_id)
                    
                    if res:
                        db.add_photo(album_id, e.file_name, res['public_url'], res['storage_path'], "Upload App", get_current_user(), res['size'])
                        status_txt.value = f"Sucesso: {e.file_name}"
                        status_txt.color = "green"
                    else:
                        status_txt.value = f"Erro Supabase: {e.file_name}"
                        status_txt.color = "red"
                    
                    # 3. Limpeza
                    try: os.remove(temp_path)
                    except: pass
                else:
                    print(f"ERRO: Arquivo não encontrado em {temp_path}")
                    status_txt.value = "Erro interno: Arquivo não salvo."
                    status_txt.color = "red"
                
                page.update()

        # FilePicker Configurado com on_upload
        file_picker = ft.FilePicker(on_result=on_files_selected, on_upload=on_upload_complete)
        page.overlay.append(file_picker)
        page.update()

        # 3. Botão Iniciar (Dispara o envio Browser -> Servidor)
        def start_upload_process(e):
            if not files_to_upload_list: return
            
            print("DEBUG: Botão Enviar Clicado.")
            btn_start_upload.disabled = True
            prog_bar.visible = True
            status_txt.value = "Enviando para o servidor..."
            page.update()
            
            # Comando mágico do Flet
            file_picker.upload(files_to_upload_list)

        btn_start_upload.on_click = start_upload_process

        header = ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_album_photos(album_id)), ft.Text("Upload", size=20, weight="bold")])
        
        current_view.current.controls = [
            header, ft.Divider(),
            ft.Column([
                ft.ElevatedButton("Selecionar Arquivos", icon=ft.Icons.FOLDER, on_click=lambda _: file_picker.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE)),
                status_txt, 
                prog_bar, 
                btn_start_upload,
                ft.Text("Aguarde a confirmação verde antes de voltar.", size=10, color="grey")
            ], spacing=20, horizontal_alignment="center")
        ]
        page.update()

    col = ft.Column(expand=True, ref=current_view)
    show_albums_list()
    return col