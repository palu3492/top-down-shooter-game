from shooter.assets import load_image


class TiledBackground:
    """Repeat one seamless texture beneath an arbitrarily large world.

    Tile placement is derived from world coordinates, not remembered between
    frames. The texture therefore stays fixed to the ground as the camera moves,
    including when the camera crosses zero or jumps by more than one tile.
    """

    def __init__(self, relative):
        self.tile = load_image(relative)

    def draw(self, screen, world_left, world_top):
        """Cover `screen`, starting at this world-space top-left coordinate."""
        tile_width, tile_height = self.tile.get_size()
        start_x = -(int(world_left) % tile_width)
        start_y = -(int(world_top) % tile_height)

        for top in range(start_y, screen.get_height(), tile_height):
            for left in range(start_x, screen.get_width(), tile_width):
                screen.blit(self.tile, (left, top))
