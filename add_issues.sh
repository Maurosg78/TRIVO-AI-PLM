#!/usr/bin/env bash

PROJECT_NUMBER=28
OWNER="Maurosg78"
REPO="trivo-ai-plm"   # Asegúrate que coincide exactamente con tu repo

# Lista de issues que quieres añadir
ISSUES=(1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22)

for ISSUE_NUMBER in "${ISSUES[@]}"; do
  echo "➕ Agregando Issue #${ISSUE_NUMBER} al Project ${PROJECT_NUMBER}…"
  gh project item-add "${PROJECT_NUMBER}" \
    --owner "${OWNER}" \
    --url "https://github.com/${OWNER}/${REPO}/issues/${ISSUE_NUMBER}"
done
