#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
base="$project_root/tmp/tree-replacement/map_master_tree_repairs_review_30.png"
output="$project_root/tmp/tree-replacement/map_master_tree_repairs_review_76.png"

declare -a layers
add_layer() {
  local patch_path="$1"
  local x="$2"
  local y="$3"
  layers+=("(" "$patch_path" -geometry "+${x}+${y}" ")")
}

while IFS=$'\t' read -r patch_path x y; do
  add_layer "$patch_path" "$x" "$y"
done < <(jq -r '.patches[] | [.patch, (.world_placement[0]|tostring), (.world_placement[1]|tostring)] | @tsv' \
  "$project_root/tmp/tree-replacement/worker_east/manifest.json")

while IFS=$'\t' read -r patch_path x y; do
  add_layer "$patch_path" "$x" "$y"
done < <(jq -r '.patches[] | [.patch, (.placement_world[0]|tostring), (.placement_world[1]|tostring)] | @tsv' \
  "$project_root/tmp/tree-replacement/worker_north/manifest.json")

while IFS=$'\t' read -r patch_path x y; do
  add_layer "$patch_path" "$x" "$y"
done < <(jq -r '.patches[] | [.patch, (.world_placement[0]|tostring), (.world_placement[1]|tostring)] | @tsv' \
  "$project_root/tmp/tree-replacement/worker_south/patch_manifest.json")

while IFS=$'\t' read -r relative_patch x y; do
  add_layer "$project_root/tmp/tree-replacement/worker_root/$relative_patch" "$x" "$y"
done < <(jq -r '.entries[] | [.patch, (.placement[0]|tostring), (.placement[1]|tostring)] | @tsv' \
  "$project_root/tmp/tree-replacement/worker_root/manifest.json")

magick "$base" "${layers[@]}" -background none -layers merge "$output"
magick "$output" -resize 1250x1250 "$project_root/tmp/tree-replacement/map_master_tree_repairs_review_76_preview.png"

printf '%s\n' "$output"
