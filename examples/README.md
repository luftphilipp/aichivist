# Example: one "tidy up" run

All files and names here are invented.

## 1. Create the demo

```bash
python examples/make_demo.py ~/aichivist-demo
aichivist inventory ~/aichivist-demo/Downloads
```

`Downloads/` (the inbox) now holds six unnamed files – all of them are to be filed; `archive/` is the empty filing plan.

## 2. What the agent does (following `templates/RULES.md`)

| Inbox file | Content (read by the agent) | Decision | Command |
|---|---|---|---|
| `scan_0042.txt` | health insurance policy, valid from 2026-01-01 | Personal/Insurance | `aichivist mv … "archive/Personal/Insurance/2026-01-01 Example Health policy basic insurance.txt"` |
| `invoice(1).txt` | mobile invoice February, dated 2026-03-02 | Personal/Phone & internet (by subject, not "invoices") | `aichivist mv … "archive/Personal/Phone & internet/2026-03-02 Example Mobile invoice February 2026.txt"` |
| `invoice(1) copy.txt` | same checksum as the invoice | **deletion list**, not moved | – (human approves → `aichivist trash …`) |
| `voucher.txt` | gift card, no date in the document | no date in the name | `aichivist mv … "archive/Personal/Finance & invoices/Vouchers/Example Store gift card 50.txt"` |
| `IMG_2231.txt` | school diploma | Applications/Certificates | `aichivist mv … "archive/Applications/Certificates/Example School diploma.txt"` |
| `lecture3.txt` | statistics lecture slides | Study, open term | `aichivist mv … "archive/Study/01_Term/Statistics/Slides/Lecture 3 Descriptive statistics.txt"` |

Then the agent adds one catalog line per file, e.g. in `archive/Personal/_catalog.md`:

| File | Content | Search terms | Date |
|---|---|---|---|
| Insurance/2026-01-01 Example Health policy basic insurance.txt | basic health insurance policy, valid from 2026-01-01 | health, policy | 2026-01-01 |

and reports: *5 filed, 1 duplicate on the deletion list, 0 open questions.*

## 2b. The same as a filing plan (what the plugin does)

```bash
P=~/aichivist-demo/plan.md
aichivist plan add $P ~/aichivist-demo/Downloads/scan_0042.txt "~/aichivist-demo/archive/Personal/Insurance/2026-01-01 Example Health policy basic insurance.txt" --reason "health policy"
aichivist plan add $P "~/aichivist-demo/Downloads/invoice(1) copy.txt" TRASH --reason "duplicate of invoice(1).txt"
aichivist plan check $P      # simulate
aichivist plan approve $P    # you approve
aichivist plan apply $P      # executes; plan.md now shows done / error per row
```

## 3. Close a finished collection

```bash
aichivist close ~/aichivist-demo/archive/Study/01_Term --note "all grades received"
aichivist mv ~/aichivist-demo/Downloads/x.txt ~/aichivist-demo/archive/Study/01_Term/x.txt
# refused: … is inside the closed collection …
aichivist verify ~/aichivist-demo/archive/Study/01_Term
# intact: matches the manifest
```

## 4. Archive it as a BagIt bag

```bash
aichivist export-bag ~/aichivist-demo/archive/Study/01_Term ~/aichivist-demo/bag
aichivist validate-bag ~/aichivist-demo/bag
# valid: payload matches the manifests
```

## 5. Undo

```bash
aichivist undo --last 5
```
