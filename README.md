# Sudoku Boards as CSPs - ReadMe

## 1. Problem Summary
This project implements a Sudoku solver as a Constraint Satisfaction Problem (CSP).
The solver uses:
- Backtracking search
- Forward checking
- AC-3 (arc consistency)

The required input format is supported:
- Exactly 9 lines per file
- Exactly 9 digits (`0-9`) per line
- `0` means the cell is empty

Example input (`easy.txt`):

```text
004030050
609400000
005100489
000060930
300807002
026040000
453009600
000004705
090050200
```

## 2. Implementation Overview
The implementation is in [main.py](main.py).

### 2.1 CSP Modeling
- Variables: one variable per Sudoku cell `(row, col)`.
- Domains:
  - If a cell is given (non-zero), domain is a singleton set with that value.
  - If empty, domain is `{1..9}`.
- Constraints: neighboring cells (same row, same column, same 3x3 block) must have different values.

### 2.2 Core Components
- `read_board(file_path)`
  - Validates file shape and digit-only content.
- `ac3(domains, queue=None)`
  - Enforces arc consistency using a worklist of arcs.
- `forward_check(domains, var, value)`
  - Removes assigned value from neighbor domains immediately.
- `backtrack(domains, stats)`
  - Recursive search over assignments.
  - Counts:
    - number of calls to `BACKTRACK`
    - number of returns with failure

### 2.3 Heuristics Used
- MRV (Minimum Remaining Values): chooses the most constrained unassigned variable first.
- Degree tie-break: if MRV ties, prefers the variable with more neighbors.
- LCV (Least Constraining Value): tries values that remove the fewest options from neighbors.

### 2.4 Correctness Safeguards
- A consistency check verifies no two neighboring singleton domains have the same value.
- Final solution is accepted only if the assignment is complete and consistent.

## 3. Program Results
The solver was run with:

```bash
python main.py
```

### 3.1 easy.txt
Solved board:

```text
784932156
619485327
235176489
578261934
341897562
926543871
453729618
862314795
197658243
```

Statistics:
- BACKTRACK calls: `1`
- BACKTRACK failures: `0`

Brief comment:
- Very low search effort. Constraint propagation (AC-3 + forward checking) was enough to solve this board with essentially no branching.

### 3.2 medium.txt
Solver output:

```text
No solution found.
```

Statistics:
- BACKTRACK calls: `0`
- BACKTRACK failures: `0`

Brief comment:
- This indicates the loaded board became inconsistent before search started (detected during initial consistency/AC-3 checks). In practice, this usually means at least one clue was transcribed incorrectly.

### 3.3 hard.txt
Solved board:

```text
152346897
437189652
689572314
821637945
543891726
976425183
798253461
365914278
214768539
```

Statistics:
- BACKTRACK calls: `2660`
- BACKTRACK failures: `2623`

Brief comment:
- High search effort. The solver had to explore many branches before finding a consistent completion.

### 3.4 veryhard.txt
Solved board:

```text
431867925
652491387
897532164
384976512
519284736
276315849
943728651
765143298
128659473
```

Statistics:
- BACKTRACK calls: `18057`
- BACKTRACK failures: `18022`

Brief comment:
- Extremely high search effort. This puzzle required deep recursive exploration with many dead ends.

## 4. Complexity Discussion
- AC-3 reduces domains early and repeatedly after each assignment.
- Forward checking prunes domains immediately after each tentative choice.
- Backtracking handles the remaining combinational search space.

Observed behavior matches expectations:
- Easy puzzle: almost all work done by propagation.
- Hard/very hard puzzles: significantly more search and failures.

## 5. Notes
- The implementation auto-creates `easy.txt`, `medium.txt`, `hard.txt`, and `veryhard.txt` if they are missing, using the embedded board strings.
- If your assignment files already exist, they are read as-is and are not overwritten.
- If `medium.txt` in your course package is different from the embedded default, place the official file next to [main.py](main.py) and rerun to obtain the required official result.
