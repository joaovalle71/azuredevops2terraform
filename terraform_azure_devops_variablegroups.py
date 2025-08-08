import json
import re
import sys
import argparse

def gerar_terraform_variablegroup_ado(json_variablegroup_str):
    """
    Gera o bloco Terraform 'resource' para criação de um variable group Azure DevOps
    e o bloco 'import' a partir de uma string JSON.

    Args:
        json_variablegroup_str (str): A string JSON completa (que pode ser uma lista de um item)
                                      lida da entrada.

    Returns:
        tuple: Uma tupla contendo duas strings:
                - O bloco Terraform do recurso `azuredevops_variable_group`.
                - O bloco `import` para o variable group (ou string vazia se o ID não for encontrado).
                Retorna (None, None) se os dados essenciais não forem encontrados no JSON.
    """
    try:
        data = json.loads(json_variablegroup_str)
        if isinstance(data, list) and len(data) > 0:
            dados_vg = data[0]
        elif isinstance(data, dict):
            dados_vg = data
        else:
            print("Erro: JSON de entrada inválido ou formato inesperado.", file=sys.stderr)
            return None, None
    except json.JSONDecodeError:
        print("Erro: JSON de entrada inválido. Verifique a sintaxe.", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"Erro inesperado ao processar JSON: {e}", file=sys.stderr)
        return None, None

    vg_id = dados_vg.get("id")
    vg_name = dados_vg.get("name")
    project_id = dados_vg.get("projectReference", {}).get("id")
    project_name = dados_vg.get("projectReference", {}).get("name")
    variables = dados_vg.get("variables", {})

    if not all([vg_id, vg_name, project_id, project_name]):
        print("Erro: ID/nome do variable group ou ID/nome do projeto não encontrados no JSON de entrada.", file=sys.stderr)
        return None, None

    vg_resource_name_snake_case = re.sub(r'[^a-z0-9]+', '_', vg_name.lower()).strip('_')
    if not vg_resource_name_snake_case:
        vg_resource_name_snake_case = "unnamed_variablegroup"

    project_resource_name_snake_case = re.sub(r'[^a-z0-9]+', '_', project_name.lower()).strip('_')
    if not project_resource_name_snake_case:
        project_resource_name_snake_case = "unnamed_project_ref"

    # Monta o bloco de variáveis
    variables_block = ""
    for var_name, var_data in variables.items():
        value = var_data.get("value", "")
        is_secret = var_data.get("isSecret", False)
        variables_block += f"    {var_name} = {{\n      value     = \"{value}\"\n      is_secret = {str(is_secret).lower()}\n    }}\n"

    terraform_resource = f"""
resource \"azuredevops_variable_group\" \"{vg_resource_name_snake_case}\" {{
  project_id = azuredevops_project.{project_resource_name_snake_case}.id
  name       = \"{vg_name}\"

  variable {{
{variables_block}  }}
}}
"""
    terraform_import_block = ""
    if vg_id and project_id:
        terraform_import_block = f"""
import {{
  id = \"{project_id}/{vg_id}\"
  to = azuredevops_variable_group.{vg_resource_name_snake_case}
}}
"""
    return terraform_resource, terraform_import_block

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera blocos Terraform para criação e importação de variable groups Azure DevOps."
    )
    parser.add_argument(
        "--json",
        help="Caminho para o arquivo JSON de entrada do variable group Azure DevOps. Se não fornecido, lê do stdin.",
    )
    parser.add_argument(
        "--terraform",
        help="Caminho para o arquivo onde os comandos de criação do Terraform serão salvos. Se não fornecido, imprime no stdout.",
    )
    parser.add_argument(
        "--import",
        dest="import_file",
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
        if not sys.stdin.isatty():
            json_input_str = sys.stdin.read()
        else:
            print("Erro: Nenhuma entrada JSON fornecida via --json ou stdin.", file=sys.stderr)
            sys.exit(1)

    resource_block, import_block = gerar_terraform_variablegroup_ado(json_input_str)

    if not resource_block and not import_block:
        sys.exit(1)

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
