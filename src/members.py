from dataclasses import dataclass


@dataclass(frozen=True)
class Member:
    uid: int
    code: str


diana = Member(uid=672328094, code="嘉然")
bella = Member(uid=672353429, code="贝拉")
queen = Member(uid=672342685, code="乃琳")
snow = Member(uid=3537115310721781, code="思诺")
fiona = Member(uid=3537115310721181, code="心宜")

ALL = [diana, bella, queen, snow, fiona]
