"""
Módulo de integração com API ViaCEP
Busca endereços através do CEP
"""
import requests
from typing import Optional, Dict


class ViaCEPService:
    """Serviço para buscar endereços via CEP usando a API ViaCEP"""
    
    BASE_URL = "https://viacep.com.br/ws"
    
    @staticmethod
    def clean_cep(cep: str) -> str:
        """
        Remove caracteres não numéricos do CEP
        
        Args:
            cep (str): CEP com ou sem formatação
            
        Returns:
            str: CEP apenas com números
        """
        return ''.join(filter(str.isdigit, cep))
    
    @staticmethod
    def format_cep(cep: str) -> str:
        """
        Formata CEP no padrão XXXXX-XXX
        
        Args:
            cep (str): CEP sem formatação
            
        Returns:
            str: CEP formatado
        """
        clean = ViaCEPService.clean_cep(cep)
        if len(clean) == 8:
            return f"{clean[:5]}-{clean[5:]}"
        return cep
    
    @staticmethod
    def search_by_cep(cep: str) -> Optional[Dict[str, str]]:
        """
        Busca endereço completo pelo CEP
        
        Args:
            cep (str): CEP a ser consultado
            
        Returns:
            Dict com dados do endereço ou None em caso de erro
            
        Exemplo de retorno:
        {
            'cep': '01310-100',
            'logradouro': 'Avenida Paulista',
            'complemento': '',
            'bairro': 'Bela Vista',
            'localidade': 'São Paulo',
            'uf': 'SP',
            'ibge': '3550308',
            'gia': '1004',
            'ddd': '11',
            'siafi': '7107'
        }
        """
        try:
            clean_cep = ViaCEPService.clean_cep(cep)
            
            if len(clean_cep) != 8:
                return None
            
            url = f"{ViaCEPService.BASE_URL}/{clean_cep}/json/"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verifica se o CEP foi encontrado
                if 'erro' not in data:
                    return data
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Erro ao consultar CEP: {e}")
            return None
        except Exception as e:
            print(f"Erro inesperado: {e}")
            return None
    
    @staticmethod
    def format_address(address_data: Dict[str, str]) -> str:
        """
        Formata os dados do endereço em uma string legível
        
        Args:
            address_data (Dict): Dados retornados pela API
            
        Returns:
            str: Endereço formatado
        """
        parts = []
        
        if address_data.get('logradouro'):
            parts.append(address_data['logradouro'])
        
        if address_data.get('complemento'):
            parts.append(address_data['complemento'])
        
        if address_data.get('bairro'):
            parts.append(address_data['bairro'])
        
        if address_data.get('localidade') and address_data.get('uf'):
            parts.append(f"{address_data['localidade']}/{address_data['uf']}")
        
        if address_data.get('cep'):
            parts.append(f"CEP: {address_data['cep']}")
        
        return ", ".join(parts)
