#!/usr/bin/env python3
"""
Script para crear y configurar el Next-Gen Project Board (Projects v2) en GitHub
usando la API GraphQL. Lee .github/projects/kanban.yml y crea el tablero público,
columnas y tarjetas según la plantilla.
"""

import os
import sys
import yaml
import requests
from dotenv import load_dotenv
from github import Github

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)
gh_token = os.getenv('GITHUB_TOKEN')
if not gh_token:
    print("🚨 No se encontró GITHUB_TOKEN en .env")
    sys.exit(1)

# Determinar owner y repo a partir de remote.origin.url
remote_url = os.popen('git config --get remote.origin.url').read().strip()
if remote_url.startswith('git@'):
    owner, repo = remote_url.split(':',1)[1].rstrip('.git').split('/',1)
elif remote_url.startswith('https://'):
    owner, repo = remote_url.split('github.com/')[1].rstrip('.git').split('/',1)
else:
    print("🚨 URL remoto no reconocida:", remote_url)
    sys.exit(1)

# Leer plantilla Kanban y credenciales
kanban_path = os.path.join(os.path.dirname(__file__), '..', '.github', 'projects', 'kanban.yml')
with open(kanban_path) as f:
    cfg = yaml.safe_load(f)

proj_name = cfg.get('name', f"{repo} Development Board")
proj_desc = cfg.get('description', '')

GRAPHQL_URL = "https://api.github.com/graphql"
headers = {"Authorization": f"bearer {gh_token}"}

# Obtener IDs de repo, owner y proyectos Next-Gen existentes
query_repo = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    owner { id }
    projectsV2(first: 20) {
      nodes { id title }
    }
  }
}
"""
variables = {"owner": owner, "name": repo}
resp = requests.post(GRAPHQL_URL, json={"query": query_repo, "variables": variables}, headers=headers)
data = resp.json().get("data", {}).get("repository", {})
repo_id = data.get("id")
owner_id = data.get("owner", {}).get("id")
existing_projects = data.get("projectsV2", {}).get("nodes", [])

if not repo_id or not owner_id:
    print("🚨 No se pudo obtener los IDs del repositorio o owner:", resp.json())
    sys.exit(1)

# Crear o leer el proyecto Next-Gen
proj_id = None
for p in existing_projects:
    if p["title"] == proj_name:
        proj_id = p["id"]
        print(f"📋 Project existente: {proj_name}")
        break

if not proj_id:
    mutation_create = """
    mutation($input: CreateProjectV2Input!) {
      createProjectV2(input: $input) {
        projectV2 { id }
      }
    }
    """
    input_data = {
        "repositoryId": repo_id,
        "ownerId": owner_id,
        "title": proj_name
    }
    resp = requests.post(GRAPHQL_URL, json={"query": mutation_create, "variables": {"input": input_data}}, headers=headers)
    result = resp.json()
    if not result.get("data") or result.get("errors"):
        print("🚨 Error al crear el proyecto Next-Gen:", result)
        sys.exit(1)
    proj_id = result["data"]["createProjectV2"]["projectV2"]["id"]
    print(f"✅ Project creado: {proj_name}")

# Obtener el campo Status y sus opciones
query_fields = """
query($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      fields(first: 20) {
        nodes {
          __typename
          ... on ProjectV2SingleSelectField {
            id
            name
            settings {
              ... on ProjectV2SingleSelectFieldSetting {
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
  }
}
"""
resp = requests.post(GRAPHQL_URL, json={"query": query_fields, "variables": {"projectId": proj_id}}, headers=headers)
result_fields = resp.json()
if not result_fields.get("data") or not result_fields["data"].get("node"):
    print("🚨 Error al obtener campos del Project Next-Gen:", result_fields)
    sys.exit(1)
fields_nodes = result_fields["data"]["node"]["fields"]["nodes"]
# Filtrar sólo configuraciones de campo de tipo SingleSelect
status_configs = [f for f in fields_nodes if f.get("__typename") == "ProjectV2SingleSelectField" and f.get("name") == "Status"]
if not status_configs:
    print("🚨 No se encontró el campo 'Status' correctamente configurado:", fields_nodes)
    sys.exit(1)
status_field = status_configs[0]
status_field_id = status_field["id"]
# Extraer opciones de esa configuración
status_options = {opt["name"]: opt["id"] for opt in status_field.get("settings", {}).get("options", [])}

# Crear opciones por columna en Status
for col in cfg.get("columns", []):
    col_name = col.get("name")
    if col_name not in status_options:
        mutation_add_opt = """
        mutation($input: AddProjectV2FieldOptionInput!) {
          addProjectV2FieldOption(input: $input) {
            projectV2FieldOption { id name }
          }
        }
        """
        vars_opt = {"input": {"fieldId": status_field_id, "name": col_name}}
        resp2 = requests.post(GRAPHQL_URL, json={"query": mutation_add_opt, "variables": vars_opt}, headers=headers)
        new_opt = resp2.json()["data"]["addProjectV2FieldOption"]["projectV2FieldOption"]
        status_options[new_opt["name"]] = new_opt["id"]
        print(f"➕ Opción añadida a Status: {col_name}")

# Inicializar PyGithub para creación de issues
gh = Github(gh_token)
gh_repo = gh.get_repo(f"{owner}/{repo}")

# Crear issues y items
for col in cfg.get("columns", []):
    col_name = col.get("name")
    opt_id = status_options.get(col_name)
    if not opt_id:
        continue
    for card in col.get("cards", []):
        title = card.get("title")
        body = card.get("description", "")
        labels = card.get("labels", [])
        assignees = card.get("assignees", [])
        issue = gh_repo.create_issue(title=title, body=body, labels=labels, assignees=assignees)
        print(f"🟢 Issue creado: {title}")
        mutation_item = """
        mutation($input: AddProjectV2ItemInput!) {
          addProjectV2Item(input: $input) { item { id } }
        }
        """
        resp3 = requests.post(GRAPHQL_URL, json={"query": mutation_item, "variables": {"input": {"projectId": proj_id, "contentId": issue.id}}}, headers=headers)
        item_id = resp3.json()["data"]["addProjectV2Item"]["item"]["id"]
        mutation_update = """
        mutation($input: UpdateProjectV2ItemFieldValueInput!) {
          updateProjectV2ItemFieldValue(input: $input) {
            projectV2Item { id }
          }
        }
        """
        upd_vars = {"input": {"projectId": proj_id, "itemId": item_id, "fieldId": status_field_id, "value": {"singleSelectOptionId": opt_id}}}
        requests.post(GRAPHQL_URL, json={"query": mutation_update, "variables": upd_vars}, headers=headers)
        print(f"✅ Item agregado en {col_name}: {title}")

print("🎉 Kanban Next-Gen cargado con éxito.") 