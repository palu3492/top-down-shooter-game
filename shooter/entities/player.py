import pygame

from shooter.assets import load_animation

from shooter import config

KNIFE_ATTACK_FPS = 12
IDLE_ANIMATION_FPS = 30

ANIMATIONS = {
    "knife": {
        "IDLE": ("Player Animations/Idle Knife", "survivor-idle_knife_", 20),
        "MOVE": ("Player Animations/Move Knife", "survivor-move_knife_", 20),
        "SHOOT": ("Player Animations/Attack Knife", "survivor-attack_knife_", 5),
    },
    **{
        weapon: {
            "IDLE": (
                f"Player Animations/{weapon.upper()}/IDLE",
                f"survivor-idle_{weapon}_",
                20,
            ),
            "MOVE": (
                f"Player Animations/{weapon.upper()}/MOVE",
                f"survivor-move_{weapon}_",
                20,
            ),
            "SHOOT": (
                f"Player Animations/{weapon.upper()}/SHOOT",
                f"survivor-shoot_{weapon}_",
                3,
            ),
        }
        for weapon in ("m16", "smg", "shotgun", "sniper")
    },
}


class Human(pygame.sprite.Sprite):
    def __init__(self, window_size):
        pygame.sprite.Sprite.__init__(self)
        self.type = "IDLE"
        self.current_idle = 0
        self.current_move = 0
        self.current_shoot = 0
        self.attack_frames_remaining = 0
        self.health = config.PLAYER_HEALTH
        self.animation_clock = 0.0
        self.frame = 0
        self.animation_sets = {
            weapon: {
                name: load_animation(
                    directory, prefix, count, config.PLAYER_SCALE, True
                )
                for name, (directory, prefix, count) in animations.items()
            }
            for weapon, animations in ANIMATIONS.items()
        }
        self.weapon_id = "knife"
        self.frames = self.animation_sets[self.weapon_id]
        self.image = self.frames["IDLE"][0]
        self.rect = self.image.get_rect()
        self.recentre(window_size)

    def recentre(self, window_size):
        """The player is always drawn at the middle of the screen, so a change
        of resolution moves them rather than leaving them off to one side."""
        self.rect.x = (window_size[0] / 2.0) - (self.rect.size[0] / 2.0)
        self.rect.y = (window_size[1] / 2.0) - (self.rect.size[1] / 2.0)

    def rot_center(self, angle):
        """Rotate the current frame about its centre."""
        centre = self.rect.center
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect(center=centre)

    def update_anim(self, type, dt=1 / config.ANIMATION_FPS, weapon_id=None):
        if weapon_id is not None and weapon_id != self.weapon_id:
            self.weapon_id = weapon_id
            self.frames = self.animation_sets[weapon_id]
            self.attack_frames_remaining = 0
        if type == "SHOOT" and self.attack_frames_remaining == 0:
            self.current_shoot = 0
            self.frame = 0
            self.animation_clock = 0.0
            self.attack_frames_remaining = len(self.frames["SHOOT"]) - 1
        self.type = "SHOOT" if self.attack_frames_remaining else type
        animation_fps = (
            KNIFE_ATTACK_FPS
            if self.type == "SHOOT" and self.weapon_id == "knife"
            else IDLE_ANIMATION_FPS
            if self.type == "IDLE"
            else config.ANIMATION_FPS
        )
        self.animation_clock += dt * animation_fps
        steps, self.animation_clock = divmod(self.animation_clock, 1)
        for _ in range(int(steps)):
            self._advance()
        self.image = self.frames[self.type][self.frame]
        self.health_regen(dt)

    def _advance(self):
        type = self.type
        frame = 0
        if self.type == "IDLE":
            if self.current_idle < 19:
                self.current_idle += 1
            else:
                self.current_idle = 0
            frame = self.current_idle
        elif type == "MOVE":
            if self.current_move < 19:
                self.current_move += 1
            else:
                self.current_move = 0
            frame = self.current_move
        elif type == "SHOOT":
            self.current_shoot = min(
                self.current_shoot + 1, len(self.frames["SHOOT"]) - 1
            )
            self.attack_frames_remaining = max(0, self.attack_frames_remaining - 1)
            frame = self.current_shoot

        self.frame = frame

    def remove_health(self, damage):
        self.health -= damage
        return self.health <= 0

    def add_health(self, repair):
        self.health += repair

    def restore_health(self):
        self.health = config.PLAYER_HEALTH

    def get_health(self):
        if self.health > 0:
            return int(self.health)
        else:
            return 0

    def health_regen(self, dt=config.SIM_DT):
        if self.health < config.PLAYER_HEALTH:
            self.health = min(
                config.PLAYER_HEALTH, self.health + config.PLAYER_REGEN * dt
            )
