import requests
import os
import json
import argparse
import sys
import base64 # Importar para codificação Base64 do PAT

def extract_azure_devops_api_data(url: str, output_filename: str = None) -> None:
    """
    Extrai dados de APIs do Azure DevOps em formato JSON,
    lidando com a paginação e a forma genérica de adição de dados.
    Salva os dados em um arquivo ou os imprime na tela.

    Args:
        url (str): A URL da API do Azure DevOps a ser consultada.
                   Ex: 'https://dev.azure.com/{organization}/{project}/_apis/git/repositories?api-version=7.1-preview.1'
        output_filename (str, optional): O nome do arquivo onde os dados JSON serão salvos.
                                         Se None, os dados serão impressos na tela.
    Raises:
        ValueError: Se a variável de ambiente AZURE_DEVOPS_EXT_PAT não estiver definida.
        requests.exceptions.RequestException: Se ocorrer um erro durante a requisição HTTP.
    """

    azure_devops_ext_pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
    if not azure_devops_ext_pat:
        raise ValueError("A variável de ambiente 'AZURE_DEVOPS_EXT_PAT' não está definida. Por favor, configure-a.")

    # Codifica o PAT em Base64 para autenticação básica
    pat_encoded = base64.b64encode(f":{azure_devops_ext_pat}".encode('ascii')).decode('ascii')

    headers = {
        "Authorization": f"Basic {pat_encoded}",
        "Accept": "application/json; api-version=7.1-preview.1" # Exemplo de versão da API, ajuste conforme necessário
    }

    all_data = []
    current_url = url
    continuation_token = None

    while True: # Loop contínuo até que não haja mais token de continuação
        request_url = current_url
        if continuation_token:
            # Adiciona o token de continuação como um parâmetro de query
            # Note: Para algumas APIs, pode ser um cabeçalho, mas a maioria usa query param
            request_url = f"{current_url}{'&' if '?' in current_url else '?'}continuationToken={continuation_token}"

        try:
            response = requests.get(request_url, headers=headers)
            response.raise_for_status()  # Levanta um erro para códigos de status HTTP 4xx/5xx

            page_data = response.json()

            # --- Lógica GENÉRICA para estender a lista com base na estrutura da resposta da API ---
            # As APIs do Azure DevOps frequentemente encapsulam os dados em uma chave 'value'
            if isinstance(page_data, dict) and "value" in page_data and isinstance(page_data["value"], list):
                all_data.extend(page_data["value"])
            elif isinstance(page_data, list):
                # Caso raro onde a resposta é diretamente uma lista, mas mais comum em "value"
                all_data.extend(page_data)
            elif isinstance(page_data, dict):
                # Se for um dicionário e não tiver "value" como lista,
                # tenta encontrar a primeira chave que contenha uma lista
                found_list = False
                for key, value in page_data.items():
                    if isinstance(value, list):
                        all_data.extend(value)
                        found_list = True
                        break

                if not found_list:
                    # Se nenhuma lista for encontrada, adiciona o dicionário completo
                    all_data.append(page_data)
            else:
                # Caso a resposta não seja nem lista nem dicionário
                all_data.append(page_data)


            # --- Paginação do Azure DevOps: Verifica o cabeçalho 'x-ms-continuationtoken' ou 'ContinuationToken' ---
            continuation_token = response.headers.get('x-ms-continuationtoken')
            if not continuation_token: # Tenta uma variação comum do cabeçalho
                continuation_token = response.headers.get('ContinuationToken')

            if not continuation_token:
                break # Sai do loop se não houver mais token de continuação

        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição para {request_url}: {e}", file=sys.stderr)
            raise
        except json.JSONDecodeError:
            print(f"Erro ao decodificar JSON da resposta da URL: {request_url}", file=sys.stderr)
            raise
        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}", file=sys.stderr)
            raise

    # Lógica para salvar em arquivo ou imprimir na tela
    if output_filename:
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=4, ensure_ascii=False)
            print(f"Dados salvos com sucesso em '{output_filename}'")
        except IOError as e:
            print(f"Erro ao salvar os dados no arquivo '{output_filename}': {e}", file=sys.stderr)
            raise
    else:
        print(json.dumps(all_data, indent=4, ensure_ascii=False))

# python extract_azure_devops_api_data.py "https://dev.azure.com/vtaldevops/_apis/projects?api-version=7.1" 
# python extract_azure_devops_api_data.py "https://vsaex.dev.azure.com/vtaldevops/_apis/UserEntitlements?top=10000&api-version=7.1-preview.1"
# python extract_azure_devops_api_data.py "https://dev.azure.com/vtaldevops/_apis/projects/devopsutils?api-version=7.1&includeCapabilities=true"
# --- Bloco de chamada de exemplo (main) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrai dados de APIs do Azure DevOps e salva em arquivo ou imprime na tela.")

    parser.add_argument("url", type=str,
                        help="A URL da API do Azure DevOps a ser consultada. Ex: https://dev.azure.com/{org}/{proj}/_apis/git/repositories?api-version=7.1-preview.1")

    parser.add_argument("output_filename", nargs='?', type=str, default=None,
                        help="Opcional: Nome do arquivo para salvar os dados JSON. Se omitido, os dados serão impressos na tela.")

    args = parser.parse_args()

    try:
        extract_azure_devops_api_data(args.url, args.output_filename)
    except ValueError as e:
        print(f"Erro de configuração: {e}", file=sys.stderr)
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição HTTP: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}", file=sys.stderr)
      
