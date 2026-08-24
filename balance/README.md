# Survival playtest tuning

Edit `survival.toml`, save it, then start a fresh Survival match. The profile is
the source of truth for that new run.

- `player_speed`, enemy speed, health, and contact damage control movement and
  pressure.
- `pistol_*`, `smg_*`, and `tool_*` control purchased-gun and starting-tool feel.
- `*_wave_*`, spawn burst settings, preparation timers, and `kill_reward`
  control the first-five-wave pacing and economy.
- Starting ammo and health regeneration control recovery pressure.

Station prices and offers remain authored in the selected map's TMX interaction
objects, since they are map content rather than global Survival rules.
