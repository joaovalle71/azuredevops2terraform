import json
import re
import sys
import argparse

def gerar_terraform_projeto_ado(json_projeto_str):
    """
    Gera o bloco Terraform 'resource' para criação de um projeto Azure DevOps
    e o bloco 'import' (conforme a nova sintaxe do Terraform) a partir de uma string JSON,
    incluindo dados do bloco 'capabilities'.

    Args:
        json_projeto_str (str): A string JSON completa lida da entrada.

    Returns:
        tuple: Uma tupla contendo duas strings:
                - O bloco Terraform do recurso `azuredevops_project`.
                - O bloco `import` para o projeto (ou string vazia se o ID não for encontrado).
                Retorna (None, None) se os dados essenciais não forem encontrados no JSON.
    """
    try:
        data = json.loads(json_projeto_str)
        if isinstance(data, list) and len(data) > 0:
            dados_projeto = data[0]
        elif isinstance(data, dict):
            dados_projeto = data
        else:
            print("Erro: JSON de entrada inválido ou formato inesperado.", file=sys.stderr)
            return None, None
    except json.JSONDecodeError:
        print("Erro: JSON de entrada inválido. Verifique a sintaxe.", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"Erro inesperado ao processar JSON: {e}", file=sys.stderr)
        return None, None

    project_id = dados_projeto.get("id")
    project_name = dados_projeto.get("name")
    project_description = dados_projeto.get("description", "")
    project_visibility = dados_projeto.get("visibility", "private")

    capabilities = dados_projeto.get("capabilities", {})

    process_template_data = capabilities.get("processTemplate", {})
    work_item_template = process_template_data.get("templateName", "Agile")

    version_control_data = capabilities.get("versioncontrol", {})
    version_control = version_control_data.get("sourceControlType", "Git")

    if not all([project_id, project_name]):
        print("Erro: ID ou nome do projeto não encontrados no JSON de entrada.", file=sys.stderr)
        return None, None

    resource_name_snake_case = re.sub(r'[^a-z0-9]+', '_', project_name.lower()).strip('_')
    if not resource_name_snake_case:
        resource_name_snake_case = "unnamed_project"

    formatted_description = json.dumps(project_description)

    terraform_resource = f"""
resource "azuredevops_project" "{resource_name_snake_case}" {{
  name               = "{project_name}"
  description        = {formatted_description}
  visibility         = "{project_visibility}"
  version_control    = "{version_control}"
  work_item_template = "{work_item_template}"
}}
"""
    terraform_import_block = ""
    if project_id:
        terraform_import_block = f"""
import {{
  id = "{project_id}"
  to = azuredevops_project.{resource_name_snake_case}
}}
"""
    return terraform_resource, terraform_import_block

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera blocos Terraform para criação e importação de projetos Azure DevOps."
    )
    parser.add_argument(
        "--json",
        help="Caminho para o arquivo JSON de entrada do projeto Azure DevOps. Se não fornecido, lê do stdin.",
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

    resource_block, import_block = gerar_terraform_projeto_ado(json_input_str)

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
