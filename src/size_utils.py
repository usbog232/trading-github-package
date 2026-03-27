from decimal import Decimal, ROUND_DOWN
from typing import Union


Number = Union[int, float, str]


def quantize_down(value: Number, decimals: int) -> float:
    q = Decimal('1').scaleb(-decimals)
    d = Decimal(str(value)).quantize(q, rounding=ROUND_DOWN)
    return float(d)
