#!/usr/bin/env zsh
set -euo pipefail

root=${0:a:h:h}
work="$root/tmp/imagegen/player-weapons"
assets="$root/Assets/Player Animations"

typeset -A sheets=(
  m16 "$work/m16-sheet-magenta.png"
  smg "$work/smg-sheet-magenta.png"
  shotgun "$work/shotgun-sheet-magenta.png"
  sniper "$work/sniper-sheet-magenta.png"
)

for weapon in m16 smg shotgun sniper; do
  sheet=${sheets[$weapon]}
  source="$work/$weapon-cells"
  mkdir -p "$source"
  magick "$sheet" -crop 4x3@ +repage "$source/cell-%02d.png"

  for state in idle move shoot; do
    case $state in
      idle) row=0 ; count=20 ; prefix=survivor-idle_${weapon}_ ;;
      move) row=1 ; count=20 ; prefix=survivor-move_${weapon}_ ;;
      shoot) row=2 ; count=3 ; prefix=survivor-shoot_${weapon}_ ;;
    esac
    out="$assets/${weapon:u}/${state:u}"
    mkdir -p "$out"

    for key in 0 1 2 3; do
      cell=$((row * 4 + key))
      # Remove the generated flat magenta field, trim it, then place every
      # pose on the legacy 313x207 canvas about one stable centre pivot.
      magick "$source/cell-$(printf '%02d' $cell).png" \
        -alpha on -fuzz 30% -transparent '#ff00ff' -trim +repage \
        -resize '296x190>' -gravity center -background none -extent 313x207 \
        "$source/$state-key-$key.png"
    done

    for ((frame = 0; frame < count; frame++)); do
      if [[ $state == shoot ]]; then
        key=$frame
      else
        # Four key poses held for five 60 Hz frames: a readable 12 fps source
        # cadence without interpolated ghosting around the weapon silhouette.
        key=$((frame / 5))
      fi
      cp "$source/$state-key-$key.png" "$out/$prefix$frame.png"
    done
  done
done
