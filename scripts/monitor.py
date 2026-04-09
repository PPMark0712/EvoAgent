import time


def checker():
    now = time.localtime()
    if now.tm_hour >= 20 and now.tm_min < 5:
        return "晚上好"
    return None


def make_provider(checker_func, *, interval, return_times):
    returned = 0

    def monitor():
        nonlocal returned
        if return_times is not None and returned >= int(return_times):
            raise EOFError
        while True:
            text = checker_func()
            if text:
                returned += 1
                return text
            time.sleep(interval)

    return monitor


provider = make_provider(checker, interval=60.0, return_times=1)
