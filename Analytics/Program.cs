using Npgsql;

var builder = WebApplication.CreateBuilder(args);

// ── Connection string resolution ────────────────────────────────────────────
// Priority:
//   1. ConnectionStrings:Postgres in appsettings.json
//   2. DATABASE_URL  (postgres://user:pass@host:port/db)
//   3. Individual POSTGRES_HOST / _PORT / _DB / _USER / _PASSWORD env vars

static string BuildConnectionString(IConfiguration config)
{
    var cs = config.GetConnectionString("Postgres");
    if (!string.IsNullOrWhiteSpace(cs)) return cs;

    var dbUrl = Environment.GetEnvironmentVariable("DATABASE_URL");
    if (!string.IsNullOrWhiteSpace(dbUrl))
    {
        // Convert postgres:// URL → Npgsql connection string
        var uri = new Uri(dbUrl);
        var userInfo = uri.UserInfo.Split(':');
        return $"Host={uri.Host};Port={uri.Port};Database={uri.AbsolutePath.TrimStart('/')};" +
               $"Username={userInfo[0]};Password={Uri.UnescapeDataString(userInfo.Length > 1 ? userInfo[1] : "")};SSL Mode=Prefer;Trust Server Certificate=true";
    }

    var host     = Environment.GetEnvironmentVariable("POSTGRES_HOST")     ?? "localhost";
    var port     = Environment.GetEnvironmentVariable("POSTGRES_PORT")     ?? "5432";
    var db       = Environment.GetEnvironmentVariable("POSTGRES_DB")       ?? "flowerbingo";
    var user     = Environment.GetEnvironmentVariable("POSTGRES_USER")     ?? "postgres";
    var password = Environment.GetEnvironmentVariable("POSTGRES_PASSWORD") ?? "";
    return $"Host={host};Port={port};Database={db};Username={user};Password={password};SSL Mode=Prefer;Trust Server Certificate=true";
}

var connectionString = BuildConnectionString(builder.Configuration);
builder.Services.AddSingleton(_ => NpgsqlDataSource.Create(connectionString));

builder.Services.AddOpenApi();
builder.Services.AddCors(o => o.AddDefaultPolicy(p => p.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));

var app = builder.Build();

if (app.Environment.IsDevelopment())
    app.MapOpenApi();

// ── Global JSON error handler ─────────────────────────────────────────────
app.UseExceptionHandler(errApp => errApp.Run(async ctx =>
{
    ctx.Response.StatusCode  = 500;
    ctx.Response.ContentType = "application/json";
    var feature = ctx.Features.Get<Microsoft.AspNetCore.Diagnostics.IExceptionHandlerFeature>();
    var msg = feature?.Error?.Message ?? "Unknown error";
    await ctx.Response.WriteAsJsonAsync(new { error = msg });
}));

app.UseCors();
app.UseDefaultFiles();
app.UseStaticFiles();

// ── Category helpers ─────────────────────────────────────────────────────────
static string CategoryName(int cat) => cat switch
{
    1 => "Wildflower",
    2 => "Rose",
    3 => "Tulip",
    4 => "Orchid",
    5 => "Flower Basket",
    _ => "Unknown"
};

static string CategoryEmoji(int cat) => cat switch
{
    1 => "🌼",
    2 => "🌹",
    3 => "🌷",
    4 => "🌸",
    5 => "🧺",
    _ => "❓"
};

// ── GET /api/leaderboard ─────────────────────────────────────────────────────
app.MapGet("/api/leaderboard", async (NpgsqlDataSource db) =>
{
    try
    {
    await using var conn = await db.OpenConnectionAsync();

    // Fetch point config
    var pointConfig = new Dictionary<string, int>
    {
        ["easy_points"]   = 0,
        ["medium_points"] = 0,
        ["hard_points"]   = 0,
        ["elite_points"]  = 0,
    };

    await using (var cmd = conn.CreateCommand())
    {
        cmd.CommandText = "SELECT name, amount FROM public.global_configs WHERE name = ANY(@names)";
        cmd.Parameters.AddWithValue("names", new[] { "easy_points", "medium_points", "hard_points", "elite_points" });
        await using var reader = await cmd.ExecuteReaderAsync();
        while (await reader.ReadAsync())
        {
            var name = reader.GetString(0);
            // amount may be stored as integer or text depending on the schema
            var raw = reader.GetValue(1);
            if (raw != null && int.TryParse(raw.ToString(), out var v))
                pointConfig[name] = v;
        }
    }

    int easy   = pointConfig["easy_points"];
    int medium = pointConfig["medium_points"];
    int hard   = pointConfig["hard_points"];
    int elite  = pointConfig["elite_points"];

    var rows = new List<object>();
    await using (var cmd = conn.CreateCommand())
    {
        cmd.CommandText = $"""
            SELECT
                t.id                                        AS team_id,
                t.team_name,
                COALESCE(SUM(
                    CASE
                        WHEN ta.is_active = false
                             AND COALESCE(ta.was_skipped, false) = false
                        THEN CASE ta.category
                            WHEN 1 THEN {easy}  * CASE WHEN COALESCE(ta.catchup, false) = true THEN 1.5 ELSE 1 END
                            WHEN 2 THEN {medium} * CASE WHEN COALESCE(ta.catchup, false) = true THEN 1.5 ELSE 1 END
                            WHEN 3 THEN {hard}  * CASE WHEN COALESCE(ta.catchup, false) = true THEN 1.5 ELSE 1 END
                            WHEN 4 THEN {elite} * CASE WHEN COALESCE(ta.catchup, false) = true THEN 1.5 ELSE 1 END
                            WHEN 5 THEN 1337
                            ELSE 0
                        END
                        ELSE 0
                    END
                ), 0)                                       AS points,
                COUNT(*) FILTER (
                    WHERE ta.is_active = false AND COALESCE(ta.was_skipped, false) = false
                )                                           AS completed_tiles,
                COUNT(*) FILTER (
                    WHERE ta.is_active = false AND COALESCE(ta.was_skipped, false) = true
                )                                           AS skipped_tiles,
                COUNT(*) FILTER (WHERE ta.is_active = true) AS active_tiles,
                COUNT(*) FILTER (
                    WHERE ta.is_active = false AND ta.catchup = true
                )                                           AS catchup_tiles
            FROM public.teams t
            LEFT JOIN public.tile_assignments ta ON ta.team_id = t.id
            GROUP BY t.id, t.team_name
            ORDER BY points DESC, t.team_name ASC
            """;

        await using var reader = await cmd.ExecuteReaderAsync();
        int rank = 0;
        double? prevPoints = null;
        int displayRank = 0;
        while (await reader.ReadAsync())
        {
            double pts = reader.GetDouble(reader.GetOrdinal("points"));
            if (pts != prevPoints) { rank++; displayRank = rank; }
            prevPoints = pts;

            rows.Add(new
            {
                team_id        = reader.GetInt32(reader.GetOrdinal("team_id")),
                team_name      = reader.GetString(reader.GetOrdinal("team_name")),
                points         = (int)pts,
                rank           = displayRank,
                completed_tiles = reader.GetInt64(reader.GetOrdinal("completed_tiles")),
                skipped_tiles  = reader.GetInt64(reader.GetOrdinal("skipped_tiles")),
                active_tiles   = reader.GetInt64(reader.GetOrdinal("active_tiles")),
                catchup_tiles  = reader.GetInt64(reader.GetOrdinal("catchup_tiles")),
            });
        }
    }

    return Results.Ok(new { leaderboard = rows, point_config = new { easy, medium, hard, elite } });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

// ── GET /api/stats ───────────────────────────────────────────────────────────
app.MapGet("/api/stats", async (NpgsqlDataSource db) =>
{
    try
    {
    await using var conn = await db.OpenConnectionAsync();
    await using var cmd  = conn.CreateCommand();
    cmd.CommandText = """
        SELECT
            (SELECT COUNT(*) FROM public.tile_submissions)                                                     AS total_submissions,
            (SELECT COUNT(*) FROM public.tile_submissions WHERE is_approved = true)                            AS total_approvals,
            (SELECT COUNT(*) FROM public.tile_submissions WHERE is_approved = false AND updated_at IS NOT NULL) AS total_denials,
            (SELECT COUNT(*) FROM public.tile_assignments  WHERE is_active = false AND COALESCE(was_skipped, false) = false) AS total_completions,
            (SELECT COUNT(*) FROM public.teams)                                                                AS total_teams,
            (SELECT COUNT(*) FROM public.tile_submissions WHERE updated_at IS NULL)                            AS pending_submissions,
            (SELECT COALESCE(is_catchup_mech_active, false) FROM public.global_game_states ORDER BY id LIMIT 1) AS catchup_active,
            (SELECT COALESCE(is_game_running, false)         FROM public.global_game_states ORDER BY id LIMIT 1) AS game_running
        """;

    await using var reader = await cmd.ExecuteReaderAsync();
    if (!await reader.ReadAsync()) return Results.Ok(new { });

    return Results.Ok(new
    {
        total_submissions  = reader.GetInt64(0),
        total_approvals    = reader.GetInt64(1),
        total_denials      = reader.GetInt64(2),
        total_completions  = reader.GetInt64(3),
        total_teams        = reader.GetInt64(4),
        pending_submissions = reader.GetInt64(5),
        catchup_active     = reader.GetBoolean(6),
        game_running       = reader.GetBoolean(7),
    });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

// ── GET /api/events?limit=200 ────────────────────────────────────────────────
app.MapGet("/api/events", async (NpgsqlDataSource db, int limit = 200) =>
{
    try
    {
    await using var conn = await db.OpenConnectionAsync();
    await using var cmd  = conn.CreateCommand();

    // Combined event log:
    //  - "submission"  when a submission is created
    //  - "progress"    when approved but tile still not finished
    //  - "completed"   when the LAST approval finishes a tile
    //  - "denied"      when rejected
    //  - "skipped"     when tile was skipped and it's the latest approval
    cmd.CommandText = $"""
        WITH approved_ranked AS (
            SELECT
                ts.id,
                ts.updated_at                                           AS event_time,
                ts.tile_assignment_id,
                ta.team_id,
                ta.tile_id,
                ta.category,
                ta.is_active,
                ta.was_skipped,
                ta.catchup,
                ROW_NUMBER() OVER (
                    PARTITION BY ts.tile_assignment_id
                    ORDER BY ts.updated_at DESC
                )                                                       AS rn_desc
            FROM public.tile_submissions ts
            JOIN public.tile_assignments ta ON ta.id = ts.tile_assignment_id
            WHERE ts.is_approved = true AND ts.updated_at IS NOT NULL
        )
        SELECT
            'submission'                                                AS event_type,
            ts.created_at                                               AS event_time,
            t.team_name,
            ti.tile_name,
            ta.category,
            false                                                       AS catchup
        FROM public.tile_submissions ts
        JOIN public.tile_assignments ta ON ta.id = ts.tile_assignment_id
        JOIN public.teams t             ON t.id  = ta.team_id
        JOIN public.tiles ti            ON ti.id = ta.tile_id

        UNION ALL

        SELECT
            CASE
                WHEN ar.is_active = false AND NOT COALESCE(ar.was_skipped, false) AND ar.rn_desc = 1
                    THEN 'completed'
                WHEN COALESCE(ar.was_skipped, false) AND ar.rn_desc = 1
                    THEN 'skipped'
                ELSE 'progress'
            END                                                         AS event_type,
            ar.event_time,
            t.team_name,
            ti.tile_name,
            ar.category,
            COALESCE(ar.catchup, false)                                 AS catchup
        FROM approved_ranked ar
        JOIN public.teams t  ON t.id  = ar.team_id
        JOIN public.tiles ti ON ti.id = ar.tile_id

        UNION ALL

        SELECT
            'denied'                                                    AS event_type,
            ts.updated_at                                               AS event_time,
            t.team_name,
            ti.tile_name,
            ta.category,
            false                                                       AS catchup
        FROM public.tile_submissions ts
        JOIN public.tile_assignments ta ON ta.id = ts.tile_assignment_id
        JOIN public.teams t             ON t.id  = ta.team_id
        JOIN public.tiles ti            ON ti.id = ta.tile_id
        WHERE ts.is_approved = false AND ts.updated_at IS NOT NULL

        ORDER BY event_time DESC
        LIMIT {Math.Min(limit, 500)}
        """;

    var events = new List<object>();
    await using var reader = await cmd.ExecuteReaderAsync();
    while (await reader.ReadAsync())
    {
        int cat = reader.GetInt32(reader.GetOrdinal("category"));
        events.Add(new
        {
            event_type    = reader.GetString(0),
            event_time    = reader.GetDateTime(1).ToString("yyyy-MM-ddTHH:mm:ssZ"),
            team_name     = reader.GetString(reader.GetOrdinal("team_name")),
            tile_name     = reader.GetString(reader.GetOrdinal("tile_name")),
            category      = cat,
            category_name = CategoryName(cat),
            category_emoji = CategoryEmoji(cat),
            catchup       = reader.GetBoolean(reader.GetOrdinal("catchup")),
        });
    }

    return Results.Ok(new { events });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

// ── GET /api/point-history ───────────────────────────────────────────────────
// Returns the point_history table grouped by team, sorted by date asc.
// Used to power the "points over time" chart.
app.MapGet("/api/point-history", async (NpgsqlDataSource db) =>
{
    try
    {
    await using var conn = await db.OpenConnectionAsync();
    await using var cmd  = conn.CreateCommand();
    cmd.CommandText = """
        SELECT
            t.team_name,
            ph.date,
            ph.points
        FROM public.point_history ph
        JOIN public.teams t ON t.id = ph.team_id
        ORDER BY ph.date ASC
        """;

    // Group client-side: build { team_name → [{date, points}] }
    var byTeam = new Dictionary<string, List<object>>();
    await using var reader = await cmd.ExecuteReaderAsync();
    while (await reader.ReadAsync())
    {
        var name  = reader.GetString(0);
        var date  = reader.GetDateTime(1).ToString("yyyy-MM-ddTHH:mm:ssZ");
        var pts   = reader.GetInt32(2);
        if (!byTeam.TryGetValue(name, out var list))
            byTeam[name] = list = [];
        list.Add(new { date, points = pts });
    }

    return Results.Ok(new { series = byTeam });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

// ── GET /api/category-breakdown ───────────────────────────────────────────────
// Completions, skips, and points earned broken down by tile category.
app.MapGet("/api/category-breakdown", async (NpgsqlDataSource db) =>
{
    try
    {
        await using var conn = await db.OpenConnectionAsync();

        // Re-fetch point config
        var pc = new Dictionary<string, int>
            { ["easy_points"]=0, ["medium_points"]=0, ["hard_points"]=0, ["elite_points"]=0 };
        await using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = "SELECT name, amount FROM public.global_configs WHERE name = ANY(@n)";
            cmd.Parameters.AddWithValue("n", new[] { "easy_points","medium_points","hard_points","elite_points" });
            await using var r = await cmd.ExecuteReaderAsync();
            while (await r.ReadAsync())
            {
                var raw = r.GetValue(1);
                if (raw != null && int.TryParse(raw.ToString(), out var v)) pc[r.GetString(0)] = v;
            }
        }
        int[] pts = { 0, pc["easy_points"], pc["medium_points"], pc["hard_points"], pc["elite_points"], 1337 };

        await using var cmd2 = conn.CreateCommand();
        cmd2.CommandText = """
            SELECT
                ta.category,
                COUNT(*) FILTER (WHERE ta.is_active = false AND NOT COALESCE(ta.was_skipped,false)) AS completions,
                COUNT(*) FILTER (WHERE ta.is_active = false AND COALESCE(ta.was_skipped,false))     AS skips,
                COUNT(*) FILTER (WHERE ta.is_active = true)                                         AS active,
                COUNT(*) FILTER (WHERE ta.is_active = false AND COALESCE(ta.catchup,false) = true
                                   AND NOT COALESCE(ta.was_skipped,false))                          AS catchup_completions
            FROM public.tile_assignments ta
            GROUP BY ta.category
            ORDER BY ta.category
            """;

        var rows = new List<object>();
        await using var rdr = await cmd2.ExecuteReaderAsync();
        while (await rdr.ReadAsync())
        {
            int cat          = rdr.GetInt32(0);
            long completions = rdr.GetInt64(1);
            long skips       = rdr.GetInt64(2);
            long active      = rdr.GetInt64(3);
            long catchupComp = rdr.GetInt64(4);
            int basePoints   = cat < pts.Length ? pts[cat] : 0;
            long normalComp  = completions - catchupComp;
            long pointsEarned = (long)(normalComp * basePoints + catchupComp * basePoints * 1.5);
            rows.Add(new
            {
                category       = cat,
                category_name  = CategoryName(cat),
                category_emoji = CategoryEmoji(cat),
                completions,
                skips,
                active,
                catchup_completions = catchupComp,
                points_earned  = pointsEarned,
            });
        }
        return Results.Ok(new { breakdown = rows });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

// ── GET /api/daily-activity?days=30 ──────────────────────────────────────────
// Submissions, approvals, and denials grouped by calendar day.
app.MapGet("/api/daily-activity", async (NpgsqlDataSource db, int days = 30) =>
{
    try
    {
        await using var conn = await db.OpenConnectionAsync();
        await using var cmd  = conn.CreateCommand();
        cmd.CommandText = $"""
            SELECT
                DATE_TRUNC('day', created_at)::date                             AS day,
                COUNT(*)                                                         AS submissions,
                COUNT(*) FILTER (WHERE is_approved = true)                       AS approvals,
                COUNT(*) FILTER (WHERE is_approved = false AND updated_at IS NOT NULL) AS denials,
                COUNT(*) FILTER (WHERE updated_at IS NULL)                       AS pending
            FROM public.tile_submissions
            WHERE created_at >= NOW() - INTERVAL '{Math.Min(days, 90)} days'
            GROUP BY 1
            ORDER BY 1 ASC
            """;

        var rows = new List<object>();
        await using var rdr = await cmd.ExecuteReaderAsync();
        while (await rdr.ReadAsync())
            rows.Add(new
            {
                day         = rdr.GetDateTime(0).ToString("yyyy-MM-dd"),
                submissions = rdr.GetInt64(1),
                approvals   = rdr.GetInt64(2),
                denials     = rdr.GetInt64(3),
                pending     = rdr.GetInt64(4),
            });

        return Results.Ok(new { activity = rows });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

// ── GET /api/team-performance ─────────────────────────────────────────────────
// Per-team: total submissions, approvals, denials, denial rate, avg admin
// response time (submission → approval/denial).
app.MapGet("/api/team-performance", async (NpgsqlDataSource db) =>
{
    try
    {
        await using var conn = await db.OpenConnectionAsync();
        await using var cmd  = conn.CreateCommand();
        cmd.CommandText = """
            SELECT
                t.team_name,
                COUNT(ts.id)                                                    AS total_submissions,
                COUNT(ts.id) FILTER (WHERE ts.is_approved = true)               AS approvals,
                COUNT(ts.id) FILTER (WHERE ts.is_approved = false
                                     AND ts.updated_at IS NOT NULL)             AS denials,
                ROUND(AVG(
                    EXTRACT(EPOCH FROM (ts.updated_at - ts.created_at))
                ) FILTER (WHERE ts.updated_at IS NOT NULL)::numeric, 1)         AS avg_response_secs,
                MIN(ts.created_at)                                              AS first_submission,
                MAX(ts.created_at)                                              AS last_submission
            FROM public.teams t
            LEFT JOIN public.tile_assignments ta ON ta.team_id = t.id
            LEFT JOIN public.tile_submissions ts ON ts.tile_assignment_id = ta.id
            GROUP BY t.id, t.team_name
            ORDER BY total_submissions DESC
            """;

        var rows = new List<object>();
        await using var rdr = await cmd.ExecuteReaderAsync();
        while (await rdr.ReadAsync())
        {
            long total   = rdr.IsDBNull(1) ? 0 : rdr.GetInt64(1);
            long approv  = rdr.IsDBNull(2) ? 0 : rdr.GetInt64(2);
            long denied  = rdr.IsDBNull(3) ? 0 : rdr.GetInt64(3);
            double? avgSecs = rdr.IsDBNull(4) ? null : (double?)Convert.ToDouble(rdr.GetValue(4));
            double denialRate = total > 0 ? Math.Round((double)denied / total * 100, 1) : 0;
            rows.Add(new
            {
                team_name        = rdr.GetString(0),
                total_submissions = total,
                approvals        = approv,
                denials          = denied,
                denial_rate_pct  = denialRate,
                avg_response_secs = avgSecs,
                first_submission = rdr.IsDBNull(5) ? null : rdr.GetDateTime(5).ToString("yyyy-MM-ddTHH:mm:ssZ"),
                last_submission  = rdr.IsDBNull(6) ? null : rdr.GetDateTime(6).ToString("yyyy-MM-ddTHH:mm:ssZ"),
            });
        }
        return Results.Ok(new { teams = rows });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

// ── GET /api/top-tiles?limit=15 ───────────────────────────────────────────────
// Most frequently completed tiles across all teams.
app.MapGet("/api/top-tiles", async (NpgsqlDataSource db, int limit = 15) =>
{
    try
    {
        await using var conn = await db.OpenConnectionAsync();
        await using var cmd  = conn.CreateCommand();
        cmd.CommandText = $"""
            SELECT
                ti.tile_name,
                ti.category,
                COUNT(*)                                               AS completions,
                COUNT(*) FILTER (WHERE COALESCE(ta.catchup, false))    AS catchup_completions,
                COUNT(DISTINCT ta.team_id)                             AS unique_teams
            FROM public.tile_assignments ta
            JOIN public.tiles ti ON ti.id = ta.tile_id
            WHERE ta.is_active = false AND NOT COALESCE(ta.was_skipped, false)
            GROUP BY ti.id, ti.tile_name, ti.category
            ORDER BY completions DESC
            LIMIT {Math.Min(limit, 50)}
            """;

        var rows = new List<object>();
        await using var rdr = await cmd.ExecuteReaderAsync();
        while (await rdr.ReadAsync())
        {
            int cat = rdr.GetInt32(1);
            rows.Add(new
            {
                tile_name          = rdr.GetString(0),
                category           = cat,
                category_name      = CategoryName(cat),
                category_emoji     = CategoryEmoji(cat),
                completions        = rdr.GetInt64(2),
                catchup_completions = rdr.GetInt64(3),
                unique_teams       = rdr.GetInt64(4),
            });
        }
        return Results.Ok(new { tiles = rows });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

// ── GET /api/submission-heatmap ───────────────────────────────────────────────
// Counts by hour-of-day and day-of-week to see when people are most active.
app.MapGet("/api/submission-heatmap", async (NpgsqlDataSource db) =>
{
    try
    {
        await using var conn = await db.OpenConnectionAsync();
        await using var cmd  = conn.CreateCommand();
        cmd.CommandText = """
            SELECT
                EXTRACT(DOW  FROM created_at)::int AS dow,
                EXTRACT(HOUR FROM created_at)::int AS hour,
                COUNT(*)                            AS submissions
            FROM public.tile_submissions
            GROUP BY 1, 2
            ORDER BY 1, 2
            """;

        var cells = new List<object>();
        await using var rdr = await cmd.ExecuteReaderAsync();
        while (await rdr.ReadAsync())
            cells.Add(new
            {
                dow         = rdr.GetInt32(0),
                hour        = rdr.GetInt32(1),
                submissions = rdr.GetInt64(2),
            });

        return Results.Ok(new { heatmap = cells });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

// ── GET /api/player-stats ─────────────────────────────────────────────────────
// Per-player: submissions, approvals, denials, rerolls, team.
// display_name is populated lazily when a player interacts with the bot.
app.MapGet("/api/player-stats", async (NpgsqlDataSource db) =>
{
    try
    {
        await using var conn = await db.OpenConnectionAsync();
        await using var cmd  = conn.CreateCommand();
        cmd.CommandText = """
            SELECT
                p.discord_id,
                COALESCE(NULLIF(p.display_name, ''), p.discord_id)          AS display_name,
                COALESCE(t.team_name, 'No Team')                            AS team_name,
                COUNT(DISTINCT ts.id)                                       AS total_submissions,
                COUNT(DISTINCT ts.id) FILTER (WHERE ts.is_approved = true)  AS approvals,
                COUNT(DISTINCT ts.id) FILTER (
                    WHERE ts.is_approved = false AND ts.updated_at IS NOT NULL
                )                                                           AS denials,
                COUNT(DISTINCT ta_r.id)                                     AS rerolls
            FROM public.players p
            LEFT JOIN public.teams t
                ON t.id = p.team_id
            LEFT JOIN public.tile_submissions ts
                ON ts.player_id = p.id
            LEFT JOIN public.tile_assignments ta_r
                ON ta_r.rerolled_by_discord_id = p.discord_id
            GROUP BY p.id, p.discord_id, p.display_name, t.team_name
            ORDER BY approvals DESC, total_submissions DESC
            """;

        var rows = new List<object>();
        await using var rdr = await cmd.ExecuteReaderAsync();
        while (await rdr.ReadAsync())
        {
            rows.Add(new
            {
                discord_id        = rdr.GetString(0),
                display_name      = rdr.GetString(1),
                team_name         = rdr.GetString(2),
                total_submissions = rdr.GetInt64(3),
                approvals         = rdr.GetInt64(4),
                denials           = rdr.GetInt64(5),
                rerolls           = rdr.GetInt64(6),
            });
        }
        return Results.Ok(new { players = rows });
    }
    catch (Exception ex) { return Results.Json(new { error = ex.Message }, statusCode: 500); }
});

app.Run();
