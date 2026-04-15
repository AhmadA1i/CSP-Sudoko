from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


Cell = Tuple[int, int]
DomainMap = Dict[Cell, Set[int]]


@dataclass
class SolverStats:
	backtrack_calls: int = 0
	backtrack_failures: int = 0


class SudokuCSP:
	def __init__(self, grid: List[List[int]]) -> None:
		self.grid = grid
		self.cells: List[Cell] = [(r, c) for r in range(9) for c in range(9)]
		self.neighbors: Dict[Cell, Set[Cell]] = {
			cell: self._compute_neighbors(cell) for cell in self.cells
		}
		self.arcs: List[Tuple[Cell, Cell]] = [
			(xi, xj) for xi in self.cells for xj in self.neighbors[xi]
		]

	@staticmethod
	def read_board(file_path: Path) -> List[List[int]]:
		lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
		if len(lines) != 9:
			raise ValueError(f"{file_path}: expected exactly 9 lines, got {len(lines)}")

		board: List[List[int]] = []
		for i, line in enumerate(lines, start=1):
			if len(line) != 9 or not line.isdigit():
				raise ValueError(
					f"{file_path}: line {i} must contain exactly 9 digits (0-9), got '{line}'"
				)
			board.append([int(ch) for ch in line])
		return board

	def initial_domains(self) -> DomainMap:
		domains: DomainMap = {}
		for r in range(9):
			for c in range(9):
				value = self.grid[r][c]
				cell = (r, c)
				if value == 0:
					domains[cell] = set(range(1, 10))
				else:
					domains[cell] = {value}
		return domains

	def is_complete(self, domains: DomainMap) -> bool:
		return all(len(domains[cell]) == 1 for cell in self.cells)

	def is_consistent(self, domains: DomainMap) -> bool:
		for cell in self.cells:
			if len(domains[cell]) != 1:
				continue
			value = next(iter(domains[cell]))
			for n in self.neighbors[cell]:
				if len(domains[n]) == 1 and next(iter(domains[n])) == value:
					return False
		return True

	def _compute_neighbors(self, cell: Cell) -> Set[Cell]:
		r, c = cell
		result: Set[Cell] = set()

		for k in range(9):
			if k != c:
				result.add((r, k))
			if k != r:
				result.add((k, c))

		br, bc = (r // 3) * 3, (c // 3) * 3
		for rr in range(br, br + 3):
			for cc in range(bc, bc + 3):
				if (rr, cc) != cell:
					result.add((rr, cc))
		return result

	def revise(self, domains: DomainMap, xi: Cell, xj: Cell) -> bool:
		revised = False
		if len(domains[xj]) == 1:
			forbidden = next(iter(domains[xj]))
			if len(domains[xi]) == 1 and forbidden in domains[xi]:
				# Two neighboring singleton domains with the same value violates Sudoku constraints.
				return False
			if forbidden in domains[xi] and len(domains[xi]) > 1:
				domains[xi].remove(forbidden)
				revised = True
		return revised

	def ac3(self, domains: DomainMap, queue: Optional[List[Tuple[Cell, Cell]]] = None) -> bool:
		worklist = list(self.arcs if queue is None else queue)

		while worklist:
			xi, xj = worklist.pop(0)
			revise_result = self.revise(domains, xi, xj)
			if revise_result is False and len(domains[xi]) == 1 and len(domains[xj]) == 1 and domains[xi] == domains[xj]:
				return False
			if revise_result:
				if len(domains[xi]) == 0:
					return False
				for xk in self.neighbors[xi]:
					if xk != xj:
						worklist.append((xk, xi))
		return True

	def select_unassigned_variable(self, domains: DomainMap) -> Cell:
		unassigned = [cell for cell in self.cells if len(domains[cell]) > 1]
		# Minimum Remaining Values (MRV), then Degree heuristic tie-break.
		return min(unassigned, key=lambda cell: (len(domains[cell]), -len(self.neighbors[cell])))

	def order_domain_values(self, domains: DomainMap, var: Cell) -> List[int]:
		values = list(domains[var])

		def conflicts(value: int) -> int:
			count = 0
			for n in self.neighbors[var]:
				if len(domains[n]) > 1 and value in domains[n]:
					count += 1
			return count

		# Least Constraining Value (LCV).
		return sorted(values, key=conflicts)

	def is_assignment_consistent(self, domains: DomainMap, var: Cell, value: int) -> bool:
		return all(
			not (len(domains[n]) == 1 and next(iter(domains[n])) == value)
			for n in self.neighbors[var]
		)

	def forward_check(self, domains: DomainMap, var: Cell, value: int) -> bool:
		for n in self.neighbors[var]:
			if len(domains[n]) > 1 and value in domains[n]:
				domains[n].remove(value)
				if len(domains[n]) == 0:
					return False
		return True

	@staticmethod
	def clone_domains(domains: DomainMap) -> DomainMap:
		return {cell: set(vals) for cell, vals in domains.items()}

	def backtrack(self, domains: DomainMap, stats: SolverStats) -> Optional[DomainMap]:
		stats.backtrack_calls += 1

		if self.is_complete(domains):
			if self.is_consistent(domains):
				return domains
			stats.backtrack_failures += 1
			return None

		var = self.select_unassigned_variable(domains)

		for value in self.order_domain_values(domains, var):
			if not self.is_assignment_consistent(domains, var, value):
				continue

			next_domains = self.clone_domains(domains)
			next_domains[var] = {value}

			if not self.forward_check(next_domains, var, value):
				continue

			# Propagate only arcs that could be affected by assigning var.
			local_queue = [(n, var) for n in self.neighbors[var]]
			if not self.ac3(next_domains, local_queue):
				continue

			result = self.backtrack(next_domains, stats)
			if result is not None:
				return result

		stats.backtrack_failures += 1
		return None

	def solve(self) -> Tuple[Optional[List[List[int]]], SolverStats]:
		stats = SolverStats()
		domains = self.initial_domains()

		if not self.is_consistent(domains):
			return None, stats

		if not self.ac3(domains):
			return None, stats

		solved_domains = self.backtrack(domains, stats)
		if solved_domains is None:
			return None, stats

		solved_grid = [[0 for _ in range(9)] for _ in range(9)]
		for r in range(9):
			for c in range(9):
				solved_grid[r][c] = next(iter(solved_domains[(r, c)]))
		return solved_grid, stats


def format_grid(grid: List[List[int]]) -> str:
	return "\n".join("".join(str(n) for n in row) for row in grid)


def write_default_boards_if_missing(base_dir: Path) -> None:
	boards = {
		"easy.txt": [
			"004030050",
			"609400000",
			"005100489",
			"000060930",
			"300807002",
			"026040000",
			"453009600",
			"000004705",
			"090050200",
		],
		# These three are transcribed from the assignment figure.
		"medium.txt": [
			"000030040",
			"100970000",
			"000851070",
			"002607830",
			"906010207",
			"031502900",
			"010369000",
			"000005703",
			"090070000",
		],
		"hard.txt": [
			"102040007",
			"000080000",
			"009500304",
			"000607900",
			"540000026",
			"006405000",
			"708003400",
			"000010000",
			"200060509",
		],
		"veryhard.txt": [
			"001007000",
			"600400300",
			"000030064",
			"380076000",
			"000000036",
			"270015000",
			"000020051",
			"700100200",
			"008009000",
		],
	}

	for name, lines in boards.items():
		path = base_dir / name
		if not path.exists():
			path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def comment_on_stats(name: str, stats: SolverStats) -> str:
	calls = stats.backtrack_calls
	fails = stats.backtrack_failures
	if calls == 0:
		return f"{name}: no backtracking phase was reached (likely inconsistent input)."

	fail_ratio = fails / calls
	if fail_ratio < 0.15:
		level = "low search effort"
	elif fail_ratio < 0.4:
		level = "moderate search effort"
	else:
		level = "high search effort"

	return (
		f"{name}: BACKTRACK calls={calls}, failures={fails}, "
		f"failure ratio={fail_ratio:.2f} -> {level}."
	)


def main() -> None:
	base_dir = Path(__file__).resolve().parent
	write_default_boards_if_missing(base_dir)

	board_files = ["easy.txt", "medium.txt", "hard.txt", "veryhard.txt"]

	for file_name in board_files:
		path = base_dir / file_name
		board = SudokuCSP.read_board(path)
		solver = SudokuCSP(board)
		solution, stats = solver.solve()

		print(f"=== {file_name} ===")
		if solution is None:
			print("No solution found.")
		else:
			print(format_grid(solution))
		print(comment_on_stats(file_name, stats))
		print()


if __name__ == "__main__":
	main()
