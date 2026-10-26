"""
此测试文件由ai生成
prompt:
    针对题目B的描述，写测试文件，需要包括题目中的测试样例，功能性测试，此外还要有各种变量的边界测试；
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
import unittest
from pathlib import Path

RUN_STRESS = '1'

# Warehouse tuple: (warehouse_id, stock, fixed_cost, unit_cost)
Warehouse = tuple[str, int, int, int]


def expected_output(allocations: list[tuple[str, int]], cost: int) -> str:
    """Produce exactly the output format specified by Task B."""
    rows = sorted((warehouse_id, quantity) for warehouse_id, quantity in allocations if quantity > 0)
    return "\n".join(
        [f"{len(rows)} {cost}"]
        + [f"{warehouse_id} {quantity}" for warehouse_id, quantity in rows]
    )


def brute_force_oracle(warehouses: list[Warehouse], demand: int) -> str:
    """Independent, exhaustive oracle for SMALL test inputs only.

    Comparison key (in priority order):
        (number_of_used_warehouses, total_cost, sorted_allocation_list)

    Not used on large cases, where enumerating allocations would be too slow.
    """
    ordered = sorted(warehouses, key=lambda w: w[0])
    if sum(stock for _, stock, _, _ in ordered) < demand:
        return "-1"

    best: tuple[int, int, tuple[tuple[str, int], ...]] | None = None

    def search(index: int, remaining: int, used: int, cost: int,
               allocations: tuple[tuple[str, int], ...]) -> None:
        nonlocal best
        if index == len(ordered):
            if remaining == 0:
                candidate = (used, cost, allocations)
                if best is None or candidate < best:
                    best = candidate
            return

        warehouse_id, stock, fixed_cost, unit_cost = ordered[index]
        # Do not explore more used warehouses than a completed best solution.
        for quantity in range(min(stock, remaining) + 1):
            next_used = used + (quantity > 0)
            if best is not None and next_used > best[0]:
                continue
            next_cost = cost + (fixed_cost + quantity * unit_cost if quantity else 0)
            next_allocations = (
                allocations + ((warehouse_id, quantity),) if quantity else allocations
            )
            search(index + 1, remaining - quantity, next_used,
                   next_cost, next_allocations)

    search(0, demand, 0, 0, ())
    assert best is not None
    return expected_output(list(best[2]), best[1])


class TaskBFulfilmentTests(unittest.TestCase):
    """Run the actual Python program via stdin/stdout (black-box testing)."""

    @classmethod
    def setUpClass(cls) -> None:
        base_dir = Path(__file__).resolve().parent
        chosen = os.environ.get("TASK_B_PROGRAM")
        if chosen:
            candidate = Path(chosen).expanduser()
            if not candidate.is_absolute():
                candidate = base_dir / candidate
        else:
            # Supports the user's project layout: A/main.py, B/main.py,
            # test_task_b.py at project root.
            nested = base_dir / "B" / "main.py"
            candidate = nested if nested.is_file() else base_dir / "main.py"
        cls.solver_path = candidate.resolve()
        if not cls.solver_path.is_file():
            raise AssertionError(
                f"找不到被测程序：{cls.solver_path}\n"
                "请把 main.py 放在 B/ 文件夹或测试文件旁边，或用环境变量 "
                "TASK_B_PROGRAM 指向你的 Python 解答文件。"
            )

    def run_solver(self, warehouses: list[Warehouse], demand: int,
                   *, timeout: float | None = None) -> str:
        self.assertTrue(1 <= len(warehouses) <= 30)
        self.assertTrue(1 <= demand <= 2000)
        self.assertEqual(len({w[0] for w in warehouses}), len(warehouses),
                         "Test fixture must have unique warehouse IDs")

        input_data = "\n".join(
            [f"{len(warehouses)} {demand}"]
            + [f"{warehouse_id} {stock} {fixed} {unit}"
               for warehouse_id, stock, fixed, unit in warehouses]
        ) + "\n"

        seconds = timeout if timeout is not None else float(os.environ.get("TASK_B_TIMEOUT", "15"))
        try:
            completed = subprocess.run(
                [sys.executable, str(self.solver_path)],
                input=input_data,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=seconds,
                cwd=str(self.solver_path.parent),
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.fail(f"程序运行超过 {seconds:g} 秒，输入：\n{input_data[:1200]}")

        self.assertEqual(
            completed.returncode, 0,
            f"程序异常退出（exit={completed.returncode}）\n"
            f"STDERR:\n{completed.stderr}\nINPUT:\n{input_data[:1200]}"
        )
        # Ignore trailing spaces and terminal newlines, but not additional
        # banners, prompts, debug prints, or lines in an incorrect order.
        return "\n".join(line.strip() for line in completed.stdout.strip().splitlines())

    def check(self, warehouses: list[Warehouse], demand: int, expected: str,
              *, timeout: float | None = None) -> None:
        actual = self.run_solver(warehouses, demand, timeout=timeout)
        expected_text = expected.strip()
        # assertEqual(first, second): first is EXPECTED, second is ACTUAL.
        # Keeping this order fixes the misleading left/right comparison view.
        self.assertEqual(
            expected_text,
            actual,
            f"输入仓库={warehouses}, Q={demand}\n"
            f"预期（符合题意）:\n{expected_text}\n"
            f"实际（程序输出）:\n{actual}",
        )

    # --------------------- 官方样例及基本功能 ---------------------

    def test_01_official_example(self) -> None:
        self.check(
            [("AU", 5, 8, 2), ("CN", 7, 20, 1), ("US", 4, 3, 4)],
            7,
            "1 27\nCN 7",
        )

    def test_02_one_warehouse_exact_stock(self) -> None:
        self.check([("W1", 5, 10, 3)], 5, "1 25\nW1 5")

    def test_03_one_warehouse_part_of_stock(self) -> None:
        # Charge only for the allocated 3 items, not all 10 in stock.
        self.check([("W1", 10, 10, 3)], 3, "1 19\nW1 3")

    def test_04_one_warehouse_insufficient_stock(self) -> None:
        self.check([("W1", 4, 10, 3)], 5, "-1")

    def test_05_total_stock_less_than_order(self) -> None:
        self.check([("A", 2, 1, 1), ("B", 3, 1, 1)], 6, "-1")

    def test_06_total_stock_exactly_order(self) -> None:
        self.check([("B", 3, 4, 3), ("A", 2, 2, 2)], 5,
                   "2 19\nA 2\nB 3")

    def test_07_all_warehouses_zero_stock(self) -> None:
        self.check([("A", 0, 0, 0), ("B", 0, 0, 0)], 1, "-1")

    def test_08_zero_stock_warehouse_must_not_be_used(self) -> None:
        self.check([("FREE", 0, 0, 0), ("PAID", 2, 10, 3)], 2,
                   "1 16\nPAID 2")

    def test_09_q_minimum_one(self) -> None:
        self.check([("B", 1, 4, 2), ("A", 0, 0, 0)], 1, "1 6\nB 1")

    # --------------------- 一级目标：仓库数量最少 ---------------------

    def test_10_one_warehouse_beats_cheaper_two(self) -> None:
        # ONE costs 1050, while SMALL1 + SMALL2 cost 0. ONE must win.
        self.check(
            [("ONE", 5, 1000, 10), ("SMALL1", 3, 0, 0),
             ("SMALL2", 2, 0, 0)],
            5, "1 1050\nONE 5",
        )

    def test_11_two_warehouses_beat_cheaper_three(self) -> None:
        # A+one small costs 100; the three small warehouses together cost 0.
        self.check(
            [("A", 4, 100, 0), ("B", 2, 0, 0),
             ("C", 2, 0, 0), ("D", 2, 0, 0)],
            6, "2 100\nA 4\nB 2",
        )

    def test_12_min_warehouse_count_not_largest_stock_greedy(self) -> None:
        # Two warehouses needed. Largest stocks A+B are expensive;
        # cheaper feasible subset is B+C with 5+3=8.
        self.check(
            [("A", 6, 0, 100), ("B", 5, 0, 1), ("C", 3, 0, 1)],
            8, "2 8\nB 5\nC 3",
        )

    # --------------------- 二级目标：总成本最小 ---------------------

    def test_13_same_count_cheapest_single_warehouse(self) -> None:
        self.check([("A", 5, 2, 10), ("B", 5, 3, 2)], 5,
                   "1 13\nB 5")

    def test_14_fixed_cost_vs_unit_cost(self) -> None:
        # A: 100 + 5*1 = 105; B: 0 + 5*20 = 100.
        self.check([("A", 5, 100, 1), ("B", 5, 0, 20)], 5,
                   "1 100\nB 5")

    def test_15_allocate_more_to_cheaper_unit_cost(self) -> None:
        # Both needed; A gets only 2, B gets 4.
        self.check([("A", 4, 0, 10), ("B", 4, 0, 1)], 6,
                   "2 24\nA 2\nB 4")

    def test_16_positive_fixed_cost_paid_only_once(self) -> None:
        self.check([("A", 5, 11, 2)], 4, "1 19\nA 4")

    def test_17_zero_unit_cost_can_be_cheaper(self) -> None:
        self.check([("A", 5, 1, 0), ("B", 5, 0, 1)], 5,
                   "1 1\nA 5")

    def test_18_unused_fixed_cost_is_not_charged(self) -> None:
        self.check([("A", 4, 8, 2), ("B", 4, 1_000_000, 0)], 4,
                   "1 16\nA 4")

    # --------------------- 三级目标：字典序最小 ---------------------

    def test_19_equal_cost_one_warehouse_id(self) -> None:
        # Input is not sorted by ID; lexicographically smaller ID wins.
        self.check([("ZZ", 5, 0, 3), ("AA", 5, 0, 3)], 5,
                   "1 15\nAA 5")

    def test_20_equal_cost_different_two_warehouse_sets(self) -> None:
        # A1+B2, A1+C2 and A2+B1 have equal count and cost.
        # Sorted list (A,1),(B,2) is smallest.
        self.check([("C", 2, 0, 0), ("B", 2, 0, 0), ("A", 2, 0, 0)],
                   3, "2 0\nA 1\nB 2")

    def test_21_equal_cost_different_quantities_same_ids(self) -> None:
        # A1+B4 < A2+B3 < A3+B2 < A4+B1.
        self.check([("B", 4, 0, 2), ("A", 4, 0, 2)], 5,
                   "2 10\nA 1\nB 4")

    def test_22_lexicographical_ids_not_numerical_ids(self) -> None:
        # CRITICAL: warehouse_id is a STRING. "10" < "2" lexicographically.
        # Both warehouses can satisfy Q=3 at cost 0, so "10" must win.
        self.check([("2", 3, 0, 0), ("10", 3, 0, 0)], 3,
                   "1 0\n10 3")

    def test_23_lex_order_quantity_before_next_warehouse_id(self) -> None:
        # A1+B5 wins over A2+B4 and A1+C5.
        self.check([("C", 5, 0, 0), ("B", 5, 0, 0), ("A", 4, 0, 0)],
                   6, "2 0\nA 1\nB 5")

    def test_24_zero_stock_ids_do_not_appear_in_output(self) -> None:
        self.check([("A", 0, 0, 0), ("B", 3, 0, 0), ("C", 0, 0, 0)],
                   2, "1 0\nB 2")

    def test_25_input_order_must_not_determine_output_order(self) -> None:
        self.check([("Z", 2, 0, 1), ("A", 1, 0, 1), ("M", 2, 0, 1)],
                   5, "3 5\nA 1\nM 2\nZ 2")

    # --------------------- 约束边界及大数量 ---------------------

    def test_26_maximum_q_with_one_warehouse(self) -> None:
        self.check([("MAX", 2000, 1_000_000, 1_000_000)], 2000,
                   "1 2001000000\nMAX 2000")

    def test_27_maximum_q_two_warehouses_exact_stock(self) -> None:
        self.check([("B", 800, 20, 3), ("A", 1200, 10, 2)], 2000,
                   "2 4830\nA 1200\nB 800")

    def test_28_maximum_q_two_warehouses_partial_stock(self) -> None:
        self.check([("A", 1000, 0, 5), ("B", 1500, 0, 1)], 2000,
                   "2 4000\nA 500\nB 1500")

    def test_29_maximum_w_and_not_enough_total_stock(self) -> None:
        self.check([(f"W{i:02d}", 66, 0, 0) for i in range(30)],
                   2000, "-1")

    def test_30_maximum_w_zero_cost_multiple_ties(self) -> None:
        # Q=3, 30 warehouses, all of stock 1. Three lex-smallest IDs win.
        warehouses = [(f"W{i:02d}", 1, 0, 0) for i in range(29, -1, -1)]
        self.check(warehouses, 3,
                   "3 0\nW00 1\nW01 1\nW02 1")

    def test_31_maximum_w_cost_priority(self) -> None:
        warehouses = [(f"W{i:02d}", 1, 30 - i, 0) for i in range(30)]
        self.check(warehouses, 2, "2 3\nW28 1\nW29 1")

    def test_32_all_fixed_costs_and_unit_costs_zero(self) -> None:
        self.check([("B", 4, 0, 0), ("C", 4, 0, 0), ("A", 3, 0, 0)],
                   5, "2 0\nA 1\nB 4")

    # --------------------- 独立小规模穷举对照 ---------------------

    def test_33_random_small_cases_against_exhaustive_oracle(self) -> None:
        """Seeded random cases: compare solver against exhaustive allocation search."""
        rng = random.Random(20261025)
        rounds = 100 if RUN_STRESS == "1" else 30
        for case_no in range(rounds):
            w = rng.randint(1, 5)
            warehouses = [
                (f"W{i:02d}", rng.randint(0, 4),
                 rng.randint(0, 12), rng.randint(0, 7))
                for i in range(w)
            ]
            rng.shuffle(warehouses)
            demand = rng.randint(1, 12)
            oracle_output = brute_force_oracle(warehouses, demand)
            with self.subTest(case=case_no, Q=demand, warehouses=warehouses):
                self.check(warehouses, demand, oracle_output)

    # --------------------- 可选性能/最大规模测试 ---------------------

    @unittest.skipUnless(RUN_STRESS == "1",
                         "设置 RUN_STRESS=1 后运行最大规模测试")
    def test_34_stress_max_w_max_q_all_needed_and_lex_tie(self) -> None:
        # Each warehouse holds 67 => sum=2010. With Q=2000, all 30
        # warehouses are necessary. Lex-smallest allocation assigns only 57
        # to W00, then 67 to each remaining warehouse.
        warehouses = [(f"W{i:02d}", 67, 0, 0) for i in range(29, -1, -1)]
        allocations = [("W00", 57)] + [(f"W{i:02d}", 67) for i in range(1, 30)]
        self.check(warehouses, 2000, expected_output(allocations, 0), timeout=60)

    @unittest.skipUnless(RUN_STRESS == "1",
                         "设置 RUN_STRESS=1 后运行最大规模测试")
    def test_35_stress_max_w_max_q_unique_cost_optimum(self) -> None:
        # Each warehouse has capacity 100; 20 warehouses are minimally
        # required for Q=2000. W00...W19 have strictly cheaper unit costs
        # than W20...W29, so all first 20 must be fully used.
        warehouses = [(f"W{i:02d}", 100, 0, i) for i in range(29, -1, -1)]
        allocations = [(f"W{i:02d}", 100) for i in range(20)]
        total_cost = sum(i * 100 for i in range(20))
        self.check(warehouses, 2000,
                   expected_output(allocations, total_cost), timeout=60)


if __name__ == "__main__":
    unittest.main(verbosity=2)
