CREATE TABLE IF NOT EXISTS public.flower_basket_history (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tile_id integer NOT NULL UNIQUE REFERENCES public.tiles(id),
    spawned_at timestamp without time zone NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.flower_basket_history IS 'Tracks every flower basket tile spawned so basket tiles are never reused.';
COMMENT ON COLUMN public.flower_basket_history.tile_id IS 'Tile id used for a flower basket spawn (unique, no duplicates).';
COMMENT ON COLUMN public.flower_basket_history.spawned_at IS 'Timestamp when this flower basket tile was spawned.';
