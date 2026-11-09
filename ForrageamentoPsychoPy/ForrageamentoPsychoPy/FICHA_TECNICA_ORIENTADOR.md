# Ficha técnica — Forrageamento visual (PsychoPy)

Documento de apoio para orientação de dissertação. Parâmetros extraídos do código (`forrageamento_exp1.py`, `forrageamento_exp2_session.py`) e dos CSV em `conditions/`, na versão do repositório em que este ficheiro existe.

### Índice

| Secção | Conteúdo |
|--------|----------|
| **§1** | Ambiente e visualização (comum) |
| **§2** | Parâmetros comuns (painel, L/T, AOI, marcador) |
| **§3** | **Experimento 1** — trials, fases, CSV, frequências Left/Right |
| **§4** | **Experimento 2** — visão geral, fluxo, CSV de sessões, tabela 1–10, painéis, decaimento *k*, visual/HUD, exportação (eventos + resumo) |
| **§5** | Nota sobre “probabilidade do lado” (redacção método) |
| **§6** | Nomes dos ficheiros de dados |

---

## 1. Ambiente e visualização

| Aspeto | Valor / notas |
|--------|----------------|
| **PsychoPy** | Coder; compatível com versões indicadas no cabeçalho do script principal |
| **Distância olhos–ecrã (protocolo)** | **70 cm** (`VIEWING_DISTANCE_CM`) — registada em TXT/XLSX, mensagens EyeLink e texto das instruções |
| **Janela (defeito)** | `1680×1050` px (`DEFAULT_WINDOW_W` / `H`); ecrã completo; unidades de estímulo **pix** |
| **Fundo** | `BACKGROUND_COLOR` = (−0.4, −0.4, −0.4) (RGB normalizado PsychoPy −1…1) |
| **Escala de layout** | `layout_scale(sw,sh) = min(sw/1280, sh/768)` — referência `REF_LAYOUT_W×H` = **1280×768** |
| **Margens do painel** | `LAYOUT_MARGIN_X` = 16, `LAYOUT_MARGIN_Y` = 24 (multiplicadas por `sc`, mínimo 8 px) |
| **Fonte (instruções)** | `INSTRUCTIONS_UI_FONT` = Arial |
| **Registo do olhar** | EyeLink (IP configurável, p.ex. `FORR_EYELINK_HOST`); modo **dummy** = rato como proxy do olhar |
| **Sair e gravar** | Sequência **T** e de seguida **Esc** (não confundir com Esc sozinho) |
| **Pausa / recalibração EyeLink** | Teclas **X** ou **C** (com tracker e janela activos): ecrã de pausa → **Espaço** abre `doTrackerSetup` com `EyeLinkCoreGraphicsPsychoPy`; depois retoma gravação com `SYNCTIME`. Sem efeito em modo dummy. |

---

## 2. Parâmetros comuns aos dois experimentos (estímulos L / T)

### 2.1 Tamanho e disposição do painel

| Aspeto | Definição no código |
|--------|----------------------|
| **Tamanho do painel** | `procedural_panel_size`: proporção nativa `PANEL_NAT_FALLBACK` = **(630, 800)** px, *contain* na “metade útil” (largura interna da metade do ecrã × altura útil). Mesmo tamanho esq./dir. |
| **Grelha lógica** (cols×rows) | `cell_base = max(36, min(56, min(panel_w, panel_h)/10))`; `n_cols = max(5, int(panel_w/cell_base))`; `n_rows = max(6, int(panel_h/(cell_base×1.05)))` |
| **Altura do glifo (L e T)** | `letter_h = min(cell_w, cell_h) × 0.68` com `cell_w = panel_w/n_cols`, `cell_h = panel_h/n_rows` |
| **Letras** | `TextStim`, `bold=True`, cor e orientação sorteadas |
| **Contorno do painel** | `Rect` com +4 px face ao painel; `lineColor` (0.12,0.12,0.12); `lineWidth` 2; sem preenchimento |
| **Dispersão** | `_scatter_positions_in_rect`: distância mínima entre centros = `letter_h × 0.82`; **inset** = `max(letter_h×0.38, 6)` px |

### 2.2 Aparência (L, T na tarefa)

| Aspeto | Valor |
|--------|--------|
| **Cinzas** | `GRAYS_FOR_L`: 7 níveis (−0.22 … 0.38) em passos de ~0.10; **uma cor por letra** (incl. T) |
| **Orientação** | 0°, 90°, 180° ou 270° (sorteio uniforme) |
| **AOI de confirmação do T** | Meia-largura `max(22 px, letter_h×0.78)`; meia-altura `max(22 px, letter_h×0.88)` (`TARGET_T_AOI_*`) |
| **Tempo de fixação + resposta** | `TARGET_FIX_MS` = **500 ms** com olhar na AOI + tecla **Espaço** para confirmar |

### 2.3 Marcador do lado “inativo” (quadrado)

No painel não visível em determinado momento, mostra-se um `Rect` (apelido histórico “ampulheta”):

| Uso | Preenchimento | Contorno |
|-----|----------------|----------|
| **Exp1 e Exp2** (implementação actual) | `EXP2_INACTIVE_SIDE_FILL` = (−0.52, −0.52, −0.52) | `EXP2_INACTIVE_SIDE_LINE` = (−0.64, −0.64, −0.64) |

*(Constantes `SIDE_MARKER_*` mais escuras mantêm-se no código como defeito genérico de `make_hourglass_stim` se não se passar cor.)*

---

## 3. Experimento 1 (trials discretos)

### 3.1 Estrutura de um trial

| Fase | Descrição |
|------|-----------|
| **Drift** | Fixação no centro; AOI circular raio `max(24, DRIFT_AOI_RADIUS×sc)` com `DRIFT_AOI_RADIUS` = 60 na referência |
| **Critério drift** | `DRIFT_FIX_MS` = **300 ms** contínuos dentro do círculo |
| **Escolha de metade** | Após `PRE_CHOICE_HOLD_MS` = **800 ms**, permanência na banda esquerda/direita ≥ `REGION_CHOICE_MIN_DWELL_MS` = **200 ms**; faixa central neutra (`REGION_CHOICE_NEUTRAL_HALF_W_FRAC` = 0.09, mín. `REGION_CHOICE_NEUTRAL_HALF_W_MIN_PX` = 72 px na largura neutra) |
| **Forrageamento** | Uma metade **ativa** com painel cheio; a outra metade mostra só o marcador cinza |
| **COD** | Olhar na metade **inativa** ≥ `COD_FIX_MS` = **600 ms** → pausa cinza `COD_GREY_MS` = **400 ms** (`BACKGROUND_COLOR`, sem painéis) → troca do lado ativo; variável `cod_switch_count` |
| **Alvo** | No lado onde está o T (`target_side`), olhar na AOI do T ≥ 500 ms + **Espaço**; ou fim automático após `search_max_s` (configurável no arranque, predef. 120 s, desde `foraging_start`, inclui pausas COD) |
| **Escolha discreta** | Pergunta lateral do T; teclas setas (← / →); feedback **1 s** ecrã cheio: **verde** se correta, **cinza** se errada |

### 3.2 Quantidade de estímulos no painel (Exp1)

Função **`build_search_panel_stims`**:

- `n_grid = n_cols × n_rows`
- `n_items = max(SEARCH_PANEL_STIM_COUNT_MIN, int(n_grid × SEARCH_PANEL_STIM_COUNT_FRAC))` com **mínimo 20** e **fração 0.75**

Interpretação: número de posições por painel **não** vem de contagens fixas por linha de CSV; emerge da grelha e da regra 75%. Num dos painéis inclui-se **um T** (no lado correto); no outro, **só L** (`n_items` letras).

### 3.3 Condicionamento e “sessão” (Exp1)

| Aspeto | Detalhe |
|--------|---------|
| **Índice de razões** | `conditions/conditions_exp1_sessions.csv` — sessão 1–5 → razão L/R do S+ |
| **CSV de trials por razão** | `conditions/conditions_exp1_<rótulo>.csv` (ex.: `conditions_exp1_10vs90.csv`) |
| **Campo `correctkey`** | Left / Right = lado do T (S+) naquele trial |
| **Ordem dos trials** | Por defeito **permutada** com semente determinística `trial_order_seed(participant_id, experimento, sessão, repetição)` — reprodutível |
| **Semente dos estímulos** | `stimulus_layout_seed(..., índice trial, chave condição)` — posições/orientações/cinzas |
| **Sessão no menu** | Valores **1–5**: escolhem a **razão** (e o CSV correspondente). Rótulos no diálogo: `1 — 10/90` … `5 — 90/10` |
| **Repetição** | `session_run` ≥ 1 (duas sessões independentes por razão, conforme o projeto) |
| **Override** | `--conditions caminho.csv` ignora o CSV da razão da sessão |

### 3.4 Razões L/R por sessão (desenho)

| Sessão | Rótulo | Trials Left (T) | Trials Right (T) | Total |
|--------|--------|-----------------|------------------|-------|
| 1 | 10vs90 | 12 | 108 | 120 |
| 2 | 25vs75 | 30 | 90 | 120 |
| 3 | 50vs50 | 60 | 60 | 120 |
| 4 | 75vs25 | 90 | 30 | 120 |
| 5 | 90vs10 | 108 | 12 | 120 |

`conditions_exp1.csv` (legado) = cópia de **50vs50**. A razão da sessão é gravada na coluna `ratio_label` dos CSV de saída e nas mensagens EyeLink `EXP1_RATIO_LABEL`.

*(Se o CSV for editado, atualizar estes números na tese.)*

---

## 4. Experimento 2 (sessão contínua)

Implementação principal: `forrageamento_exp2_session.py` (sessão contínua), com instruções e constantes partilhadas em `forrageamento_exp1.py` (`run_instructions_exp2`, `build_exp2_fixed_lt_panel`, `exp2_decay_k_per_panel`, etc.). Arranque pelo mesmo script principal (`forrageamento_exp1.py`) com `--experiment 2` ou menu “Experimento 2”.

### 4.0 Visão geral e diferenças face ao Exp1

| Aspeto | Experimento 1 | Experimento 2 |
|--------|----------------|---------------|
| **Unidade de correr** | Muitos **trials** (sequência de drift → metade → forrageamento → pergunta) | **Uma sessão contínua** até ao tempo limite ou T+Esc |
| **Escolha inicial de metade** | Sim (dwell no ecrã) | **Não** — começa no painel **esquerdo** |
| **COD** (olhar na inactiva para trocar) | `COD_FIX_MS` 600 ms + `COD_GREY_MS` 400 ms | **Igual ao Exp1** — olhar na metade inactiva ≥ 600 ms → pausa cinza 400 ms → troca de painel visível |
| **Onde está o T** | Um painel tem T, o outro só L | **Ambos** os painéis têm **L + T**; manipula-se **quantos L** por lado (`n_L_left` / `n_L_right`) |
| **Condição por “sessão”** | Sessão 1–5 escolhe **razão L/R do S+** (`conditions_exp1_sessions.csv` → CSV por razão) | Sessão 1–10 escolhe **linha** em `conditions_exp2_sessions.csv` (rácios e contagens) |
| **Decaimento de L** | Não | Sim — ver §4.5 |

**Resumo da tarefa (Exp2):** O participante vê um painel de cada vez; para trocar de metade, olha para a região inactiva (COD como no Exp1: 600 ms + 400 ms cinza). No painel visível localiza o T e confirma com **Espaço** após ~0,5 s na AOI; ganha **pontos**; os **L** decaem em **ambos** os painéis; após reforço, **só** o painel reforçado repõe L e layout; o outro **continua** a decair.

### 4.1 Fluxo de execução

1. **`run_instructions_exp2`** — texto em blocos (título “Experimento 2”, corpo, exemplo procedural L/T, regras de ponto e L, rodapé “Pressione a barra de espaço…”), mensagem EyeLink `PHASE instructions_exp2`.
2. **`run_exp2_session_wrapper`** — após Espaço nas instruções, chama **`run_continuous_exp2_session`** com a linha CSV seleccionada (`session_row`).
3. **Loop principal** — relógio de sessão; actualização do lado activo pelo olhar; ticks de decaimento por segundo; detecção de reforço (AOI T + Espaço); desenho só do painel activo + marcador cinza no outro + HUD “Pontos: N”.

**Estado inicial:** `active_side` começa em **`left`**; horas/contadores de tempo por metade (`forage_time_left_s` / `forage_time_right_s`) acumulam conforme o olhar.

### 4.2 Selecção da condição por “sessão”

| Aspeto | Detalhe |
|--------|---------|
| **Ficheiro** | `conditions/conditions_exp2_sessions.csv` |
| **Sessão no menu** | **1–10** (`SESSION_CONDITION_MAX_EXP2`) |
| **Regra** | Escolhe-se a linha cuja coluna `session` coincide com o número de sessão |

Cada linha define: `ratio_label`, `w_esq`, `w_dir`, `n_L_left`, `n_L_right`, `duration_s`, e (no CSV) `correctkey` — este último **não** coloca o T num único lado na tarefa; ambos os painéis têm T; o campo é sobretudo **metadado** exportado.

### 4.3 Tabela de condições (ficheiro actual)

| Sessão | Rótio | w_esq : w_dir | n_L esq. | n_L dir. | Duração (s) | correctkey (CSV) |
|--------|-------|---------------|----------|----------|-------------|------------------|
| 1 | 20vs60 | 20:60 | 38 | 112 | 420 | Right |
| 2 | 40vs60 | 40:60 | 60 | 90 | 420 | Right |
| 3 | 60vs60 | 60:60 | 75 | 75 | 420 | Right |
| 4 | 60vs40 | 60:40 | 90 | 60 | 420 | Left |
| 5 | 60vs20 | 60:20 | 112 | 38 | 420 | Left |
| 6–10 | (repetição do bloco 1–5) | idem | idem | idem | 420 | idem |

**Soma de L:** sempre **150** no conjunto dos dois painéis (**75 por lado** em média global; repartição conforme colunas).

**Proporção de L à esquerda (desenho):** \(n\_L\_left / 150\) — ex.: 20vs60 → 38/150 ≈ 25,3 % à esquerda e 112/150 à direita (coerente com pesos 20/(20+60) e 60/(20+60)).

### 4.4 Construção dos painéis (Exp2)

| Aspeto | Detalhe |
|--------|---------|
| **Função** | `build_exp2_fixed_lt_panel` |
| **Contagens** | `n_slots = n_L_distractors + 1` (**sempre um T** por painel) |
| **Posições** | Scatter como no Exp1, mas **sem baralhar a lista de posições** após gerada; o índice do T é `rng.randrange(n_slots)` |
| **Decaimento** | Remove apenas **L** (lista `l_stims`); o **T** mantém-se até reforço |

### 4.5 Decaimento temporal

**Constantes:** `EXP2_N_DISTRACTOR_TOTAL` = 150, `EXP2_DECAY_REF_PER_S` = 5, `EXP2_DECAY_REF_MAX_PER_SIDE` = 60.

**Taxa por painel:**

\[
k = \max\left(1,\ \mathrm{round}\left(\frac{5 \times (150/2)}{60}\right)\right) = \max(1,\mathrm{round}(6{,}25)) = 6
\]

Ou seja, **6 letras L removidas por painel** em cada **tick** (com L ainda visíveis escolhidas ao acaso entre as restantes).

**Cadência:** a partir de **t = 1 s** de relógio de sessão, **a cada 1 s** (`next_decay_at += 1`) aplica-se o tick nos dois painéis.

### 4.6 Visualização, reforço e fim de sessão

| Aspeto | Detalhe |
|--------|---------|
| **Metade activa** | `gx < 0` → painel esquerdo; caso contrário direito (dummy: posição do rato) |
| **Conteúdo** | Só o painel activo mostra L+T; o outro mostra marcador + HUD “Pontos” |
| **Reforço** | Olhar na AOI do T no lado activo ≥ 500 ms + **Espaço** → +1 ponto; **repõe** os L iniciais **só no painel reforçado** e novo layout nesse painel |
| **Duração** | Coluna `duration_s` (420 s no CSV); override opcional variável de ambiente `FORR_EXP2_DURATION_S` |
| **Fim antecipado** | `T` + `Esc` (pedido global de gravação e saída) |
| **Critério normal de fim** | Tempo de sessão ≥ `duration_s` (relógio `session_clock`) |

### 4.7 Sementes reprodutíveis e shuffle do decaimento

| Aspeto | Detalhe |
|--------|---------|
| **Layouts dos painéis** | `stimulus_layout_seed(participant_id, 2, sessão, repetição, índice de “apresentação” por lado, chave com `ratio_label`)` — novo layout após cada reforço nesse painel |
| **Ordem de remoção dos L no decaimento** | `random.Random` com semente derivada do mesmo participante/sessão/repetição (`exp2_decay_shuffle|ratio_label`) — `_remove_k_ls` baralha os L visíveis antes de ocultar os primeiros *k* |

### 4.8 Exportação de dados (Experimento 2)

**Eventos** (`*_exp2_events.csv`): colunas fixas `participant_id`, `experiment` (= 2), `session_condition`, `session_run`, `event_index`, `t_session_s`, `event_type`, `n_L_left`, `n_L_right`, `points_total`, `active_side`, `ratio_label`, `detail`. Tipos de evento incluem p.ex. `foraging_start`, `decay_tick`, `reinforcement`, `session_end` / `session_abort`.

**Resumo** (`*_exp2_summary.csv`): inclui entre outros `ratio_label`, `points_total`, `duration_s_run`, `duration_s_planned`, `forage_time_left_s`, `forage_time_right_s`, `k_decay_per_panel`, `initial_n_L_left`, `initial_n_L_right`, `aborted`, `ended_by_t_esc`, `correctkey_csv` (valor copiado do CSV de sessões, metadado), flags `single_visible_panel_by_gaze`, `dual_target_scoring`, etc.

**TXT:** texto legível com participante, sessão, repetição, modo (EyeLink vs dummy), caminhos dos CSV.

---

## 5. Síntese: “probabilidade do lado” (redacção para método)

- **Experimento 1:** O lado do **T** é determinado **trial a trial** pelo campo `correctkey` (frequências marginais no CSV, ver §3.4). A **ordem** dos trials é permutada de forma reprodutível.
- **Experimento 2:** **Ambos** os lados têm **T** em todo o tempo; o desenho manipula a **proporção de L** por lado (e o decaimento), não “lado do T” como evento binário. Comportamento lateral (tempo de olhar) é **livre** e registado (p.ex. tempos por metade no output), não fixado a uma probabilidade experimental de lado.

---

## 6. Ficheiros de dados (indicativos)

- **Exp1:** prefixos `forrageamento_exp1_...` em `data/`: CSV de trials, segmentos, eventos, TXT, XLSX (se `openpyxl`). Camada **análise** (derivada, não altera os brutos): `_analysis_trials.csv` (proporções de forrageamento, escolha discreta, `matching_log_*` por trial), `_analysis_session.csv` (agregado sessão para matching law), `_analysis_segments.csv` (`duration_prop_of_trial`).
- **Exp2:** `forrageamento_exp2_<participante>_s<sessão>_r<repetição>_<timestamp>_exp2_events.csv`, `_exp2_summary.csv`, `_exp2.txt` (ver §4.8). Camada análise: `_exp2_analysis.csv` (rácios de desenho + obtidos, tempos, matching), `_exp2_reinforcements.csv` (cada ponto), `_exp2_dwell_bins.csv` (dwell por bins de 10 s).

---

*Última actualização: inclui secção completa do **Experimento 2** (§4, subsecções 4.0–4.8). Alinhado ao código em `ForrageamentoPsychoPy`; alterações de constantes ou CSV devem ser reflectidas neste ficheiro.*
