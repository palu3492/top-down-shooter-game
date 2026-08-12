import math
import random

import pygame

from shooter import config
from shooter.assets import load_animation, load_sized
from shooter.render import Interpolated

ANIMATIONS = {
    "IDLE": ("Zombie Animations/zombie_idle", "skeleton-idle_", 17),
    "MOVE": ("Zombie Animations/zombie_move", "skeleton-move_", 17),
    "ATTACK": ("Zombie Animations/zombie_attack", "skeleton-attack_", 9),
}


# A crowd all moving at exactly one speed reads as a single object. Each
# zombie gets its own pace, so a wave arrives strung out rather than in rank.
PACE_SPREAD = 0.18

# How close two of them get before they start pushing each other away, and how
# hard, as a fraction of walking speed. Enough to stop them stacking into one
# sprite without turning the crowd into a pinball table.
PERSONAL_SPACE = 76
SHOVE = 1.8


def keep_apart(zombies, camera, dt=config.SIM_DT):
    """Push overlapping zombies off each other.

    Every push is worked out before anything moves, so the result does not
    depend on the order the group happens to iterate in -- which is what keeps
    a wave identical at any frame rate.
    """
    crowd = list(zombies)
    pushes = [[0.0, 0.0] for _ in crowd]

    for index, one in enumerate(crowd):
        for other_index in range(index + 1, len(crowd)):
            other = crowd[other_index]
            away_x = one.zombie_x - other.zombie_x
            away_y = one.zombie_y - other.zombie_y
            gap = math.hypot(away_x, away_y)
            if gap >= PERSONAL_SPACE:
                continue
            if gap == 0:
                # Exactly stacked. Any fixed direction will do; without one
                # they would sit inside each other for ever.
                away_x, away_y, gap = 1.0, 0.0, 1.0
            crowding = (PERSONAL_SPACE - gap) / PERSONAL_SPACE
            unit_x, unit_y = away_x / gap, away_y / gap

            # Each is shoved at its own pace rather than the crowd's, so a
            # stunned zombie stays sluggish while it is pushed out of a pile
            # instead of being flung across the field at full walking speed.
            for slot, direction, zombie in (
                (index, 1, one),
                (other_index, -1, other),
            ):
                shove = crowding * SHOVE * zombie.zombie_speed * dt * direction
                pushes[slot][0] += unit_x * shove
                pushes[slot][1] += unit_y * shove

    for zombie, (push_x, push_y) in zip(crowd, pushes, strict=True):
        if push_x or push_y:
            zombie.zombie_x += push_x
            zombie.zombie_y += push_y
            zombie.move_position(*camera)


def spawn_margin(walking_speed=None):
    """How far outside the view a wave starts, for a zombie walking this fast.

    Measured as the distance covered in `SPAWN_LEAD_SECONDS`, so the player
    gets the same warning rather than the same number of pixels. That only
    holds if it is *this* zombie's speed: since AT36 they each walk at their
    own pace, and using the shared one gave the quickest of them a fifth less
    warning than the setting claims.

    Read when a zombie spawns rather than bound at import, because ZOMBIE_SPEED
    is a setting and a value copied once would ignore it.
    """
    if walking_speed is None:
        walking_speed = config.ZOMBIE_SPEED
    return max(walking_speed * config.SPAWN_LEAD_SECONDS, max(config.ZOMBIE_SIZE))


class Zombie(Interpolated, pygame.sprite.Sprite):
    def __init__(self, window_size, cash, visible=None):
        self.player_cash = cash
        pygame.sprite.Sprite.__init__(self)
        self.zombie_x = self.zombie_y = 0
        self.type = "MOVE"
        self.current_idle = self.current_move = self.current_attack = 0
        self.pace = random.uniform(1 - PACE_SPREAD, 1 + PACE_SPREAD)
        self.zombie_speed = self.walking_speed
        self.stun_seconds = 0.0
        self.animation_clock = 0.0
        self.zombie_health = config.ZOMBIE_HEALTH
        self.window_size = window_size
        self.frames = {
            name: load_animation(directory, prefix, count, config.ZOMBIE_SCALE, True)
            for name, (directory, prefix, count) in ANIMATIONS.items()
        }
        self.upright = load_sized(
            "Zombie Animations/zombie_idle/skeleton-idle_0.png",
            *config.ZOMBIE_SIZE,
            True,
        )
        self.image = self.upright
        self.rect = self.image.get_rect()
        self.spawn_zombie(visible)
        self.remember_position()

    # Spawns zombies out side of screen size
    def spawn_zombie(self, visible=None):
        """On a ring just outside what the player can see.

        The ring used to be anchored at the world origin, so a player standing
        at the far side of a 5000x5000 world got waves that started thousands of
        pixels away and difficulty that depended on where they were standing.
        """
        area = self.spawn_area(visible)
        margin = spawn_margin(self.walking_speed)
        side = random.randint(1, 4)
        if side == 1:
            self.set_position(random.randint(area.left, area.right), area.top - margin)
        elif side == 2:
            self.set_position(
                random.randint(area.left, area.right), area.bottom + margin
            )
        elif side == 3:
            self.set_position(area.left - margin, random.randint(area.top, area.bottom))
        else:
            self.set_position(
                area.right + margin, random.randint(area.top, area.bottom)
            )

    def spawn_area(self, visible):
        """Without a camera the visible world is the window at the origin, which
        is where it genuinely is before anyone has moved."""
        if visible is not None:
            return pygame.Rect(visible)
        return pygame.Rect(0, 0, self.window_size[0], self.window_size[1])

    def update_anim(self, type, dt=1 / config.ANIMATION_FPS):
        if type != "Null":
            self.type = type

        self.animation_clock += dt * config.ANIMATION_FPS
        steps, self.animation_clock = divmod(self.animation_clock, 1)
        for _ in range(int(steps)):
            self._advance()
        self._show()

    def _advance(self):

        if self.type == "IDLE":
            if self.current_idle < 16:
                self.current_idle += 1
            else:
                self.current_idle = 0
        elif self.type == "MOVE":
            if self.current_move < 16:
                self.current_move += 1
            else:
                self.current_move = 0
        elif self.type == "ATTACK":
            if self.current_attack < 8:
                self.current_attack += 1
            else:
                self.current_attack = 0

    def _show(self):
        frame = {
            "IDLE": self.current_idle,
            "MOVE": self.current_move,
            "ATTACK": self.current_attack,
        }[self.type]
        self.upright = self.frames[self.type][frame]
        self.image = self.upright
        self.rect = self.upright.get_rect(topleft=self.rect.topleft)

    @property
    def world_x(self):
        return self.zombie_x

    @property
    def world_y(self):
        return self.zombie_y

    def get_position(self):
        return (self.zombie_x, self.zombie_y)

    def set_position(self, x, y):
        self.zombie_y = y
        self.zombie_x = x

    def move_y(self, y):
        self.rect.y += y

    def move_x(self, x):
        self.rect.x += x

    def reset_position(self, visible=None):
        self.spawn_zombie(visible)

    def move_position(self, camera_x, camera_y):
        self.rect.x = self.zombie_x + camera_x
        self.rect.y = self.zombie_y + camera_y

    def move_toward_center(self, camera_x, camera_y, dt=config.SIM_DT):
        self.remember_position()
        zombie_pos = self.rect.x, self.rect.y
        distance_from_center_x = (self.window_size[0] / 2.0) - zombie_pos[0] - 120
        distance_from_center_y = (self.window_size[1] / 2.0) - zombie_pos[1] - 110
        angle = math.atan2(
            distance_from_center_x, distance_from_center_y
        )  # find angle of zombie toward center
        move_x_amount = self.zombie_speed * math.sin(angle) * dt
        move_y_amount = self.zombie_speed * math.cos(angle) * dt
        self.zombie_x += move_x_amount
        self.zombie_y += move_y_amount
        self.move_position(camera_x, camera_y)
        self.face_player()

    def face_player(self):
        """Turn to look at whoever is being chased.

        Always applied to `self.upright` -- the frame the animation chose --
        never to whatever is currently being drawn. Rotating an already rotated
        sprite lands it on a bigger surface every time, and a caller that turns
        without animating would grow it without bound.
        """
        towards_x = self.window_size[0] / 2 - self.rect.centerx
        towards_y = self.window_size[1] / 2 - self.rect.centery
        if not (towards_x or towards_y):
            return

        upright = self.upright
        turned = pygame.transform.rotate(
            upright, math.degrees(math.atan2(-towards_y, towards_x))
        )
        # `rect` is deliberately left alone. A rotated sprite needs a bigger
        # surface, and letting the footprint grow with it would mean a zombie
        # coming at forty-five degrees reached the player before one walking
        # straight in -- the hitbox goes from 144x155 to 201x205 on the turn.
        self.image = turned
        self.image_offset = (
            (upright.get_width() - turned.get_width()) / 2,
            (upright.get_height() - turned.get_height()) / 2,
        )

    def health_bar(self, screen, at=None):
        x, y = at if at else self.rect.topleft
        pygame.draw.rect(
            screen,
            config.HEALTH_RED,
            (x + 75, y, self.zombie_health * 1.2, 22),
        )
        pygame.draw.rect(
            screen,
            config.HEALTH_GREY,
            (x + 75, y, 100 * 1.2, 22),
            4,
        )

    def remove_health(self, damage):
        if self.zombie_health <= 0:
            return False
        self.zombie_health -= damage
        if self.zombie_health <= 0:
            self.player_cash.increase_cash(config.KILL_REWARD)
            return True
        return False

    def add_health(self, repair):
        self.zombie_health += repair

    def remove_speed(self, stun_amount):
        self.zombie_speed = stun_amount
        self.stun_seconds = config.STUN_SECONDS

    @property
    def walking_speed(self):
        """This one's own pace, not the crowd's."""
        return config.ZOMBIE_SPEED * self.pace

    def zombie_speed_timer(self, dt=config.SIM_DT):
        if self.stun_seconds > 0:
            self.stun_seconds -= dt
        else:
            self.zombie_speed = self.walking_speed
