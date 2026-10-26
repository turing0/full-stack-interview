'''
此测试文件由ai生成
prompt:
    针对题目A的描述，写测试文件，需要包括题目中的测试样例，功能性测试，此外还要有qty不合法的测试；
    要有各种边界测试，比如：reserve、SHIP、RELEASE、restock 数量的各种情况，比库存多、相等、少于，正数负数，非法输入等
    以及你能想到的边界条件
'''
from __future__ import annotations

"""Task A - Inventory Reservation Ledger：黑盒命令行测试。

运行方式（将本文件与 main.py 放在同一个目录）：
    python -m unittest -v test_main

可选的 200,000 条命令压力测试：
    PowerShell: $env:RUN_STRESS='1'; python -m unittest -v test_main
    CMD:        set RUN_STRESS=1 && python -m unittest -v test_main

测试约定：
- 程序通过 stdin 读取 `S N` 和后续 N 行命令，通过 stdout 输出结果。
- 每条命令输出 `STATUS on_hand reserved`。
- 最终输出 `OPEN k`，后面跟 k 行 `order_id qty`，按 order_id 字典序排序。
  （题目仅说输出未完成预留并排序，未明确每条 OPEN 的文本格式；
    如面试官另有规定，请只修改测试中对应的期望格式。）
- 格式不合法的命令输出 REJECTED、不得改变库存状态。
- 题目只保证被拒绝的“业务操作”会占用 event_id；并未明确格式错误的
  命令是否占用 event_id，因此不测试格式错误命令的重放结果。
"""

import os
import random
import subprocess
import sys
import unittest
from pathlib import Path


PROGRAM = Path(__file__).with_name("main.py")
MAX_QTY = 10**12


class InventoryLedgerCLITests(unittest.TestCase):
    """不依赖 InventoryLedger 类的内部实现，直接校验 CLI 行为。"""

    def assert_ledger(
        self,
        stock: int,
        commands: list[str],
        expected_lines: list[str],
        *,
        timeout: int = 10,
    ) -> None:
        if not PROGRAM.is_file():
            self.fail(f"找不到 {PROGRAM}。请将 main.py 与 test_main.py 放在同一目录。")

        data = f"{stock} {len(commands)}\n" + "\n".join(commands) + "\n"
        try:
            completed = subprocess.run(
                [sys.executable, str(PROGRAM)],
                input=data,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.fail(f"程序执行超过 {timeout} 秒，可能陷入死循环或等待额外输入")

        self.assertEqual(
            completed.returncode,
            0,
            f"程序异常退出 (exit={completed.returncode})\n"
            f"stderr:\n{completed.stderr[:3000]}\n"
            f"input:\n{data[:1000]}",
        )
        actual = completed.stdout.splitlines()
        self.assertEqual(
            actual,
            expected_lines,
            f"stdout 不符合预期。\n输入前 1000 字符:\n{data[:1000]}\n"
            f"stderr:\n{completed.stderr[:1000]}",
        )

    def test_01_official_example(self) -> None:
        """题目中的完整示例。"""
        self.assert_ledger(
            10,
            [
                "RESERVE e1 o100 4",
                "RESERVE e2 o200 7",
                "SHIP e3 o100 2",
                "RELEASE e4 o100 2",
                "RESTOCK e5 3",
                "RESERVE e2 o999 1",
            ],
            [
                "OK 10 4",
                "REJECTED 10 4",
                "OK 8 2",
                "OK 8 0",
                "OK 11 0",
                "DUPLICATE 11 0",
                "OPEN 0",
            ],
        )

    def test_02_reserve_less_equal_greater_than_available(self) -> None:
        """RESERVE：小于/等于/大于可用库存，且不能把 on_hand 当作 available。"""
        self.assert_ledger(
            10,
            [
                "RESERVE a o1 4",  # 4 < 10
                "RESERVE b o2 6",  # 6 == available
                "RESERVE c o3 1",  # 1 > available (0)
                "RESERVE d o1 1",  # 累计预留不能超过库存
            ],
            [
                "OK 10 4",
                "OK 10 10",
                "REJECTED 10 10",
                "REJECTED 10 10",
                "OPEN 2",
                "o1 4",
                "o2 6",
            ],
        )

    def test_03_zero_stock_and_restock_enables_reserve(self) -> None:
        """初始库存为 0，拒绝预留；补货以后可以预留并全部发货。"""
        self.assert_ledger(
            0,
            [
                "RESERVE a o1 1",
                "RESTOCK b 1",
                "RESERVE c o1 1",
                "SHIP d o1 1",
            ],
            [
                "REJECTED 0 0",
                "OK 1 0",
                "OK 1 1",
                "OK 0 0",
                "OPEN 0",
            ],
        )

    def test_04_release_partial_equal_excess_and_nonexistent(self) -> None:
        """RELEASE：小于/等于/大于本订单已预留量，以及不存在的订单。"""
        self.assert_ledger(
            10,
            [
                "RESERVE e1 x 5",
                "RELEASE e2 x 2",   # 小于预留量
                "RELEASE e3 x 4",   # 大于剩余 3
                "RELEASE e4 x 3",   # 恰好剩余 3
                "RELEASE e5 x 1",   # 已经清零
                "RELEASE e6 z 1",   # 不存在的订单
            ],
            [
                "OK 10 5",
                "OK 10 3",
                "REJECTED 10 3",
                "OK 10 0",
                "REJECTED 10 0",
                "REJECTED 10 0",
                "OPEN 0",
            ],
        )

    def test_05_release_does_not_reduce_on_hand(self) -> None:
        """释放预留只改变 reserved，不减少实际库存。"""
        self.assert_ledger(
            3,
            [
                "RESERVE a one 3",
                "RELEASE b one 3",
                "RESERVE c two 3",
            ],
            ["OK 3 3", "OK 3 0", "OK 3 3", "OPEN 1", "two 3"],
        )

    def test_06_ship_partial_equal_excess_and_nonexistent(self) -> None:
        """SHIP：不能超过本订单预留量；正常发货同时扣 on_hand 和 reserved。"""
        self.assert_ledger(
            10,
            [
                "RESERVE a order 6",
                "SHIP b order 7",    # 超过预留
                "SHIP c order 3",    # 部分发货
                "SHIP d order 3",    # 全部发完
                "SHIP e order 1",    # 剩余 0
                "SHIP f missing 1",  # 不存在的订单
            ],
            [
                "OK 10 6",
                "REJECTED 10 6",
                "OK 7 3",
                "OK 4 0",
                "REJECTED 4 0",
                "REJECTED 4 0",
                "OPEN 0",
            ],
        )

    def test_07_ship_cannot_borrow_another_orders_reservation(self) -> None:
        """总预留足够，不代表某一订单的预留足够。"""
        self.assert_ledger(
            10,
            [
                "RESERVE e1 a 2",
                "RESERVE e2 b 8",
                "SHIP e3 a 3",
                "SHIP e4 a 2",
            ],
            [
                "OK 10 2",
                "OK 10 10",
                "REJECTED 10 10",
                "OK 8 8",
                "OPEN 1",
                "b 8",
            ],
        )

    def test_08_restock_less_equal_greater_than_stock(self) -> None:
        """RESTOCK：少于/等于/大于当前库存均可成功，补货不设库存不足限制。"""
        self.assert_ledger(
            4,
            [
                "RESTOCK a 1",   # 1 < 4
                "RESTOCK b 5",   # 5 == 当前库存 5
                "RESTOCK c 11",  # 11 > 当前库存 10
            ],
            ["OK 5 0", "OK 10 0", "OK 21 0", "OPEN 0"],
        )

    def test_09_restock_does_not_change_existing_reservations(self) -> None:
        self.assert_ledger(
            5,
            [
                "RESERVE a x 4",
                "RESTOCK b 3",
                "RESERVE c y 4",
                "SHIP d x 2",
            ],
            ["OK 5 4", "OK 8 4", "OK 8 8", "OK 6 6", "OPEN 2", "x 2", "y 4"],
        )

    def test_10_duplicate_event_across_all_operation_types(self) -> None:
        """同一 event_id 无论改成哪种操作、订单、数量都只能执行一次。"""
        self.assert_ledger(
            10,
            [
                "RESERVE same x 4",
                "RESERVE same y 1",
                "SHIP same x 2",
                "RELEASE same x 4",
                "RESTOCK same 7",
                "SHIP new x 4",
                "SHIP new x 1",
            ],
            [
                "OK 10 4",
                "DUPLICATE 10 4",
                "DUPLICATE 10 4",
                "DUPLICATE 10 4",
                "DUPLICATE 10 4",
                "OK 6 0",
                "DUPLICATE 6 0",
                "OPEN 0",
            ],
        )

    def test_11_rejected_business_event_must_still_be_idempotent(self) -> None:
        """失败的业务事件也占用 event_id；后来库存充足，重放仍然 DUPLICATE。"""
        self.assert_ledger(
            1,
            [
                "RESERVE failed x 2",
                "RESTOCK add 10",
                "RESERVE failed x 2",
                "RESERVE allowed x 2",
            ],
            ["REJECTED 1 0", "OK 11 0", "DUPLICATE 11 0", "OK 11 2", "OPEN 1", "x 2"],
        )

    def test_12_rejected_ship_and_release_event_replay(self) -> None:
        """SHIP/RELEASE 业务拒绝后，即使之后预留增多，重放仍是 DUPLICATE。"""
        self.assert_ledger(
            10,
            [
                "RESERVE r1 x 2",
                "SHIP ship_bad x 3",
                "RELEASE release_bad x 3",
                "RESERVE r2 x 3",
                "SHIP ship_bad x 3",
                "RELEASE release_bad x 3",
            ],
            [
                "OK 10 2",
                "REJECTED 10 2",
                "REJECTED 10 2",
                "OK 10 5",
                "DUPLICATE 10 5",
                "DUPLICATE 10 5",
                "OPEN 1",
                "x 5",
            ],
        )

    def test_13_multiple_orders_and_open_sorted(self) -> None:
        """OPEN 只显示剩余预留大于 0 的订单，并按 order_id 字典序输出。"""
        self.assert_ledger(
            20,
            [
                "RESERVE a z 1",
                "RESERVE b b 5",
                "RESERVE c a 2",
                "RELEASE d b 5",  # b 不应出现在 OPEN
                "RESERVE e A 3",  # 大小写的字典序
            ],
            [
                "OK 20 1",
                "OK 20 6",
                "OK 20 8",
                "OK 20 3",
                "OK 20 6",
                "OPEN 3",
                "A 3",
                "a 2",
                "z 1",
            ],
        )

    def test_14_event_ids_are_case_sensitive(self) -> None:
        self.assert_ledger(
            3,
            ["RESERVE E x 1", "RESERVE e x 1", "RESERVE E x 1"],
            ["OK 3 1", "OK 3 2", "DUPLICATE 3 2", "OPEN 1", "x 2"],
        )

    def test_15_same_order_multiple_reservations_accumulate(self) -> None:
        self.assert_ledger(
            8,
            [
                "RESERVE a order 2",
                "RESERVE b order 3",
                "RELEASE c order 1",
                "SHIP d order 2",
                "RESERVE e order 4",
            ],
            [
                "OK 8 2",
                "OK 8 5",
                "OK 8 4",
                "OK 6 2",
                "OK 6 6",
                "OPEN 1",
                "order 6",
            ],
        )

    def test_16_invalid_qty_in_all_four_commands(self) -> None:
        """零、负数、非整数、超过题目约束上限的 qty 均拒绝且状态不变。"""
        invalid_quantities = ["0", "-1", "-999", "1.5", "abc", "1e3", str(MAX_QTY + 1)]
        command_templates = [
            "RESERVE {eid} o1 {qty}",
            "RELEASE {eid} o1 {qty}",
            "SHIP {eid} o1 {qty}",
            "RESTOCK {eid} {qty}",
        ]
        # 各坏命令使用独立的 event_id，不依赖“格式错误的事件是否占用 ID”这一未定义行为。
        for template in command_templates:
            with self.subTest(operation=template.split()[0]):
                commands = ["RESERVE seed o1 3"]
                expected = ["OK 5 3"]
                for index, qty in enumerate(invalid_quantities):
                    commands.append(template.format(eid=f"bad_{index}", qty=qty))
                    expected.append("REJECTED 5 3")
                commands.append("SHIP after o1 1")
                expected.extend(["OK 4 2", "OPEN 1", "o1 2"])
                self.assert_ledger(5, commands, expected)

    def test_17_invalid_command_name_and_arity(self) -> None:
        """未知命令、大小写错误、缺字段、多字段、空行全部拒绝。"""
        bad_commands = [
            "DELETE e1 x 1",
            "reserve e1 x 1",
            "Ship e1 x 1",
            "RESERVE",
            "RESERVE e1 x",
            "RESERVE e1 x 1 extra",
            "RELEASE e1",
            "RELEASE e1 x",
            "RELEASE e1 x 1 extra",
            "SHIP e1",
            "SHIP e1 x",
            "SHIP e1 x 1 extra",
            "RESTOCK",
            "RESTOCK e1",
            "RESTOCK e1 1 extra",
            "",  # 空白命令行
        ]
        # 一次子进程测试所有非法命令，降低 Windows 平台反复启动解释器的开销。
        commands = ["RESERVE seed x 3"]
        for index, bad in enumerate(bad_commands):
            commands.append(bad.replace("e1", f"bad_{index}"))
        commands.append("RELEASE good x 1")
        expected = ["OK 5 3"] + ["REJECTED 5 3"] * len(bad_commands)
        expected += ["OK 5 2", "OPEN 1", "x 2"]
        self.assert_ledger(5, commands, expected)

    def test_18_non_ascii_ids_are_invalid(self) -> None:
        """题目要求 event_id/order_id 为 ASCII token。"""
        self.assert_ledger(
            2,
            [
                "RESERVE 事件 x 1",
                "RESERVE good 订单 1",
                "RESTOCK 补货 1",
                "RESERVE valid x 1",
            ],
            ["REJECTED 2 0", "REJECTED 2 0", "REJECTED 2 0", "OK 2 1", "OPEN 1", "x 1"],
        )

    def test_19_maximum_qty_and_initial_stock(self) -> None:
        """精确测试上限 10^12，以及 Python 整数处理。"""
        q = MAX_QTY
        self.assert_ledger(
            q,
            [
                f"RESERVE a x {q}",
                f"SHIP b x {q}",
                f"RESTOCK c {q}",
                f"RESERVE d y {q}",
            ],
            [
                f"OK {q} {q}",
                "OK 0 0",
                f"OK {q} 0",
                f"OK {q} {q}",
                "OPEN 1",
                f"y {q}",
            ],
        )

    def test_20_on_hand_can_exceed_initial_stock_limit_after_restock(self) -> None:
        """S<=10^12 是初始值上限，不意味着补货后的库存也最多 10^12。"""
        q = MAX_QTY
        self.assert_ledger(
            q,
            [f"RESTOCK e1 {q}", f"RESTOCK e2 {q}", f"RESERVE e3 x {q}"],
            [f"OK {2*q} 0", f"OK {3*q} 0", f"OK {3*q} {q}", "OPEN 1", f"x {q}"],
        )

    def test_21_no_partial_mutation_on_business_rejection(self) -> None:
        """拒绝的 RESERVE/RELEASE/SHIP 都不能对任一状态产生部分改动。"""
        self.assert_ledger(
            5,
            [
                "RESERVE a x 4",
                "RESERVE b y 2",  # 库存不足，不得先加订单预留
                "RELEASE c x 5",  # 不能先清空一部分
                "SHIP d x 5",     # 不能先扣 on_hand
                "SHIP e x 2",     # 前面没有破坏 x=4
                "RESERVE f y 3",  # 已发货释放的可用额度仍遵循 on_hand-reserved
            ],
            [
                "OK 5 4",
                "REJECTED 5 4",
                "REJECTED 5 4",
                "REJECTED 5 4",
                "OK 3 2",
                "REJECTED 3 2",
                "OPEN 1",
                "x 2",
            ],
        )

    def test_22_zero_and_one_remaining_stock(self) -> None:
        self.assert_ledger(
            2,
            [
                "RESERVE a x 1",
                "RESERVE b y 1",
                "SHIP c x 1",
                "RESERVE d z 1",  # on_hand=1, reserved=1 => available=0
                "RELEASE e y 1",
                "RESERVE f z 1",
            ],
            [
                "OK 2 1",
                "OK 2 2",
                "OK 1 1",
                "REJECTED 1 1",
                "OK 1 0",
                "OK 1 1",
                "OPEN 1",
                "z 1",
            ],
        )

    def test_23_ascii_symbols_in_ids(self) -> None:
        """非空 ASCII token 可以包含没有空格的符号；大小写与字符串均应原样区分。"""
        self.assert_ledger(
            3,
            [
                "RESERVE evt-1 order_1 1",
                "RESERVE evt.2 @123 1",
                "RESERVE evt/3 order-2 1",
            ],
            [
                "OK 3 1",
                "OK 3 2",
                "OK 3 3",
                "OPEN 3",
                "@123 1",
                "order-2 1",
                "order_1 1",
            ],
        )

    def test_24_open_order_ids_are_sorted_as_strings(self) -> None:
        self.assert_ledger(
            3,
            ["RESERVE a o2 1", "RESERVE b o10 1", "RESERVE c o1 1"],
            ["OK 3 1", "OK 3 2", "OK 3 3", "OPEN 3", "o1 1", "o10 1", "o2 1"],
        )

    def test_25_randomized_differential_against_reference_model(self) -> None:
        """固定随机种子：混合 1200 条命令，与独立参考状态机逐行对比。"""
        rng = random.Random(20261025)
        stock = 37
        on_hand = stock
        orders: dict[str, int] = {}
        seen: set[str] = set()
        commands: list[str] = []
        expected: list[str] = []
        known_event_ids: list[str] = []

        for i in range(1200):
            action = rng.choice(("RESERVE", "RELEASE", "SHIP", "RESTOCK"))
            order_id = f"o{rng.randrange(20):02d}"
            qty = rng.randint(1, 50)
            if known_event_ids and rng.random() < 0.20:
                event_id = rng.choice(known_event_ids)
            else:
                event_id = f"event_{i}"
                known_event_ids.append(event_id)

            if action == "RESTOCK":
                commands.append(f"RESTOCK {event_id} {qty}")
            else:
                commands.append(f"{action} {event_id} {order_id} {qty}")

            # 独立参考模型：仅使用有效输入测试业务规则/幂等性。
            if event_id in seen:
                status = "DUPLICATE"
            else:
                seen.add(event_id)
                status = "OK"
                total_reserved = sum(orders.values())
                current = orders.get(order_id, 0)

                if action == "RESERVE":
                    if qty > on_hand - total_reserved:
                        status = "REJECTED"
                    else:
                        orders[order_id] = current + qty
                elif action in ("RELEASE", "SHIP"):
                    if qty > current:
                        status = "REJECTED"
                    else:
                        new_reserved = current - qty
                        if new_reserved:
                            orders[order_id] = new_reserved
                        else:
                            orders.pop(order_id, None)
                        if action == "SHIP":
                            on_hand -= qty
                else:  # RESTOCK
                    on_hand += qty

            expected.append(f"{status} {on_hand} {sum(orders.values())}")
            # 参考模型的不变量，确保测试数据本身自洽。
            self.assertGreaterEqual(on_hand - sum(orders.values()), 0)

        expected.append(f"OPEN {len(orders)}")
        expected.extend(f"{order_id} {orders[order_id]}" for order_id in sorted(orders))
        self.assert_ledger(stock, commands, expected)

    def test_26_whitespace_and_long_ascii_ids(self) -> None:
        """分隔符允许多个空格或制表符；ASCII ID 没有给定长度上限。"""
        event_id = "event_" + "e" * 256
        order_id = "order_" + "x" * 256
        self.assert_ledger(
            1,
            [
                f"  RESERVE\t{event_id}\t{order_id}\t1  ",
                "  RESTOCK  add_stock\t2  ",
            ],
            ["OK 1 1", "OK 3 1", "OPEN 1", f"{order_id} 1"],
        )

    def test_27_duplicate_restock_does_not_increase_stock_again(self) -> None:
        """已成功 RESTOCK 的 event_id 重放不能重复补货。"""
        self.assert_ledger(
            1,
            [
                "RESTOCK e1 5",
                "RESTOCK e1 7",
                "RESERVE e2 x 6",
                "SHIP e3 x 6",
            ],
            ["OK 6 0", "DUPLICATE 6 0", "OK 6 6", "OK 0 0", "OPEN 0"],
        )

    @unittest.skipUnless(os.environ.get("RUN_STRESS") == "1", "设置 RUN_STRESS=1 开启 20 万命令压力测试")
    def test_28_optional_max_commands_200000(self) -> None:
        """最大 N=200000；反复补货而非超大输入行，检验性能/吞吐。"""
        n = 200_000
        commands = [f"RESTOCK e{i} 1" for i in range(n)]
        expected = [f"OK {i} 0" for i in range(1, n + 1)] + ["OPEN 0"]
        self.assert_ledger(0, commands, expected, timeout=60)


if __name__ == "__main__":
    unittest.main(verbosity=2)


