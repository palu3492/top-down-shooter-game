from pytmx import TiledMap

tmx = TiledMap("/Users/alexpalumbo/Documents/projects/test_map/test_map_1.tmx")

collision_layer = tmx.get_layer_by_name("Collision")

for obj in collision_layer:
    print(
        f"x={obj.x}, "
        f"y={obj.y}, "
        f"width={obj.width}, "
        f"height={obj.height}"
    )
