from .records import line_total

RAN_MAIN = False


def price(orders, tax):
    return sum(line_total(order) for order in orders) + tax


if __name__ == "__main__":
    RAN_MAIN = True
    raise SystemExit("main should not run")
