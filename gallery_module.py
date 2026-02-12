"""
Módulo de Galeria de Fotos
Gerenciamento de álbuns e fotos com Supabase Storage
VERSÃO FINAL REFINADA - Flet 0.25.2
(Visual Limpo + Correção Botões Lightbox)
"""
import flet as ft
from datetime import datetime
import uuid
import os
import asyncio
import glob

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
            if "row-level security" in str(e):
                print("DICA: Execute o script setup_permissions.sql no Supabase.")
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
            if "row-level security" in str(e):
                print("DICA: Execute o script setup_permissions.sql no Supabase.")
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
            # Tratamento de erro melhorado para RLS
            error_msg = str(e)
            if "new row violates row-level security policy" in error_msg or "403" in error_msg:
                print("\n[ERRO CRÍTICO] Bloqueio de Segurança do Supabase.")
                print("MOTIVO: O banco de dados recusou a gravação.")
                print("SOLUÇÃO: Copie e execute o código do arquivo 'setup_permissions.sql' no painel do Supabase.\n")
            else:
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
    
    # Lista local para navegação no Lightbox
    current_album_photos_list = []
    
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
                            # Imagem de capa
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
            if hasattr(page, 'close'):
                page.close(dialog)
            else:
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
            if hasattr(page, 'close'):
                page.close(dialog)
            else:
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
        page.open(dialog)
    
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
    
    # --- LIGHTBOX (VISUALIZADOR ECRÃ INTEIRO) ---
    def open_lightbox(start_index):
        """Abre o visualizador de imagens em tela cheia"""
        current_index = [start_index]
        
        # Referência para a imagem e contador
        img_ref = ft.Ref[ft.Image]()
        count_ref = ft.Ref[ft.Text]()
        
        def get_current_url():
            if 0 <= current_index[0] < len(current_album_photos_list):
                return db.get_photo_url(current_album_photos_list[current_index[0]]['storage_path'])
            return ""

        def close_lightbox(e):
            page.overlay.remove(lightbox_stack)
            page.update()

        def next_photo(e=None):
            if current_index[0] < len(current_album_photos_list) - 1:
                current_index[0] += 1
                new_url = get_current_url()
                if img_ref.current:
                    img_ref.current.src = new_url
                    img_ref.current.update() 
                if count_ref.current:
                    count_ref.current.value = f"{current_index[0] + 1} / {len(current_album_photos_list)}"
                    count_ref.current.update()
                page.update()

        def prev_photo(e=None):
            if current_index[0] > 0:
                current_index[0] -= 1
                new_url = get_current_url()
                if img_ref.current:
                    img_ref.current.src = new_url
                    img_ref.current.update()
                if count_ref.current:
                    count_ref.current.value = f"{current_index[0] + 1} / {len(current_album_photos_list)}"
                    count_ref.current.update()
                page.update()
        
        # Lógica de Gestos (Swipe)
        def on_pan_end(e: ft.DragEndEvent):
            if e.primary_velocity is None: return
            if e.primary_velocity < -300: # Arrastar para esquerda -> Próximo
                next_photo()
            elif e.primary_velocity > 300: # Arrastar para direita -> Anterior
                prev_photo()

        # Componente de Imagem
        img_control = ft.Image(
            ref=img_ref,
            src=get_current_url(),
            fit="contain",
            width=page.width,
            height=page.height,
        )

        # Overlay (Camadas) - CORRIGIDO: Botões fora do GestureDetector
        lightbox_stack = ft.Stack(
            controls=[
                # 1. Camada de Fundo + Imagem (Captura Swipe)
                ft.GestureDetector(
                    on_pan_end=on_pan_end,
                    content=ft.Container(
                        bgcolor="black",
                        opacity=0.95,
                        width=page.width,
                        height=page.height,
                        alignment=ft.alignment.center,
                        content=img_control, # Imagem dentro do fundo
                        on_click=close_lightbox # Clicar na imagem/fundo fecha
                    )
                ),
                
                # 2. Camada de Interface (Botões e Texto) - Por cima de tudo
                # Contador de Páginas
                ft.Container(
                    content=ft.Text(
                        ref=count_ref,
                        value=f"{current_index[0] + 1} / {len(current_album_photos_list)}",
                        color="white",
                        size=16,
                        weight="bold"
                    ),
                    alignment=ft.alignment.top_center,
                    padding=ft.padding.only(top=20),
                    # Importante: ignorar toques nesta área para não bloquear o fundo
                    # (A menos que seja um botão)
                ),
                # Botão Anterior (Seta Esquerda)
                ft.Container(
                    content=ft.IconButton(
                        ft.Icons.ARROW_BACK_IOS, 
                        icon_color="white", 
                        icon_size=30, 
                        on_click=prev_photo,
                        tooltip="Anterior",
                        style=ft.ButtonStyle(bgcolor=ft.colors.with_opacity(0.3, "black"))
                    ),
                    alignment=ft.alignment.center_left,
                    padding=20,
                    visible=len(current_album_photos_list) > 1
                ),
                # Botão Próximo (Seta Direita)
                ft.Container(
                    content=ft.IconButton(
                        ft.Icons.ARROW_FORWARD_IOS, 
                        icon_color="white", 
                        icon_size=30, 
                        on_click=next_photo,
                        tooltip="Próximo",
                        style=ft.ButtonStyle(bgcolor=ft.colors.with_opacity(0.3, "black"))
                    ),
                    alignment=ft.alignment.center_right,
                    padding=20,
                    visible=len(current_album_photos_list) > 1
                ),
                # Botão Fechar (X no topo)
                ft.Container(
                    content=ft.IconButton(
                        ft.Icons.CLOSE, 
                        icon_color="white", 
                        icon_size=30, 
                        on_click=close_lightbox,
                        tooltip="Fechar"
                    ),
                    alignment=ft.alignment.top_right,
                    padding=20
                )
            ],
            width=page.width,
            height=page.height,
        )
        
        page.overlay.append(lightbox_stack)
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
        
        # Atualizar lista global para o lightbox
        current_album_photos_list.clear()
        current_album_photos_list.extend(photos)
        
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
            for index, photo in enumerate(photos):
                # Obter URL da foto
                photo_url = db.get_photo_url(photo['storage_path'])
                
                # Container da imagem clicável
                clickable_image = ft.Container(
                    content=ft.Image(
                        src=photo_url,
                        fit="cover",
                        width=250, # Largura responsiva seria melhor, mas fixo é ok para grid
                        height=160, # Altura ajustada
                        error_content=ft.Icon(ft.Icons.BROKEN_IMAGE, size=40)
                    ),
                    width=250,
                    height=160,
                    border_radius=ft.border_radius.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ink=True, # Efeito de clique
                    on_click=lambda e, idx=index: open_lightbox(idx), # Abre lightbox ao clicar
                    tooltip="Clique para ampliar"
                )

                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            clickable_image,
                            # Info e Botões (SEM O NOME DO ARQUIVO)
                            ft.Container(
                                content=ft.Column([
                                    # Descrição (só mostra se existir)
                                    ft.Text(photo.get('description', ''), size=10, color="grey", max_lines=2, visible=bool(photo.get('description', ''))),
                                    ft.Row([
                                        # Botão Download
                                        ft.IconButton(
                                            icon=ft.Icons.DOWNLOAD,
                                            icon_color="blue",
                                            icon_size=20,
                                            tooltip="Baixar / Abrir original",
                                            on_click=lambda e, url=photo_url: page.launch_url(url)
                                        ),
                                        # Botão Delete
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color="red",
                                            icon_size=20,
                                            tooltip="Deletar foto",
                                            on_click=lambda e, pid=photo['id']: delete_photo(pid),
                                            disabled=readonly,
                                            visible=not readonly
                                        )
                                    ], alignment=ft.MainAxisAlignment.END)
                                ], spacing=2),
                                padding=5
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
                    # Proporção ajustada para cartão mais compacto (1.0 = quadrado)
                    child_aspect_ratio=1.0, 
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
        
        def confirm_del(e):
            if hasattr(page, 'close'):
                page.close(dlg)
            else:
                dlg.open = False
                page.update()
                
            loading = show_loading(page, "Deletando foto...")
            if db.delete_photo(photo_id):
                hide_loading(page, loading)
                show_success(page, "Foto deletada com sucesso!")
                show_album_photos(selected_album['id'])
            else:
                hide_loading(page, loading)
                show_error(page, "Erro ao deletar foto.")

        def cancel_del(e):
            if hasattr(page, 'close'):
                page.close(dlg)
            else:
                dlg.open = False
                page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Excluir Foto"),
            content=ft.Text("Tem certeza? Esta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel_del),
                ft.TextButton("Excluir", on_click=confirm_del, style=ft.ButtonStyle(color="red"))
            ]
        )
        page.open(dlg)
    
    def glob_uploads():
        # ATENÇÃO: Procurando na pasta correta 'temp_uploads'
        return glob.glob("temp_uploads/*") if os.path.exists("temp_uploads") else []

    def show_upload_form(album_id):
        """Formulário de upload de fotos (Modo Híbrido: Direto ou Upload)"""
        photo_description = ft.TextField(label="Descrição (opcional)", multiline=True)
        selected_files_text = ft.Text("Nenhum arquivo selecionado", size=12, color="grey")
        progress_text = ft.Text("", size=12, color="blue")
        
        # BARRA DE PROGRESSO ADICIONADA
        upload_progress_bar = ft.ProgressBar(width=400, color="blue", bgcolor="#eeeeee", value=0, visible=False)
        
        # Armazena arquivos selecionados
        selected_files_storage = {'files': [], 'picker': None}
        upload_button_ref = {'button': None}
        select_button_ref = {'button': None} 
        
        # Estado de sincronização de upload
        upload_status = {'pending': 0, 'event': asyncio.Event()}

        def on_upload_result(e: ft.FilePickerUploadEvent):
            # Callback para monitorar uploads em modo Web
            if e.progress == 1.0:
                upload_status['pending'] -= 1
                if upload_status['pending'] <= 0:
                    upload_status['event'].set()

        # --- Lógica FilePicker corrigida para Flet 0.25+ ---
        def on_picker_result(e: ft.FilePickerResultEvent):
            if e.files:
                selected_files_storage['files'] = e.files
                count = len(e.files)
                selected_files_text.value = f"{count} arquivo(s) selecionado(s)"
                if upload_button_ref['button']:
                    upload_button_ref['button'].visible = True
                    upload_button_ref['button'].disabled = False
            else:
                selected_files_storage['files'] = []
                selected_files_text.value = "Seleção cancelada"
                if upload_button_ref['button']:
                    upload_button_ref['button'].visible = False
            page.update()

        # FilePicker configurado com on_upload para sincronização
        file_picker = ft.FilePicker(on_result=on_picker_result, on_upload=on_upload_result)
        selected_files_storage['picker'] = file_picker
        page.overlay.append(file_picker)
        page.update()

        def handle_pick_files(e):
            file_picker.pick_files(
                allow_multiple=True,
                allowed_extensions=["jpg", "jpeg", "png", "gif", "webp"],
                dialog_title="Selecione as fotos"
            )
        
        # --- Lógica de Upload Assíncrona ---
        async def upload_process_async(desc):
            """Processa os arquivos selecionados em background"""
            files = selected_files_storage['files']
            if not files:
                show_warning(page, "Nenhum arquivo para enviar.")
                return

            # Configurar UI para estado de carregamento
            if upload_button_ref['button']:
                upload_button_ref['button'].disabled = True
            if select_button_ref['button']:
                select_button_ref['button'].disabled = True
            
            upload_progress_bar.visible = True
            upload_progress_bar.value = 0
            progress_text.value = "Iniciando envio..."
            page.update()

            # --- ETAPA 1: Identificar quais arquivos precisam de upload local ---
            files_ready_to_process = []
            files_needing_upload = []
            
            for f in files:
                if f.path:
                    # Tem caminho, usa direto (Desktop)
                    files_ready_to_process.append({'obj': f, 'path': f.path, 'is_temp': False})
                else:
                    # Não tem caminho (Web), precisa de upload
                    files_needing_upload.append(f)
            
            # --- ETAPA 2: Upload para pasta temporária (Se necessário) ---
            if files_needing_upload:
                progress_text.value = "Enviando arquivos para o servidor..."
                page.update()
                
                os.makedirs("temp_uploads", exist_ok=True)
                files_before = set(glob_uploads())
                
                upload_objects = []
                for f in files_needing_upload:
                    url = page.get_upload_url(f.name, 600)
                    upload_objects.append(ft.FilePickerUploadFile(f.name, upload_url=url))
                
                # Configurar contador para sincronização
                upload_status['pending'] = len(upload_objects)
                upload_status['event'].clear()

                if selected_files_storage['picker']:
                    # CORREÇÃO CRÍTICA: Sem await aqui, pois upload() é síncrono/fire-and-forget
                    selected_files_storage['picker'].upload(upload_objects)
                    
                    # Aguarda o evento de conclusão disparado pelo on_upload_result
                    # Timeout de segurança de 120s
                    try:
                        await asyncio.wait_for(upload_status['event'].wait(), timeout=120.0)
                    except asyncio.TimeoutError:
                        print("Aviso: Timeout aguardando upload. Tentando prosseguir...")
                
                # Aguarda um pouco para o sistema de arquivos atualizar
                await asyncio.sleep(1.0)
                
                files_after = set(glob_uploads())
                new_files = list(files_after - files_before)
                
                # Mapeia os arquivos novos encontrados na pasta temp
                # Tenta associar pelo nome, mas pega qualquer novo se não bater
                for nf in new_files:
                    f_mock = type('obj', (object,), {'name': os.path.basename(nf)})
                    files_ready_to_process.append({'obj': f_mock, 'path': nf, 'is_temp': True})

            # --- ETAPA 3: Envio para o Supabase ---
            uploaded_count = 0
            errors = []
            total_files = len(files_ready_to_process)

            if total_files == 0:
                errors.append("Nenhum arquivo pôde ser processado (Falha no upload inicial).")

            for i, item in enumerate(files_ready_to_process):
                f = item['obj']
                f_path = item['path']
                is_temp = item['is_temp']
                
                try:
                    # Atualizar progresso visual
                    progress_text.value = f"Salvando {i+1} de {total_files}: {f.name}"
                    upload_progress_bar.value = (i / total_files)
                    page.update()
                    
                    with open(f_path, 'rb') as file_obj:
                        file_bytes = file_obj.read()
                    
                    # Enviar para Supabase
                    upload_result = db.upload_photo_to_storage(file_bytes, f.name, album_id)
                    
                    if upload_result:
                        # Obter nome do usuário de forma segura
                        uploader_name = "Desconhecido"
                        if isinstance(current_user, dict):
                            uploader_name = current_user.get('username', 'Desconhecido') or 'Desconhecido'

                        db.add_photo(
                            album_id=album_id,
                            file_name=f.name,
                            file_path=upload_result['public_url'],
                            storage_path=upload_result['storage_path'],
                            description=desc,
                            uploaded_by=uploader_name,
                            file_size=len(file_bytes)
                        )
                        uploaded_count += 1
                        
                        # Se for arquivo temporário, apagar
                        if is_temp:
                            try:
                                os.remove(f_path)
                            except:
                                pass
                    else:
                        errors.append(f"Falha no envio para nuvem: {f.name}")
                        
                except Exception as ex:
                    print(f"Erro ao processar arquivo: {ex}")
                    errors.append(f"Erro local: {str(ex)}")

            # Finalizar barra
            upload_progress_bar.value = 1.0
            progress_text.value = "Concluído!"
            page.update()
            
            await asyncio.sleep(0.5)

            if uploaded_count > 0:
                show_success(page, f"{uploaded_count} foto(s) enviada(s)!")
                show_album_photos(album_id) 
            else:
                if upload_button_ref['button']:
                    upload_button_ref['button'].disabled = False
                if select_button_ref['button']:
                    select_button_ref['button'].disabled = False
                upload_progress_bar.visible = False
                progress_text.value = ""
                
                msg = "\n".join(errors[:2])
                if "violate" in str(errors):
                    msg += "\n\nDICA: Verifique as permissões (RLS) no Supabase."
                show_error(page, f"Falha no envio.\n{msg}")
                page.update()

        def trigger_upload(e):
            """Inicia a task assíncrona usando page.run_task"""
            page.run_task(upload_process_async, photo_description.value)
        
        # Botões
        select_button = ft.ElevatedButton(
            "Selecionar Fotos",
            icon=ft.Icons.FILE_OPEN,
            on_click=handle_pick_files,
            style=ft.ButtonStyle(bgcolor="#1976D2", color="white")
        )
        select_button_ref['button'] = select_button

        upload_button = ft.ElevatedButton(
            "Fazer Upload",
            icon=ft.Icons.UPLOAD,
            visible=False if not selected_files_storage['files'] else True,
            on_click=trigger_upload,
            style=ft.ButtonStyle(bgcolor="#4CAF50", color="white")
        )
        upload_button_ref['button'] = upload_button
        
        content = ft.Column([
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: show_album_photos(album_id), tooltip="Voltar"),
                ft.Text("Adicionar Fotos", size=20, weight="bold")
            ]),
            ft.Divider(),
            photo_description,
            select_button,
            selected_files_text,
            upload_progress_bar, # Barra aqui
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