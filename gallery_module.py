"""
Módulo de Galeria de Fotos
Gerenciamento de álbuns e fotos com Supabase Storage
"""
import flet as ft
from datetime import datetime
import base64
import io
from PIL import Image
import uuid

# ==============================================================================
# FUNÇÕES DE GALERIA NO DATABASE
# ==============================================================================

def add_gallery_methods_to_database(db_class):
    """Adiciona métodos de galeria à classe Database"""
    
    def create_album(self, name, description, event_date, created_by):
        """Cria um novo álbum"""
        try:
            data = {
                'name': name,
                'description': description,
                'event_date': event_date,
                'created_by': created_by
            }
            response = self.supabase.table('albums').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao criar álbum: {e}")
            return None
    
    def get_all_albums(self):
        """Lista todos os álbuns"""
        try:
            response = self.supabase.table('albums').select('*').order('event_date', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao listar álbuns: {e}")
            return []
    
    def get_album_by_id(self, album_id):
        """Busca álbum por ID"""
        try:
            response = self.supabase.table('albums').select('*').eq('id', album_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao buscar álbum: {e}")
            return None
    
    def update_album(self, album_id, name, description, event_date):
        """Atualiza álbum"""
        try:
            data = {
                'name': name,
                'description': description,
                'event_date': event_date
            }
            self.supabase.table('albums').update(data).eq('id', album_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao atualizar álbum: {e}")
            return False
    
    def delete_album(self, album_id):
        """Deleta álbum e suas fotos"""
        try:
            # Primeiro, deletar todas as fotos do álbum no storage
            photos = self.get_photos_by_album(album_id)
            for photo in photos:
                try:
                    self.supabase.storage.from_('gallery').remove([photo['storage_path']])
                except:
                    pass
            
            # Deletar álbum (cascade vai deletar fotos da tabela)
            self.supabase.table('albums').delete().eq('id', album_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao deletar álbum: {e}")
            return False
    
    def add_photo(self, album_id, file_name, file_path, storage_path, description, uploaded_by, file_size):
        """Adiciona foto ao álbum"""
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
            response = self.supabase.table('photos').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao adicionar foto: {e}")
            return None
    
    def get_photos_by_album(self, album_id):
        """Lista fotos de um álbum"""
        try:
            response = self.supabase.table('photos').select('*').eq('album_id', album_id).order('created_at', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao listar fotos: {e}")
            return []
    
    def delete_photo(self, photo_id):
        """Deleta foto"""
        try:
            # Buscar info da foto
            response = self.supabase.table('photos').select('*').eq('id', photo_id).execute()
            if response.data:
                photo = response.data[0]
                # Deletar do storage
                try:
                    self.supabase.storage.from_('gallery').remove([photo['storage_path']])
                except:
                    pass
                # Deletar do banco
                self.supabase.table('photos').delete().eq('id', photo_id).execute()
                return True
            return False
        except Exception as e:
            print(f"Erro ao deletar foto: {e}")
            return False
    
    def upload_photo_to_storage(self, file_bytes, file_name, album_id):
        """Faz upload de foto para Supabase Storage"""
        try:
            # Gerar nome único
            unique_name = f"{album_id}/{uuid.uuid4()}_{file_name}"
            
            # Upload para storage
            self.supabase.storage.from_('gallery').upload(
                unique_name,
                file_bytes,
                file_options={"content-type": "image/jpeg"}
            )
            
            # Obter URL pública
            url = self.supabase.storage.from_('gallery').get_public_url(unique_name)
            
            return {
                'storage_path': unique_name,
                'public_url': url
            }
        except Exception as e:
            print(f"Erro ao fazer upload: {e}")
            return None
    
    def get_photo_url(self, storage_path):
        """Obtém URL pública da foto"""
        try:
            return self.supabase.storage.from_('gallery').get_public_url(storage_path)
        except Exception as e:
            print(f"Erro ao obter URL: {e}")
            return None
    
    # Adicionar métodos à classe
    db_class.create_album = create_album
    db_class.get_all_albums = get_all_albums
    db_class.get_album_by_id = get_album_by_id
    db_class.update_album = update_album
    db_class.delete_album = delete_album
    db_class.add_photo = add_photo
    db_class.get_photos_by_album = get_photos_by_album
    db_class.delete_photo = delete_photo
    db_class.upload_photo_to_storage = upload_photo_to_storage
    db_class.get_photo_url = get_photo_url

# ==============================================================================
# VIEW DE GALERIA
# ==============================================================================

def gallery_view(page: ft.Page, db, current_user, show_success, show_error, show_warning, show_loading, hide_loading, readonly=False):
    """View principal da galeria de fotos"""
    
    current_view = ft.Ref[ft.Column]()
    selected_album = {'id': None}
    
    def show_albums_list(e=None):
        """Mostra lista de álbuns"""
        albums = db.get_all_albums()
        
        album_cards = []
        
        if not albums:
            album_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PHOTO_ALBUM, size=64, color="grey"),
                        ft.Text("Nenhum álbum criado.", size=16, color="grey"),
                        ft.Text("Clique em + para criar seu primeiro álbum!", size=12, color="grey")
                    ], horizontal_alignment="center", spacing=10),
                    padding=40
                )
            )
        else:
            for album in albums:
                # Contar fotos
                photos_count = len(db.get_photos_by_album(album['id']))
                
                # Formatar data
                event_date = album.get('event_date', '')
                if event_date:
                    try:
                        dt = datetime.fromisoformat(str(event_date))
                        event_date = dt.strftime("%d/%m/%Y")
                    except:
                        pass
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            # Imagem de capa (placeholder por enquanto)
                            ft.Container(
                                content=ft.Icon(ft.Icons.PHOTO_LIBRARY, size=60, color="white"),
                                bgcolor="#1976D2",
                                height=150,
                                alignment=ft.alignment.Alignment(0, 0),
                                border_radius=ft.border_radius.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0)
                            ),
                            # Informações
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(album['name'], size=18, weight="bold"),
                                    ft.Text(album.get('description', ''), size=12, color="grey"),
                                    ft.Divider(height=5),
                                    ft.Row([
                                        ft.Icon(ft.Icons.PHOTO, size=16, color="grey"),
                                        ft.Text(f"{photos_count} foto(s)", size=12, color="grey"),
                                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color="grey"),
                                        ft.Text(event_date if event_date else "Sem data", size=12, color="grey")
                                    ], spacing=5),
                                    ft.Divider(height=5),
                                    ft.Row([
                                        ft.TextButton(
                                            "Ver Fotos",
                                            icon=ft.Icons.VISIBILITY,
                                            on_click=lambda e, aid=album['id']: show_album_photos(aid)
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color="red",
                                            tooltip="Deletar álbum",
                                            on_click=lambda e, aid=album['id'], aname=album['name']: confirm_delete_album(aid, aname),
                                            disabled=readonly
                                        ) if not readonly else ft.Container()
                                    ], alignment="spaceBetween")
                                ], spacing=5),
                                padding=10
                            )
                        ]),
                        width=300
                    ),
                    elevation=2
                )
                album_cards.append(card)
        
        # Header
        header_controls = [ft.Text("Galeria de Fotos", size=24, weight="bold")]
        if not readonly:
            header_controls.append(
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    bgcolor="#1976D2",
                    icon_color="white",
                    tooltip="Criar novo álbum",
                    on_click=show_create_album_form
                )
            )
        
        content = ft.Column([
            ft.Row(header_controls, alignment="spaceBetween"),
            ft.Divider(),
            ft.Container(
                content=ft.GridView(
                    album_cards,
                    runs_count=3,
                    max_extent=320,
                    child_aspect_ratio=0.8,
                    spacing=10,
                    run_spacing=10
                ),
                expand=True
            )
        ], expand=True, scroll="auto")
        
        current_view.current.controls = [content]
        page.update()
    
    def confirm_delete_album(album_id, album_name):
        """Confirma exclusão de álbum"""
        def delete_confirmed(e):
            dialog.open = False
            page.update()
            
            loading = show_loading(page, "Deletando álbum...")
            
            if db.delete_album(album_id):
                hide_loading(page, loading)
                show_success(page, f"Álbum '{album_name}' deletado com sucesso!")
                show_albums_list()
            else:
                hide_loading(page, loading)
                show_error(page, "Erro ao deletar álbum.")
        
        def cancel_delete(e):
            dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirmar Exclusão"),
            content=ft.Text(f"Tem certeza que deseja deletar o álbum '{album_name}' e todas as suas fotos?"),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel_delete),
                ft.TextButton("Deletar", on_click=delete_confirmed, style=ft.ButtonStyle(color="red"))
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    def show_create_album_form(e=None):
        """Formulário de criação de álbum"""
        album_name = ft.TextField(label="Nome do Álbum *", hint_text="Ex: Culto de Ano Novo 2026")
        album_desc = ft.TextField(label="Descrição", multiline=True, min_lines=2, max_lines=4)
        album_date = ft.TextField(label="Data do Evento", hint_text="DD/MM/AAAA", width=200)
        
        def save_album(e):
            if not album_name.value:
                show_warning(page, "Preencha o nome do álbum!")
                return
            
            loading = show_loading(page, "Criando álbum...")
            
            # Converter data
            event_date = None
            if album_date.value:
                try:
                    dt = datetime.strptime(album_date.value, "%d/%m/%Y")
                    event_date = dt.strftime("%Y-%m-%d")
                except:
                    pass
            
            result = db.create_album(
                album_name.value,
                album_desc.value,
                event_date,
                current_user['username']
            )
            
            hide_loading(page, loading)
            
            if result:
                show_success(page, f"Álbum '{album_name.value}' criado com sucesso!")
                show_albums_list()
            else:
                show_error(page, "Erro ao criar álbum.")
        
        content = ft.Column([
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=show_albums_list, tooltip="Voltar"),
                ft.Text("Novo Álbum", size=20, weight="bold")
            ]),
            ft.Divider(),
            album_name,
            album_desc,
            album_date,
            ft.Divider(),
            ft.ElevatedButton(
                "Criar Álbum",
                icon=ft.Icons.SAVE,
                on_click=save_album,
                style=ft.ButtonStyle(bgcolor="#1976D2", color="white")
            )
        ], spacing=15, scroll="auto")
        
        current_view.current.controls = [content]
        page.update()
    
    def show_album_photos(album_id):
        """Mostra fotos de um álbum"""
        selected_album['id'] = album_id
        album = db.get_album_by_id(album_id)
        
        if not album:
            show_error(page, "Álbum não encontrado!")
            show_albums_list()
            return
        
        photos = db.get_photos_by_album(album_id)
        
        photo_cards = []
        
        if not photos:
            photo_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE, size=64, color="grey"),
                        ft.Text("Nenhuma foto neste álbum.", size=16, color="grey"),
                        ft.Text("Clique em + para adicionar fotos!", size=12, color="grey")
                    ], horizontal_alignment="center", spacing=10),
                    padding=40
                )
            )
        else:
            for photo in photos:
                # Obter URL da foto
                photo_url = db.get_photo_url(photo['storage_path'])
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            # Imagem
                            ft.Container(
                                content=ft.Image(
                                    src=photo_url,
                                    fit=ft.ImageFit.COVER,
                                    width=250,
                                    height=250,
                                    error_content=ft.Icon(ft.Icons.BROKEN_IMAGE, size=40)
                                ),
                                width=250,
                                height=250,
                                border_radius=ft.border_radius.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0),
                                clip_behavior=ft.ClipBehavior.HARD_EDGE
                            ),
                            # Info
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(photo['file_name'], size=12, weight="bold", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(photo.get('description', ''), size=10, color="grey", max_lines=2),
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color="red",
                                            icon_size=20,
                                            tooltip="Deletar foto",
                                            on_click=lambda e, pid=photo['id']: delete_photo(pid),
                                            disabled=readonly
                                        ) if not readonly else ft.Container()
                                    ], alignment="end")
                                ], spacing=2),
                                padding=10
                            )
                        ]),
                        width=250
                    )
                )
                photo_cards.append(card)
        
        # Header
        header_controls = [
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=show_albums_list, tooltip="Voltar"),
            ft.Text(album['name'], size=20, weight="bold")
        ]
        
        if not readonly:
            header_controls.append(
                ft.IconButton(
                    icon=ft.Icons.ADD_PHOTO_ALTERNATE,
                    bgcolor="#1976D2",
                    icon_color="white",
                    tooltip="Adicionar fotos",
                    on_click=lambda e: show_upload_form(album_id)
                )
            )
        
        content = ft.Column([
            ft.Row(header_controls, alignment="spaceBetween"),
            ft.Text(album.get('description', ''), size=14, color="grey"),
            ft.Divider(),
            ft.Container(
                content=ft.GridView(
                    photo_cards,
                    runs_count=4,
                    max_extent=270,
                    child_aspect_ratio=0.85,
                    spacing=10,
                    run_spacing=10
                ) if photos else ft.Column(photo_cards),
                expand=True
            )
        ], expand=True, scroll="auto")
        
        current_view.current.controls = [content]
        page.update()
    
    def delete_photo(photo_id):
        """Deleta uma foto"""
        loading = show_loading(page, "Deletando foto...")
        
        if db.delete_photo(photo_id):
            hide_loading(page, loading)
            show_success(page, "Foto deletada com sucesso!")
            show_album_photos(selected_album['id'])
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao deletar foto.")
    
    def glob_uploads():
        """Retorna todos os caminhos de arquivos dentro de uploads/, recursivo"""
        import os
        result = []
        for root, dirs, files in os.walk("uploads"):
            for f in files:
                result.append(os.path.join(root, f))
        return result
    
    def show_upload_form(album_id):
        """Formulário de upload de fotos"""
        photo_description = ft.TextField(label="Descrição (opcional)", multiline=True)
        selected_files_text = ft.Text("Nenhum arquivo selecionado", size=12, color="grey")
        progress_text = ft.Text("", size=12, color="blue")
        
        selected_files = {'files': [], 'picker': None}
        upload_button_ref = {'button': None}
        
        def on_upload_progress(e: ft.FilePickerUploadEvent):
            """Callback de progresso do upload"""
            if e.progress is not None:
                progress_text.value = f"Enviando {e.file_name}: {int(e.progress * 100)}%"
                page.update()
        
        async def handle_pick_files(e):
            """Seleciona arquivos usando a API assíncrona"""
            try:
                # Criar FilePicker com callback de progresso
                file_picker = ft.FilePicker(on_upload=on_upload_progress)
                selected_files['picker'] = file_picker
                
                files = await file_picker.pick_files(
                    allow_multiple=True,
                    allowed_extensions=["jpg", "jpeg", "png", "gif", "webp"],
                    dialog_title="Selecione as fotos"
                )
                
                if files:
                    selected_files['files'] = files
                    selected_files_text.value = f"{len(files)} arquivo(s) selecionado(s)"
                    if upload_button_ref['button']:
                        upload_button_ref['button'].visible = True
                else:
                    selected_files['files'] = []
                    selected_files_text.value = "Seleção cancelada"
                    if upload_button_ref['button']:
                        upload_button_ref['button'].visible = False
                
                page.update()
            except Exception as ex:
                print(f"Erro ao selecionar arquivos: {ex}")
                import traceback
                traceback.print_exc()
                show_error(page, "Erro ao selecionar arquivos.")
        
        async def start_upload(description):
            """Inicia o processo de upload"""
            if not selected_files['files']:
                show_warning(page, "Nenhum arquivo selecionado!")
                return
            
            if not selected_files['picker']:
                show_error(page, "Erro: FilePicker não disponível!")
                return
            
            import os
            
            try:
                loading = show_loading(page, f"Fazendo upload de {len(selected_files['files'])} foto(s)...")
                
                # Garantir que a pasta uploads existe
                os.makedirs("uploads", exist_ok=True)
                
                # Tirar snapshot da pasta antes do upload
                files_before = set(glob_uploads())
                print(f"Arquivos na pasta antes do upload: {files_before}")
                
                # Preparar lista de uploads usando nome original
                upload_list = []
                for file in selected_files['files']:
                    upload_url = page.get_upload_url(file.name, 600)
                    upload_list.append(
                        ft.FilePickerUploadFile(
                            name=file.name,
                            upload_url=upload_url
                        )
                    )
                
                # Fazer upload para o servidor do Flet
                print(f"Iniciando upload de {len(upload_list)} arquivo(s)...")
                await selected_files['picker'].upload(upload_list)
                print("Upload para Flet concluído!")
                
                hide_loading(page, loading)
                
                # Tirar snapshot depois e encontrar os arquivos novos
                files_after = set(glob_uploads())
                new_files = files_after - files_before
                print(f"Arquivos novos encontrados: {new_files}")
                
                if not new_files:
                    show_error(page, "Nenhum arquivo foi salvo pelo Flet após o upload.")
                    return
                
                # Enviar os arquivos novos para o Supabase
                loading = show_loading(page, "Processando fotos no Supabase...")
                uploaded_count = 0
                errors = []
                
                for file_path in new_files:
                    try:
                        file_name = os.path.basename(file_path)
                        
                        with open(file_path, 'rb') as f:
                            file_bytes = f.read()
                        
                        print(f"✓ Arquivo lido: {file_name} ({len(file_bytes)} bytes)")
                        
                        # upload_photo_to_storage gera o nome único internamente
                        upload_result = db.upload_photo_to_storage(file_bytes, file_name, album_id)
                        
                        if upload_result:
                            db.add_photo(
                                album_id=album_id,
                                file_name=file_name,
                                file_path=upload_result['public_url'],
                                storage_path=upload_result['storage_path'],
                                description=description,
                                uploaded_by=current_user['username'],
                                file_size=len(file_bytes)
                            )
                            uploaded_count += 1
                            print(f"✓ Upload para Supabase concluído: {file_name}")
                        else:
                            errors.append(f"Falha no upload para Supabase: {file_name}")
                        
                        # Limpar arquivo temporário
                        try:
                            os.remove(file_path)
                            print(f"✓ Arquivo temporário removido: {file_path}")
                        except Exception as ex:
                            print(f"Aviso: Não foi possível remover arquivo temporário: {ex}")
                            
                    except Exception as ex:
                        error_msg = f"Erro ao processar {file_path}: {str(ex)}"
                        print(error_msg)
                        errors.append(error_msg)
                        import traceback
                        traceback.print_exc()
                
                hide_loading(page, loading)
                progress_text.value = ""
                
                if uploaded_count > 0:
                    show_success(page, f"{uploaded_count} foto(s) adicionada(s) com sucesso!")
                    if errors:
                        print(f"\n⚠ Avisos/Erros: {len(errors)}")
                        for err in errors[:5]:
                            print(f"  - {err}")
                    show_album_photos(album_id)
                else:
                    error_summary = "\n".join(errors[:2])
                    show_error(page, f"Erro ao processar as fotos.\n{error_summary}")
                    
            except Exception as ex:
                hide_loading(page, loading)
                progress_text.value = ""
                print(f"Erro geral no upload: {ex}")
                import traceback
                traceback.print_exc()
                show_error(page, f"Erro ao fazer upload: {str(ex)}")
        
        def trigger_upload(e):
            """Wrapper síncrono para chamar a função assíncrona"""
            import asyncio
            
            # Obter o loop de eventos
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Executar a corrotina
            loop.create_task(start_upload(photo_description.value))
        
        # Criar o botão de upload
        upload_button = ft.ElevatedButton(
            "Fazer Upload",
            icon=ft.Icons.UPLOAD,
            visible=False,
            on_click=trigger_upload,
            style=ft.ButtonStyle(bgcolor="#4CAF50", color="white")
        )
        
        # Salvar referência
        upload_button_ref['button'] = upload_button
        
        content = ft.Column([
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: show_album_photos(album_id), tooltip="Voltar"),
                ft.Text("Adicionar Fotos", size=20, weight="bold")
            ]),
            ft.Divider(),
            photo_description,
            ft.ElevatedButton(
                "Selecionar Fotos",
                icon=ft.Icons.FILE_OPEN,
                on_click=handle_pick_files,
                style=ft.ButtonStyle(bgcolor="#1976D2", color="white")
            ),
            selected_files_text,
            progress_text,
            upload_button,
            ft.Text("Formatos aceitos: JPG, PNG, GIF, WEBP", size=12, color="grey"),
            ft.Text("Os arquivos serão enviados ao clicar em 'Fazer Upload'", size=10, color="grey")
        ], spacing=15, scroll="auto")
        
        current_view.current.controls = [content]
        page.update()
    
    # Inicializar view
    col = ft.Column(expand=True, ref=current_view)
    show_albums_list()
    return col