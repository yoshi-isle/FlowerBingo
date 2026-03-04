-- Migration: reroll tracking + player display names
-- Run once against your database

-- Track which discord user triggered a reroll (tile skip)
ALTER TABLE public.tile_assignments
    ADD COLUMN IF NOT EXISTS rerolled_by_discord_id TEXT;

-- Cache the player's Discord display name so Analytics can show it
ALTER TABLE public.players
    ADD COLUMN IF NOT EXISTS display_name TEXT;
