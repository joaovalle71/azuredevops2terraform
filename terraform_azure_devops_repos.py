import json
import re
import sys
import argparse

def gerar_terraform_repositorio_ado(json_repositorio_str):
    """
    Gera o bloco Terraform 'resource' para criação de um repositório Git Azure DevOps
    e o bloco 'import' a partir de uma string JSON,
    incluindo 'initialization' e 'lifecycle' com 'ignore_changes' e 'prevent_destroy'.

    Args:
        json_repositorio_str (str): A string JSON completa (que pode ser uma lista de um item)
                                    lida da entrada.

    Returns:
        tuple: Uma tupla contendo duas strings:
                - O bloco Terraform do recurso `azuredevops_git_repository`.
                - O bloco `import` para o repositório (ou string vazia se o ID não for encontrado).
                Retorna (None, None) se os dados essenciais não forem encontrados no JSON.
    """
    try:
        data = json.loads(json_repositorio_str)
        if isinstance(data, list) and len(data) > 0:
            dados_repositorio = data[0]
        elif isinstance(data, dict):
            dados_repositorio = data
        else:
            print("Erro: JSON de entrada inválido ou formato inesperado.", file=sys.stderr)
            return None, None
    except json.JSONDecodeError:
        print("Erro: JSON de entrada inválido. Verifique a sintaxe.", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"Erro inesperado ao processar JSON: {e}", file=sys.stderr)
        return None, None

    repo_id = dados_repositorio.get("id")
    repo_name = dados_repositorio.get("name")
    
    # Extrair dados do projeto pai
    project_data = dados_repositorio.get("project", {})
    project_id = project_data.get("id") # Usado para o bloco import
    project_name = project_data.get("name") # Usado para a referência do project_id no resource

    if not all([repo_id, repo_name, project_id, project_name]):
        print("Erro: ID/nome do repositório ou ID/nome do projeto não encontrados no JSON de entrada.", file=sys.stderr)
        return None, None

    # Gerar nome do recurso em snake_case para o repositório
    repo_resource_name_snake_case = re.sub(r'[^a-z0-9]+', '_', repo_name.lower()).strip('_')
    if not repo_resource_name_snake_case:
        repo_resource_name_snake_case = "unnamed_repository"

    # Gerar nome do projeto em snake_case para a referência do resource
    project_resource_name_snake_case = re.sub(r'[^a-z0-9]+', '_', project_name.lower()).strip('_')
    if not project_resource_name_snake_case:
        project_resource_name_snake_case = "unnamed_project_ref"

    # Bloco Terraform do Recurso
    terraform_resource = f"""
resource "azuredevops_git_repository" "{repo_resource_name_snake_case}" {{
  project_id = azuredevops_project.{project_resource_name_snake_case}.id
  name       = "{repo_name}"

  # Incluindo o bloco initialization com init_type "Clean"
  initialization {{
    init_type = "Clean"
  }}

  # Incluindo o bloco lifecycle para gerenciar importação e proteção contra destruição
  lifecycle {{
    ignore_changes = [
      # Ignora mudanças em initialization para suportar importação de repositórios existentes
      # Dado que um repo agora existe, seja importado para o estado do terraform ou criado pelo terraform,
      # não nos importamos com a configuração de initialization contra o recurso existente
      initialization,
    ]
    prevent_destroy = true
  }}
}}
"""
    # Bloco Terraform para Import (nova sintaxe)
    terraform_import_block = ""
    if repo_id and project_id:
        terraform_import_block = f"""
import {{
  id = "{project_id}/{repo_id}"
  to = azuredevops_git_repository.{repo_resource_name_snake_case}
}}
"""

    return terraform_resource, terraform_import_block

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera blocos Terraform para criação e importação de repositórios Git Azure DevOps."
    )
    parser.add_argument(
        "--json",
        help="Caminho para o arquivo JSON de entrada do repositório Azure DevOps. Se não fornecido, lê do stdin.",
    )
    parser.add_argument(
        "--terraform",
        help="Caminho para o arquivo onde os comandos de criação do Terraform serão salvos. Se não fornecido, imprime no stdout.",
    )
    parser.add_argument(
        "--import",
        dest="import_file", # Usa 'dest' para evitar conflito com palavra reservada 'import'
        help="Caminho para o arquivo onde os comandos de importação do Terraform serão salvos. Se não fornecido, imprime no stdout.",
    )

    args = parser.parse_args()

    json_input_str = ""
    if args.json:
        try:
            with open(args.json, "r", encoding="utf-8") as f:
                json_input_str = f.read()
        except FileNotFoundError:
            print(f"Erro: Arquivo JSON '{args.json}' não encontrado.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Erro ao ler arquivo JSON '{args.json}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Se nenhum arquivo JSON for fornecido, tenta ler do stdin
        if not sys.stdin.isatty(): # Verifica se algo foi piped para stdin
            json_input_str = sys.stdin.read()
        else:
            print("Erro: Nenhuma entrada JSON fornecida via --json ou stdin.", file=sys.stderr)
            sys.exit(1)

    resource_block, import_block = gerar_terraform_repositorio_ado(json_input_str)

    if not resource_block and not import_block:
        sys.exit(1) # Sai com erro se nada foi gerado

    # Saída dos comandos de criação do Terraform
    if resource_block:
        if args.terraform:
            try:
                with open(args.terraform, "w", encoding="utf-8") as f:
                    f.write(resource_block)
                print(f"Bloco Terraform de recurso salvo em '{args.terraform}'")
            except Exception as e:
                print(f"Erro ao escrever no arquivo Terraform '{args.terraform}': {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("--- Bloco Terraform para o Recurso ---")
            print(resource_block)

    # Saída dos comandos de importação do Terraform
    if import_block:
        if args.import_file:
            try:
                with open(args.import_file, "w", encoding="utf-8") as f:
                    f.write(import_block)
                print(f"Bloco Terraform de importação salvo em '{args.import_file}'")
            except Exception as e:
                print(f"Erro ao escrever no arquivo de importação '{args.import_file}': {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("\n--- Bloco Terraform para Import ---")
            print(import_block)
