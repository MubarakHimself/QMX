# Trading-node increment — transcript fidelity scan (SRC-12), 2026-08-29

Seat T of the change-mode increment. Sources read in full: `archive/trading-node.txt` (SRC-12, 801 rendered lines / 52 KB), `.memlog.md` lines 40, 41, 48, 49, and `ARCHITECTURE-SPINE.md` lines 989–1003 ("Operator rulings 2026-08-28"). Extractions written to `_docwork/harvest/node/extractions-T.yaml` (EXT-2160..EXT-2169). `_docwork/extractions.yaml` untouched.

Method: the transcript's terminal wrapping was normalised (whitespace collapsed, no other change) and every quoted fragment in the memlog and spine was searched as a contiguous string. "Verbatim" below means the exact character sequence occurs contiguously in the operator's own words; anything else is listed as a discrepancy with the transcript wording supplied.

The operator's turns in this sitting are five typed/dictated turns after `❯` (the kickoff `/bmad-architecture` prompt; a model-tier nudge; an internet-outage resume; the next-session-prompt turn) plus four dictated answers inside the single `AskUserQuestion` round. There is no operator turn after the agent's closing summary.

## 1. Verified quotes

| # | Quote as the memlog/spine carry it | Transcript status | Turn |
|---|---|---|---|
| 1 | the same setting or the same logic behind even the agentic system | **VERBATIM** | Q1 answer |
| 2 | it's a user interface on the desktop application as per the overall architecture | **VERBATIM** | Q1 answer |
| 3 | there is nothing like commands or anything | **VERBATIM** (spine capitalises "There" and drops the leading "So"; memlog matches) | Q1 answer |
| 4 | a very separate system, like how big tech teams work | **VERBATIM** (referent differs — see D8) | Q4 answer |
| 5 | two days to a week | **VERBATIM** (spine capitalises "Two"; memlog matches) | Q2 answer |
| 6 | I think a week is enough and sufficient | **VERBATIM** | Q2 answer |
| 7 | the last part should be about the MIS | **VERBATIM** (memlog only) | Q2 answer |
| 8 | two separate acts | **VERBATIM** ("So, two separate acts.") | Q3 answer |
| 9 | doesn't concern you | **VERBATIM** ("so that doesn't concern you because it's part of the agentic system") | Q3 answer |
| 10 | I will not pay for news | **VERBATIM** ("I will not pay for news.") | Q4 answer |
| 11 | I'm not certain yet | **VERBATIM** ("Okay, I'm not certain yet, okay.") | Q4 answer |
| 12 | That question is not for this layer | **VERBATIM** (spine lowercases "that"; scope differs — see D9) | Q4 answer |
| 13 | if we haven't, leave it for now | **VERBATIM** but capitalised in the transcript: "If we haven't, leave it for now." | Q4 answer |
| 14 | first, make the trading node work / Make sure it can execute | **VERBATIM as two sentences**: "Okay, first, make the trading node work. Make sure it can execute." Both memlog and spine merge them with a comma. | Q4 answer |

Nothing in R1–R4 is fabricated: every ruling has an operator sentence behind it, and the four rulings' substance is faithfully carried. The defects below are quotation-form and attribution defects, plus two carry gaps.

## 2. Discrepancies

**D1 — MISATTRIBUTED (highest severity). "I know what you're talking about".** Memlog line 48 and spine R2 attribute this to the operator as evidence he knows a Prometheus/Grafana-class stack. He said the opposite about himself and addressed the phrase to the agent:

> "I don't know if you set it up or you've considered it Prometheus, Grafana. I know how DevOps work, I'm not so technical, I don't know what all that is, but you know what I'm talking about."

Absorbing docs must not present the operator as claiming familiarity with the observability stack. The ruling itself (tracking is mandatory through the soak week) is unaffected; the naming of Prometheus and Grafana *is* his.

**D2 — SPLICED QUOTE. "A simple click on the user interface… two separate acts."** Does not occur contiguously. The transcript has, separately: "But promotion is more like a click on the user interface to be like, okay, now this can go to the live trading node" and, later in the same turn, "So, two separate acts. Promotion is just a simple click because promotion, I'm going to be looking at the results, how it performed". Substance is correct; the quotation is a composite of two sentences with a capitalised "A" added.

**D3 — RECONSTRUCTED QUOTE. "it might have its own page… I'm not certain yet".** The transcript reads: "In fact, it is going to be a plug-in to the UI. It's not a, it doesn't have its own page or something. Okay, I think it might. I think it might. That's why I don't want to talk about it because we don't know. I don't know yet. Okay, I'm not certain yet, okay." The operator leaned to *no* dedicated page and then hedged; the memlog/spine phrasing reverses the lean while keeping the uncertainty. Uncertainty carried faithfully, wording not verbatim.

**D4 — PARAPHRASE IN QUOTES. "focus on live trading".** Transcript: "For you, you're focusing on live trading."

**D5 — DROPPED SELF-CORRECTION. "later versions, yes, we're going to iterate".** Transcript: "Now, the later versions, yes, no, we're going to iterate." The "no," is the operator correcting himself mid-sentence; meaning is unchanged.

**D6 — NOT A QUOTE. "QMF is portable".** The spine renders this in quotation marks. Transcript: "because QMF we made it portable, unless I recall properly, but it is bloody portable. And if it isn't, that doesn't concern you." The "not this layer's concern" disposition is his, and is conditional on the portability being false.

**D7 — SPEAKER OF THE ENUMERATION. R1's list (status, kill everything, resolve a stuck order, promote)** is the *asking agent's* wording inside the AskUserQuestion prompt, not the operator's. His own words: "killing and all that, typing commands and whatnot most likely is going to be controlled via a UI." The hedge "most likely" sits immediately before the flat "So there is nothing like commands or anything."

**D8 — RELOCATED REFERENT. "a very separate system, like how big tech teams work".** Verbatim, but in the transcript it is said of the **DevOps layer or lens** ("I don't think the development operations layer or lens needs to be part of QMX"), not of the deployment recipes. Spine R1 attaches it to the `just node-…` operations toolkit and the memlog also uses it for the separate observability stack; both are downstream readings of one sentence about the DevOps lens as a whole.

**D9 — INFERENCE PRESENTED AS A REFUSAL TO NAME. "that question is not for this layer".** The transcript ties the refusal explicitly to the **node command** half of the bundled Q1 (name *and* command): "things that you're asking about in the question, I think is it the node command? That question is not for this layer. I will repeat this: it's not for this layer. That question was for a layer about QMF." The spine's reading — "the operator declined to rule the name itself" — is a defensible inference (Q1 bundled name and command), but it is an inference. Recommended handling: record it as the brief already does ("the operator declined to name the product — record that") while noting the quote's stated referent was the command question.

**D10 — Case/punctuation only (no meaning change).** Spine capitalises "There is nothing…" and "Two days to a week…"; both merge "first, make the trading node work. Make sure it can execute." into one comma-joined clause; the spine lowercases "if we haven't, leave it for now."

## 3. Uncarried or under-carried operator statements

**U1 — The post-promotion warm-up recollection is unanswered (real gap).** In the Q3 answer: "And I believe, according to the documentation, not every bot starts trading right away. I do recall there is some sort of warm-up period, unless I'm wrong." Neither the memlog nor the spine addresses it. The spine carries the inherited admission row "registration linters, technical demo/paper shakedown, one operator signature; **no probation, no paper-performance gate**" and its only warm-up is the deploy-level first-deploy warm-up week (TN-9). The memlog instead folds the operator's recollection into his *other* sentence about the agentic system's pre-promotion paper period, which is a different thing (pre-promotion, not post-promotion). The increment should close this explicitly: the corpus answer is that promotion admission has no per-bot probation, and the warm-up he remembers is the deploy warm-up week.

**U2 — Why the UI is out of scope (rationale dropped).** "we are not going to build the UI yet. We are mostly back-end data and DevOps. This entire part so far is back-end data and DevOps. The reason we are not putting in the UI is because the UI is a bit large. We can't really have only the UI and take the trading node, it won't make sense. Okay, we are trying to be efficient with our resources." The memlog keeps only "for now back-end + data + DevOps only"; the spine drops the sizing/efficiency rationale entirely. It is the operator's own justification for the UI being its own later sitting.

**U3 — "the trading node is very back-end heavy, to be honest with you. The user interface is less."** A scope statement, carried nowhere.

**U4 — The DevOps lens was DELEGATED, not ruled.** "Now, the one I'm not so certain on, and I will need you to take point on, is the dev opsulence [dictation for: the DevOps lens]. That one I'm not so certain on because I feel like it is going to be standard… unless we don't need it, but we do need it, in my opinion. We need to have logs." The spine presents the DevOps posture as ruled; the transcript shows an explicit delegation with a stated need. Relevant to the increment's authority line (rider, not direct ruling) for everything DevOps-shaped.

**U5 — The "Hammers agent" survives only in the memlog.** "I'm going to have a dedicated agent, I believe it's the Hammers agent. Don't worry about it, we shall set it up because we still haven't done the entire UI stuff and whatnot." Memlog line 48 records it once; the spine's R2 drops it. It is the operator's named future consumer of the observability stack and should survive absorption as a deferred/known-later item, not disappear.

**U6 — The question-quality instruction is recorded nowhere.** Of the promotion question: "don't be stupid, please don't. This is annoying, by the way. Such a question is very annoying" and "this is a very stupid question. Sorry to say, but it is. I get you didn't have all the other context that I'm providing earlier." A posture statement (do not ask what the corpus and plain logic already settle), consistent with the standing operator rules; worth carrying as posture, never as doc prose.

**U7 — The fidelity instruction.** "Okay, I hope I'm clear and quote me right, please. These are more of brain dumps than actual answers." The memlog paraphrases this as its framing ("dictated brain dumps, quoted faithfully and distilled"); the instruction itself — quote me right — is the operator's own and is the standard this scan applies.

**U8 — Two kickoff non-negotiables were superseded by the operator's own later dumps, and nothing records the supersession as such.** Kickoff: "No UI in this phase. UI comes after the agentic system. Every operator-facing control the node needs (promotion to live, kill switch, config edits, status) **gets a CLI/API door now** and a screen later" and "the first milestone is the node running paper mode on a demo account for **~2 days**". R1 deletes the CLI half; R4's dump reverses the no-UI framing ("consider it in almost everything"); R2 makes the milestone a week. The spine's effects are right; the changelog should state plainly that these are the operator overriding his own opening instructions, so a later reader does not treat the kickoff text as live.

**U9 — Naming remark (vocabulary).** The operator's own word for the node's place in the UI is "a plug-in to the UI" — a banned word in this corpus. The memlog reproduces it verbatim; the spine paraphrases it as "one surface inside that UI". Absorbing docs must keep the paraphrase. (`extractions-T.yaml` contains the word three times, inside the quoted operator text and in the instruction not to reuse it; it must not be copied into `docs/` prose.)

**U10 — Epics-stage constraints stated by the operator, owned by prompt 14, not by this increment.** "a SMALL epic set (aim 5–8 epics), wave plan, paper-milestone epics first, routed for the Grok epic-factory lane (fast workhorse)… Sequence the live-connection story so it is the first thing unblocked by the tokens." Carry forward, do not re-decide.

**U11 — Process nudge (no doc bearing).** Mid-sitting: "I would prefer if you use dynamic workflows as well as sub-agents… Use them and use Opus 5, as I said earlier, as well as Bulk Workers or even Sonnet 5. Thank you. But you don't need to respond to this, it's a simple nudge." This relaxes the kickoff's own "avoid Sonnet" line. Session-mechanics only; no absorption.

**Checked and NOT uncarried** (verified present, so no gap should be minted): the "~40 bots at the 95th-percentile design load" footprint — the spine carries it as "the roughly 40-seat design reference (`variables.yaml:145`)" measured by the TN-23 bench harness at 10/40/100/200 seats; the ticket 006 trendbar-basis question; the three-session timeliness rationale behind R4; the cron/agent JSON scraping idea as R4's later fallback; the Kronos-on-GitHub candidate; the ~60% parts belief (answered by the inventory as 45–60% effort-weighted).

## 4. Framing, delegation and autonomy

**The sitting framing is operator-authored.** The kickoff turn is the operator's own long typed prompt and it fixes the scope, the non-negotiables, the five ordered deliverables, the reviewer-gate requirement, the memlog-for-compaction rule, and a "things to check that I may not have thought about" list. The agent authored no framing document that the operator then ratified.

**The four rulings are agent-questioned and operator-dictated**; the R1–R4 *texts* in the spine and the memlog are agent-authored distillations of those dictated answers. The operator ratified them only by delegation — there is no turn in which he read back or approved the spine text. The last operator turn ("run the validation… so there is no ambiguity, no assumption, and no contradiction") is the closest thing to a sign-off and is procedural, not textual.

**Autonomy was explicitly authorised, in the operator's words:**

> "Treat this as a one-shot: run the whole sitting autonomously, batch every genuinely open decision into at most two AskUserQuestion rounds, and otherwise do not wait on me. I am non-technical; the corpus is my memory."

and, closing the same turn: "Work autonomously. Batch questions. Everything ratified or assumed goes into the memlog." The answer style is fixed too: "Only what none of it decides comes to me, dumbed down (plain words, a concrete example, ≤3 sentences, a recommended option first)." One round of four questions was used, inside the authorised two. This grant is the authority behind `authority: rider` on every non-directly-ruled entry in this increment.

## 5. The next-steps statement

Kickoff turn, steps 3–5, in the operator's words: step 3 is "`/documentation-factory` change-mode absorption of the node spine into `docs/`: mint the DECs, the node component(s), ADRs, the overall C4 architecture and deployment diagrams, the ops/observability lens pages, glossary terms; keep `lint_docs --strict` clean." Step 4 is "`bmad-create-epics-and-stories` for the node — a SMALL epic set (aim 5–8 epics), wave plan, paper-milestone epics first, routed for the Grok epic-factory lane (fast workhorse)… Sequence the live-connection story so it is the first thing unblocked by the tokens." Step 5 is the plain-words hand-off, ending "the exact command to start the Grok factory on the node epics. Then stop. You do not launch coding."

Final turn, which is why SRC-12 exists at all:

> "You append a prompt for me for the documentation factory and also run the validation or some sort of regression… So you run everything architecture or the plan or everything you've produced is solid. Then I'm going to export this session as is so that the documentation factory is going to be using it. So you do that. Actually, it's next session prompt, it's actually existing. You do that, so there is no ambiguity, no assumption, and no contradiction. Do that for me, and I believe we call it a day."

So: this increment (documentation-factory change mode) is step 3; the node epics are step 4 and inherit the 5–8 / paper-milestone-first / live-connection-first constraints; the factory lane runs only after that, and the operator's standing instruction is that the session stops before any coding is launched. The acceptance bar he set for this absorption is his own phrase — no ambiguity, no assumption, and no contradiction.
