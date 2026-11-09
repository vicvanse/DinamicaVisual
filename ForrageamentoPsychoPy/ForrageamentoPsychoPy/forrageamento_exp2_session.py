# -*- coding: utf-8 -*-
"""
Experiment 2 — continuous foraging session.

One panel visible at a time; switch halves with COD (same timings as Exp1).
Both panels always contain a T; the menu session changes distractor (L) counts.

What the session row controls (from conditions_exp2_sessions.csv):
  session_condition — menu session id (1–10); picks the CSV row / ratio
  session_run       — repetition index only (does not change proportions)
  ratio_label       — design label stored in outputs (e.g. 20vs60)
  n_L_left/right    — initial L count on each panel (sum = 150)
  duration_s        — planned session length (s); override FORR_EXP2_DURATION_S
  correctkey        — exported metadata only (not used to place a single-side T)

Event CSV columns (EXP2_EVENT_FIELDNAMES):
  t_session_s   — time since session start (s)
  event_type    — e.g. foraging_start, decay_tick, reinforcement, session_end
  n_L_left/right — L still visible after the event
  points_total  — cumulative reinforcements
  active_side   — which panel is currently visible (left/right)
  detail        — free-text extras for that event
"""

# =============================================================================
# CODE MAP (English) — what each block in this file does
# =============================================================================
# Helpers: hide/show L letters, append timeline events, write CSV, sanitize names.
# save_exp2_exports: write events/summary/TXT (+ analysis layer) under data/.
# _build_side / _remove_k_ls: build one panel; hide k random visible L (decay).
# run_continuous_exp2_session: main loop — gaze-driven active panel, COD switch,
#   per-second L decay on both sides, Space+AOI reinforcement, HUD points.
# run_exp2_session_wrapper: instructions → continuous session → save exports.
# =============================================================================

from __future__ import print_function

import csv
import errno
import os
import random
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

import forrageamento_exp1 as fe

# Same PsychoPy module objects as Exp1 (avoids NameError / missing `event`).
core = fe.core
visual = fe.visual
event = fe.event


EXP2_EVENT_FIELDNAMES = (
    "participant_id",
    "experiment",
    "session_condition",
    "session_run",
    "event_index",
    "t_session_s",
    "event_type",
    "n_L_left",
    "n_L_right",
    "points_total",
    "active_side",
    "ratio_label",
    "detail",
)


# Some PsychoPy versions ignore TextStim.opacity; parking off-screen is reliable.
_HIDDEN_LETTER_X = -20000.0


def _hide_letter(stim: Any) -> None:
    """Hide one letter stim (opacity/contrast + move far off-screen)."""
    try:
        stim.opacity = 0.0
    except Exception:
        pass
    try:
        stim.contrast = 0.0
    except Exception:
        pass
    try:
        stim.pos = (_HIDDEN_LETTER_X, _HIDDEN_LETTER_X)
    except Exception:
        pass


def _is_l_stim_visible(s: Any) -> bool:
    """True if this L stim is still considered visible (not decay-hidden)."""
    try:
        px, py = s.pos
        if px < -10000.0:
            return False
    except Exception:
        pass
    try:
        op = float(getattr(s, "opacity", 1.0))
    except Exception:
        op = 1.0
    return op > 0.01


def _visible_l_stims(l_stims: List[Any]) -> List[Any]:
    """Filter to L stims that are still visible."""
    return [s for s in l_stims if _is_l_stim_visible(s)]


def _append_event(
    rows: List[Dict[str, Any]],
    participant_safe: str,
    session_condition: int,
    session_run: int,
    t_s: float,
    event_type: str,
    n_L_left: int,
    n_L_right: int,
    points_total: int,
    active_side: str,
    ratio_label: str,
    detail: str = "",
) -> None:
    """Append one Exp2 timeline event row (t relative to session start)."""
    rows.append(
        {
            "participant_id": participant_safe,
            "experiment": 2,
            "session_condition": session_condition,
            "session_run": session_run,
            "event_index": len(rows),
            "t_session_s": round(float(t_s), 6),
            "event_type": event_type,
            "n_L_left": n_L_left,
            "n_L_right": n_L_right,
            "points_total": points_total,
            "active_side": active_side,
            "ratio_label": ratio_label,
            "detail": detail,
        }
    )


def _write_exp2_csv(path: str, rows: List[Dict[str, Any]], fieldnames: Tuple[str, ...]) -> None:
    """Write a DictWriter CSV with a fixed column order."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=list(fieldnames), extrasaction="ignore", restval=""
        )
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _sanitize_filename_token(raw: Any) -> str:
    """Make a filesystem-safe token for output filenames."""
    s = str(raw or "").strip()
    bad = '<>:"/\\|?*'
    s = "".join((c if c not in bad else "_") for c in s)
    s = s.rstrip(" .")
    s = "_".join(s.split())
    return s or "NA"


def _is_writable_dir(folder: str) -> bool:
    """True if folder exists/can be created and is writable."""
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, ".__forr_write_test__.tmp")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def save_exp2_exports(
    event_rows: List[Dict[str, Any]],
    summary_row: Dict[str, Any],
    participant_safe: str,
    session_condition: int,
    session_run: int,
    ts: str,
    session_note: str,
    dummy_mode: bool,
    session_row: Optional[Dict[str, str]] = None,
) -> Tuple[str, str, str]:
    """Write Exp2 events/summary/TXT under data/ and derived analysis CSVs. Returns (events_path, summary_path, txt_path)."""
    data_folder_pref = os.path.join(os.path.dirname(fe.__file__), "data")
    data_folder = data_folder_pref
    if not _is_writable_dir(data_folder):
        cwd_data = os.path.join(os.getcwd(), "data")
        if _is_writable_dir(cwd_data):
            data_folder = cwd_data
        else:
            data_folder = tempfile.gettempdir()
            os.makedirs(data_folder, exist_ok=True)
    participant_safe = fe.sanitize_participant_id(participant_safe)
    ts_safe = _sanitize_filename_token(ts)
    sess_safe = _sanitize_filename_token(session_condition)
    run_safe = _sanitize_filename_token(session_run)
    base = os.path.join(
        data_folder,
        "forrageamento_exp2_{0}_s{1}_r{2}_{3}".format(
            participant_safe,
            sess_safe,
            run_safe,
            ts_safe,
        ),
    )
    base = os.path.normpath(base)
    csv_evt = base + "_exp2_events.csv"
    csv_sum = base + "_exp2_summary.csv"
    txt_path = base + "_exp2.txt"
    try:
        _write_exp2_csv(csv_evt, event_rows, EXP2_EVENT_FIELDNAMES)
        _write_exp2_csv(csv_sum, [summary_row], tuple(summary_row.keys()))
    except OSError as e:
        # Retry with a short guaranteed-safe basename in a writable folder.
        fallback_ts = time.strftime("%Y%m%d_%H%M%S")
        fb_base = os.path.join(
            data_folder,
            "forrageamento_exp2_fallback_{0}".format(fallback_ts),
        )
        csv_evt = fb_base + "_exp2_events.csv"
        csv_sum = fb_base + "_exp2_summary.csv"
        txt_path = fb_base + "_exp2.txt"
        print(
            "Aviso: nome de ficheiro inválido no Exp2; a usar fallback seguro.\n"
            "  erro: {0}\n"
            "  base original: {1}\n"
            "  base fallback: {2}".format(e, base, fb_base),
        )
        try:
            _write_exp2_csv(csv_evt, event_rows, EXP2_EVENT_FIELDNAMES)
            _write_exp2_csv(csv_sum, [summary_row], tuple(summary_row.keys()))
        except OSError as e2:
            # Final fallback: use OS temp dir.
            temp_base = os.path.join(
                tempfile.gettempdir(),
                "forrageamento_exp2_emergency_{0}".format(fallback_ts),
            )
            csv_evt = temp_base + "_exp2_events.csv"
            csv_sum = temp_base + "_exp2_summary.csv"
            txt_path = temp_base + "_exp2.txt"
            print(
                "Aviso: fallback local também falhou; a usar pasta TEMP.\n"
                "  erro fallback: {0}\n"
                "  base TEMP: {1}".format(e2, temp_base),
            )
            _write_exp2_csv(csv_evt, event_rows, EXP2_EVENT_FIELDNAMES)
            _write_exp2_csv(csv_sum, [summary_row], tuple(summary_row.keys()))
    mode = "dummy (rato)" if dummy_mode else "EyeLink"
    lines = [
        "Forrageamento visual — Experimento 2 (sessão contínua)",
        "Participante: {0}".format(participant_safe),
        "Sessão (CSV): {0}".format(session_condition),
        "Repetição: {0}".format(session_run),
        "Data/hora: {0}".format(ts),
        "Distância olhos–ecrã (protocolo): {0} cm".format(int(fe.VIEWING_DISTANCE_CM)),
        "Modo: {0}".format(mode),
        "Nota: {0}".format(session_note or "—"),
        "",
        "Resumo:",
        "\t".join(str(summary_row.get(k, "")) for k in sorted(summary_row.keys())),
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    try:
        import forrageamento_analysis_export as _fa

        p_a, p_r, p_d = _fa.write_exp2_analysis_exports(
            base, event_rows, summary_row, session_row=session_row
        )
        print(
            "  CSV análise Exp2: {0}\n  CSV reforços: {1}\n  CSV dwell (bins 10s): {2}".format(
                p_a, p_r, p_d
            )
        )
    except Exception as ex:
        print(
            "  Aviso: exportação _exp2_analysis_* omitida ({0})".format(ex),
        )
    print(
        "Dados Exp2 gravados:\n  Eventos: {0}\n  Resumo: {1}\n  TXT: {2}".format(
            csv_evt, csv_sum, txt_path
        )
    )
    return csv_evt, csv_sum, txt_path


def _build_side(
    win: visual.Window,
    cx: float,
    cy: float,
    panel_w: float,
    panel_h: float,
    n_L: int,
    include_T: bool,
    layout_seed: int,
):
    """Build stimuli for one panel side (L count + T) using Exp2 fixed layout."""
    rng = random.Random(int(layout_seed) & 0x7FFFFFFFFFFFFFFF)
    return fe.build_exp2_fixed_lt_panel(
        win, cx, cy, panel_w, panel_h, n_L, include_T, rng
    )


def _remove_k_ls(l_stims: List[Any], k: int, rng: random.Random) -> int:
    """Hide up to k currently-visible L letters (random order). Returns how many hidden."""
    vis = _visible_l_stims(l_stims)
    if k <= 0 or not vis:
        return 0
    rng.shuffle(vis)
    n = 0
    for s in vis[: min(k, len(vis))]:
        _hide_letter(s)
        n += 1
    return n


def run_continuous_exp2_session(
    win: visual.Window,
    kb,
    mouse: event.Mouse,
    tracker: Any,
    dummy_mode: bool,
    participant_safe: str,
    session_condition: int,
    session_run: int,
    session_row: Dict[str, str],
) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run one continuous Exp2 session using the chosen conditions row.

    session_condition / session_row set the L proportions and duration.
    session_run only affects reproducible RNG seeds and output filenames.
    Returns (aborted, event_rows, summary_row).
    """
    sw, sh = float(win.size[0]), float(win.size[1])
    sc = fe.layout_scale(sw, sh)
    margin_x = max(8, int(fe.LAYOUT_MARGIN_X * sc))
    margin_y = max(8, int(fe.LAYOUT_MARGIN_Y * sc))

    # Scheduled design from the selected session row (see conditions_exp2_sessions.csv).
    ratio_label = (session_row.get("ratio_label") or "").strip()
    try:
        n_L_left = int(session_row.get("n_L_left", 0))
        n_L_right = int(session_row.get("n_L_right", 0))
    except ValueError:
        n_L_left, n_L_right = 75, 75
    initial_left = n_L_left
    initial_right = n_L_right
    try:
        duration_s = float(session_row.get("duration_s") or 420.0)
    except ValueError:
        duration_s = 420.0
    _d_env = os.environ.get("FORR_EXP2_DURATION_S", "").strip()
    if _d_env:
        try:
            duration_s = float(_d_env)
        except ValueError:
            pass

    # Letters removed from EACH panel every second (symmetric; independent of ratio).
    k_decay = fe.exp2_decay_k_per_panel()
    decay_rng = random.Random(
        fe.stimulus_layout_seed(
            participant_safe,
            2,
            session_condition,
            session_run,
            999,
            "exp2_decay_shuffle|" + ratio_label,
        )
        & 0x7FFFFFFFFFFFFFFF
    )

    # Índice de "apresentação" por painel: 0 = início; +1 a cada reforço nesse lado (novo T + Ls completos).
    layout_pres_index = {"left": 0, "right": 0}

    fe.send_msg(tracker, "EXP2_SESSION_START ratio={0} k_decay_per_panel={1}".format(ratio_label, k_decay))
    fe.send_msg(
        tracker,
        "EXP2_FIXED_LAYOUT both_panels_visible no_region_choice",
    )
    fe.send_msg(
        tracker,
        "EXP2_INITIAL_L left={0} right={1} duration_s={2:.1f}".format(
            initial_left, initial_right, duration_s
        ),
    )

    event_rows: List[Dict[str, Any]] = []
    reinforcement_count = 0
    points_total = 0

    left_cx, left_cy = -sw / 4.0, 0.0
    right_cx, right_cy = sw / 4.0, 0.0
    half_inner_w = sw / 2.0 - 2.0 * margin_x
    max_panel_h = sh - 2.0 * margin_y
    panel_w, panel_h = fe.procedural_panel_size(half_inner_w, max_panel_h)

    def rebuild_left() -> Tuple[List[Any], List[Any], Any, Optional[Tuple[float, float, float, float]]]:
        seed = fe.stimulus_layout_seed(
            participant_safe,
            2,
            session_condition,
            session_run,
            layout_pres_index["left"],
            "exp2fixL|" + ratio_label,
        )
        return _build_side(
            win,
            left_cx,
            left_cy,
            panel_w,
            panel_h,
            n_L_left,
            True,
            seed,
        )

    def rebuild_right() -> Tuple[List[Any], List[Any], Any, Optional[Tuple[float, float, float, float]]]:
        seed = fe.stimulus_layout_seed(
            participant_safe,
            2,
            session_condition,
            session_run,
            layout_pres_index["right"],
            "exp2fixR|" + ratio_label,
        )
        return _build_side(
            win,
            right_cx,
            right_cy,
            panel_w,
            panel_h,
            n_L_right,
            True,
            seed,
        )

    all_left, l_stims_left, t_left, t_aoi_left = rebuild_left()
    all_right, l_stims_right, t_right, t_aoi_right = rebuild_right()

    fe.emit_dataviewer_ias_exp2_dual_targets(
        tracker, float(sw), float(sh), t_aoi_left, t_aoi_right
    )

    fe.emit_dataviewer_ias_forage_panels(
        tracker, float(sw), float(sh), float(panel_w), float(panel_h)
    )

    fe.send_msg(tracker, "PHASE foraging_start_exp2")
    session_clock = core.Clock()
    next_decay_at = 1.0

    time_left_s = 0.0
    time_right_s = 0.0
    last_split_t = session_clock.getTime()

    hud_points = visual.TextStim(
        win,
        text="Pontos: 0",
        pos=(0.0, sh * 0.42),
        height=max(18.0, 26.0 * sc),
        color=(0.95, 0.95, 0.55),
        units="pix",
        bold=True,
        font=fe.INSTRUCTIONS_UI_FONT,
    )
    hourglass = fe.make_hourglass_stim(
        win,
        (right_cx, 0.0),
        sc,
        fill_color=fe.EXP2_INACTIVE_SIDE_FILL,
        line_color=fe.EXP2_INACTIVE_SIDE_LINE,
    )

    target_fix_accum_left = 0.0
    target_fix_accum_right = 0.0
    active_side = "left"
    cod_switch_count = 0
    cod_grey_until = 0.0
    in_cod_grey = False
    inactive_dwell_entry: Optional[float] = None
    last_frame_t = core.getTime()
    ended_by_t_esc = False
    aborted = False

    fe.send_msg(
        tracker,
        "EXP2_COD cod_fix_ms={0} cod_grey_ms={1}".format(
            int(fe.COD_FIX_MS), int(fe.COD_GREY_MS)
        ),
    )

    _append_event(
        event_rows,
        participant_safe,
        session_condition,
        session_run,
        session_clock.getTime(),
        "foraging_start",
        n_L_left,
        n_L_right,
        points_total,
        active_side,
        ratio_label,
        "single_visible_panel_cod_exp1_timing",
    )

    while True:
        fe.poll_global_quit_t_esc(kb, tracker, win)
        if fe.QUIT_SAVE_REQUESTED:
            ended_by_t_esc = True
            aborted = True
            break

        t_sess = session_clock.getTime()

        hud_points.text = "Pontos: {0}".format(points_total)

        while next_decay_at <= min(t_sess, duration_s):
            remove_l = _remove_k_ls(l_stims_left, k_decay, decay_rng)
            remove_r = _remove_k_ls(l_stims_right, k_decay, decay_rng)
            n_L_left = len(_visible_l_stims(l_stims_left))
            n_L_right = len(_visible_l_stims(l_stims_right))
            fe.send_msg(
                tracker,
                "EXP2_DECAY_TICK t={0:.2f} removed_L={1}/{2} n_L={3}/{4}".format(
                    next_decay_at, remove_l, remove_r, n_L_left, n_L_right
                ),
            )
            _append_event(
                event_rows,
                participant_safe,
                session_condition,
                session_run,
                next_decay_at,
                "decay_tick",
                n_L_left,
                n_L_right,
                points_total,
                active_side,
                ratio_label,
                "removed_L={0}/{1}".format(remove_l, remove_r),
            )
            next_decay_at += 1.0
            t_sess = session_clock.getTime()

        if t_sess >= duration_s:
            break

        now = session_clock.getTime()

        if in_cod_grey:
            if now >= cod_grey_until:
                in_cod_grey = False
                active_side = "right" if active_side == "left" else "left"
                inactive_dwell_entry = None
                last_split_t = now
                fe.send_msg(tracker, "COD_SWITCH side_active {0}".format(active_side))
                _append_event(
                    event_rows,
                    participant_safe,
                    session_condition,
                    session_run,
                    now,
                    "cod_end",
                    n_L_left,
                    n_L_right,
                    points_total,
                    active_side,
                    ratio_label,
                    "",
                )
            else:
                win.color = fe.BACKGROUND_COLOR
                win.flip()
                continue

        dt_split = now - last_split_t
        last_split_t = now
        if active_side == "left":
            time_left_s += dt_split
        else:
            time_right_s += dt_split

        if dummy_mode:
            gx, gy = mouse.getPos()
        else:
            g = fe.get_gaze_xy_pix(tracker, win)
            gx, gy = (g if g else (0.0, 0.0))

        inactive = "right" if active_side == "left" else "left"
        icx, icy, ihw, ihh = (
            fe.half_left_bounds(sw, sh)
            if inactive == "left"
            else fe.half_right_bounds(sw, sh)
        )
        in_inactive = fe.in_rect(gx, gy, icx, icy, ihw, ihh)
        if in_inactive:
            if inactive_dwell_entry is None:
                inactive_dwell_entry = now
            elif (now - inactive_dwell_entry) * 1000.0 >= fe.COD_FIX_MS:
                fe.send_msg(tracker, "COD_START inactive={0}".format(inactive))
                _append_event(
                    event_rows,
                    participant_safe,
                    session_condition,
                    session_run,
                    now,
                    "cod_start",
                    n_L_left,
                    n_L_right,
                    points_total,
                    active_side,
                    ratio_label,
                    inactive,
                )
                cod_switch_count += 1
                in_cod_grey = True
                cod_grey_until = now + fe.COD_GREY_MS / 1000.0
                inactive_dwell_entry = None
                win.color = fe.BACKGROUND_COLOR
                win.flip()
                continue
        else:
            inactive_dwell_entry = None

        in_left = (
            t_aoi_left is not None
            and fe.in_rect(gx, gy, t_aoi_left[0], t_aoi_left[1], t_aoi_left[2], t_aoi_left[3])
        )
        in_right = (
            t_aoi_right is not None
            and fe.in_rect(gx, gy, t_aoi_right[0], t_aoi_right[1], t_aoi_right[2], t_aoi_right[3])
        )
        if in_left and in_right:
            if gx < 0.0:
                in_right = False
            else:
                in_left = False
        if active_side == "left":
            in_right = False
        else:
            in_left = False
        keys = kb.getKeys(keyList=["space"], waitRelease=False)
        now_frame = core.getTime()
        dt = min(max(now_frame - last_frame_t, 0.0), 0.1)
        last_frame_t = now_frame
        if dt <= 0.0:
            dt = 1.0 / 60.0
        if in_left:
            target_fix_accum_left += dt
        else:
            target_fix_accum_left = 0.0
        if in_right:
            target_fix_accum_right += dt
        else:
            target_fix_accum_right = 0.0

        fix_thr = fe.TARGET_FIX_MS / 1000.0
        if len(keys) > 0:
            reinforced_side = None
            if in_left and target_fix_accum_left >= fix_thr:
                reinforced_side = "left"
            elif in_right and target_fix_accum_right >= fix_thr:
                reinforced_side = "right"
            if reinforced_side is not None:
                points_total += 1
                reinforcement_count += 1
                fe.send_msg(
                    tracker,
                    "EXP2_REINFORCEMENT points={0} side={1}".format(
                        points_total, reinforced_side
                    ),
                )
                if reinforced_side == "left":
                    layout_pres_index["left"] += 1
                    n_L_left = initial_left
                    all_left, l_stims_left, t_left, t_aoi_left = rebuild_left()
                    fe.send_msg(
                        tracker,
                        "EXP2_PANEL_RESET side=left pres_idx={0} (new_T_and_full_L)".format(
                            layout_pres_index["left"]
                        ),
                    )
                else:
                    layout_pres_index["right"] += 1
                    n_L_right = initial_right
                    all_right, l_stims_right, t_right, t_aoi_right = rebuild_right()
                    fe.send_msg(
                        tracker,
                        "EXP2_PANEL_RESET side=right pres_idx={0} (new_T_and_full_L)".format(
                            layout_pres_index["right"]
                        ),
                    )
                fe.emit_dataviewer_ias_exp2_dual_targets(
                    tracker, float(sw), float(sh), t_aoi_left, t_aoi_right
                )
                target_fix_accum_left = 0.0
                target_fix_accum_right = 0.0
                _append_event(
                    event_rows,
                    participant_safe,
                    session_condition,
                    session_run,
                    session_clock.getTime(),
                    "reinforcement",
                    len(_visible_l_stims(l_stims_left)),
                    len(_visible_l_stims(l_stims_right)),
                    points_total,
                    active_side,
                    ratio_label,
                    "reinforced_side={0}".format(reinforced_side),
                )

        win.color = fe.BACKGROUND_COLOR
        if active_side == "left":
            fe.draw_stim_batch(all_left)
            hourglass.pos = (right_cx, 0.0)
            hourglass.draw()
        else:
            fe.draw_stim_batch(all_right)
            hourglass.pos = (left_cx, 0.0)
            hourglass.draw()
        hud_points.draw()
        win.flip()

    summary = {
        "participant_id": participant_safe,
        "experiment": 2,
        "session_condition": session_condition,
        "session_run": session_run,
        "ratio_label": ratio_label,
        "points_total": points_total,
        "duration_s_run": round(min(session_clock.getTime(), duration_s), 3),
        "duration_s_planned": duration_s,
        "cod_switch_count": cod_switch_count,
        "forage_time_left_s": round(time_left_s, 4),
        "forage_time_right_s": round(time_right_s, 4),
        "aborted": 1 if aborted else 0,
        "ended_by_t_esc": 1 if ended_by_t_esc else 0,
        "k_decay_per_panel": k_decay,
        "initial_n_L_left": initial_left,
        "initial_n_L_right": initial_right,
        "both_panels_visible": 0,
        "single_visible_panel_by_gaze": 1,
        "dual_target_scoring": 1,
        "correctkey_csv": (session_row.get("correctkey") or "").strip(),
    }

    _append_event(
        event_rows,
        participant_safe,
        session_condition,
        session_run,
        session_clock.getTime(),
        "session_end" if not aborted else "session_abort",
        len(_visible_l_stims(l_stims_left)),
        len(_visible_l_stims(l_stims_right)),
        points_total,
        active_side,
        ratio_label,
        "t_esc" if ended_by_t_esc else "time_complete",
    )

    return not aborted, event_rows, summary


def run_exp2_session_wrapper(
    win: visual.Window,
    kb,
    mouse: event.Mouse,
    tracker: Any,
    dummy_mode: bool,
    participant_safe: str,
    session_condition: int,
    session_run: int,
    session_row: Dict[str, str],
) -> bool:
    """Show Exp2 instructions, run the continuous session, then save exports."""
    ok_instr = fe.run_instructions_exp2(win, kb, tracker)
    if not ok_instr:
        fe.run_experiment_end_screen(win, kb, tracker)
        ts = time.strftime("%Y%m%d_%H%M%S")
        save_exp2_exports(
            [],
            {
                "participant_id": participant_safe,
                "experiment": 2,
                "session_condition": session_condition,
                "session_run": session_run,
                "note": "T+Esc nas instruções",
            },
            participant_safe,
            session_condition,
            session_run,
            ts,
            "T+Esc nas instruções",
            dummy_mode,
        )
        return True

    ok, event_rows, summary = run_continuous_exp2_session(
        win,
        kb,
        mouse,
        tracker,
        dummy_mode,
        participant_safe,
        session_condition,
        session_run,
        session_row,
    )
    fe.run_experiment_end_screen(win, kb, tracker)
    ts = time.strftime("%Y%m%d_%H%M%S")
    note = (
        "T+Esc durante sessão"
        if fe.QUIT_SAVE_REQUESTED or bool(summary.get("ended_by_t_esc"))
        else "Sessão Exp2 concluída"
    )
    if not summary:
        summary = {
            "participant_id": participant_safe,
            "experiment": 2,
            "session_condition": session_condition,
            "session_run": session_run,
            "note": "sem dados",
        }
    save_exp2_exports(
        event_rows,
        summary,
        participant_safe,
        session_condition,
        session_run,
        ts,
        note,
        dummy_mode,
        session_row=session_row,
    )
    return ok
