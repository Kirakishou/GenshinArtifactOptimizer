import functools

def iterate_integer_composition(arr, itr):
    while arr[itr] == 0:
        arr[itr] = arr[itr + 1]
        arr[itr + 1] = 0
        itr -= 1

    arr[itr] -= 1
    arr[itr + 1] += 1
    if itr != len(arr) - 2:
        itr += 1

    return (arr, itr)


def comp_over_limits(arr, lims):
    for i in range(len(arr)):
        if arr[i] > lims[i]:
            return True
    return False


def k_slots_at_least_d(arr, d, k):
    num_valid = 0
    for val in arr:
        if val >= d:
            num_valid += 1
            if num_valid == k:
                return True
    return False


def is_iteration_finished(arr, sum, lims=None):
    if lims:
        end_total = 0
        for i in range(len(arr) - 1, -1, -1):
            if arr[i] < lims[i]:
                return False
            end_total += arr[i]
            if end_total == sum:
                return True
    return arr[-1] == sum