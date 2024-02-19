from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from types import NoneType

from typing import Dict, List, Optional, Any, TypeVar, Callable, Type, cast
import dateutil.parser

T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)


def from_datetime(x: Any) -> datetime:
    return dateutil.parser.parse(x)


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except Exception:
            pass
    assert False


def to_float(x: Any) -> float:
    assert isinstance(x, float)
    return x


def to_int(x: Any) -> int:
    assert isinstance(x, int)
    return x


def to_none(x: Any) -> None:
    assert isinstance(x, NoneType)
    return x


def to_class(c: Type[T], x: Any) -> dict:
    return cast(Any, x).to_dict()


@dataclass(order=True)
class MemberTimeDataclass:
    """Class for keeping member connected time and current role"""

    name: str
    id: int
    highest_role_id: int
    connected_at: datetime
    disconnected_at: Optional[datetime] = None
    last_connected_at: Optional[datetime] = None
    last_connected_by: Optional[timedelta] = None
    expected_exponential_intervals: List[float] = None
    total_minutes_connected: float = 0

    def connected_by(self) -> timedelta:
        if (
            self.connected_at is None
            or self.disconnected_at is None
            or isinstance(self.connected_at, str)
            or isinstance(self.disconnected_at, str)
        ):
            print(
                f"Error.. returning 0. {type(self.connected_at)=}{type(self.disconnected_at)=}"
            )
            return timedelta(days=0, seconds=0, microseconds=0)
        return self.disconnected_at - self.connected_at

    def update_total_minutes(self) -> None:
        self.total_minutes_connected += self.connected_by().total_seconds() / 60

    def update_last_connected_by(self) -> None:
        self.last_connected_by = self.connected_by()

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(obj: Any) -> "MemberTimeDataclass":
        assert isinstance(obj, dict)
        name = obj.get("name")
        id = obj.get("id")
        highest_role_id = obj.get("highest_role_id")
        connected_at = from_datetime(obj.get("connected_at"))
        disconnected_at = from_union(
            [from_none, from_datetime], obj.get("disconnected_at")
        )
        last_connected_by = from_union(
            [from_float, from_none], obj.get("last_connected_by")
        )
        expected_exponential_intervals = from_union(
            [lambda x: from_list(from_float, x), from_none],
            obj.get("expected_exponential_intervals"),
        )
        total_minutes_connected = obj.get("total_minutes_connected")
        last_connected_at = from_union(
            [from_none, from_datetime], obj.get("last_connected_at")
        )
        return MemberTimeDataclass(
            name=name,
            id=id,
            highest_role_id=highest_role_id,
            connected_at=connected_at,
            disconnected_at=disconnected_at,
            last_connected_by=last_connected_by,
            expected_exponential_intervals=expected_exponential_intervals,
            total_minutes_connected=total_minutes_connected,
            last_connected_at=last_connected_at,
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["name"] = self.name
        result["id"] = self.id
        result["highest_role_id"] = self.highest_role_id
        result["connected_at"] = (
            self.connected_at.isoformat() if self.connected_at is not None else None
        )
        result["disconnected_at"] = (
            self.disconnected_at.isoformat()
            if self.disconnected_at is not None
            else None
        )
        if self.last_connected_by is not None and isinstance(
            self.last_connected_by, timedelta
        ):
            result["last_connected_by"] = self.last_connected_by.total_seconds()
        elif (
            isinstance(self.last_connected_by, float)
            and self.last_connected_by is not None
        ):
            result["last_connected_by"] = self.last_connected_by
        else:
            result["last_connected_by"] = None

        result["last_connected_at"] = (
            self.last_connected_at.isoformat()
            if self.last_connected_at is not None
            else None
        )
        result["expected_exponential_intervals"] = self.expected_exponential_intervals
        result["total_minutes_connected"] = self.total_minutes_connected
        return result


def member_time_dataclass_from_dict(s: Any) -> List[MemberTimeDataclass]:
    return from_list(MemberTimeDataclass.from_dict, s)


def member_time_dataclass_to_dict(x: List[MemberTimeDataclass]) -> Any:
    return [i.to_dict() for i in x]
