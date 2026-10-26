import sys

'''
此题目的一些思路卡住，借助ai询问了思路，本题目是多重背包，转移方程的确定询问了ai
'''

def main():
    INF = float('inf')

    # input data
    w, q = map(int, sys.stdin.readline().split())
    warehouse_data = []
    for _ in range(w):
        data = sys.stdin.readline().split()
        warehouse_data.append([data[0]] + list(map(int, data[1:])))

    # warehouse_id 升序排序
    warehouse_data.sort(key=lambda x: x[0])

    '''
    算法: dynamic programming
    dp[i][j]表示前i个仓库容量为j的最小花费
    转移方程： dp[i][j] = min(dp[i-1][j], dp[i - 1][j - k] + warehouse_data[i][2] * (k > 0) + k * warehouse_data[i][-1])，k从1到仓库最大库存
    '''
    # dp[i][j] 表示前 i 个仓库凑出总数量 j 的最优状态 (warehouse_count, total_cost)
    # 基础状态：前 0 个仓库凑出 0 个数量，需要 0 个仓库，花费 0
    dp = [[(INF, INF)] *(q+1) for i in range(w+1)]
    dp[0][0] = (0, 0)
    # path[i][j] 记录第i个仓库用了多少数量
    path = [[0] * (q + 1) for _ in range(w + 1)]

    for i in range(1,w+1):# 遍历仓库
        wid, stock, f_cost, u_cost = warehouse_data[i - 1]
        for j in range(q+1):
            dp[i][j] = dp[i - 1][j] # 不选当前仓库
            path[i][j] = 0
            # 选择仓库
            for k in range(min(j, stock), 0, -1): # 优先选择让当前仓库分配更大数量，从而把更小的余量留给字典序更靠前的仓库
                prev_cnt, prev_cost = dp[i - 1][j - k]
                if prev_cnt != INF:
                    curr_cnt = prev_cnt + 1
                    curr_cost = prev_cost + f_cost + k * u_cost
                    if (curr_cnt, curr_cost) < dp[i][j]:
                        dp[i][j] = (curr_cnt, curr_cost)
                        path[i][j] = k

    if dp[w][q][0] == INF:
        print(-1)
    else:
        print(f"{dp[w][q][0]} {dp[w][q][1]}")

        # 回溯路径
        allocations = []
        curr_j = q
        for i in range(w, 0, -1): # 从最后一个仓库往回推，一直推到第 1 个仓库
            k = path[i][curr_j]
            if k > 0:
                allocations.append((warehouse_data[i - 1][0], k))
                curr_j -= k
        # 倒序输出
        for wid, k in allocations[::-1]:
            print(f"{wid} {k}")



if __name__ == '__main__':
    main()
