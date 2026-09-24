# Translation workflow details

## Model and dependency preflight

Read the current `collaboration.spawn_agent` model override options at the start of each run. Present all actual display names and exact IDs to the user; options from another tool or an older session are not evidence of subagent availability. Use the chosen ID for every translator and no override for the auditor. If the chosen ID is rejected or disappears, obtain a new choice before dispatching translators.

After the user selects a translator model, list the concrete commands and PDF capabilities planned for this run. Check their imports or runtime availability in the **environment where each command will execute**, including bundled dependencies. `scripts/translation_files.py` uses only Python's standard library. A package such as PyYAML is needed only if a selected step actually imports it; do not install or propose it by default. Present only confirmed missing, necessary packages, stating each package's task, installation command or method, target environment, and any workable no-install alternative. If there are no missing packages, explicitly report that no installation is needed. Ask the user to approve the method before installing. After the method is agreed, summarize the whole translation workflow and obtain a separate explicit confirmation to begin. Only then may the coordinator install agreed packages and start work.

Subagents have no environment-management permission under this skill. Put this restriction in **each agent's prompt**, even when that agent starts with no inherited history: no package installation, upgrade, or removal; no virtual-environment creation or modification; no global configuration or destructive work-environment changes. Translators read only their own PDF copy and send Markdown. The auditor only saves assigned translation text and reports status.

## Boundaries and handoff

- Use the first numbered main-text heading (often `1. Introduction`) as A for fragment 1. The next heading is B. Repeat for every numbered heading, including parent headings immediately followed by a child heading; such a fragment may contain only its title. The final B is `References`. Preserve the source heading hierarchy as Markdown: main sections `##`, one decimal level `###`, two decimal levels `####`.
- Do not include abstract, References entries, page headers, publisher logos, or repeated peer-review overlays. Include body text, text tables, figure/table captions, footnotes that belong to the body, and citation markers. The coordinator reads only headings for assignment; each translator reads the text between its own boundaries from its own PDF copy through `pdf:pdf`.
- Prepare a JSON array of heading strings in PDF order, ending with `References`. The file preparation command makes one byte-identical PDF copy per fragment, checks SHA-256, creates a manifest, and reserves output names. Use a fresh workspace for each run:

  `python scripts/translation_files.py prepare --pdf /absolute/source.pdf --headings /absolute/headings.json --workspace /absolute/run-directory`

- The manifest gives each translator its start heading, end heading, PDF copy, and output filename. Filename format: `NN__<start-title-slug>__to__<end-title-slug>.md`. The last slug is `references`. Give the translator its exact assignment and selected model. Because the model override may require `fork_turns="none"`, repeat all task context in the prompt rather than relying on conversation history.
- Render [Auditor's input prompt](auditor-prompt.md) first: replace `{{manifest_path}}`, `{{fragments_dir}}`, and `{{coordinator_task_name}}` with absolute values, then spawn the auditor with **no model override**. Wait for its ready message before starting translators.
- For each manifest record, render [Translater n's input prompt](translater-prompt.md): replace `{{fragment_number}}`, `{{pdf_copy_path}}`, `{{start_heading}}`, `{{end_heading}}`, `{{heading_prefix}}` (`##`, `###`, or `####`), and `{{auditor_task_name}}`. Pass the **entire rendered prompt**, not a path, to the translator spawned with the model the user selected. Ensure no `{{...}}` placeholder remains. The translator's final Markdown reply is the **single canonical text**; its message to the auditor is an identical copy with a numbered header outside the Markdown payload.
- The auditor checks for a normal translation rather than a greeting/error and writes only the Markdown payload verbatim to the manifest path. It must not edit the text, silently fill gaps, or assess accuracy. If a payload is abnormal, have that translator rework it before accepting the file. Keep a status table and schedule a new translator only when one of the two translator slots is free.

## SHA-256 handoff verification

For each fragment, after the translator's final reply and the auditor's save are both available, the coordinator saves the **raw final reply as received from the agent tool** to a separate scratch UTF-8 file, such as `handoffs/03.final.md`. Do not copy from the auditor file, trim whitespace, normalize newlines, or append a final newline. If the tool cannot provide the reply without such alteration, do not claim verified consistency or merge; report the limitation.

Compare the scratch file to the auditor's fragment file:

`python scripts/translation_files.py verify --manifest /absolute/run-directory/fragment_manifest.json --number 3 --final-text /absolute/run-directory/handoffs/03.final.md`

The command reads both files in chunks, compares their SHA-256 digests, and records a digest receipt only on a match. On mismatch, halt that fragment: give the auditor the raw canonical reply for another form check and verbatim save, or request a new translator submission; then run verification again. Do not repair the fragment silently. The coordinator tells the auditor that all fragments are verified only when every receipt exists and matches its current file. The auditor then returns its final report and ends.

## Merge and phase acceptance

After all manifest files are accepted:

`python scripts/translation_files.py merge --manifest /absolute/run-directory/fragment_manifest.json --output /absolute/run-directory/outputs/paper_translation_initial.md`

The merge command requires all expected files, no extra fragment files, UTF-8 readability, a numbered opening heading in each fragment, no References heading, and a valid verification receipt matching every current fragment file. It joins fragments in manifest order, inserting only the needed blank lines. The coordinator checks that the heading sequence matches the PDF, the body ends before References, and figure/table captions remain present. Confirm the auditor's final report has arrived and no `Translater n` or `Auditor` is still running before phase acceptance.

## Figure and formula correction—coordinator only

1. Reopen the source PDF and inventory body figures by visual page position and caption. Ignore publisher marks and non-body images. Extract or render each figure faithfully, including labels, and save a copy under the corrected document's `assets/` folder as `figure-1.png`, `figure-2.png`, etc. Place `<img src="./assets/figure-1.png" alt="figure-1" />` immediately before its separate `**图 1.** 描述` paragraph. Match figures and captions one-to-one and correct caption wording against the PDF.
2. Inspect **all display equations first**, preferably against rendered PDF crops; compare variables, subscripts, superscripts, sum bounds, brackets, roots, norms, bars, and bold/upright styling. Only then inspect **all inline mathematical expressions** and the surrounding explanatory notation. PDF text extraction can lose math formatting, so use visual evidence for ambiguous symbols.
3. Save a new corrected Markdown file. Do not overwrite the initial merge or any auditor-saved fragment. Perform a structural check against the heading manifest, initial merge, and source PDF: every body heading appears once in the correct order and Markdown level; no Abstract or References section enters the body; paragraphs, tables, captions, and equations remain under their corresponding headings and in source order; no content is accidentally duplicated or dropped during correction. Also check relative image paths and actual files, figure numbering/order and caption adjacency, balanced math delimiters, and unchanged SHA-256 of the initial merge. Deliver both the corrected file and its image assets.
