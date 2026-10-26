import sys

class Inventory:
    def __init__(self, stock):
        self.on_hand = stock
        self.reserved = {} # orderId : qty
        self.total_reserved = 0
        self.processed_events = set()

    def process(self, command_arr):
        if command_arr[1] in self.processed_events:
            return 'DUPLICATE'
        self.processed_events.add(command_arr[1])

        # qty检查
        if not str.isdecimal(command_arr[-1]) or int(command_arr[-1])<=0:
            return 'REJECTED'
        qty = int(command_arr[-1])
        if command_arr[0] == "RESERVE":
            if self.on_hand-self.total_reserved >= qty:
                self.reserved[command_arr[2]] = self.reserved.get(command_arr[2],0) + qty
                self.total_reserved += qty
                return 'OK'
            else:
                return 'REJECTED'
        elif command_arr[0] == "RELEASE":
            if self.reserved.get(command_arr[2]) is None or qty > self.reserved.get(command_arr[2]):
                return 'REJECTED'
            self.reserved[command_arr[2]] -= qty
            self.total_reserved -= qty
            if self.reserved[command_arr[2]]==0:
                self.reserved.pop(command_arr[2])
            return 'OK'
        elif command_arr[0] == "SHIP":
            if self.reserved.get(command_arr[2]) is None or qty > self.reserved.get(command_arr[2]):
                return 'REJECTED'
            self.on_hand -= qty
            self.reserved[command_arr[2]] -= qty
            self.total_reserved -= qty
            if self.reserved[command_arr[2]]==0:
                self.reserved.pop(command_arr[2])
            return 'OK'
        elif command_arr[0] == "RESTOCK":
            self.on_hand += qty
            return 'OK'
        else: # 错误命令
            pass


def main():
    s, n = map(int, sys.stdin.readline().split())
    ledger = Inventory(s)
    for _ in range(n):
        command_arr = sys.stdin.readline().split()
        result = ledger.process(command_arr)
        print(result, ledger.on_hand, ledger.total_reserved)

    # 输出 open
    print('OPEN', len(ledger.reserved.keys()))
    for orderId, qty in ledger.reserved.items():
        print(orderId, qty)


if __name__ == '__main__':
    main()

