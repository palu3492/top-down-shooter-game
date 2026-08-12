"""Drawing entities between simulation steps.

`rect` is simulation state: collision reads it, and AT16 showed what happens
when rendering mutates it. So nothing here writes to `rect` — entities expose
where they should be *drawn* and the blit happens at that position instead.
"""


def lerp(previous, current, alpha):
    return previous + (current - previous) * alpha


class Interpolated:
    """World-positioned sprite that remembers where it was last step."""

    def remember_position(self):
        self.prev_x, self.prev_y = self.world_x, self.world_y

    def draw_position(self, camera_x, camera_y, alpha):
        return (
            lerp(self.prev_x, self.world_x, alpha) + camera_x,
            lerp(self.prev_y, self.world_y, alpha) + camera_y,
        )


def blit_group(screen, group, camera_x, camera_y, alpha):
    for sprite in group:
        screen.blit(sprite.image, sprite.draw_position(camera_x, camera_y, alpha))
