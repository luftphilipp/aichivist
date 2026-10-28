"""German messages. Key: the English text as written in the code; value: the German text with the same {fields}."""

GERMAN_NOUNS = {
    "file": ("Datei", "Dateien"),
    "document": ("Dokument", "Dokumente"),
    "duplicate file": ("doppelte Datei", "doppelte Dateien"),
    "group": ("Gruppe", "Gruppen"),
}

GERMAN = {
    # survey
    "{place}: {files}, {size} - disk {free} free of {total}":
        "{place}: {files}, {size} – Laufwerk: {free} von {total} frei",
    "  types: {top}": "  Dateitypen: {top}",
    "  empty": "  leer",
    "  ! {n} with unclear names": "  ! {n} mit unklarem Namen",
    " (e.g. {names})": " (z. B. {names})",
    "  ! {n} ({size}) unchanged for years": "  ! {n} ({size}) seit Jahren unverändert",
    "  i {n} ({size}) only in the cloud - counted, not downloaded":
        "  i {n} ({size}) nur in der Cloud – gezählt, nicht heruntergeladen",
    "  ! keep out of cloud sync: {folder} ({n})": "  ! nicht in die Cloud-Synchronisation: {folder} ({n})",
    "  i {n} smaller code projects - keep them in Git rather than cloud sync":
        "  i {n} kleinere Code-Projekte – besser mit Git sichern als in der Cloud",
    "  ! program folder, keep it as it is: {folder} ({kind})": "  ! Programmordner, so lassen: {folder} ({kind})",
    "  … and {n} more program folders": "  … und {n} weitere Programmordner",
    "  drive health: {status}{extra} ({detail})": "  Zustand des Laufwerks: {status}{extra} ({detail})",
    "passed": "in Ordnung",
    "failed": "fehlerhaft",
    "unknown": "unbekannt",
    "{files} in {groups} waste {size} (e.g. {a} = {b})": "{files} in {groups} belegen unnötig {size} (z. B. {a} = {b})",
    "no duplicate files found": "keine doppelten Dateien gefunden",
    "Nothing was changed. Next: ask your agent to \"tidy up\" - it proposes a filing plan for you to approve.":
        "Es wurde nichts verändert. Nächster Schritt: Bitte deine KI „räum auf“ – sie schlägt dir einen Ablageplan "
        "zum Freigeben vor.",
    # structure
    "{area}: {n} folders – the structure looks tidy.": "{area}: {n} Ordner – die Struktur sieht aufgeräumt aus.",
    "{area}: {n} folders, {k} things to improve": "{area}: {n} Ordner, {k} Verbesserungsmöglichkeiten",
    "e.g.:": "z. B.:",
    "{n} top-level folders – group them into up to 10 areas (e.g. Personal, Finance, Work, Study)":
        "{n} Ordner auf oberster Ebene – zu höchstens 10 Bereichen zusammenfassen (z. B. Privat, Finanzen, Arbeit, "
        "Studium)",
    "{folder}: {n} folders deep – flatten to at most 4 levels": "{folder}: {n} Ordner tief – auf höchstens 4 Ebenen "
                                                                "verflachen",
    "{folder}: contains only one folder – that level can go":
        "{folder}: enthält nur einen Ordner – diese Ebene kann weg",
    "{folder}: only {n} file(s) – move them up and remove the folder":
        "{folder}: nur {n} Datei(en) – eine Ebene höher legen und den Ordner entfernen",
    "{folder}: empty – can be removed": "{folder}: leer – kann entfernt werden",
    "{folder}: sorted by file type, not subject – file its {n} files by what they are about":
        "{folder}: nach Dateityp statt nach Thema sortiert – die {n} Dateien nach Inhalt ablegen",
    "'{folder}' exists {n} times ({where}) – keep one place for this subject":
        "„{folder}“ gibt es {n}-mal ({where}) – für dieses Thema nur einen Ort verwenden",
    "too many top-level folders": "zu viele Ordner auf oberster Ebene",
    "folders nested too deeply": "zu tief verschachtelte Ordner",
    "folders that only contain one folder": "Ordner, die nur einen Ordner enthalten",
    "folders with only 1–2 files": "Ordner mit nur 1–2 Dateien",
    "empty folders": "leere Ordner",
    "folders sorted by file type": "nach Dateityp sortierte Ordner",
    "folder names used several times": "mehrfach verwendete Ordnernamen",
    "Nothing was changed. Simple fixes: `aichivist structure <folder> --plan plan.md`; for regrouping, ask your AI "
    "to propose a leaner structure.":
        "Es wurde nichts verändert. Einfache Korrekturen: `aichivist structure <Ordner> --plan plan.md`; für eine "
        "neue Gliederung bitte deine KI um einen schlankeren Vorschlag.",
    # storage
    "only {n} cop(ies) – add {more} more (e.g. an external drive, or a backup to the cloud)":
        "nur {n} Kopie(n) – {more} weitere anlegen (z. B. eine externe Festplatte oder ein Backup in die Cloud)",
    "all copies are on the same kind of storage – use a second kind (drive, cloud, NAS)":
        "alle Kopien auf derselben Art von Speicher – eine zweite Art nutzen (Festplatte, Cloud, NAS)",
    "no copy away from home – a fire or burglary would take everything; keep one copy in the cloud or a drive at "
    "another place":
        "keine Kopie außer Haus – ein Brand oder Einbruch nähme alles mit; eine Kopie in die Cloud oder auf eine "
        "Festplatte an einem anderen Ort",
    "only in the cloud – if the account is lost or closed, so are the files; keep a local copy":
        "nur in der Cloud – geht das Konto verloren oder wird es geschlossen, sind die Dateien weg; eine Kopie lokal "
        "behalten",
    "{place}: unknown kind '{kind}' (use {known})": "{place}: unbekannte Art „{kind}“ (möglich: {known})",
    "{place}: price without 'month', 'year' or 'once' – cost not counted":
        "{place}: Preis ohne „month“, „year“ oder „once“ – Kosten nicht gezählt",
    "safe (3-2-1)": "sicher (3-2-1)",
    "at risk": "gefährdet",
    "{area}: {copies} copies on {kinds} kind(s), {away} away from home – {status}":
        "{area}: {copies} Kopie(n) auf {kinds} Speicherart(en), {away} außer Haus – {status}",
    "Cost per year: {costs} – total {total}": "Kosten pro Jahr: {costs} – total {total}",
    "NOTE {problem}": "HINWEIS {problem}",
    "Prices are the ones in your table – check current offers before deciding. Nothing was changed.":
        "Die Preise stammen aus deiner Tabelle – vor einem Entscheid aktuelle Angebote prüfen. Es wurde nichts "
        "verändert.",
    "{table} does not exist yet. List your storage places like this:":
        "{table} gibt es noch nicht. Trage deine Speicherorte so ein:",
    # program data
    "in the program folder {place}": "im Programmordner {place}",
    "in the hidden program folder {place}": "im versteckten Programmordner {place}",
    "is a {kind}": "ist eine {kind}",
    "part of a {kind} ({folder})": "Teil einer {kind} ({folder})",
    "contains a {kind} ({folder})": "enthält eine {kind} ({folder})",
    "the link {link} points to it": "die Verknüpfung {link} zeigt darauf",
    " and {n} more": " und {n} weiteren",
    "open in {programs}{more} – close it first": "geöffnet in {programs}{more} – zuerst schließen",
    "no program depends on it": "kein Programm hängt davon ab",
    "Before moving: adjust the program, or move with --leave-link (plan mark `link`).":
        "Vor dem Verschieben: das Programm umstellen oder mit --leave-link verschieben (Plan-Markierung `link`).",
    "program": "Programm",
    "Photos library": "Fotos-Mediathek",
    "Music library": "Musik-Mediathek",
    "TV library": "TV-Mediathek",
    "Lightroom catalog": "Lightroom-Katalog",
    "Final Cut library": "Final-Cut-Mediathek",
    "Logic project": "Logic-Projekt",
    "GarageBand project": "GarageBand-Projekt",
    "Aperture library": "Aperture-Mediathek",
    "virtual machine": "virtuelle Maschine",
    "Obsidian vault": "Obsidian-Sammlung",
    "Zotero library": "Zotero-Bibliothek",
    "Calibre library": "Calibre-Bibliothek",
    "Anki profile": "Anki-Profil",
    "Steam library": "Steam-Bibliothek",
    "Firefox/Thunderbird profile": "Firefox-/Thunderbird-Profil",
    "Minecraft folder": "Minecraft-Ordner",
    "code project": "Code-Projekt",
    "iTunes library": "iTunes-Mediathek",
    # file operations and collections
    "{path} is inside the closed collection {root}; reopen it first":
        "{path} liegt im abgeschlossenen Bestand {root}; zuerst wieder öffnen",
    "{path} contains the closed collection {inner}; reopen it first":
        "{path} enthält den abgeschlossenen Bestand {inner}; zuerst wieder öffnen",
    "copy of {src} did not match the original; original kept":
        "die Kopie von {src} stimmte nicht mit dem Original überein; Original behalten",
    "{src}: a program may stop working – {reasons}. If deleting it is intended, use --app-data":
        "{src}: ein Programm könnte nicht mehr funktionieren – {reasons}. Ist das Löschen gewollt, dann mit "
        "--app-data",
    "{src}: a program may stop working – {reasons}. Adjust the program and use --app-data, or keep a link at the "
    "old place with --leave-link":
        "{src}: ein Programm könnte nicht mehr funktionieren – {reasons}. Programm umstellen und --app-data nutzen, "
        "oder mit --leave-link eine Verknüpfung am alten Ort lassen",
    "source missing: {src}": "Quelle fehlt: {src}",
    "target exists, nothing overwritten: {dst}": "Ziel existiert schon, nichts überschrieben: {dst}",
    "target folder missing (new folders need approval): {folder}":
        "Zielordner fehlt (neue Ordner brauchen eine Freigabe): {folder}",
    "could not leave a link at {src} ({err}); nothing moved. Files can only be linked on the same drive":
        "konnte am alten Ort {src} keine Verknüpfung anlegen ({err}); nichts verschoben. Dateien lassen sich nur auf "
        "demselben Laufwerk verknüpfen",
    "not a folder: {area}": "kein Ordner: {area}",
    "already closed: {area}": "schon abgeschlossen: {area}",
    "{area} contains the closed collection {inner}; nested collections are not supported – close the sub-folders "
    "separately":
        "{area} enthält den abgeschlossenen Bestand {inner}; verschachtelte Bestände gehen nicht – die Unterordner "
        "einzeln abschließen",
    "not closed: {area}": "nicht abgeschlossen: {area}",
    "{area} is part of the closed collection {root}; reopen that folder":
        "{area} gehört zum abgeschlossenen Bestand {root}; diesen Ordner wieder öffnen",
    "not closed, nothing to verify: {area}": "nicht abgeschlossen, nichts zu prüfen: {area}",
    "open": "offen",
    "closed": "abgeschlossen",
    " since {when}, {files}": " seit {when}, {files}",
    "intact: matches the manifest": "intakt: stimmt mit der Prüfliste überein",
    "refused": "abgelehnt",
    "error": "Fehler",
    # plans
    "source missing": "Quelle fehlt",
    "same source as an earlier row": "gleiche Quelle wie in einer früheren Zeile",
    "source is in (or contains) a closed collection":
        "Quelle liegt in einem abgeschlossenen Bestand (oder enthält einen)",
    "a program may stop working – {reasons} (mark `link` to keep a link at the old place)":
        "ein Programm könnte nicht mehr funktionieren – {reasons} (mit `link` markieren, um eine Verknüpfung am alten "
        "Ort zu lassen)",
    "target exists (nothing would be overwritten)": "Ziel existiert schon (es würde nichts überschrieben)",
    "same target as an earlier row": "gleiches Ziel wie in einer früheren Zeile",
    "target folder missing (new folders need approval: apply with --create-folders)":
        "Zielordner fehlt (neue Ordner brauchen eine Freigabe: mit --create-folders ausführen)",
    "target is in a closed collection": "Ziel liegt in einem abgeschlossenen Bestand",
    "proposed": "vorgeschlagen",
    "{n} rows approved": "{n} Zeilen freigegeben",
    "{n} rows approved.": "{n} Zeilen freigegeben.",
    "ROW": "ZEILE",
    "{n} rows, no problems": "{n} Zeilen, keine Probleme",
    "{done} done, {failed} failed (see the plan file)": "{done} erledigt, {failed} fehlgeschlagen (siehe Plandatei)",
    "{n} proposals added to {plan}": "{n} Vorschläge zu {plan} hinzugefügt",
    "review finished ({url})": "Durchsicht beendet ({url})",
    "review plan": "Plan durchsehen",
    "Filing plan – {n} proposals": "Ablageplan – {n} Vorschläge",
    "Untick what you do not want. Nothing moves before you confirm here and the plan is applied.":
        "Entferne das Häkchen bei allem, was du nicht willst. Nichts wird verschoben, bevor du hier bestätigst und "
        "der Plan ausgeführt wird.",
    "Document": "Dokument",
    "New name and place": "Neuer Name und Ort",
    "Why": "Warum",
    "Approve ticked rows": "Angehakte Zeilen freigeben",
    "Trash": "Papierkorb",
    "You can close this tab. Tell your AI to apply the plan (or run <code>aichivist plan apply</code>).":
        "Du kannst diesen Tab schließen. Sag deiner KI, sie soll den Plan ausführen (oder starte "
        "<code>aichivist plan apply</code>).",
    # other commands
    "No earlier snapshot - {n} entries recorded.": "Noch kein früherer Stand – {n} Einträge erfasst.",
    "MOVED BY HAND": "VON HAND VERSCHOBEN",
    "(a correction? consider adapting the rules)": "(eine Korrektur? Regeln eventuell anpassen)",
    "MOVED": "VERSCHOBEN",
    "NEW": "NEU",
    "CHANGED": "GEÄNDERT",
    "REMOVED": "ENTFERNT",
    "No changes.": "Keine Änderungen.",
    "link left at {path}": "Verknüpfung am alten Ort gelassen: {path}",
    "trash": "Papierkorb",
    "SKIPPED (closed collection, or files no longer where the journal says)":
        "ÜBERSPRUNGEN (abgeschlossener Bestand, oder Dateien nicht mehr dort, wo das Protokoll sagt)",
    "{n} step(s) undone": "{n} Schritt(e) rückgängig gemacht",
    "nothing to undo": "nichts rückgängig zu machen",
    "ADDED": "ERGÄNZT",
    "(describe it)": "(beschreiben)",
    "NOT IN CATALOG": "NICHT IM KATALOG",
    "NOT ON DISK": "NICHT VORHANDEN",
    "complete: catalog and files match": "vollständig: Katalog und Dateien stimmen überein",
    "catalog page: {page}": "Katalogseite: {page}",
    "Catalog – {area}": "Katalog – {area}",
    "{entries} entries from {catalogs} catalog(s) in {area}": "{entries} Einträge aus {catalogs} Katalog(en) in {area}",
    "Search: issuer, subject, year …": "Suchen: Absender, Thema, Jahr …",
    "{n} of {total} entries": "{n} von {total} Einträgen",
    "camera": "Kamera",
    "file name": "Dateiname",
    "modified date": "Änderungsdatum",
    "{n} photos/videos proposed in {plan}": "{n} Fotos/Videos in {plan} vorgeschlagen",
    "{n} photos/videos – nothing changed; add --plan <plan.md> to propose them":
        "{n} Fotos/Videos – nichts verändert; mit --plan <plan.md> vorschlagen",
    "{files} waiting in {where} – ask your AI to tidy up.": "{files} warten in {where} – bitte deine KI aufzuräumen.",
    "below the threshold": "unter der Schwelle",
    "no daily check was installed": "es war keine tägliche Prüfung eingerichtet",
    "name at least one inbox, e.g. aichivist watch ~/Downloads": "mindestens einen Eingang nennen, z. B. aichivist "
                                                                  "watch ~/Downloads",
    "daily at {at}: a reminder when {n}+ files wait": "täglich um {at}: eine Erinnerung, sobald {n}+ Dateien warten",
    "PLACEHOLDER": "PLATZHALTER",
    "line {n}": "Zeile {n}",
    "MISSING FOLDER": "ORDNER FEHLT",
    "rules complete: no placeholders, all folders exist":
        "Regeln vollständig: keine Platzhalter, alle Ordner vorhanden",
    "The newest version on GitHub has not passed its tests yet ({state}) – keeping the installed one.":
        "Die neueste Version auf GitHub hat ihre Tests noch nicht bestanden ({state}) – die installierte bleibt.",
    "Newest tested version on GitHub: {commit}": "Neueste geprüfte Version auf GitHub: {commit}",
    "Updated to {commit} from GitHub.": "Aktualisiert auf {commit} von GitHub.",
    "Update failed – the installed version stays.": "Aktualisierung fehlgeschlagen – die installierte Version bleibt.",
    "Claude Desktop extension: double-click the newest .mcpb from the releases page (if Windows asks which app to "
    "use: Claude Desktop → Settings → Extensions → Advanced settings → Install Extension…).":
        "Claude-Desktop-Erweiterung: die neueste .mcpb von der Release-Seite doppelklicken (fragt Windows nach einem "
        "Programm: Claude Desktop → Einstellungen → Erweiterungen → Erweiterte Einstellungen → "
        "Erweiterung installieren…).",
    # start menu
    "aichivist – your AI tidies up your documents like an archivist.":
        "aichivist – deine KI räumt deine Dokumente auf wie ein Archivar.",
    "Look at my Downloads (nothing is changed)": "Meine Downloads anschauen (es wird nichts verändert)",
    "Look at another folder": "Einen anderen Ordner anschauen",
    "Are my backups safe? (3-2-1 check)": "Sind meine Daten sicher gesichert? (3-2-1-Check)",
    "Searchable page of my catalogs": "Durchsuchbare Seite meiner Kataloge",
    "Daily reminder when files pile up": "Tägliche Erinnerung, wenn sich Dateien stapeln",
    "Let an AI tidy up (Claude Desktop, Claude Code, …)": "Eine KI aufräumen lassen (Claude Desktop, Claude Code …)",
    "Install aichivist permanently": "aichivist dauerhaft installieren",
    "Quit": "Beenden",
    "Your choice: ": "Deine Wahl: ",
    "Please type a number from the list.": "Bitte eine Zahl aus der Liste eingeben.",
    "That did not work: {error}": "Das hat nicht geklappt: {error}",
    "Folder (drag it into this window, or type the path){hint}: ":
        "Ordner (ins Fenster ziehen oder Pfad eingeben){hint}: ",
    "Not a folder: {folder}": "Kein Ordner: {folder}",
    "Looking at {folder} – nothing is changed …": "Ich schaue mir {folder} an – es wird nichts verändert …",
    "Your storage table (Markdown file; leave empty to see the format): ":
        "Deine Speicher-Tabelle (Markdown-Datei; leer lassen, um das Format zu sehen): ",
    "List your storage places in a file like this, then choose this option again:":
        "Trage deine Speicherorte so in eine Datei ein und wähle diesen Punkt dann nochmals:",
    "Install aichivist for your user so it works from everywhere? [y/N] ":
        "aichivist für deinen Benutzer installieren, damit es überall funktioniert? [j/N] ",
    "Installed. From now on: python3 -m aichivist <command>": "Installiert. Ab jetzt: python3 -m aichivist <Befehl>",
    "Installation failed – aichivist still works from this folder.":
        "Installation fehlgeschlagen – aichivist funktioniert weiterhin aus diesem Ordner.",
    "Remind you every morning once {n} files wait in {folder}? [y/N] ":
        "Jeden Morgen erinnern, sobald {n} Dateien in {folder} warten? [j/N] ",
    "Instructions: {link}": "Anleitung: {link}",
    "Next: choose 6 – it shows the quickest way to let an AI tidy up on this computer.":
        "Weiter: Wähle 6 – dort steht der schnellste Weg, wie eine KI auf diesem Computer aufräumt.",
    "No AI app found on this computer. The easiest one: Claude Desktop – {link}":
        "Auf diesem Computer ist keine KI-App installiert. Am einfachsten: Claude Desktop – {link}",
    "Claude Desktop: download aichivist-<version>.mcpb from the releases page, double-click it (if Windows asks "
    "which app to use: Claude Desktop → Settings → Extensions → Advanced settings → Install Extension…), choose "
    "the folders Claude may organize, then ask: \"Tidy up my Downloads.\"":
        "Claude Desktop: aichivist-<Version>.mcpb von der Release-Seite herunterladen, doppelklicken (fragt Windows "
        "nach einem Programm: Claude Desktop → Einstellungen → Erweiterungen → Erweiterte Einstellungen → "
        "Erweiterung installieren…), die Ordner wählen, die Claude ordnen darf, dann fragen: "
        "„Räum meine Downloads auf.“",
    "Claude Code: type /plugin install aichivist --marketplace luftphilipp/aichivist, then say: \"Set up aichivist.\"":
        "Claude Code: /plugin install aichivist --marketplace luftphilipp/aichivist eingeben, dann sagen: "
        "„Richte aichivist ein.“",
    "Codex, Gemini CLI, Cursor: copy templates/AGENTS.md from this folder to where your AI reads its instructions.":
        "Codex, Gemini CLI, Cursor: templates/AGENTS.md aus diesem Ordner dorthin kopieren, wo deine KI ihre "
        "Anweisungen liest.",
    "The AI proposes a plan; nothing is moved before you say yes.":
        "Die KI schlägt einen Plan vor; nichts wird verschoben, bevor du Ja sagst.",
}
