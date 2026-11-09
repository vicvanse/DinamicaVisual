# -*- coding: utf-8 -*-
"""
Derived analysis export layers (raw session CSVs are never modified).

Used for matching-law / discrete-choice plots. Key fields:
  session_condition — menu session id that selected the scheduled proportion
  session_run       — repetition of that same condition (not a new ratio)
  ratio_label       — scheduled design label (e.g. 10vs90 or 20vs60)
  prop_forage_*     — obtained foraging-time proportions
  matching_log_B    — log ratio of obtained behavior (left/right forage)
  matching_log_R*   — log ratio of programmed or obtained reinforcement
"""

# =============================================================================
# CODE MAP (English) — what each block in this file does
# =============================================================================
# Fieldname tuples: column order for derived analysis CSVs (raw files untouched).
# Helpers: safe float/log-ratio/proportion; parse ratio_label "AvsB".
# Exp1 enrichers: per-trial props + matching logs; segment props; session aggregate.
# Exp2 enrichers: summary matching; reinforcement list; dwell bins (10 s).
# Writers: write_exp1_analysis_exports / write_exp2_analysis_exports → *_analysis_*.csv
# =============================================================================

from __future__ import division, print_function

import csv
import math
import os
from typing import Any, Dict, List, Optional, Tuple

# Per-trial derived columns (matching / discrete choice).
EXP1_TRIAL_ANALYSIS_FIELDNAMES = (
    "participant_id",
    "experiment",
    "session_condition",
    "session_run",
    "ratio_label",
    "trial",
    "trial_id",
    "condition_trial",
    "target_side",
    "left_panel",
    "right_panel",
    "first_side_choice",
    "forage_time_left_s",
    "forage_time_right_s",
    "forage_time_total_s",
    "prop_forage_left",
    "prop_forage_right",
    "cod_switch_count",
    "first_side_is_left",
    "choice_left",
    "choice_right",
    "accuracy_01",
    "rt_discrete_s",
    "reinforcement_side",
    "reinforcement_is_left",
    "utility_T_on_left",
    "utility_T_on_right",
    "matching_log_B",
    "matching_log_R_trial",
    "aborted",
    "discrete_key",
    "correctkey",
)

# One row per Exp1 session (aggregated matching law).
EXP1_SESSION_ANALYSIS_FIELDNAMES = (
    "participant_id",
    "experiment",
    "session_condition",
    "session_run",
    "ratio_label",
    "w_left_design",
    "w_right_design",
    "n_left_design",
    "n_right_design",
    "n_trials",
    "n_trials_completed",
    "forage_time_left_total_s",
    "forage_time_right_total_s",
    "forage_time_total_s",
    "prop_forage_left",
    "prop_forage_right",
    "n_reinforcement_left",
    "n_reinforcement_right",
    "prop_reinforcement_left",
    "matching_log_B",
    "matching_log_R",
    "matching_log_R_design",
    "n_discrete_left",
    "n_discrete_right",
    "prop_discrete_left",
    "mean_rt_discrete_s",
    "mean_accuracy",
    "mean_cod_switch_count",
)

# Per forage segment within a trial.
EXP1_SEGMENT_ANALYSIS_FIELDNAMES = (
    "participant_id",
    "experiment",
    "session_condition",
    "session_run",
    "trial",
    "segment_index",
    "side",
    "side_is_left",
    "duration_s",
    "duration_prop_of_trial",
    "found_target_during_segment",
    "target_side",
    "trial_switch_count",
    "aborted_trial",
)

# Exp2 session summary + matching logs.
EXP2_SUMMARY_ANALYSIS_FIELDNAMES = (
    "participant_id",
    "experiment",
    "session_condition",
    "session_run",
    "ratio_label",
    "w_left_design",
    "w_right_design",
    "prop_L_left_design",
    "prop_L_right_design",
    "initial_n_L_left",
    "initial_n_L_right",
    "forage_time_left_s",
    "forage_time_right_s",
    "forage_time_total_s",
    "prop_forage_left",
    "prop_forage_right",
    "points_total",
    "duration_s_run",
    "duration_s_planned",
    "rate_reinforcement_per_min",
    "n_reinforcement_left",
    "n_reinforcement_right",
    "prop_reinforcement_left",
    "matching_log_B",
    "matching_log_R_design",
    "matching_log_R_obtained",
    "k_decay_per_panel",
    "aborted",
    "ended_by_t_esc",
    "correctkey_csv",
)

# Exp2 gaze dwell in fixed time bins.
EXP2_DWELL_BIN_FIELDNAMES = (
    "participant_id",
    "experiment",
    "session_condition",
    "session_run",
    "ratio_label",
    "bin_index",
    "bin_start_s",
    "bin_end_s",
    "dwell_left_s",
    "dwell_right_s",
    "dwell_total_s",
    "prop_dwell_left",
    "points_total_end_bin",
    "n_reinforcement_left_cum",
    "n_reinforcement_right_cum",
)

# One row per Exp2 point/reinforcement.
EXP2_REINFORCEMENT_FIELDNAMES = (
    "participant_id",
    "experiment",
    "session_condition",
    "session_run",
    "reinforcement_index",
    "t_session_s",
    "reinforced_side",
    "reinforced_is_left",
    "points_total_after",
    "n_L_left",
    "n_L_right",
    "active_side",
    "ratio_label",
)


def _safe_float(v: Any, default: float = 0.0) -> float:
    """Parse a float from CSV cell text; return default on failure."""
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_log_ratio(num: float, den: float) -> str:
    """Natural log(num/den) as string, or empty if non-positive."""
    if num <= 0.0 or den <= 0.0:
        return ""
    return str(round(math.log(num / den), 6))


def _prop(num: float, den: float) -> str:
    """num/den as string proportion, or empty if den <= 0."""
    if den <= 0.0:
        return ""
    return str(round(num / den, 6))


def parse_ratio_label(ratio_label: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse "10vs90" → (10, 90); returns (None, None) if invalid."""
    s = (ratio_label or "").strip().lower().replace(" ", "")
    if "vs" not in s:
        return None, None
    parts = s.split("vs", 1)
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


def _side_is_left(side: str) -> str:
    """Return "1" if side is left, else "0"."""
    return "1" if (side or "").strip().lower() == "left" else "0"


def _parse_reinforced_side(detail: str) -> str:
    """Extract left/right from an Exp2 event detail string."""
    d = (detail or "").strip().lower()
    if "reinforced_side=left" in d:
        return "left"
    if "reinforced_side=right" in d:
        return "right"
    return ""


def enrich_exp1_trial_analysis(row: Dict[str, Any]) -> Dict[str, Any]:
    """Build one Exp1 analysis-trial row (forage props, choice, matching logs)."""
    fl = _safe_float(row.get("forage_time_left_s"))
    fr = _safe_float(row.get("forage_time_right_s"))
    total = fl + fr
    target = (row.get("target_side") or "").strip().lower()
    first = (row.get("first_side_choice") or "").strip().lower()
    dk = (row.get("discrete_key") or "").strip().lower()
    acc = row.get("accuracy")
    lp, rp = row.get("left_panel", ""), row.get("right_panel", "")

    r_side = target if target in ("left", "right") else ""
    r_left = 1.0 if r_side == "left" else 0.0
    r_right = 1.0 if r_side == "right" else 0.0

    out = {
        "participant_id": row.get("participant_id", ""),
        "experiment": row.get("experiment", ""),
        "session_condition": row.get("session_condition", ""),
        "session_run": row.get("session_run", ""),
        "ratio_label": row.get("ratio_label", ""),
        "trial": row.get("trial", ""),
        "trial_id": row.get("trial_id", ""),
        "condition_trial": row.get("condition_trial", ""),
        "target_side": target,
        "left_panel": lp,
        "right_panel": rp,
        "first_side_choice": first,
        "forage_time_left_s": fl,
        "forage_time_right_s": fr,
        "forage_time_total_s": round(total, 6),
        "prop_forage_left": _prop(fl, total),
        "prop_forage_right": _prop(fr, total),
        "cod_switch_count": row.get("cod_switch_count", ""),
        "first_side_is_left": _side_is_left(first),
        "choice_left": "1" if dk == "left" else ("0" if dk else ""),
        "choice_right": "1" if dk == "right" else ("0" if dk else ""),
        "accuracy_01": (
            "1"
            if str(acc).strip() in ("1", "1.0", "True", "true")
            else ("0" if str(acc).strip() in ("0", "0.0", "False", "false") else "")
        ),
        "rt_discrete_s": row.get("rt_discrete_s", ""),
        "reinforcement_side": r_side,
        "reinforcement_is_left": _side_is_left(r_side),
        "utility_T_on_left": "1" if lp == "T" else "0",
        "utility_T_on_right": "1" if rp == "T" else "0",
        "matching_log_B": _safe_log_ratio(fl, fr) if total > 0 else "",
        "matching_log_R_trial": _safe_log_ratio(r_left, r_right) if r_side else "",
        "aborted": row.get("aborted", ""),
        "discrete_key": row.get("discrete_key", ""),
        "correctkey": row.get("correctkey", ""),
    }
    return out


def enrich_exp1_segment_analysis(seg: Dict[str, Any]) -> Dict[str, Any]:
    """Build one Exp1 analysis-segment row (duration as proportion of trial)."""
    dur = _safe_float(seg.get("duration_s"))
    trial_total = _safe_float(seg.get("trial_total_segment_time_s"))
    side = (seg.get("side") or "").strip().lower()
    return {
        "participant_id": seg.get("participant_id", ""),
        "experiment": seg.get("experiment", ""),
        "session_condition": seg.get("session_condition", ""),
        "session_run": seg.get("session_run", ""),
        "trial": seg.get("trial", ""),
        "segment_index": seg.get("segment_index", ""),
        "side": side,
        "side_is_left": _side_is_left(side),
        "duration_s": dur,
        "duration_prop_of_trial": _prop(dur, trial_total),
        "found_target_during_segment": seg.get("found_target_during_segment", ""),
        "target_side": seg.get("target_side", ""),
        "trial_switch_count": seg.get("trial_switch_count", ""),
        "aborted_trial": seg.get("aborted_trial", ""),
    }


def build_exp1_session_analysis(rows_out: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate all Exp1 trials into one session-level matching-law row."""
    if not rows_out:
        return {}
    meta = rows_out[0]
    completed = [
        r
        for r in rows_out
        if not str(r.get("aborted", "")).strip().lower() in ("true", "1", "1.0")
    ]
    fl_sum = sum(_safe_float(r.get("forage_time_left_s")) for r in completed)
    fr_sum = sum(_safe_float(r.get("forage_time_right_s")) for r in completed)
    f_total = fl_sum + fr_sum

    n_r_left = sum(
        1
        for r in completed
        if (r.get("target_side") or "").strip().lower() == "left"
    )
    n_r_right = sum(
        1
        for r in completed
        if (r.get("target_side") or "").strip().lower() == "right"
    )
    # Desenho: todos os trials da sessão (incl. abortados), via correctkey / target_side.
    n_design_left = sum(
        1
        for r in rows_out
        if (r.get("correctkey") or r.get("target_side") or "").strip().lower() == "left"
    )
    n_design_right = sum(
        1
        for r in rows_out
        if (r.get("correctkey") or r.get("target_side") or "").strip().lower() == "right"
    )
    ratio = (meta.get("ratio_label") or "").strip()
    w_l, w_r = parse_ratio_label(ratio)
    if w_l is None and n_design_left + n_design_right > 0:
        # Fallback: pesos relativos ≈ contagens de desenho normalizadas a 100.
        total_d = float(n_design_left + n_design_right)
        w_l = int(round(100.0 * float(n_design_left) / total_d))
        w_r = int(round(100.0 * float(n_design_right) / total_d))
    n_disc_left = sum(
        1
        for r in completed
        if (r.get("discrete_key") or "").strip().lower() == "left"
    )
    n_disc_right = sum(
        1
        for r in completed
        if (r.get("discrete_key") or "").strip().lower() == "right"
    )
    n_disc = n_disc_left + n_disc_right
    rts = [
        _safe_float(r.get("rt_discrete_s"), -1.0)
        for r in completed
        if _safe_float(r.get("rt_discrete_s"), -1.0) >= 0.0
    ]
    accs = [
        1.0
        for r in completed
        if str(r.get("accuracy", "")).strip() in ("1", "1.0", "True", "true")
    ]
    cod = [_safe_float(r.get("cod_switch_count")) for r in completed]

    w_l_f = float(w_l) if w_l is not None else 0.0
    w_r_f = float(w_r) if w_r is not None else 0.0

    return {
        "participant_id": meta.get("participant_id", ""),
        "experiment": meta.get("experiment", ""),
        "session_condition": meta.get("session_condition", ""),
        "session_run": meta.get("session_run", ""),
        "ratio_label": ratio,
        "w_left_design": w_l if w_l is not None else "",
        "w_right_design": w_r if w_r is not None else "",
        "n_left_design": n_design_left,
        "n_right_design": n_design_right,
        "n_trials": len(rows_out),
        "n_trials_completed": len(completed),
        "forage_time_left_total_s": round(fl_sum, 6),
        "forage_time_right_total_s": round(fr_sum, 6),
        "forage_time_total_s": round(f_total, 6),
        "prop_forage_left": _prop(fl_sum, f_total),
        "prop_forage_right": _prop(fr_sum, f_total),
        "n_reinforcement_left": n_r_left,
        "n_reinforcement_right": n_r_right,
        "prop_reinforcement_left": _prop(float(n_r_left), float(n_r_left + n_r_right)),
        "matching_log_B": _safe_log_ratio(fl_sum, fr_sum) if f_total > 0 else "",
        "matching_log_R": _safe_log_ratio(float(n_r_left), float(n_r_right))
        if (n_r_left + n_r_right) > 0
        else "",
        "matching_log_R_design": _safe_log_ratio(w_l_f, w_r_f)
        if w_l_f > 0 and w_r_f > 0
        else "",
        "n_discrete_left": n_disc_left,
        "n_discrete_right": n_disc_right,
        "prop_discrete_left": _prop(float(n_disc_left), float(n_disc)) if n_disc else "",
        "mean_rt_discrete_s": str(round(sum(rts) / len(rts), 6)) if rts else "",
        "mean_accuracy": str(round(sum(accs) / len(completed), 6)) if completed else "",
        "mean_cod_switch_count": str(round(sum(cod) / len(cod), 6)) if cod else "",
    }


def enrich_exp2_summary_analysis(
    summary: Dict[str, Any],
    event_rows: List[Dict[str, Any]],
    session_row: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Enrich Exp2 summary with design/obtained ratios and matching logs."""
    ratio = (summary.get("ratio_label") or "").strip()
    w_l, w_r = parse_ratio_label(ratio)
    if session_row:
        if w_l is None:
            try:
                w_l = int(session_row.get("w_esq", "") or 0)
            except ValueError:
                w_l = None
        if w_r is None:
            try:
                w_r = int(session_row.get("w_dir", "") or 0)
            except ValueError:
                w_r = None

    fl = _safe_float(summary.get("forage_time_left_s"))
    fr = _safe_float(summary.get("forage_time_right_s"))
    f_total = fl + fr
    duration = _safe_float(summary.get("duration_s_run"))
    points = _safe_float(summary.get("points_total"))
    init_l = _safe_float(summary.get("initial_n_L_left"))
    init_r = _safe_float(summary.get("initial_n_L_right"))
    l_total = init_l + init_r
    if l_total <= 0:
        l_total = 150.0

    n_reinf_l = 0
    n_reinf_r = 0
    for ev in event_rows:
        if (ev.get("event_type") or "") != "reinforcement":
            continue
        rs = _parse_reinforced_side(ev.get("detail", ""))
        if rs == "left":
            n_reinf_l += 1
        elif rs == "right":
            n_reinf_r += 1

    w_l_f = float(w_l) if w_l is not None else 0.0
    w_r_f = float(w_r) if w_r is not None else 0.0

    return {
        "participant_id": summary.get("participant_id", ""),
        "experiment": summary.get("experiment", 2),
        "session_condition": summary.get("session_condition", ""),
        "session_run": summary.get("session_run", ""),
        "ratio_label": ratio,
        "w_left_design": w_l if w_l is not None else "",
        "w_right_design": w_r if w_r is not None else "",
        "prop_L_left_design": _prop(init_l, l_total),
        "prop_L_right_design": _prop(init_r, l_total),
        "initial_n_L_left": summary.get("initial_n_L_left", ""),
        "initial_n_L_right": summary.get("initial_n_L_right", ""),
        "forage_time_left_s": round(fl, 6),
        "forage_time_right_s": round(fr, 6),
        "forage_time_total_s": round(f_total, 6),
        "prop_forage_left": _prop(fl, f_total),
        "prop_forage_right": _prop(fr, f_total),
        "points_total": int(points),
        "duration_s_run": round(duration, 6),
        "duration_s_planned": summary.get("duration_s_planned", ""),
        "rate_reinforcement_per_min": _prop(points * 60.0, duration) if duration > 0 else "",
        "n_reinforcement_left": n_reinf_l,
        "n_reinforcement_right": n_reinf_r,
        "prop_reinforcement_left": _prop(float(n_reinf_l), float(n_reinf_l + n_reinf_r)),
        "matching_log_B": _safe_log_ratio(fl, fr) if f_total > 0 else "",
        "matching_log_R_design": _safe_log_ratio(w_l_f, w_r_f) if w_l_f > 0 and w_r_f > 0 else "",
        "matching_log_R_obtained": _safe_log_ratio(float(n_reinf_l), float(n_reinf_r))
        if (n_reinf_l + n_reinf_r) > 0
        else "",
        "k_decay_per_panel": summary.get("k_decay_per_panel", ""),
        "aborted": summary.get("aborted", ""),
        "ended_by_t_esc": summary.get("ended_by_t_esc", ""),
        "correctkey_csv": summary.get("correctkey_csv", ""),
    }


def build_exp2_reinforcement_rows(
    event_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """One analysis row per Exp2 reinforcement event."""
    out: List[Dict[str, Any]] = []
    idx = 0
    for ev in event_rows:
        if (ev.get("event_type") or "") != "reinforcement":
            continue
        rs = _parse_reinforced_side(ev.get("detail", ""))
        out.append(
            {
                "participant_id": ev.get("participant_id", ""),
                "experiment": ev.get("experiment", 2),
                "session_condition": ev.get("session_condition", ""),
                "session_run": ev.get("session_run", ""),
                "reinforcement_index": idx,
                "t_session_s": ev.get("t_session_s", ""),
                "reinforced_side": rs,
                "reinforced_is_left": _side_is_left(rs),
                "points_total_after": ev.get("points_total", ""),
                "n_L_left": ev.get("n_L_left", ""),
                "n_L_right": ev.get("n_L_right", ""),
                "active_side": ev.get("active_side", ""),
                "ratio_label": ev.get("ratio_label", ""),
            }
        )
        idx += 1
    return out


def _exp2_dwell_segments(
    evs: List[Dict[str, Any]],
) -> List[Tuple[float, float, str]]:
    """Intervalos [t0, t1) com active_side constante entre eventos."""
    if not evs:
        return []
    segments: List[Tuple[float, float, str]] = []
    t_prev = 0.0
    side_prev = (evs[0].get("active_side") or "left").strip().lower()
    for ev in evs[1:]:
        t_ev = _safe_float(ev.get("t_session_s"))
        segments.append((t_prev, t_ev, side_prev))
        t_prev = t_ev
        side_prev = (ev.get("active_side") or side_prev).strip().lower()
    t_end = _safe_float(evs[-1].get("t_session_s"))
    segments.append((t_prev, t_end, side_prev))
    return segments


def _overlap_dwell(
    seg_start: float, seg_end: float, side: str, bin_start: float, bin_end: float
) -> Tuple[float, float]:
    """Seconds of overlap between a dwell segment and a time bin."""
    a = max(seg_start, bin_start)
    b = min(seg_end, bin_end)
    dt = max(0.0, b - a)
    if side == "left":
        return dt, 0.0
    return 0.0, dt


def build_exp2_dwell_bins(
    event_rows: List[Dict[str, Any]],
    bin_s: float = 10.0,
) -> List[Dict[str, Any]]:
    """Bin Exp2 gaze dwell into fixed 10 s windows for time-course plots."""
    if not event_rows:
        return []
    evs = sorted(event_rows, key=lambda e: _safe_float(e.get("t_session_s")))
    meta = evs[0]
    ratio = evs[0].get("ratio_label", "")
    pid = meta.get("participant_id", "")
    sess = meta.get("session_condition", "")
    run = meta.get("session_run", "")
    exp = meta.get("experiment", 2)

    t_end = _safe_float(evs[-1].get("t_session_s"))
    if t_end <= 0:
        return []

    segments = _exp2_dwell_segments(evs)
    reinf_by_t: List[Tuple[float, str]] = []
    for ev in evs:
        if (ev.get("event_type") or "") == "reinforcement":
            reinf_by_t.append(
                (_safe_float(ev.get("t_session_s")), _parse_reinforced_side(ev.get("detail", "")))
            )

    n_bins = max(1, int(math.ceil(t_end / bin_s)))
    rows: List[Dict[str, Any]] = []
    points_at_t: List[Tuple[float, int]] = [
        (_safe_float(ev.get("t_session_s")), int(_safe_float(ev.get("points_total"))))
        for ev in evs
    ]

    for b in range(n_bins):
        bin_start = b * bin_s
        bin_end = min((b + 1) * bin_s, t_end)
        bin_left = 0.0
        bin_right = 0.0
        for seg_start, seg_end, side in segments:
            dl, dr = _overlap_dwell(seg_start, seg_end, side, bin_start, bin_end)
            bin_left += dl
            bin_right += dr

        n_rl = sum(1 for t, s in reinf_by_t if s == "left" and t <= bin_end)
        n_rr = sum(1 for t, s in reinf_by_t if s == "right" and t <= bin_end)
        pts = 0
        for t_pt, p_val in points_at_t:
            if t_pt <= bin_end:
                pts = p_val
        b_total = bin_left + bin_right

        rows.append(
            {
                "participant_id": pid,
                "experiment": exp,
                "session_condition": sess,
                "session_run": run,
                "ratio_label": ratio,
                "bin_index": b,
                "bin_start_s": round(bin_start, 3),
                "bin_end_s": round(bin_end, 3),
                "dwell_left_s": round(bin_left, 6),
                "dwell_right_s": round(bin_right, 6),
                "dwell_total_s": round(b_total, 6),
                "prop_dwell_left": _prop(bin_left, b_total),
                "points_total_end_bin": pts,
                "n_reinforcement_left_cum": n_rl,
                "n_reinforcement_right_cum": n_rr,
            }
        )

    return rows


def _write_analysis_csv(
    path: str, rows: List[Dict[str, Any]], fieldnames: Tuple[str, ...]
) -> None:
    """Write an analysis CSV with the given fieldnames."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=list(fieldnames), extrasaction="ignore", restval=""
        )
        w.writeheader()
        for row in rows:
            w.writerow(row)


def write_exp1_analysis_exports(
    base_path: str,
    rows_out: List[Dict[str, Any]],
    segment_rows: List[Dict[str, Any]],
) -> Tuple[str, str, str]:
    """Grava *_analysis_trials.csv, *_analysis_session.csv, *_analysis_segments.csv."""
    trial_rows = [enrich_exp1_trial_analysis(r) for r in rows_out]
    seg_rows = [enrich_exp1_segment_analysis(s) for s in segment_rows]
    session_row = build_exp1_session_analysis(rows_out)

    p_trials = base_path + "_analysis_trials.csv"
    p_session = base_path + "_analysis_session.csv"
    p_segments = base_path + "_analysis_segments.csv"

    _write_analysis_csv(p_trials, trial_rows, EXP1_TRIAL_ANALYSIS_FIELDNAMES)
    _write_analysis_csv(
        p_session, [session_row] if session_row else [], EXP1_SESSION_ANALYSIS_FIELDNAMES
    )
    _write_analysis_csv(p_segments, seg_rows, EXP1_SEGMENT_ANALYSIS_FIELDNAMES)
    return p_trials, p_session, p_segments


def write_exp2_analysis_exports(
    base_path: str,
    event_rows: List[Dict[str, Any]],
    summary: Dict[str, Any],
    session_row: Optional[Dict[str, str]] = None,
    dwell_bin_s: float = 10.0,
) -> Tuple[str, str, str, str]:
    """Grava *_exp2_analysis.csv, *_exp2_reinforcements.csv, *_exp2_dwell_bins.csv."""
    summary_a = enrich_exp2_summary_analysis(summary, event_rows, session_row)
    reinf_rows = build_exp2_reinforcement_rows(event_rows)
    dwell_rows = build_exp2_dwell_bins(event_rows, bin_s=dwell_bin_s)

    p_summary = base_path + "_exp2_analysis.csv"
    p_reinf = base_path + "_exp2_reinforcements.csv"
    p_dwell = base_path + "_exp2_dwell_bins.csv"

    _write_analysis_csv(p_summary, [summary_a], EXP2_SUMMARY_ANALYSIS_FIELDNAMES)
    _write_analysis_csv(p_reinf, reinf_rows, EXP2_REINFORCEMENT_FIELDNAMES)
    _write_analysis_csv(p_dwell, dwell_rows, EXP2_DWELL_BIN_FIELDNAMES)
    return p_summary, p_reinf, p_dwell
