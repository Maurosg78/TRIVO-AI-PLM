#!/usr/bin/env python3
"""
Sincroniza el campo 'Sprint' en el Project Next-Gen (v2) con los milestones de cada issue.
Requisitos: python-dotenv, PyGithub, requests.
"""
import os
import sys
import subprocess
import requests
from dotenv import load_dotenv
from github import Github

# Cargo token de .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)
token = os.getenv('GITHUB_TOKEN')
if not token:
    print('🚨 No se encontró GITHUB_TOKEN en .env')
    sys.exit(1)

# Determinar slug owner/repo desde remote.origin.url
remote = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url']).decode().strip()
if remote.startswith('git@'):
    slug = remote.split(':',1)[1].removesuffix('.git')
elif 'github.com/' in remote:
    slug = remote.split('github.com/')[1].removesuffix('.git')
else:
    print('🚨 URL remoto no reconocida:', remote)
    sys.exit(1)
owner, repo = slug.split('/', 1)

# GraphQL endpoint y headers
gql_url = 'https://api.github.com/graphql'
headers = {'Authorization': f'bearer {token}'}

# 1) Obtener ID del Project Next-Gen
query_proj = '''
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    projectsV2(first: 20) { nodes { id title } }
  }
}
'''
resp = requests.post(gql_url, json={'query': query_proj, 'variables': {'owner': owner, 'name': repo}}, headers=headers)
proj_nodes = resp.json().get('data', {}).get('repository', {}).get('projectsV2', {}).get('nodes', [])
proj = next((p for p in proj_nodes if p['title'] == 'TRIVO-AI-PLM Development Board'), None)
if not proj:
    print('🚨 No se encontró el proyecto Next-Gen en el repo')
    sys.exit(1)
proj_id = proj['id']
print(f'📋 Proyecto encontrado: {proj["title"]} ({proj_id})')

# 2) Obtener nodo con items y campos Single Select
desc_fields_items = '''
query($pid: ID!) {
  node(id: $pid) {
    ... on ProjectV2 {
      fields(first: 20) { nodes { __typename ... on ProjectV2SingleSelectField { id name options { id name } } } }
      items(first: 200) { nodes { id content { __typename ... on Issue { number } } } }
    }
  }
}
'''
resp2 = requests.post(gql_url, json={'query': desc_fields_items, 'variables': {'pid': proj_id}}, headers=headers)
node = resp2.json().get('data', {}).get('node', {})
fields = node.get('fields', {}).get('nodes', [])
items = node.get('items', {}).get('nodes', [])

# 3) Buscar campo 'Sprint'
sf = next((f for f in fields if f.get('name') == 'Sprint' and f.get('__typename') == 'ProjectV2SingleSelectField'), None)
if not sf:
    print('🚨 No se encontró el campo Sprint en el proyecto. Créalo antes.')
    sys.exit(1)
field_id = sf['id']
option_map = {opt['name']: opt['id'] for opt in sf.get('options', [])}
print(f'🔧 Campo Sprint: {field_id}, opciones: {list(option_map.keys())}')

# 4) Inicializar PyGithub
gh = Github(token)
gh_repo = gh.get_repo(slug)

# 5) Iterar items y actualizar según milestone
def assign_item(item):
    num = item.get('content', {}).get('number')
    if not num:
        return
    issue = gh_repo.get_issue(num)
    ms = issue.milestone
    if not ms or not ms.title:
        return
    sprint_name = ms.title
    opt_id = option_map.get(sprint_name)
    if not opt_id:
        print(f'⚠️ Opción de sprint no válida: {sprint_name}')
        return
    item_id = item['id']
    mutation = '''
    mutation($input: UpdateProjectV2ItemFieldValueInput!) {
      updateProjectV2ItemFieldValue(input: $input) { projectV2Item { id } }
    }
    '''
    vars3 = {'input': {'projectId': proj_id, 'itemId': item_id, 'fieldId': field_id, 'value': {'singleSelectOptionId': opt_id}}}
    requests.post(gql_url, json={'query': mutation, 'variables': vars3}, headers=headers)
    print(f'✅ Issue #{num} asignado a sprint "{sprint_name}"')

for it in items:
    assign_item(it)

print('🎉 Sincronización Sprint completada.') 