"""
Componentes visuais reutilizáveis
"""
import flet as ft


def rounded_logo(size: int = 80, show_name: bool = True):
    """
    Cria um logo redondo da igreja
    
    Args:
        size (int): Tamanho do logo em pixels
        show_name (bool): Se deve mostrar o nome abaixo do logo
        
    Returns:
        ft.Column ou ft.Container: Componente do logo
    """
    logo_container = ft.Container(
        content=ft.Image(
            src="logoieq.png",
            width=size,
            height=size,
            fit="cover",
            error_content=ft.Icon(ft.Icons.CHURCH, size=size * 0.6, color="white")
        ),
        width=size,
        height=size,
        border_radius=size // 2,  # Círculo perfeito
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,  # Recorta a imagem em círculo
        bgcolor="#1976D2",  # Azul - Cor de fundo caso imagem não carregue
        alignment=ft.Alignment(0, 0),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=10,
            color="black12",
            offset=ft.Offset(0, 2),
        )
    )
    
    if show_name:
        return ft.Column(
            [
                logo_container,
                ft.Text(
                    "IEQ",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Gestão",
                    size=12,
                    color="grey",
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )
    
    return logo_container


def header_logo(size: int = 60):
    """
    Logo menor para header/cabeçalho
    
    Args:
        size (int): Tamanho do logo
        
    Returns:
        ft.Container: Logo redondo
    """
    return ft.Container(
        content=ft.Image(
            src="logoieq.png",
            width=size,
            height=size,
            fit="cover",
            error_content=ft.Icon(ft.Icons.CHURCH, size=size * 0.6, color="white")
        ),
        width=size,
        height=size,
        border_radius=size // 2,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor="#1976D2",
        alignment=ft.Alignment(0, 0),
    )
