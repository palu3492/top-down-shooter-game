"""One playthrough: the world, and how it advances and draws.

`game_loop` used to hold all of this as fifty locals, which meant there was
nothing to construct and nothing to discard -- and so no way to start a game,
end one, or have none running while a menu is up.

The rules arrive as a collaborator. `WaveSystem` is the freeplay rules today;
a campaign replaces it without this file changing.

World state -- positions, health, cash, the wave count -- lives in plain
attributes that never hold a `Surface`, so writing a session to disk later is
additive rather than a rewrite.
"""

import math

import pygame

from shooter import config, items
from shooter.background import TiledBackground
from shooter.entities import powerups as powerup_kinds
from shooter.entities.player import Human
from shooter.entities.zombie import keep_apart
from shooter.entities.powerups import PowerUps
from shooter.entities.props import Harvestable
from shooter.entities.projectiles import LETHAL, Grenade, StunGrenade
from shooter.render import blit_group
from shooter.systems import loot, shop, world
from shooter.systems.waves import WaveSystem
from shooter.ui.hud import HUD, Cash, GrenadeData, HealthBar, WeaponPanel, prompt
from shooter.ui.radar import RadarScreen
from shooter.ui.shopfront import ShopFront
from shooter.weapons import RELOAD, SLOTS, equip, everything
from shooter.viewport import visible_world

INSTAKILL_SECONDS = config.INSTAKILL_SECONDS
INSTAKILL_TOP = 40
RELOADING_TOP = 100
BACKGROUND = "Backgrounds/grass_tile.png"

# Firing is the left button only. Any `MOUSEBUTTONDOWN` used to do it, so a
# right-click, a middle-click or either side button emptied the clip -- and `E`
# being the interaction means the other buttons have their own jobs coming.
LEFT_BUTTON = 1

# `1`-`5` pick a weapon, in the order the controls map lists them.
SLOT_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5)

# `E` uses whatever the player is standing next to. Not a mouse button, because
# the mouse is aiming; not `Tab`, because that is the backpack.
INTERACT = pygame.K_e

# What the player bumps into. Smaller than the sprite, and fixed rather than
# read from `human.rect`, which grows and shrinks as the player turns -- a
# hitbox that depends on where you are aiming is not a hitbox.
PLAYER_SOLID = (70, 70)

# Chopping the same tree twice tops up the pile already lying there rather than
# starting a second one. Ten wood is one thing to look at, not ten.
MERGE_WITHIN = 110

# How long "+4 WOOD" or "NO ROOM" stays on the screen, and how far above the
# player it sits -- fixed heights near the top are where the between-wave
# banner already is, and the two printed over each other.
NOTICE_SECONDS = 1.6
NOTICE_ABOVE = 120

# `0` fills the five slots with one of everything -- which is now a way past the
# gun stand as well as past the armoury. A cheat, so it is behind `DEV_TOOLS`
# and read live: turning the setting off puts the key back to doing nothing.
GRANT_ALL = pygame.K_0

# How a game can finish. `None` means it is still being played.
LOST, WON = "LOST", "WON"


def collect_powerup(kind, human, zombie_group, carried):
    """Apply a collected power-up. Returns instakill seconds to add, if any.

    Ammunition is restored to everything carried rather than to whatever
    happens to be in hand -- a pickup walked over with the knife out used to
    refill the knife, which is to say nothing at all.
    """
    if kind == powerup_kinds.NUKE:
        zombie_group.empty()
    elif kind == powerup_kinds.MAX_HEALTH:
        human.restore_health()
    elif kind == powerup_kinds.MAX_AMMO:
        for held in carried:
            held.refill()
    elif kind == powerup_kinds.INSTAKILL:
        return INSTAKILL_SECONDS
    return 0.0


def is_zombie_attacking(human, zombie, dt=config.SIM_DT):
    attacking = pygame.sprite.collide_rect(human, zombie)
    zombie.update_anim("ATTACK" if attacking else "MOVE", dt)
    if attacking and human.remove_health(config.ZOMBIE_DAMAGE * dt):
        human.kill()
    return attacking


def explosion_touching_zombie(zombie, explosion):
    if pygame.sprite.collide_rect(zombie, explosion) and zombie.remove_health(
        config.EXPLOSION_DAMAGE
    ):
        zombie.kill()


def stun_explosion_touching_zombie(zombie, explosion):
    if pygame.sprite.collide_rect(zombie, explosion):
        zombie.remove_speed(config.STUN_SPEED)


def centred_text(screen, window, message, top, size, colour=config.WHITE):
    """Measured and centred rather than nudged by a hand-tuned offset.

    `window[0] / 2 - 70` was only ever centred for one particular string at one
    particular font size.
    """
    text = pygame.font.Font(None, size).render(message, True, colour)
    screen.blit(text, (window[0] / 2.0 - text.get_width() / 2.0, top))


class Session:
    """A game in progress."""

    def __init__(self, window, rules=WaveSystem):
        self.window = window
        self.camera_x, self.camera_y = 0, 0
        self.previous_camera = (0, 0)
        self.instakill_seconds = 0.0
        # Sampled now rather than left at the origin: input is handled before
        # the loop first calls `aim_at`, so a click on the opening frame would
        # otherwise fire at atan2(0, 0) -- straight right, wherever the pointer.
        self.aim = (0, 0)
        self.aim_at(pygame.mouse.get_pos())

        self.change_x = self.change_y = 0
        self.shooting = False

        self.background = TiledBackground(BACKGROUND)
        self.human = Human(window)
        self.human_group = pygame.sprite.Group(self.human)
        self.zombies = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.grenades = pygame.sprite.Group()
        self.explosions = pygame.sprite.Group()
        self.stun_grenades = pygame.sprite.Group()
        self.stun_explosions = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group(PowerUps())

        self.cash = Cash()
        self.carried = [equip(which) for which in SLOTS]
        self.equipped = self.carried[0]
        self.shopping = False
        self.shop_says = None
        self.backpack = items.Backpack()
        self.dropped = pygame.sprite.Group()
        self.notice = None
        self.notice_seconds = 0.0
        self.grenade_data = GrenadeData()
        self.heads_up_display = HUD(window)
        self.health_display = HealthBar(window)
        self.weapon_display = WeaponPanel(window, self.grenade_data)
        self.shop_display = ShopFront(window)
        self.radar = RadarScreen()

        self.rules = rules(window, self.zombies, self.cash, self.visible)
        # After the rules, because what stands in a level is the level's to say.
        self.props = pygame.sprite.Group(*world.build(self.rules.layout))

    @property
    def outcome(self):
        """`None` while the game is still being played.

        Losing belongs to the session: a player at zero health is lost whatever
        mode is being played. Winning belongs to the rules, because what counts
        as finished is exactly what a mode decides -- endless freeplay never
        declares one.
        """
        if not self.human.alive():
            return LOST
        return self.rules.outcome

    @property
    def visible(self):
        return visible_world((self.camera_x, self.camera_y), self.window)

    @property
    def camera(self):
        return (self.camera_x, self.camera_y)

    def resize(self):
        """Take no window: there is only ever one.

        AT25 replaced twenty copies of the render size with a single shared
        `Viewport`, so the readouts, the health bar and every zombie already read the
        new size the moment it changes. Accepting a window here would imply
        there are copies to update and quietly leave most of them stale -- the
        player is the only thing holding a position derived from it.
        """
        self.human.recentre(self.window)

    def aim_at(self, pointer):
        """Sampled once per frame; the pointer does not move between steps."""
        self.aim = (
            int(pointer[0] - self.window[0] / 2),
            -int(pointer[1] - self.window[1] / 2),
        )

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT_BUTTON:
            self._shoot()
        elif event.type == pygame.KEYDOWN:
            self._key(event.key)

    @property
    def ammo_count(self):
        """Why the weapon in hand cannot be fired, or `None`.

        Read from the weapon rather than remembered here. Holding it on the
        session meant it described whichever weapon was equipped a moment ago,
        and changing weapon wiped it.
        """
        return self.equipped.status

    def _shoot(self):
        if self.shopping or not self.equipped.ready:
            return
        self.shooting = True
        self.bullets.add(self.equipped.attack(self._muzzle(), self.aim, self._damage()))
        self.equipped.fire()

    def _damage(self):
        return LETHAL if self.instakill_seconds > 0 else self.equipped.damage

    @property
    def nearby(self):
        """What the player is standing close enough to use, if anything."""
        here = self._muzzle()
        return next((prop for prop in self.props if prop.within(here)), None)

    def _key(self, key):
        if self.shopping:
            self._shop_key(key)
            return
        if key == INTERACT:
            self._interact()
            return
        if key == pygame.K_g and self.grenade_data.grenade_amount > 0:
            self.grenades.add(Grenade(*self._muzzle(), *self.aim))
            self.grenade_data.grenade_amount -= 1
        elif key == pygame.K_f and self.grenade_data.stun_grenade_amount > 0:
            self.stun_grenades.add(StunGrenade(*self._muzzle(), *self.aim))
            self.grenade_data.stun_grenade_amount -= 1
        elif key == pygame.K_r:
            self.equipped.manual_reload()
        elif key in SLOT_KEYS:
            self._equip(SLOT_KEYS.index(key))
        elif key == GRANT_ALL and config.DEV_TOOLS:
            self._grant_everything()

    def _grant_everything(self):
        """Every weapon there is, loaded, on the number keys.

        For trying the armoury without playing to it. What does not fit in the
        slots is left out rather than made unreachable -- five keys is five
        weapons, and which five is a choice AT41 gives the player properly.
        """
        self.carried = everything()[: len(SLOT_KEYS)]
        self.equipped = self.carried[0]

    def _equip(self, slot):
        """Hold something else.

        Nothing is reset. A gun put away mid-reload goes on reloading and is
        still locked when it comes back -- clearing that here let the player
        cancel every reload, and fire an empty gun, with two keystrokes.
        """
        if slot >= len(self.carried):
            return
        self.equipped = self.carried[slot]

    def _interact(self):
        """Use what is at hand: a stand sells, a tree is chopped."""
        thing = self.nearby
        if thing is None:
            return
        if isinstance(thing, Harvestable):
            self._chop(thing)
            return
        self.shopping = True
        self.shop_says = None

    def _chop(self, thing):
        won = thing.harvest(self.equipped.damage, self.equipped)
        if won:
            self._spill(thing.yields.item, won, thing.middle)

    def _spill(self, item, count, at):
        """Drop this here, or add it to what is already lying here."""
        for pile in self.dropped:
            if pile.item is item and math.dist(pile.middle, at) <= MERGE_WITHIN:
                pile.count += count
                return
        self.dropped.add(world.spilled(item, count, at))

    def _drop_loot(self, standing):
        """Leave behind what the fallen were carrying.

        Only what was actually killed. A nuke empties the group without
        anything being cut down, and the field should not be carpeted for it.
        """
        for zombie in standing - set(self.zombies):
            if not zombie.killed:
                continue
            for item, count in loot.spoils(zombie.kind):
                self._spill(item, count, zombie.get_position())

    def _gather(self):
        """Take what is underfoot, as far as there is room for it.

        A pile the pack cannot take is left exactly as it was and said out
        loud: walking over wood and seeing nothing happen reads as a bug rather
        than as a full backpack.
        """
        here = self._muzzle()
        for pile in list(self.dropped):
            if not pile.within(here):
                continue
            item = pile.item
            taken = pile.take(self.backpack)
            self.say(f"+{taken} {item.name.upper()}" if taken else "NO ROOM")

    def say(self, message):
        self.notice = message
        self.notice_seconds = NOTICE_SECONDS

    def _shop_key(self, key):
        """While the stand is open the number keys buy rather than equip.

        The panel is showing exactly those numbers against exactly those guns,
        so there is nothing to remember -- and firing and reloading are off,
        because both hands are busy.
        """
        if key == INTERACT:
            self.shopping = False
            return
        if key in SLOT_KEYS:
            line = SLOT_KEYS.index(key)
            if line < len(shop.STOCK):
                self.shop_says = shop.buy(shop.STOCK[line], self.cash, self.carried)

    def _muzzle(self):
        return (
            (self.window[0] / 2.0) - self.camera_x,
            (self.window[1] / 2.0) - self.camera_y,
        )

    # ------------------------------------------------------------------
    # Simulation: one fixed step.
    # ------------------------------------------------------------------

    def step(self, pressed, dt=config.SIM_DT, trigger=False):
        if self.human.alive():
            self._walk(pressed, dt)

        self.previous_camera = self.camera
        self._advance_camera()

        for held in self.carried:
            held.tick(dt)

        self._gather()
        if self.notice_seconds > 0:
            self.notice_seconds = max(0.0, self.notice_seconds - dt)
            if not self.notice_seconds:
                self.notice = None

        # Walking away closes the stand. Nothing else would, and a shop that
        # follows the player across the map is not a place.
        if self.shopping and self.nearby is None:
            self.shopping = False

        # Holding the button keeps an automatic weapon firing. Everything else
        # is one pull per shot, and its rate is what stops the clicking.
        if trigger and self.equipped.automatic:
            self._shoot()

        self._animate_player(dt)
        # Who was standing before anything could cut them down. Loot is worked
        # out from who is missing afterwards rather than at the moment of
        # death, which happens inside a bullet, a swing and an explosion --
        # three places with no business knowing what a pickup is.
        standing = set(self.zombies)
        self._advance_zombies(dt)
        self._collect_powerups(dt)

        self.bullets.update(self.camera_x, self.camera_y, self.zombies, dt)
        self.grenades.update(self.camera_x, self.camera_y, self.explosions, dt)
        self.explosions.update(self.camera_x, self.camera_y, dt)
        self.stun_grenades.update(
            self.camera_x, self.camera_y, self.stun_explosions, dt
        )
        self.stun_explosions.update(self.camera_x, self.camera_y, dt)

        self._drop_loot(standing)

        if not self.zombies:
            self.rules.advance(self.window, self.zombies, self.cash, dt, self.visible)

        self.instakill_seconds = max(0.0, self.instakill_seconds - dt)
        self.change_x = self.change_y = 0
        self.shooting = False

    def _advance_camera(self):
        """Move, unless something is in the way.

        One axis at a time, so walking into a tree at an angle slides along it
        rather than stopping dead. Anything already overlapping is let through
        in either direction -- a player who somehow ends up inside a footprint
        should be able to walk out of it rather than be held there.
        """
        stuck = self._blocked(self.camera_x, self.camera_y)

        wanted = self._on_the_map(self.camera_x + self.change_x, 0)
        if stuck or not self._blocked(wanted, self.camera_y):
            self.camera_x = wanted

        wanted = self._on_the_map(self.camera_y + self.change_y, 1)
        if stuck or not self._blocked(self.camera_x, wanted):
            self.camera_y = wanted

    def _on_the_map(self, camera, axis):
        return min(0, max(-(config.WORLD[axis] - self.window[axis]), camera))

    def _standing_at(self, camera_x, camera_y):
        box = pygame.Rect(0, 0, *PLAYER_SOLID)
        box.center = (
            self.window[0] / 2 - camera_x,
            self.window[1] / 2 - camera_y,
        )
        return box

    def _blocked(self, camera_x, camera_y):
        here = self._standing_at(camera_x, camera_y)
        return any(
            prop.footprint is not None and prop.footprint.colliderect(here)
            for prop in self.props
        )

    def _walk(self, pressed, dt):
        if pressed[pygame.K_w]:
            self.change_y = config.PLAYER_SPEED * dt
        elif pressed[pygame.K_s]:
            self.change_y = -config.PLAYER_SPEED * dt
        if pressed[pygame.K_a]:
            self.change_x = config.PLAYER_SPEED * dt
        elif pressed[pygame.K_d]:
            self.change_x = -config.PLAYER_SPEED * dt

    def _animate_player(self, dt):
        # Preserves the original rule, quirks included: MOVE only when both
        # axes are positive, otherwise IDLE, and SHOOT overrides either.
        animation = "MOVE"
        if self.change_x <= 0 or self.change_y <= 0:
            animation = "IDLE"
        if self.shooting:
            animation = "SHOOT"
        self.human.update_anim(animation, dt, self.equipped.weapon.id)
        # Rotation resizes human.rect, which collision reads, so it has to
        # happen exactly once per step -- in the render pass it compounded with
        # frame rate and inflated the hitbox.
        self.human.rot_center(math.degrees(math.atan2(self.aim[1], self.aim[0])))

    def _advance_zombies(self, dt):
        for zombie in self.zombies:
            attacking = is_zombie_attacking(self.human, zombie, dt)
            if attacking:
                zombie.face_player()
            else:
                zombie.move_toward_center(self.camera_x, self.camera_y, dt)
            for explosion in self.explosions:
                explosion_touching_zombie(zombie, explosion)
            for stun_explosion in self.stun_explosions:
                stun_explosion_touching_zombie(zombie, stun_explosion)
            zombie.zombie_speed_timer(dt)

        keep_apart(self.zombies, self.camera, dt)

    def _collect_powerups(self, dt):
        for powerup in self.powerups:
            collected = powerup.update(self.human, self.camera_x, self.camera_y, dt)
            if collected is None:
                continue
            if collected != powerup_kinds.EXPIRED:
                self.instakill_seconds += collect_powerup(
                    collected, self.human, self.zombies, self.carried
                )
            powerup.kill()

    # ------------------------------------------------------------------
    # Render: once per frame, between steps.
    # ------------------------------------------------------------------

    def draw(self, screen, alpha):
        draw_x, draw_y = self._interpolated_camera(alpha)

        self.background.draw(screen, -draw_x, -draw_y)

        blit_group(screen, self.dropped, draw_x, draw_y, alpha)
        blit_group(screen, self.props, draw_x, draw_y, alpha)
        for prop in self.props:
            if isinstance(prop, Harvestable) and prop.left < 1:
                prop.health_bar(screen, prop.draw_position(draw_x, draw_y, alpha))
        blit_group(screen, self.powerups, draw_x, draw_y, alpha)
        for zombie in self.zombies:
            zombie.health_bar(screen, zombie.draw_position(draw_x, draw_y, alpha))
        blit_group(screen, self.zombies, draw_x, draw_y, alpha)
        self.human_group.draw(screen)
        blit_group(screen, self.bullets, draw_x, draw_y, alpha)

        if not self.zombies:
            self.rules.draw(screen, self.window)

        for group in (
            self.grenades,
            self.explosions,
            self.stun_grenades,
            self.stun_explosions,
        ):
            blit_group(screen, group, draw_x, draw_y, alpha)

        self._draw_overlays(screen)

    def _interpolated_camera(self, alpha):
        return (
            self.previous_camera[0] + (self.camera_x - self.previous_camera[0]) * alpha,
            self.previous_camera[1] + (self.camera_y - self.previous_camera[1]) * alpha,
        )

    def _draw_overlays(self, screen):
        self.radar.draw(
            screen,
            -self.camera_x + self.window[0] / 2,
            -self.camera_y + self.window[1] / 2,
        )
        for zombie in self.zombies:
            self.radar.update_zom(screen, zombie)

        if self.instakill_seconds > 0:
            centred_text(
                screen,
                self.window,
                f"INSTAKILL {int(self.instakill_seconds) + 1}s",
                INSTAKILL_TOP,
                size=34,
                colour=config.INSTAKILL_TEXT,
            )

        self.heads_up_display.update(screen, self.window)
        self.health_display.draw(screen, self.human.get_health())
        self.weapon_display.draw(screen, self.equipped)
        self.cash.update(screen, self.window)

        if self.ammo_count == RELOAD:
            centred_text(screen, self.window, "Reloading", RELOADING_TOP, size=30)

        if self.notice:
            centred_text(
                screen,
                self.window,
                self.notice,
                self.window[1] / 2 - NOTICE_ABOVE,
                size=30,
            )

        if self.shopping:
            self.shop_display.draw(screen, self.cash, self.carried, self.shop_says)
        elif self.nearby is not None:
            prompt(screen, self.window, self.nearby.label)
