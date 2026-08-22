"""Presentation camera derived from authoritative spatial state."""


class FollowCamera:
    def __init__(self, viewport, world_size, spatial, target_id):
        self.viewport = tuple(viewport)
        self.world_size = tuple(world_size)
        self.spatial = spatial
        self.target_id = target_id
        self.offset = (0.0, 0.0)
        self.sync()

    def follow(self, target_id):
        self.target_id = target_id
        return self.sync()

    def resize(self, viewport):
        self.viewport = tuple(viewport)
        return self.sync()

    def sync(self):
        target = self.spatial.get(self.target_id).transform
        desired = (
            self.viewport[0] / 2 - target.x,
            self.viewport[1] / 2 - target.y,
        )
        self.offset = tuple(
            min(0.0, max(-(world - view), wanted))
            for wanted, world, view in zip(
                desired, self.world_size, self.viewport, strict=True
            )
        )
        return self.offset
