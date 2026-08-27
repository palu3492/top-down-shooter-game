#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: $0 SOURCE DESTINATION" >&2
  exit 2
fi

source_image=$1
destination_image=$2
work_dir=$(mktemp -d /private/tmp/map-palette.XXXXXX)
trap 'rm -rf "$work_dir"' EXIT

vips colourspace "$source_image" "$work_dir/hsv.v" hsv
vips extract_band "$work_dir/hsv.v" "$work_dir/h.v" 0 --n 1
vips extract_band "$work_dir/hsv.v" "$work_dir/s.v" 1 --n 1
vips extract_band "$work_dir/hsv.v" "$work_dir/v.v" 2 --n 1
rm "$work_dir/hsv.v"

# Grass mask: hue 45-105 degrees, saturation >= 0.38, value >= 0.28.
vips relational_const "$work_dir/h.v" "$work_dir/a.v" moreeq 32
vips relational_const "$work_dir/h.v" "$work_dir/b.v" lesseq 74
vips boolean "$work_dir/a.v" "$work_dir/b.v" "$work_dir/c.v" and
rm "$work_dir/a.v" "$work_dir/b.v"
vips relational_const "$work_dir/s.v" "$work_dir/a.v" moreeq 97
vips boolean "$work_dir/c.v" "$work_dir/a.v" "$work_dir/b.v" and
rm "$work_dir/a.v" "$work_dir/c.v"
vips relational_const "$work_dir/v.v" "$work_dir/a.v" moreeq 71
vips boolean "$work_dir/b.v" "$work_dir/a.v" "$work_dir/grass-mask.v" and
rm "$work_dir/a.v" "$work_dir/b.v"

vips linear "$work_dir/h.v" "$work_dir/a.v" 0.35 35.1
vips ifthenelse "$work_dir/grass-mask.v" "$work_dir/a.v" "$work_dir/h.v" "$work_dir/h-final.v"
rm "$work_dir/a.v" "$work_dir/h.v"
vips linear "$work_dir/s.v" "$work_dir/a.v" 0.55 82.8
vips ifthenelse "$work_dir/grass-mask.v" "$work_dir/a.v" "$work_dir/s.v" "$work_dir/s-grass.v"
rm "$work_dir/a.v" "$work_dir/grass-mask.v" "$work_dir/s.v"

# Neutralize low-saturation, middle-value paving while retaining its shading.
vips relational_const "$work_dir/s-grass.v" "$work_dir/a.v" lesseq 41
vips relational_const "$work_dir/v.v" "$work_dir/b.v" moreeq 61
vips boolean "$work_dir/a.v" "$work_dir/b.v" "$work_dir/c.v" and
rm "$work_dir/a.v" "$work_dir/b.v"
vips relational_const "$work_dir/v.v" "$work_dir/a.v" lesseq 168
vips boolean "$work_dir/c.v" "$work_dir/a.v" "$work_dir/road-mask.v" and
rm "$work_dir/a.v" "$work_dir/c.v"
vips linear "$work_dir/s-grass.v" "$work_dir/a.v" 0.25 0
vips ifthenelse "$work_dir/road-mask.v" "$work_dir/a.v" "$work_dir/s-grass.v" "$work_dir/s-final.v"
rm "$work_dir/a.v" "$work_dir/road-mask.v" "$work_dir/s-grass.v"

vips bandjoin "$work_dir/h-final.v $work_dir/s-final.v $work_dir/v.v" "$work_dir/hsv-final.v"
rm "$work_dir/h-final.v" "$work_dir/s-final.v" "$work_dir/v.v"
vips copy "$work_dir/hsv-final.v" "$work_dir/hsv-typed.v" --interpretation hsv
rm "$work_dir/hsv-final.v"
vips colourspace "$work_dir/hsv-typed.v" "$destination_image[compression=1,strip=true]" srgb
