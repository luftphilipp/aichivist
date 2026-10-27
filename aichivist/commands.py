"""Command handlers. Each returns Out(code, data, lines): `data` for --json (agents), `lines` for people."""
from typing import Any, Callable, Dict, List, NamedTuple

from . import (
    apps,
    bagit,
    catalog,
    catalog_page,
    describe,
    duplicates,
    fileops,
    fulltext,
    inventory,
    journal,
    lifecycle,
    notify,
    photos,
    plan,
    protect,
    retention,
    review,
    rules,
    schedule,
    similar,
    storage,
    structure,
    style,
    survey,
    undo,
    update,
)
from .i18n import count
from .i18n import t as t_


class Out(NamedTuple):
    code: int
    data: Any
    lines: List[str]


def cmd_survey(a) -> Out:
    report = survey.run(a.places, stale_years=a.stale_years, find_duplicates=not a.no_duplicates,
                        progress=not a.json)
    return Out(0, survey.as_dict(report), survey.render(report))


def cmd_inventory(a) -> Out:
    changes = inventory.diff(a.folder, save=a.save)
    if changes.first_run:
        return Out(0, {"first_run": True, "entries": changes.entries},
                   [t_("No earlier snapshot - {n} entries recorded.", n=len(changes.entries))])
    by_hand = inventory.manual_moves(a.folder, changes)
    hint = t_("(a correction? consider adapting the rules)")
    lines = [t_("MOVED BY HAND") + f"\t{o}\t->\t{n}\t{hint}" for o, n in by_hand]
    lines += [t_("MOVED") + f"\t{o}\t->\t{n}" for o, n in changes.moved if (o, n) not in by_hand]
    for label, items in (("NEW", changes.new), ("CHANGED", changes.changed), ("REMOVED", changes.removed)):
        lines += [f"{t_(label)}\t{rel}" for rel in items]
    data = {"first_run": False, "entries": changes.entries,
            "new": changes.new, "changed": changes.changed, "removed": changes.removed,
            "moved": [{"from": o, "to": n, "by_hand": (o, n) in by_hand} for o, n in changes.moved]}
    return Out(0, data, lines or [t_("No changes.")])


def cmd_mv(a) -> Out:
    dst = fileops.move(a.source, a.target, a.create_folder, a.allow_closed, a.app_data, a.leave_link)
    note = [t_("link left at {path}", path=a.source)] if a.leave_link else []
    return Out(0, {"from": a.source, "to": str(dst), "link_left": a.leave_link}, [f"{a.source} -> {dst}"] + note)


def cmd_trash(a) -> Out:
    ctx = None if a.app_data else apps.context()
    moved = [(p, str(fileops.trash(p, a.allow_closed, a.app_data, ctx))) for p in a.paths]
    return Out(0, [{"from": p, "to": dst} for p, dst in moved], [t_("trash") + f": {p} -> {dst}" for p, dst in moved])


def cmd_apps(a) -> Out:
    ctx = apps.context()
    found = {p: apps.risks(p, ctx) for p in a.paths}
    lines = [f"{p}: " + ("; ".join(r) if r else t_("no program depends on it")) for p, r in found.items()]
    if any(found.values()):
        lines.append(t_("Before moving: adjust the program, or move with --leave-link (plan mark `link`)."))
    return Out(0, found, lines)


def cmd_storage(a) -> Out:
    if not fileops.full_path(a.table).exists():
        return Out(1, {"error": "table missing", "example": storage.EXAMPLE},
                   [t_("{table} does not exist yet. List your storage places like this:", table=a.table),
                    storage.EXAMPLE])
    report = storage.check(a.table, a.lifetime)
    return Out(0, storage.as_dict(report), storage.render(report, a.currency))


def cmd_update(a) -> Out:
    found = update.latest()
    if not found.passed:
        return Out(1, found._asdict(), [t_("The newest version on GitHub has not passed its tests yet ({state}) – "
                                           "keeping the installed one.", state=found.state)])
    if a.check:
        return Out(0, found._asdict(), [t_("Newest tested version on GitHub: {commit}", commit=found.commit[:7])])
    code = update.install(found.commit)
    lines = [t_("Updated to {commit} from GitHub.", commit=found.commit[:7]) if code == 0
             else t_("Update failed – the installed version stays.")]
    lines.append(t_("Claude Desktop extension: double-click the newest .mcpb from the releases page."))
    return Out(code, found._asdict(), lines)


def cmd_undo(a) -> Out:
    before = len(undo.open_steps())
    skipped = undo.undo(since=a.since, last=a.last)
    reverted = before - len(undo.open_steps())
    lines = [t_("SKIPPED (closed collection, or files no longer where the journal says)") + f": {e.new} -> {e.old}"
             for e in skipped]
    lines.append(t_("{n} step(s) undone", n=reverted) if reverted else t_("nothing to undo"))
    return Out(0, {"undone": reverted, "skipped": [e._asdict() for e in skipped]}, lines)


def cmd_note(a) -> Out:
    journal.write(a.old, a.new, a.action)
    return Out(0, {"logged": a.action}, ["logged"])


def _status(info) -> Out:
    detail = t_(" since {when}, {files}", when=info.closed_at, files=count(info.file_count, "file")) \
        if info.state == "closed" else ""
    return Out(0, {k: str(v) if v is not None else None for k, v in info._asdict().items()},
               [f"{info.root}: {t_(info.state)}{detail}"])


def cmd_close(a) -> Out:
    return _status(lifecycle.close(a.folder, a.note))


def cmd_reopen(a) -> Out:
    return _status(lifecycle.reopen(a.folder, a.note))


def cmd_status(a) -> Out:
    return _status(lifecycle.status(a.folder))


def cmd_verify(a) -> Out:
    problems = lifecycle.verify(a.folder)
    lines = [f"{kind.upper()}\t{rel}" for kind, items in problems.items() for rel in items]
    ok = not lines
    return Out(0 if ok else 1, problems, lines or [t_("intact: matches the manifest")])


def cmd_check_catalog(a) -> Out:
    added = catalog.add_missing(a.catalog, prefill=a.prefill) if a.add_missing else []
    result = catalog.check(a.catalog)
    lines = [t_("ADDED") + f"\t{rel}\t" + t_("(describe it)") for rel in added]
    lines += [t_("NOT IN CATALOG") + f"\t{rel}" for rel in result.not_in_catalog]
    lines += [t_("NOT ON DISK") + f"\t{rel}" for rel in result.not_on_disk]
    if result.ok:
        lines.append(t_("complete: catalog and files match"))
    return Out(0 if result.ok else 1, {"added": added, **result._asdict()}, lines)


def cmd_duplicates(a) -> Out:
    found = duplicates.find(a.paths, a.area)
    data = [{"source": str(d.source), "match": str(d.match)} for d in found]
    return Out(1 if found else 0, data, [f"DUPLICATE\t{d['source']}\t==\t{d['match']}" for d in data] or
               ["no duplicates"])


def cmd_search(a) -> Out:
    hits = fulltext.search(a.folder, " ".join(a.query))
    lines = [f"{h.file}{f' (page {h.page})' if h.page else ''}\t…{h.snippet}…" for h in hits]
    return Out(0, [h._asdict() for h in hits], lines or ["no matches"])


def cmd_check_rules(a) -> Out:
    result = rules.check(a.rules)
    lines = [t_("PLACEHOLDER") + "\t" + t_("line {n}", n=n) + f"\t{p}" for n, p in result.placeholders]
    lines += [t_("MISSING FOLDER") + f"\t{f}" for f in result.missing_folders]
    data = {"placeholders": [{"line": n, "text": p} for n, p in result.placeholders],
            "missing_folders": result.missing_folders}
    return Out(0 if result.ok else 1, data, lines or [t_("rules complete: no placeholders, all folders exist")])


def cmd_plan(a) -> Out:
    if a.plan_command == "add":
        row = plan.add(a.plan, a.source, a.target, a.reason)
        return Out(0, row._asdict(), [t_("proposed") + f": {row.source} -> {row.target}"])
    if a.plan_command == "approve":
        n = plan.approve(a.plan, a.rows, a.link)
        return Out(0, {"approved": n}, [t_("{n} rows approved", n=n)])
    if a.plan_command == "check":
        results = plan.check(a.plan, a.create_folders)
        bad = [(i, r, p) for i, (r, p) in enumerate(results, 1) if p]
        data = [{"row": i, "source": r.source, "problem": p} for i, r, p in bad]
        return Out(1 if bad else 0, data, [t_("ROW") + f" {i}\t{p}\t{r.source}" for i, r, p in bad] or
                   [t_("{n} rows, no problems", n=len(results))])
    if a.plan_command == "review":
        url = review.serve(a.plan, open_browser=True, block=True)
        return Out(0, {"url": url}, [t_("review finished ({url})", url=url)])
    result = plan.apply(a.plan, a.create_folders)
    lines = [f"error: {reason}\t{source}" for source, reason in result.errors]
    return Out(1 if result.failed else 0, result._asdict(),
               lines + [t_("{done} done, {failed} failed (see the plan file)", done=result.done, failed=result.failed)])


def cmd_photos(a) -> Out:
    found = photos.find(a.inbox)
    root = fileops.full_path(a.to)
    if a.plan:
        photos.propose(a.inbox, root, a.plan)
    data = [{"source": str(p.path), "taken": p.taken, "from": p.source, "target": str(photos.target(p, root))}
            for p in found]
    lines = [f"{p.taken}  ({t_(p.source)})\t{p.path.name}\t->\t{photos.target(p, root)}" for p in found]
    lines.append(t_("{n} photos/videos proposed in {plan}", n=len(found), plan=a.plan) if a.plan else
                 t_("{n} photos/videos – nothing changed; add --plan <plan.md> to propose them", n=len(found)))
    return Out(0, data, lines)


def cmd_catalog_page(a) -> Out:
    out = catalog_page.write(a.area, a.out, a.open)
    return Out(0, {"page": str(out)}, [t_("catalog page: {page}", page=out)])


def cmd_similar(a) -> Out:
    hits = similar.find(a.paths, a.area, a.threshold)
    return Out(1 if hits else 0, [h._asdict() for h in hits],
               [f"SIMILAR {h.similarity:.0%}\t{h.first}\t~\t{h.second}" for h in hits] or ["no similar documents"])


def cmd_suggest(a) -> Out:
    s = describe.suggest(fileops.full_path(a.file))
    return Out(0, s, [f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in s.items()])


def cmd_style(a) -> Out:
    ex = style.examples(a.area)
    lines = [f"{r['before']}  ->  {r['after']}" for r in ex["recent_renames"]]
    lines += [f"{folder}: {', '.join(names)}" for folder, names in ex["names_per_folder"].items()]
    return Out(0, ex, lines or ["no examples yet"])


def cmd_due(a) -> Out:
    if a.plan:
        rows = retention.propose(a.area, a.years, a.plan, a.archive)
        return Out(0, [r._asdict() for r in rows], [t_("{n} proposals added to {plan}", n=len(rows), plan=a.plan)])
    items = retention.due(a.area, a.years)
    return Out(0, [i._asdict() for i in items],
               [f"{i.record_date}\t{i.age_years} y\t{i.path}" for i in items] or ["nothing is due"])


def cmd_structure(a) -> Out:
    if a.plan:
        rows = structure.propose(a.folder, a.plan)
        return Out(0, [r._asdict() for r in rows], [t_("{n} proposals added to {plan}", n=len(rows), plan=a.plan)])
    report = structure.analyse(a.folder)
    data = {"area": report.area, "folders": report.folders, "findings": [f._asdict() for f in report.findings]}
    return Out(0, data, structure.render(report))


def cmd_watch(a) -> Out:
    if a.uninstall:
        done = schedule.uninstall(schedule.removal())
        return Out(0, {"removed": done}, done or [t_("no daily check was installed")])
    if not a.inboxes:
        return Out(2, {"error": "no inbox"}, [t_("name at least one inbox, e.g. aichivist watch ~/Downloads")])
    if a.install:
        try:
            planned = schedule.job(a.inboxes, a.threshold, a.at)
        except ValueError as err:
            return Out(2, {"error": str(err)}, [str(err)])
        done = schedule.install(planned)
        reminder = t_("daily at {at}: a reminder when {n}+ files wait", at=a.at, n=a.threshold)
        return Out(0, {"installed": done}, done + [reminder])
    counts = notify.count(a.inboxes)
    text = notify.message(counts, a.threshold)
    if text:
        notify.show(text)
    return Out(notify.REACHED if text else 0, [c._asdict() for c in counts], [text or t_("below the threshold")])


def cmd_export_bag(a) -> Out:
    dest = bagit.export(a.folder, a.target)
    return Out(0, {"bag": str(dest)}, [f"bag written: {dest}"])


def cmd_validate_bag(a) -> Out:
    problems = bagit.validate(a.bag)
    return Out(1 if problems else 0, {"problems": problems}, problems or ["valid: payload matches the manifests"])


def cmd_protect(a) -> Out:
    return Out(0, {"protected": str(protect.add(a.folder))}, [f"protected: {a.folder}"])


def cmd_unprotect(a) -> Out:
    protect.remove(a.folder)
    return Out(0, {"unprotected": a.folder}, [f"unprotected: {a.folder}"])


def cmd_protected(a) -> Out:
    paths = [str(p) for p in protect.listed()]
    return Out(0, paths, paths or ["no protected areas"])


HANDLERS: Dict[str, Callable[[Any], Out]] = {
    name[len("cmd_"):].replace("_", "-"): fn for name, fn in globals().items() if name.startswith("cmd_")
}
