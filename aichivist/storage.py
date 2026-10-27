"""Storage advice: is every area kept safely (3-2-1 rule) and what does the storage cost per year?

The person (or the agent, after asking) lists their storage places in a Markdown table like EXAMPLE – prices are
typed in from the current offer, never built in. Kind: computer, drive, nas, cloud, other. Where: home or away
(another building; cloud always counts as away). Holds: areas, comma separated; "Backup of <place>" holds everything
that place holds. Per: month, year or once (spread over the lifetime in years).
3-2-1: three copies, on two kinds of storage, one of them away from home.
"""
import re
from typing import Dict, List, NamedTuple, Optional

from .config import full_path
from .i18n import t

COPIES, KINDS, AWAY = 3, 2, 1
LIFETIME_YEARS = 5   # a drive bought once is counted as spread over this many years
KNOWN_KINDS = {"computer", "drive", "nas", "cloud", "other"}
PER_YEAR = {"month": 12.0, "year": 1.0}
BACKUP_OF = re.compile(r"^backup of (.+)$", re.IGNORECASE)
COLUMNS = ("place", "kind", "where", "holds", "price", "per")
EXAMPLE = """| Place | Kind | Where | Holds | Price | Per |
|---|---|---|---|---|---|
| Laptop | computer | home | Documents, Photos | 0 | |
| External drive | drive | home | Photos, Backup of Laptop | 120 | once |
| Cloud | cloud | away | Documents | 2.90 | month |
"""


class Place(NamedTuple):
    name: str
    kind: str
    away: bool
    holds: List[str]
    price: float
    per: str


class AreaVerdict(NamedTuple):
    area: str
    places: List[str]
    copies: int
    kinds: int
    away: int
    advice: List[str]


class Report(NamedTuple):
    areas: List[AreaVerdict]
    cost_per_year: Dict[str, float]
    problems: List[str]


def _price(text: str) -> float:
    cleaned = re.sub(r"[^\d.,]", "", text).replace(",", ".")
    return float(cleaned) if cleaned and cleaned.count(".") <= 1 else 0.0


def read(table_file) -> List[Place]:
    """The storage table; rows with too few cells or a header/separator are skipped."""
    places = []
    for line in full_path(table_file).read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < len(COLUMNS) or cells[0].lower() == "place" or set(cells[0]) <= set(":-"):
            continue
        name, kind, where, holds, price, per = cells[:len(COLUMNS)]
        places.append(Place(name, kind.lower(), where.lower() == "away", [h.strip() for h in holds.split(",")
                                                                           if h.strip()], _price(price), per.lower()))
    return places


def _expanded(places: List[Place]) -> Dict[str, List[str]]:
    """Area → places holding a copy; "Backup of X" counts as holding X's areas."""
    by_name = {p.name.lower(): p for p in places}
    holders: Dict[str, List[str]] = {}
    for place in places:
        for item in place.holds:
            backup = BACKUP_OF.match(item)
            source = by_name.get(backup.group(1).strip().lower()) if backup else None
            areas = [h for h in source.holds if not BACKUP_OF.match(h)] if source else [item]
            for area in areas:
                holders.setdefault(area, [])
                if place.name not in holders[area]:
                    holders[area].append(place.name)
    return holders


def _advice(copies: int, kinds: int, away: int, only_cloud: bool) -> List[str]:
    advice = []
    if copies < COPIES:
        advice.append(t("only {n} cop(ies) – add {more} more (e.g. an external drive, or a backup to the cloud)",
                        n=copies, more=COPIES - copies))
    if kinds < KINDS:
        advice.append(t("all copies are on the same kind of storage – use a second kind (drive, cloud, NAS)"))
    if away < AWAY:
        advice.append(t("no copy away from home – a fire or burglary would take everything; keep one copy in the "
                        "cloud or a drive at another place"))
    if only_cloud:
        advice.append(t("only in the cloud – if the account is lost or closed, so are the files; keep a local copy"))
    return advice


def cost_per_year(place: Place, lifetime: float = LIFETIME_YEARS) -> Optional[float]:
    if place.price == 0:
        return 0.0
    if place.per in PER_YEAR:
        return round(place.price * PER_YEAR[place.per], 2)
    if place.per == "once":
        return round(place.price / lifetime, 2)
    return None


def check(table_file, lifetime: float = LIFETIME_YEARS) -> Report:
    places = read(table_file)
    kinds = {p.name: p for p in places}
    problems = [t("{place}: unknown kind '{kind}' (use {known})", place=p.name, kind=p.kind,
                  known=", ".join(sorted(KNOWN_KINDS))) for p in places if p.kind not in KNOWN_KINDS]
    verdicts = []
    for area, names in sorted(_expanded(places).items()):
        held = [kinds[n] for n in names]
        n_kinds = len({p.kind for p in held})
        n_away = sum(1 for p in held if p.away or p.kind == "cloud")
        only_cloud = all(p.kind == "cloud" for p in held)
        verdicts.append(AreaVerdict(area, names, len(held), n_kinds, n_away,
                                    _advice(len(held), n_kinds, n_away, only_cloud)))
    costs: Dict[str, float] = {}
    for place in places:
        cost = cost_per_year(place, lifetime)
        if cost is None:
            problems.append(t("{place}: price without 'month', 'year' or 'once' – cost not counted", place=place.name))
        else:
            costs[place.name] = cost
    return Report(verdicts, costs, problems)


def render(report: Report, currency: str = "") -> List[str]:
    unit = f" {currency}" if currency else ""
    lines = []
    for v in report.areas:
        status = t("safe (3-2-1)") if not v.advice else t("at risk")
        lines.append(t("{area}: {copies} copies on {kinds} kind(s), {away} away from home – {status}", area=v.area,
                       copies=v.copies, kinds=v.kinds, away=v.away, status=status))
        lines += [f"  - {a}" for a in v.advice]
    total = sum(report.cost_per_year.values())
    costs = ", ".join(f"{n} {c:.2f}{unit}" for n, c in report.cost_per_year.items())
    lines.append(t("Cost per year: {costs} – total {total}", costs=costs, total=f"{total:.2f}{unit}"))
    lines += [t("NOTE {problem}", problem=p) for p in report.problems]
    lines.append(t("Prices are the ones in your table – check current offers before deciding. Nothing was changed."))
    return lines


def as_dict(report: Report) -> Dict:
    return {"areas": [v._asdict() for v in report.areas], "cost_per_year": report.cost_per_year,
            "total_per_year": round(sum(report.cost_per_year.values()), 2), "notes": report.problems}
