#!/usr/bin/env bash
set -euo pipefail

# Script para asignar issues al campo 'Sprint' en el Project v2 de GitHub según su milestone
# Requisitos: gh CLI, yq, jq y GITHUB_TOKEN en .env

# 1) Cargar token y variables de repo
export GITHUB_TOKEN=$(grep GITHUB_TOKEN .env | cut -d'=' -f2)
FULL_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
OWNER=${FULL_REPO%/*}

# 2) Obtener número de proyecto Next-Gen
project_number=$(gh project list --owner "$OWNER" --format json --jq ".[] | select(.name==\"TRIVO-AI-PLM Development Board\").number")
echo "✔ Project #$project_number encontrado"

# 3) Crear campo Sprint si no existe
echo "🔧 Verificando campo 'Sprint'..."
gh project field-create "$project_number" \
  --owner "$OWNER" \
  --name "Sprint" \
  --data-type SINGLE_SELECT \
  --single-select-options "Sprint 1: Infraestructura Base,Sprint 2: Sistema de Recomendación,Sprint 3: Frontend y UX" \
  --format json > /dev/null 2>&1 || echo "⚠ Campo 'Sprint' ya existía"

# 4) Iterar sprints y asignar issues
echo "🚀 Asignando issues a Sprint..."
for sprint in "Sprint 1: Infraestructura Base" "Sprint 2: Sistema de Recomendación" "Sprint 3: Frontend y UX"; do
  echo "
==> $sprint"
  # Listar números de issues con el milestone exacto
  issue_numbers=$(gh issue list --repo "$FULL_REPO" --milestone "$sprint" --json number --jq '.[].number')
  for num in $issue_numbers; do
    echo "  - Issue #$num"
    # Obtener todos los items y filtrar localmente con jq
    items_json=$(gh project item-list "$project_number" --owner "$OWNER" --format json)
    item_id=$(echo "$items_json" | jq -r ".[] | select(.content.number==$num).id")
    # Actualizar campo Sprint
    gh project item-edit "$project_number" "$item_id" \
      --owner "$OWNER" --field "Sprint" --value "$sprint" > /dev/null
    echo "    ✔ Asignado a '$sprint'"
  done
done

echo "🎉 Issues sincronizados por Sprint." 