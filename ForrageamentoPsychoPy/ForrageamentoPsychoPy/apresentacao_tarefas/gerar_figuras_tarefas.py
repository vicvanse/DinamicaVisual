#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera PNG + PDF das telas das tarefas (Exp1 e Exp2) para apresentação.

Recria o layout a partir das constantes de forrageamento_exp1.py (1680×1050).
"""
from __future__ import annotations

import os
import random
from typing import List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
from matplotlib import patheffects as pe

# Constantes alinhadas a forrageamento_exp1.py (sem importar PsychoPy).
BACKGROUND_COLOR = (-0.4, -0.4, -0.4)
EXP2_INACTIVE_SIDE_FILL = (-0.52, -0.52, -0.52)
EXP2_INACTIVE_SIDE_LINE = (-0.64, -0.64, -0.64)
CORRECT_FEEDBACK_COLOR = (-0.35, 0.78, -0.35)
GRAYS_FOR_L = (
    (-0.22, -0.22, -0.22),
    (-0.12, -0.12, -0.12),
    (-0.02, -0.02, -0.02),
    (0.08, 0.08, 0.08),
    (0.18, 0.18, 0.18),
    (0.28, 0.28, 0.28),
    (0.38, 0.38, 0.38),
)
FIXATION_GRAY = (0.45, 0.45, 0.45)
INSTRUCTIONS_PREVIEW_TARGET_GREEN = (-0.92, 0.62, -0.55)
INSTRUCTIONS_PREVIEW_BOX_FILL = (-0.28, -0.28, -0.28)
INSTRUCTIONS_PREVIEW_BOX_LINE = (-0.75, -0.75, -0.75)
REF_LAYOUT_W, REF_LAYOUT_H = 1280.0, 768.0
DEFAULT_WINDOW_W, DEFAULT_WINDOW_H = 1680, 1050
DRIFT_AOI_RADIUS = 60
LAYOUT_MARGIN_X, LAYOUT_MARGIN_Y = 16, 24
PANEL_NAT_FALLBACK = (630, 800)
SEARCH_PANEL_STIM_COUNT_FRAC = 0.75
SEARCH_PANEL_STIM_COUNT_MIN = 20
REGION_CHOICE_NEUTRAL_HALF_W_FRAC = 0.09
REGION_CHOICE_NEUTRAL_HALF_W_MIN_PX = 72.0

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PNG_DIR = os.path.join(OUT_DIR, "png")

SW, SH = float(DEFAULT_WINDOW_W), float(DEFAULT_WINDOW_H)
DPI_SCREEN = 120
FONT = "Arial"
SLIDE_W, SLIDE_H = 13.333, 7.5
SLIDE_BG = "#f4f4f1"
SLIDE_INK = "#1c1c1c"
SLIDE_MUTED = "#5a5a5a"
SLIDE_ACCENT = "#2f5d50"


def psy(rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return tuple((c + 1.0) / 2.0 for c in rgb)


BG = psy(BACKGROUND_COLOR)


def scatter_positions(cx, cy, panel_w, panel_h, n_points, min_dist, margin, rng):
    half_w = panel_w / 2.0 - margin
    half_h = panel_h / 2.0 - margin
    if half_w <= 1.0 or half_h <= 1.0 or n_points <= 0:
        return []
    md = min_dist
    best: List[Tuple[float, float]] = []
    for _relax in range(18):
        out: List[Tuple[float, float]] = []
        min_d2 = md * md
        max_attempts = max(12000, n_points * 250)
        attempts = 0
        while len(out) < n_points and attempts < max_attempts:
            attempts += 1
            x = cx + rng.uniform(-half_w, half_w)
            y = cy + rng.uniform(-half_h, half_h)
            ok = True
            for ox, oy in out:
                dx = x - ox
                dy = y - oy
                if dx * dx + dy * dy < min_d2:
                    ok = False
                    break
            if ok:
                out.append((x, y))
        if len(out) >= n_points:
            return out[:n_points]
        if len(out) > len(best):
            best = out
        md *= 0.9
    return best[:n_points] if len(best) >= n_points else best


def layout_scale(sw: float, sh: float) -> float:
    return min(float(sw) / REF_LAYOUT_W, float(sh) / REF_LAYOUT_H)


def fit_size_contain(nat_w, nat_h, box_w, box_h):
    s = min(box_w / float(nat_w), box_h / float(nat_h))
    return (max(1.0, nat_w * s), max(1.0, nat_h * s))


def procedural_panel_size(box_w, box_h):
    return fit_size_contain(PANEL_NAT_FALLBACK[0], PANEL_NAT_FALLBACK[1], box_w, box_h)


def search_panel_grid_dims(panel_w, panel_h):
    density = min(panel_w, panel_h) / 10.0
    cell_base = max(36.0, min(56.0, density))
    n_cols = max(5, int(panel_w / cell_base))
    n_rows = max(6, int(panel_h / (cell_base * 1.05)))
    return n_cols, n_rows


def region_choice_neutral_half_w(sw):
    return max(REGION_CHOICE_NEUTRAL_HALF_W_MIN_PX, sw * REGION_CHOICE_NEUTRAL_HALF_W_FRAC)


def instruction_font_heights(sh):
    return (
        max(20.0, min(34.0, sh * 0.034)),
        max(14.0, min(21.0, sh * 0.021)),
        max(15.0, min(24.0, sh * 0.024)),
    )


def instruction_example_panel_size(sw, sh, frac=0.30):
    w = min(float(sw), float(sh)) * float(frac)
    return w, w * 0.92


def new_screen(title_tag: str):
    fig = plt.figure(figsize=(SW / DPI_SCREEN, SH / DPI_SCREEN), dpi=DPI_SCREEN)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-SW / 2.0, SW / 2.0)
    ax.set_ylim(-SH / 2.0, SH / 2.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor(BG)
    fig._screen_tag = title_tag  # type: ignore[attr-defined]
    return fig, ax


def save_screen(fig, name: str) -> str:
    os.makedirs(PNG_DIR, exist_ok=True)
    path = os.path.join(PNG_DIR, name)
    fig.savefig(path, dpi=DPI_SCREEN, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def draw_letter(ax, ch, x, y, letter_h, color, ori, z=5):
    fs = letter_h * 72.0 / DPI_SCREEN * 1.08
    ax.text(
        x,
        y,
        ch,
        fontsize=fs,
        fontname=FONT,
        fontweight="bold",
        color=color,
        ha="center",
        va="center",
        rotation=-float(ori),
        zorder=z,
        clip_on=True,
    )


def draw_panel_border(ax, cx, cy, pw, ph):
    ax.add_patch(
        Rectangle(
            (cx - (pw + 4) / 2.0, cy - (ph + 4) / 2.0),
            pw + 4,
            ph + 4,
            fill=False,
            edgecolor=psy((0.12, 0.12, 0.12)),
            linewidth=2,
            zorder=2,
        )
    )


def layout_geom():
    sc = layout_scale(SW, SH)
    margin_x = max(8, int(LAYOUT_MARGIN_X * sc))
    margin_y = max(8, int(LAYOUT_MARGIN_Y * sc))
    left_cx, right_cx = -SW / 4.0, SW / 4.0
    half_inner_w = SW / 2.0 - 2.0 * margin_x
    max_panel_h = SH - 2.0 * margin_y
    pw, ph = procedural_panel_size(half_inner_w, max_panel_h)
    return sc, left_cx, right_cx, pw, ph


def build_exp1_letters(cx, cy, pw, ph, include_t, rng):
    n_cols, n_rows = search_panel_grid_dims(pw, ph)
    cell_w = pw / float(n_cols)
    cell_h = ph / float(n_rows)
    letter_h = min(cell_w, cell_h) * 0.68
    n_grid = n_cols * n_rows
    n_items = max(SEARCH_PANEL_STIM_COUNT_MIN, int(n_grid * SEARCH_PANEL_STIM_COUNT_FRAC))
    min_d = letter_h * 0.82
    inset = max(letter_h * 0.38, 6.0)
    pos = scatter_positions(cx, cy, pw, ph, n_items, min_d, inset, rng)
    if not pos:
        return [], letter_h, None
    rng.shuffle(pos)
    t_index = rng.randrange(len(pos)) if include_t else -1
    items = []
    t_xy = None
    for i, (x, y) in enumerate(pos):
        ch = "T" if include_t and i == t_index else "L"
        ori = float(rng.choice((0, 90, 180, 270)))
        col = psy(rng.choice(GRAYS_FOR_L))
        items.append((ch, x, y, ori, col))
        if ch == "T":
            t_xy = (x, y)
    return items, letter_h, t_xy


def build_exp2_letters(cx, cy, pw, ph, n_l, include_t, rng, hide_n=0):
    n_cols, n_rows = search_panel_grid_dims(pw, ph)
    cell_w = pw / float(n_cols)
    cell_h = ph / float(n_rows)
    letter_h = min(cell_w, cell_h) * 0.68
    n_slots = n_l + (1 if include_t else 0)
    min_d = letter_h * 0.82
    inset = max(letter_h * 0.38, 6.0)
    pos = scatter_positions(cx, cy, pw, ph, n_slots, min_d, inset, rng)
    while len(pos) < n_slots:
        hw = max(pw / 2.0 - inset, 8.0)
        hh = max(ph / 2.0 - inset, 8.0)
        pos.append((cx + rng.uniform(-hw, hw), cy + rng.uniform(-hh, hh)))
    t_slot = rng.randrange(n_slots) if include_t else -1
    items = []
    t_xy = None
    l_indices = []
    for i in range(n_slots):
        x, y = pos[i]
        if include_t and i == t_slot:
            ch = "T"
            t_xy = (x, y)
        else:
            ch = "L"
            l_indices.append(i)
        ori = float(rng.choice((0, 90, 180, 270)))
        col = psy(rng.choice(GRAYS_FOR_L))
        items.append((ch, x, y, ori, col, True))
    if hide_n > 0 and l_indices:
        rng2 = random.Random(rng.random())
        rng2.shuffle(l_indices)
        for i in l_indices[: min(hide_n, len(l_indices))]:
            ch, x, y, ori, col, _ = items[i]
            items[i] = (ch, x, y, ori, col, False)
    visible = [(ch, x, y, ori, col) for ch, x, y, ori, col, vis in items if vis]
    return visible, letter_h, t_xy


def draw_hourglass(ax, cx, cy, sc, fill=None, line=None):
    fill_c = psy(fill or EXP2_INACTIVE_SIDE_FILL)
    line_c = psy(line or EXP2_INACTIVE_SIDE_LINE)
    side = max(36.0, 52.0 * sc)
    ax.add_patch(
        Rectangle(
            (cx - side / 2.0, cy - side / 2.0),
            side,
            side,
            facecolor=fill_c,
            edgecolor=line_c,
            linewidth=max(1.0, 2.0 * sc),
            zorder=4,
        )
    )


def draw_fixation_cross(ax, sc):
    arm = max(14.0, 22.0 * sc)
    bar = max(2.0, 4.0 * sc)
    col = psy(FIXATION_GRAY)
    ax.add_patch(Rectangle((-arm, -bar / 2.0), arm * 2, bar, facecolor=col, edgecolor="none", zorder=5))
    ax.add_patch(Rectangle((-bar / 2.0, -arm), bar, arm * 2, facecolor=col, edgecolor="none", zorder=5))


def draw_instructions_block(ax, text, y, height_px, wrap_w_px, bold=True, color=(1, 1, 1)):
    fs = height_px * 72.0 / DPI_SCREEN
    ax.text(
        0,
        y,
        text,
        fontsize=fs,
        fontname=FONT,
        fontweight="bold" if bold else "normal",
        color=color,
        ha="center",
        va="center",
        linespacing=1.35,
        zorder=6,
        wrap=False,
    )


def draw_example_panel(ax, cx, cy, pw, ph):
    rng = random.Random(12345)
    ax.add_patch(
        Rectangle(
            (cx - (pw + 6) / 2.0, cy - (ph + 6) / 2.0),
            pw + 6,
            ph + 6,
            facecolor=psy(INSTRUCTIONS_PREVIEW_BOX_FILL),
            edgecolor=psy(INSTRUCTIONS_PREVIEW_BOX_LINE),
            linewidth=2,
            zorder=3,
        )
    )
    n_items = max(14, min(24, int(min(pw, ph) / 11.0)))
    letter_h = max(12.0, min(pw, ph) / 7.5)
    pos = scatter_positions(cx, cy, pw, ph, n_items, letter_h * 0.82, max(letter_h * 0.35, 4.0), rng)
    rng.shuffle(pos)
    t_index = rng.randrange(len(pos))
    for i, (x, y) in enumerate(pos):
        if i == t_index:
            draw_letter(ax, "T", x, y, letter_h, psy(INSTRUCTIONS_PREVIEW_TARGET_GREEN), rng.choice((0, 90, 180, 270)))
        else:
            draw_letter(ax, "L", x, y, letter_h, psy(rng.choice(GRAYS_FOR_L)), rng.choice((0, 90, 180, 270)))


def screen_instructions_exp1():
    fig, ax = new_screen("instrucoes_exp1")
    h_title, h_body, h_footer = instruction_font_heights(SH)
    y_title, y_intro, y_task = SH * 0.34, SH * 0.24, SH * 0.13
    y_example, y_rules, y_footer = SH * -0.05, SH * -0.26, SH * -0.38
    ex_w, ex_h = instruction_example_panel_size(SW, SH, frac=0.26)
    draw_instructions_block(ax, "LEIA AS INSTRUÇÕES COM ATENÇÃO!", y_title, h_title, 0)
    draw_instructions_block(
        ax,
        "Sua tarefa é encontrar a letra T entre várias letras L e indicar em qual lado ela estava.\n"
        "1. PREPARAÇÃO: Olhe para o alvo central até ele desaparecer. Depois, olhe para\n"
        "a esquerda ou para a direita para escolher por onde começar.",
        y_intro,
        h_body,
        0,
    )
    draw_instructions_block(
        ax,
        "2. BUSCA: Apenas um lado fica visível por vez. Para trocar, olhe para o lado vazio e aguarde.\n"
        "Procure o T entre os L (exemplo abaixo). O verde é só uma ajuda nesta ilustração:\n"
        "durante a tarefa, todas as letras aparecerão em tons de cinza.",
        y_task,
        h_body,
        0,
    )
    draw_example_panel(ax, 0.0, y_example, ex_w, ex_h)
    draw_instructions_block(
        ax,
        "3. RESPOSTA: Ao encontrar o T, mantenha o olhar sobre ele e pressione ESPAÇO.\n"
        "Depois, indique o lado em que ele estava:  ←  ESQUERDA    |    DIREITA  →\n"
        "A tela ficará verde se você acertar e cinza se errar.\n"
        "Tente acertar o máximo possível.",
        y_rules,
        h_body,
        0,
    )
    draw_instructions_block(ax, "PRESSIONE A BARRA DE ESPAÇO PARA COMEÇAR.", y_footer, h_footer, 0)
    return fig


def screen_instructions_exp2():
    fig, ax = new_screen("instrucoes_exp2")
    h_title, h_body, h_footer = instruction_font_heights(SH)
    draw_instructions_block(ax, "LEIA AS INSTRUÇÕES COM ATENÇÃO!", SH * 0.36, h_title, 0)
    draw_instructions_block(
        ax,
        "Sua tarefa é ganhar pontos encontrando a letra T entre várias letras L.\n"
        "1. BUSCA: Há duas áreas, uma à esquerda e outra à direita, mas apenas uma fica visível por vez.\n"
        "Para trocar de área, olhe para o lado vazio e aguarde. Em cada área existe um T.",
        SH * 0.22,
        h_body,
        0,
    )
    ex_w, ex_h = instruction_example_panel_size(SW, SH, frac=0.28)
    draw_example_panel(ax, 0.0, SH * -0.02, ex_w, ex_h)
    draw_instructions_block(
        ax,
        "O T verde é só uma ajuda nesta ilustração; durante a tarefa, todas as letras terão tons de cinza.\n"
        "2. PONTUAR: Ao encontrar o T, mantenha o olhar sobre ele e pressione ESPAÇO. Cada acerto vale 1 ponto.\n"
        "3. ATENÇÃO: As letras L desaparecem aos poucos. Após um ponto, somente a área em que você\n"
        "pontuou é reiniciada; a outra continua como estava.\n"
        "Tente ganhar o maior número de pontos possível.",
        SH * -0.24,
        h_body,
        0,
    )
    draw_instructions_block(
        ax, "PRESSIONE A BARRA DE ESPAÇO PARA INICIAR A SESSÃO.", SH * -0.38, h_footer, 0
    )
    return fig


def screen_drift():
    fig, ax = new_screen("drift")
    sc = layout_scale(SW, SH)
    draw_fixation_cross(ax, sc)
    return fig


def screen_region_choice():
    fig, ax = new_screen("escolha_metade")
    sc = layout_scale(SW, SH)
    neutral_hw = region_choice_neutral_half_w(SW)
    neutral_rect_h = SH * 0.5
    outline_w = max(1, int(1.5 * sc))
    hl = max(44.0, 58.0 * sc)
    arrow_inset = max(neutral_hw + hl * 0.35, SW * 0.18)
    left_x = min(-arrow_inset, -neutral_hw - hl * 0.25)
    right_x = max(arrow_inset, neutral_hw + hl * 0.25)
    line_thick = float(max(2.0, outline_w))
    ax.add_patch(
        Rectangle(
            (-neutral_hw, -neutral_rect_h / 2.0),
            2.0 * neutral_hw,
            neutral_rect_h,
            facecolor=BG,
            edgecolor="none",
            zorder=2,
        )
    )
    ax.add_patch(
        Rectangle(
            (-neutral_hw, -neutral_rect_h / 2.0),
            line_thick,
            neutral_rect_h,
            facecolor="white",
            edgecolor="none",
            zorder=3,
        )
    )
    ax.add_patch(
        Rectangle(
            (neutral_hw - line_thick, -neutral_rect_h / 2.0),
            line_thick,
            neutral_rect_h,
            facecolor="white",
            edgecolor="none",
            zorder=3,
        )
    )
    fs_arr = hl * 72.0 / DPI_SCREEN
    ax.text(left_x, 0, "◄", fontsize=fs_arr, color=(0.775, 0.775, 0.775), ha="center", va="center", fontname=FONT)
    ax.text(right_x, 0, "►", fontsize=fs_arr, color=(0.775, 0.775, 0.775), ha="center", va="center", fontname=FONT)
    cue_h = max(15.0, min(22.0 * sc, neutral_rect_h * 0.14))
    ax.text(
        0,
        0,
        "Olhe para a esquerda\nou para a direita\npara iniciar.",
        fontsize=cue_h * 72.0 / DPI_SCREEN,
        color="white",
        ha="center",
        va="center",
        fontname=FONT,
        fontweight="bold",
        linespacing=1.25,
        zorder=5,
    )
    return fig


def _t_is_presentable(t_xy, cx, pw, ph, lh):
    if t_xy is None:
        return False
    x, y = t_xy
    return (
        abs(x - cx) < pw * 0.32
        and abs(y) < ph * 0.28
        and abs(x - (cx - pw / 2.0)) > lh * 3.2
        and abs(x - (cx + pw / 2.0)) > lh * 3.2
    )


def screen_foraging_exp1(annotate_t: bool = False, active="left"):
    fig, ax = new_screen("forrageamento_exp1" + ("_anotado" if annotate_t else ""))
    sc, left_cx, right_cx, pw, ph = layout_geom()
    items_l, lh, t_xy = [], 20.0, None
    for seed in range(20260918, 20261120):
        rng_l = random.Random(seed)
        items_l, lh, t_xy = build_exp1_letters(left_cx, 0.0, pw, ph, include_t=True, rng=rng_l)
        if not annotate_t:
            break
        if _t_is_presentable(t_xy, left_cx, pw, ph, lh):
            items_l = [
                (ch, x, y, 0.0 if ch == "T" else ori, col) for ch, x, y, ori, col in items_l
            ]
            break
    rng_r = random.Random(20260919)
    items_r, _, _ = build_exp1_letters(right_cx, 0.0, pw, ph, include_t=False, rng=rng_r)
    if active == "left":
        draw_panel_border(ax, left_cx, 0.0, pw, ph)
        for ch, x, y, ori, col in items_l:
            draw_letter(ax, ch, x, y, lh, col, ori)
        draw_hourglass(ax, right_cx, 0.0, sc)
        if annotate_t and t_xy:
            circ = Circle(t_xy, lh * 1.35, fill=False, edgecolor="#e8c547", linewidth=2.4, zorder=8)
            circ.set_linestyle((0, (5, 3)))
            ax.add_patch(circ)
            ax.text(
                t_xy[0],
                t_xy[1] + lh * 2.1,
                "T (alvo)",
                color="#e8c547",
                fontsize=13,
                fontname=FONT,
                fontweight="bold",
                ha="center",
                va="bottom",
                zorder=9,
                path_effects=[pe.withStroke(linewidth=3, foreground="#1a1a1a")],
            )
    else:
        draw_panel_border(ax, right_cx, 0.0, pw, ph)
        for ch, x, y, ori, col in items_r:
            draw_letter(ax, ch, x, y, lh, col, ori)
        draw_hourglass(ax, left_cx, 0.0, sc)
    return fig


def screen_cod_grey():
    fig, ax = new_screen("cod_pausa")
    return fig


def screen_discrete_choice():
    fig, ax = new_screen("escolha_discreta")
    sc = layout_scale(SW, SH)
    ax.text(
        0,
        SH * 0.22,
        "Em que lado estava a letra T (alvo)?",
        fontsize=max(18.0, 28 * sc) * 72.0 / DPI_SCREEN,
        color=(0.825, 0.825, 0.825),
        ha="center",
        va="center",
        fontname=FONT,
        fontweight="bold",
    )
    hl = max(36.0, 48.0 * sc)
    fs = hl * 0.55 * 72.0 / DPI_SCREEN
    ax.text(-SW * 0.28, -SH * 0.08, "◄ Esquerda", fontsize=fs, color=(0.725, 0.725, 0.725), ha="center", va="center", fontname=FONT)
    ax.text(SW * 0.28, -SH * 0.08, "Direita ►", fontsize=fs, color=(0.725, 0.725, 0.725), ha="center", va="center", fontname=FONT)
    return fig


def screen_feedback(correct: bool):
    fig = plt.figure(figsize=(SW / DPI_SCREEN, SH / DPI_SCREEN), dpi=DPI_SCREEN)
    color = psy(CORRECT_FEEDBACK_COLOR) if correct else BG
    fig.patch.set_facecolor(color)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-SW / 2.0, SW / 2.0)
    ax.set_ylim(-SH / 2.0, SH / 2.0)
    ax.axis("off")
    ax.set_facecolor(color)
    return fig


def screen_exp2_foraging(decayed=False, annotate=False):
    tag = "exp2_decaimento" if decayed else ("exp2_anotado" if annotate else "exp2_forrageamento")
    fig, ax = new_screen(tag)
    sc, left_cx, right_cx, pw, ph = layout_geom()
    items, lh, t_xy = [], 20.0, None
    for seed in range(42, 240):
        rng = random.Random(seed)
        hide = 24 if decayed else 0
        items, lh, t_xy = build_exp2_letters(
            left_cx, 0.0, pw, ph, n_l=38, include_t=True, rng=rng, hide_n=hide
        )
        if not annotate:
            break
        if _t_is_presentable(t_xy, left_cx, pw, ph, lh):
            items = [(ch, x, y, 0.0 if ch == "T" else ori, col) for ch, x, y, ori, col in items]
            break
    draw_panel_border(ax, left_cx, 0.0, pw, ph)
    for ch, x, y, ori, col in items:
        draw_letter(ax, ch, x, y, lh, col, ori)
    draw_hourglass(ax, right_cx, 0.0, sc)
    pts = "Pontos: 3" if decayed else "Pontos: 0"
    ax.text(
        0.0,
        SH * 0.42,
        pts,
        fontsize=max(18.0, 26.0 * sc) * 72.0 / DPI_SCREEN,
        color=psy((0.95, 0.95, 0.55)),
        ha="center",
        va="center",
        fontname=FONT,
        fontweight="bold",
        zorder=10,
    )
    if annotate and t_xy:
        circ = Circle(t_xy, lh * 1.35, fill=False, edgecolor="#e8c547", linewidth=2.4, zorder=8)
        circ.set_linestyle((0, (5, 3)))
        ax.add_patch(circ)
        ax.text(
            t_xy[0],
            t_xy[1] + lh * 2.1,
            "T (alvo)",
            color="#e8c547",
            fontsize=13,
            fontname=FONT,
            fontweight="bold",
            ha="center",
            va="bottom",
            zorder=9,
            path_effects=[pe.withStroke(linewidth=3, foreground="#1a1a1a")],
        )
    return fig


def add_slide(pdf: PdfPages, title: str, subtitle: str, img_path: Optional[str], notes: str = "", extra_img: Optional[str] = None):
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), dpi=160)
    fig.patch.set_facecolor(SLIDE_BG)
    fig.text(0.045, 0.93, title, fontsize=22, fontname=FONT, fontweight="bold", color=SLIDE_INK, va="top")
    if subtitle:
        fig.text(0.045, 0.875, subtitle, fontsize=12.5, fontname=FONT, color=SLIDE_MUTED, va="top")
    fig.add_artist(
        plt.Line2D([0.045, 0.22], [0.855, 0.855], transform=fig.transFigure, color=SLIDE_ACCENT, linewidth=3, solid_capstyle="butt")
    )
    if img_path and extra_img:
        ax1 = fig.add_axes([0.045, 0.14, 0.445, 0.68])
        ax2 = fig.add_axes([0.51, 0.14, 0.445, 0.68])
        for ax, p in ((ax1, img_path), (ax2, extra_img)):
            im = plt.imread(p)
            ax.imshow(im)
            ax.axis("off")
            for sp in ax.spines.values():
                sp.set_visible(True)
                sp.set_color("#cfcfc8")
                sp.set_linewidth(0.8)
    elif img_path:
        ax = fig.add_axes([0.12, 0.16, 0.76, 0.66])
        im = plt.imread(img_path)
        ax.imshow(im)
        ax.axis("off")
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_color("#cfcfc8")
            sp.set_linewidth(0.8)
    if notes:
        fig.text(0.045, 0.055, notes, fontsize=11, fontname=FONT, color=SLIDE_MUTED, va="bottom", wrap=True)
    fig.text(0.96, 0.03, "Forrageamento visual · PsychoPy", fontsize=8, fontname=FONT, color="#9a9a94", ha="right")
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def slide_title(pdf: PdfPages):
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), dpi=160)
    fig.patch.set_facecolor(SLIDE_BG)
    fig.add_artist(
        plt.Rectangle((0, 0), 0.018, 1, transform=fig.transFigure, color=SLIDE_ACCENT, zorder=10)
    )
    fig.text(0.07, 0.58, "Forrageamento visual", fontsize=36, fontname=FONT, fontweight="bold", color=SLIDE_INK)
    fig.text(0.07, 0.49, "Como as tarefas aparecem no ecrã", fontsize=20, fontname=FONT, color=SLIDE_MUTED)
    fig.text(
        0.07,
        0.28,
        "Figuras reconstruídas a partir do código (1680 × 1050 px, fundo cinza).\n"
        "Experimento 1: trials discretos  ·  Experimento 2: sessão contínua com pontos e decaimento.\n"
        "Nas imagens “como o participante vê”, o T não está destacado — é cinza como os L.",
        fontsize=13,
        fontname=FONT,
        color=SLIDE_MUTED,
        linespacing=1.55,
        va="top",
    )
    fig.text(0.07, 0.08, "Material para apresentação  ·  não é captura de sessão real", fontsize=10, fontname=FONT, color="#9a9a94")
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def slide_flow_exp1(pdf: PdfPages):
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), dpi=160)
    fig.patch.set_facecolor(SLIDE_BG)
    fig.text(0.045, 0.93, "Experimento 1 — fluxo de um trial", fontsize=22, fontname=FONT, fontweight="bold", color=SLIDE_INK, va="top")
    fig.text(0.045, 0.875, "Cada trial passa pelas mesmas telas, nesta ordem.", fontsize=12.5, fontname=FONT, color=SLIDE_MUTED, va="top")
    fig.add_artist(
        plt.Line2D([0.045, 0.22], [0.855, 0.855], transform=fig.transFigure, color=SLIDE_ACCENT, linewidth=3)
    )
    steps = [
        ("1", "Instruções", "Só no início\nda sessão"),
        ("2", "Fixação", "300 ms no\ncentro"),
        ("3", "Escolha\nde metade", "Olhar esq.\nou dir."),
        ("4", "Busca L/T", "Um painel\nvisível"),
        ("5", "Troca COD", "600 ms + 400 ms\ncinza"),
        ("6", "Qual lado\ndo T?", "Setas ← →"),
        ("7", "Feedback", "Verde / cinza\n1 s"),
    ]
    xs = [0.10, 0.24, 0.38, 0.52, 0.66, 0.80, 0.94]
    for i, ((n, title, sub), x) in enumerate(zip(steps, xs)):
        ax = fig.add_axes([x - 0.055, 0.42, 0.11, 0.32])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.add_patch(FancyBboxPatch((0.05, 0.08), 0.9, 0.84, boxstyle="round,pad=0.04,rounding_size=0.08", facecolor="white", edgecolor="#d5d5ce", linewidth=1))
        ax.text(0.5, 0.78, n, ha="center", va="center", fontsize=16, fontweight="bold", fontname=FONT, color=SLIDE_ACCENT)
        ax.text(0.5, 0.52, title, ha="center", va="center", fontsize=10.5, fontweight="bold", fontname=FONT, color=SLIDE_INK, linespacing=1.2)
        ax.text(0.5, 0.24, sub, ha="center", va="center", fontsize=8.5, fontname=FONT, color=SLIDE_MUTED, linespacing=1.25)
        if i < len(xs) - 1:
            fig.text(x + 0.058, 0.58, "→", fontsize=16, color=SLIDE_ACCENT, ha="center", va="center", fontname=FONT)
    fig.text(
        0.045,
        0.18,
        "Na busca, só um lado mostra letras; o outro mostra um quadrado cinza. Olhar para o lado inativo\n"
        "durante 600 ms troca o painel visível (COD), com uma pausa cinza de 400 ms. O T está num único lado.\n"
        "Confirmação: 500 ms de olhar na AOI do T + Espaço. Depois pergunta de escolha discreta.",
        fontsize=12,
        fontname=FONT,
        color=SLIDE_MUTED,
        va="top",
        linespacing=1.45,
    )
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def slide_flow_exp2(pdf: PdfPages):
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), dpi=160)
    fig.patch.set_facecolor(SLIDE_BG)
    fig.text(0.045, 0.93, "Experimento 2 — sessão contínua", fontsize=22, fontname=FONT, fontweight="bold", color=SLIDE_INK, va="top")
    fig.text(0.045, 0.875, "Não há trials nem pergunta de lado. Começa no painel esquerdo.", fontsize=12.5, fontname=FONT, color=SLIDE_MUTED, va="top")
    fig.add_artist(
        plt.Line2D([0.045, 0.22], [0.855, 0.855], transform=fig.transFigure, color=SLIDE_ACCENT, linewidth=3)
    )
    bullets = [
        ("Dois painéis com T", "Há um T em cada lado. Só o painel ativo (olhar) mostra as letras; o outro tem o quadrado cinza."),
        ("Pontos", "Olhar no T ~500 ms + Espaço → +1 ponto. Só esse painel é reposto (novos L + novo layout)."),
        ("Decaimento", "A cada 1 s, 6 letras L somem em cada painel (os dois, mesmo o invisível)."),
        ("Troca de lado", "Igual ao Exp1: olhar na metade inativa 600 ms → pausa cinza 400 ms → o outro painel aparece."),
        ("Duração", "Sessão contínua (~7 min no CSV). HUD amarelo no topo: “Pontos: N”."),
    ]
    y = 0.78
    for title, body in bullets:
        fig.text(0.07, y, title, fontsize=13.5, fontname=FONT, fontweight="bold", color=SLIDE_INK, va="top")
        fig.text(0.07, y - 0.038, body, fontsize=12, fontname=FONT, color=SLIDE_MUTED, va="top")
        y -= 0.125
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    os.makedirs(PNG_DIR, exist_ok=True)
    paths = {}
    print("A gerar PNG das telas…")
    paths["instr1"] = save_screen(screen_instructions_exp1(), "01_exp1_instrucoes.png")
    paths["drift"] = save_screen(screen_drift(), "02_exp1_fixacao.png")
    paths["choice"] = save_screen(screen_region_choice(), "03_exp1_escolha_metade.png")
    paths["forage"] = save_screen(screen_foraging_exp1(False), "04_exp1_busca.png")
    paths["forage_ann"] = save_screen(screen_foraging_exp1(True), "05_exp1_busca_T_marcado.png")
    paths["cod"] = save_screen(screen_cod_grey(), "06_exp1_pausa_COD.png")
    paths["disc"] = save_screen(screen_discrete_choice(), "07_exp1_qual_lado.png")
    paths["ok"] = save_screen(screen_feedback(True), "08_exp1_feedback_acerto.png")
    paths["err"] = save_screen(screen_feedback(False), "09_exp1_feedback_erro.png")
    paths["instr2"] = save_screen(screen_instructions_exp2(), "10_exp2_instrucoes.png")
    paths["exp2"] = save_screen(screen_exp2_foraging(False, False), "11_exp2_busca.png")
    paths["exp2_ann"] = save_screen(screen_exp2_foraging(False, True), "12_exp2_busca_T_marcado.png")
    paths["exp2_dec"] = save_screen(screen_exp2_foraging(True, False), "13_exp2_decaimento.png")

    pdf_path = os.path.join(OUT_DIR, "Forrageamento_telas_das_tarefas.pdf")
    print("A montar PDF…")
    with PdfPages(pdf_path) as pdf:
        slide_title(pdf)
        slide_flow_exp1(pdf)
        add_slide(
            pdf,
            "Experimento 1 — instruções",
            "Primeiro ecrã da sessão. O T verde é só ilustração.",
            paths["instr1"],
            "Na tarefa real, L e T são todos cinza (7 tons). Confirmação: olhar no T + Espaço; depois setas.",
        )
        add_slide(
            pdf,
            "Experimento 1 — fixação (drift)",
            "Cruz cinza no centro. 300 ms de olhar contínuo dentro do círculo (raio ~60 px na referência).",
            paths["drift"],
            "Fundo RGB PsychoPy (−0.4, −0.4, −0.4). Distância olhos–ecrã no protocolo: 70 cm.",
        )
        add_slide(
            pdf,
            "Experimento 1 — escolha de metade",
            "Faixa central neutra (linhas brancas). Olhar à esquerda ou à direita inicia o trial.",
            paths["choice"],
            "800 ms de espera + 200 ms de permanência na banda escolhida. A faixa central não conta.",
        )
        add_slide(
            pdf,
            "Experimento 1 — busca (como o participante vê)",
            "Painel esquerdo ativo (L + um T cinza). Quadrado cinza no lado inativo.",
            paths["forage"],
            "O T não está destacado. Um único T por trial, num dos lados (razão L/R da sessão).",
        )
        add_slide(
            pdf,
            "Experimento 1 — o mesmo ecrã, com o T assinalado",
            "Círculo amarelo só para a apresentação — não aparece na tarefa.",
            paths["forage_ann"],
            "Útil para explicar “encontrar o T entre os L”. Na sessão, todas as letras são cinza.",
        )
        add_slide(
            pdf,
            "Experimento 1 — pausa COD",
            "Olhar 600 ms no lado inativo → ecrã vazio (mesmo cinza de fundo) durante 400 ms.",
            paths["cod"],
            "Depois o outro painel torna-se o visível. COD = change of display / troca de metade.",
        )
        add_slide(
            pdf,
            "Experimento 1 — escolha discreta",
            "Pergunta após encontrar o T (ou esgotar o tempo de procura).",
            paths["disc"],
            "Teclas ← / →. Não há rato. A seguir, feedback de 1 s.",
        )
        add_slide(
            pdf,
            "Experimento 1 — feedback",
            "Esquerda: acerto (verde, 1 s). Direita: erro (mesmo cinza do fundo, 1 s).",
            paths["ok"],
            extra_img=paths["err"],
            notes="Verde = CORRECT_FEEDBACK_COLOR (−0.35, 0.78, −0.35). Cinza = BACKGROUND_COLOR.",
        )
        slide_flow_exp2(pdf)
        add_slide(
            pdf,
            "Experimento 2 — instruções",
            "Pontos, dois T (um em cada área), decaimento dos L.",
            paths["instr2"],
            "Não há escolha inicial de metade nem pergunta de setas após cada alvo.",
        )
        add_slide(
            pdf,
            "Experimento 2 — busca (como o participante vê)",
            "Começa à esquerda. HUD “Pontos” no topo. Quadrado no lado inativo.",
            paths["exp2"],
            "Exemplo sessão 1 (20vs60): 38 L à esquerda + 1 T. À direita (invisível) haveria 112 L + 1 T.",
        )
        add_slide(
            pdf,
            "Experimento 2 — T assinalado (só apresentação)",
            "O círculo amarelo não existe na tarefa.",
            paths["exp2_ann"],
            "Ambos os painéis têm T o tempo todo. O desenho manipula quantos L há em cada lado.",
        )
        add_slide(
            pdf,
            "Experimento 2 — após decaimento",
            "Menos L no painel (os L vão desaparecendo ~6 por segundo por lado).",
            paths["exp2_dec"],
            "Depois de um ponto, só o painel reforçado volta ao número inicial de L; o outro continua a decair.",
        )

    print("PNG:", PNG_DIR)
    print("PDF:", pdf_path)
    print("Ficheiros:")
    for fn in sorted(os.listdir(PNG_DIR)):
        print(" ", fn)


if __name__ == "__main__":
    main()
