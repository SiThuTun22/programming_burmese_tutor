#!/usr/bin/env python3
"""Build docs/NLP_Final_Report.docx in NLP Project Report layout."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "docs" / "NLP_Final_Report.docx"
LOGO_PATH = ROOT / "static" / "miit-logo.png"
FIGURE_ASK = ROOT / "docs" / "figures" / "figure_4_1_ask.png"
FIGURE_INDEX = ROOT / "docs" / "figures" / "figure_4_2_index.png"
FIGURE_ADMISSION = ROOT / "docs" / "figures" / "figure_2_8_admission.jpg"
FIGURE_FACULTY = ROOT / "docs" / "figures" / "figure_2_9_faculty.jpg"
EVAL_REPORT = ROOT / "results" / "eval_report.json"

SEMESTER = "I Semester 2026-2027"
COURSE_LINE = "Natural Language Processing Project Report"
TITLE = "Context-Aware Myanmar Language Tutor for Computer Engineering"
MEMBERS = (
    ("2021-MIIT-CSE-064", "Si Thu Tun", "System Developing, Dataset Preparation, Evaluation, Report Writing"),
    ("2021-MIIT-CSE-085", "Wai Yan Win Kyaw", "Dataset Preparation"),
)
TOC_ENTRIES: tuple[tuple[str, int, str], ...] = (
    ("Chapter 1: Introduction", 0, "Chapter 1"),
    ("1.1 What is the Computer Engineering Tutor?", 1, "1.1 What is the Computer Engineering Tutor?"),
    ("1.2 The Importance of a Burmese Computer Engineering Tutor", 1, "1.2 The Importance of a Burmese Computer Engineering Tutor"),
    ("1.3 Project Overview", 1, "1.3 Project Overview"),
    ("Chapter 2: Methodology", 0, "Chapter 2"),
    ("2.1 Knowledge Notes", 1, "2.1 Knowledge Notes"),
    ("2.2 Technologies Used", 1, "2.2 Technologies Used"),
    ("2.3 Routing", 1, "2.3 Routing"),
    ("2.4 Retrieval", 1, "2.4 Retrieval"),
    ("2.5 Generation", 1, "2.5 Generation"),
    ("2.6 System Process Flow", 1, "2.6 System Process Flow"),
    ("2.7 Deployment", 1, "2.7 Deployment"),
    ("Chapter 3: Evaluation", 0, "Chapter 3"),
    ("3.1 Evaluation Metrics", 1, "3.1 Evaluation Metrics"),
    ("3.2 Results", 1, "3.2 Results"),
    ("3.3 Comparison with Gemini Chat", 1, "3.3 Comparison with Gemini Chat"),
    ("Chapter 4: Conclusion", 0, "Chapter 4"),
    ("4.1 Result", 1, "4.1 Result"),
    ("4.2 Future Work", 1, "4.2 Future Work"),
    ("4.3 Conclusion", 1, "4.3 Conclusion"),
    ("References", 0, "References"),
)


def set_run_font(run, *, size: int = 12, bold: bool = False, italic: bool = False) -> None:
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = "Times New Roman"
    run.font.color.rgb = RGBColor(0, 0, 0)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = run._element.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), "Times New Roman")
    rfonts.set(qn("w:hAnsi"), "Times New Roman")
    rfonts.set(qn("w:eastAsia"), "Myanmar Text")


def add_centered(
    doc: Document,
    text: str,
    *,
    size: int = 12,
    bold: bool = False,
    italic: bool = False,
    space_after: int = 6,
    space_before: int = 0,
    style: str | None = None,
) -> None:
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic)


def add_body(doc: Document, text: str, *, first_line: bool = True) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.5
    if first_line:
        p.paragraph_format.first_line_indent = Cm(1.25)
    run = p.add_run(text)
    set_run_font(run, size=12)


def add_section(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="Heading 2")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True
    if p.runs:
        p.runs[0].text = text
        set_run_font(p.runs[0], size=12, bold=True)
    else:
        run = p.add_run(text)
        set_run_font(run, size=12, bold=True)


def add_chapter_title(doc: Document, number: int, title: str) -> None:
    doc.add_page_break()
    add_centered(
        doc,
        f"Chapter {number}",
        size=16,
        bold=True,
        space_after=6,
        style="Heading 1",
    )
    add_centered(doc, title, size=16, bold=True, space_after=18)


def add_figure(
    doc: Document,
    path: Path,
    caption: str,
    *,
    width_in: float,
    max_height_in: float,
) -> None:
    if not path.is_file():
        add_body(doc, f"({caption}: {path.name} was not found at build time.)", first_line=False)
        return
    from PIL import Image

    with Image.open(path) as im:
        aspect = im.height / max(im.width, 1)
    width = width_in
    height = width * aspect
    if height > max_height_in:
        height = max_height_in
        width = height / aspect
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width), height=Inches(height))
    add_caption(doc, caption)


def add_caption(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    set_run_font(run, size=11)


def add_bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    if p.runs:
        p.runs[0].text = text
        set_run_font(p.runs[0], size=12)
    else:
        run = p.add_run(text)
        set_run_font(run, size=12)


def _shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _set_cell_text(cell, text: str, *, bold: bool = False, align=None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    run = p.add_run(text)
    set_run_font(run, size=11, bold=bold)


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.autofit = True
    for i, head in enumerate(headers):
        cell = table.rows[0].cells[i]
        _set_cell_text(cell, head, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        _shade_cell(cell, "D9D9D9")
    for r_i, row in enumerate(rows, start=1):
        for c_i, value in enumerate(row):
            _set_cell_text(table.rows[r_i].cells[c_i], value)


def toc_line(doc: Document, title: str, page: str, *, indent: int = 0) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Cm(0.75 * indent)
    p.paragraph_format.tab_stops.add_tab_stop(
        Cm(15.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
    )
    run = p.add_run(f"{title}\t{page}")
    set_run_font(run, size=12)


def page_setup(doc: Document) -> None:
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.54)
        section.right_margin = Cm(2.54)
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        set_run_font(run, size=10)
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = " PAGE "
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.append(begin)
        run._r.append(instr)
        run._r.append(end)


def cover(doc: Document) -> None:
    add_centered(
        doc,
        "Myanmar Institute of Information Technology",
        size=16,
        bold=True,
        space_after=12,
        space_before=24,
    )
    if LOGO_PATH.is_file():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(12)
        run = p.add_run()
        run.add_picture(str(LOGO_PATH), width=Inches(2.0))
    add_centered(doc, SEMESTER, size=14, bold=True, space_after=6)
    add_centered(doc, COURSE_LINE, size=16, bold=True, space_after=18)
    _cover_field(doc, "Project Title", TITLE)
    _cover_field(doc, "Project Members", "")
    add_table(
        doc,
        ["Roll Number", "Name", "Role"],
        [[roll, name, role] for roll, name, role in MEMBERS],
    )
    doc.add_page_break()


def _cover_field(doc: Document, label: str, value: str) -> None:
    table = doc.add_table(rows=1, cols=3)
    table.autofit = False
    table.columns[0].width = Cm(4.0)
    table.columns[1].width = Cm(0.8)
    table.columns[2].width = Cm(11.0)
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        el.set(qn("w:sz"), "0")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "auto")
        borders.append(el)
    tbl_pr.append(borders)
    cells = table.rows[0].cells
    for cell, text, bold in (
        (cells[0], label, True),
        (cells[1], ":", False),
        (cells[2], value, False),
    ):
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.5
        run = p.add_run(text)
        set_run_font(run, size=12, bold=bold)


def contents(doc: Document, pages: dict[str, str]) -> None:
    add_centered(doc, "Table of Contents", size=16, bold=True, space_after=16, space_before=12)
    for title, indent, _needle in TOC_ENTRIES:
        toc_line(doc, title, pages.get(title, "00"), indent=indent)


def chapter_1(doc: Document) -> None:
    add_chapter_title(doc, 1, "Introduction")
    add_section(doc, "1.1 What is the Computer Engineering Tutor?")
    add_body(
        doc,
        "This project is a Burmese-language assistant for CSE and ECE students "
        "at Myanmar Institute of Information Technology. Gemini (gemini-3.1-flash-lite) "
        "tutors computer-engineering subjects: programming (algorithms, Python, web, "
        "pasted code) and CSE/ECE lecture content (for example Ohm’s law, circuits, "
        "digital electronics, OS, networks). Those turns use a spoken-tutor prompt and "
        "no retrieval. Questions about the CSE or ECE B.E. (Hons.) programme, bachelor "
        "admission, faculty, and campus retrieve local JSONL notes with "
        "gemini-embedding-001; the same chat model then answers only from those passages "
        "and lists source URLs. Chit-chat, biology, general physics, and other non-CE, "
        "non-MIIT questions receive a fixed Burmese refusal.",
    )
    add_body(
        doc,
        "The system is not a locally fine-tuned language model. Ask-time routing uses "
        "keyword rules, follow-up inheritance over chat history, and an optional JSON "
        "classifier. The campus demo is Gradio, with Myanmar neural TTS (edge-tts).",
    )
    add_section(doc, "1.2 The Importance of a Burmese Computer Engineering Tutor")
    add_body(
        doc,
        "CSE and ECE students at MIIT often need help in Myanmar while keeping English for "
        "people, brands, course codes, and technical terms. A general chat model can explain "
        "Ohm’s law or Python, but it invents staff biographies and elective codes. "
        "A hybrid tutor closes that gap: Gemini for computer-engineering subjects in "
        "Burmese, retrieval-augmented generation (RAG) for CSE/ECE curriculum and admission "
        "notes plus campus and faculty facts with source URLs, and a refusal for chit-chat "
        "and non-CE topics.",
    )
    add_section(doc, "1.3 Project Overview")
    add_body(
        doc,
        "A classifier labels each turn as programming, MIIT, or out of scope. The "
        "programming label includes coding and CSE/ECE lecture questions; those turns "
        "use a tutor prompt with no retrieval. MIIT turns—CSE/ECE years, electives, "
        "capstone, admission, and faculty—retrieve JSONL passages with embeddings and "
        "constrain generation to those notes. Short follow-ups in Gradio inherit "
        "the prior MIIT or programming thread so a second ask stays on the same "
        "person, programme, or subject.",
    )
    add_body(
        doc,
        "Gradio keeps multi-turn chats, Light/Dark theme, and Listen (edge-tts). An HTTP "
        "API and CLI share the same HybridEngine without conversation memory. After "
        "make miit-index, the demo runs with make app.",
    )


def chapter_2(doc: Document) -> None:
    add_chapter_title(doc, 2, "Methodology")
    add_section(doc, "2.1 Knowledge Notes")
    add_body(
        doc,
        "Campus facts live in JSONL records {id, text, sources[]} under data/miit/. All "
        "*.jsonl files are loaded. Embeddings are stored in data/miit/index.json (rebuilt "
        "with make miit-index). There is no relational database.",
    )
    add_table(
        doc,
        ["File", "Content"],
        [
            ["institute.jsonl", "Campus, governance, programmes"],
            ["bachelor_admission.jsonl", "B.E. (Hons) CSE/ECE admission"],
            ["cse_be_hons.jsonl", "CSE years, electives, capstone"],
            ["ece_be_hons.jsonl", "ECE years, electives, capstone"],
            ["Faculty JSONL files", "Role, research, papers, work email"],
        ],
    )
    add_caption(doc, "Table 2.1: Knowledge files under data/miit/")

    add_section(doc, "2.2 Technologies Used")
    add_bullet(doc, "Python 3.12, uv, pytest")
    add_bullet(doc, "google-genai SDK: gemini-3.1-flash-lite (chat) and gemini-embedding-001")
    add_bullet(doc, "NumPy cosine similarity over the embedding index")
    add_bullet(doc, "Gradio 6 Blocks UI; Litestar POST /v1/chat")
    add_bullet(doc, "edge-tts: my-MM-NilarNeural and my-MM-ThihaNeural")

    add_section(doc, "2.3 Routing")
    add_body(
        doc,
        "classify_route labels each question. Rule hints fire first (MIIT names and campus "
        "terms, or programming terms and pasted code). If the ask is a short follow-up, "
        "inherit_thread_route keeps the last MIIT or programming topic. An optional Gemini "
        "JSON classifier with disk cache runs when rules miss. Out-of-scope questions that "
        "still sit on a prior thread are remapped. other with no thread returns a constant "
        "Burmese sentence and never calls generation.",
    )

    add_section(doc, "2.4 Retrieval")
    add_body(
        doc,
        "MIIT turns call retrieve_miit. The query concatenates the last two history "
        "questions with the new question, embeds with gemini-embedding-001, and ranks "
        "index chunks by cosine similarity. Default top-k is 3 (higher for curriculum and "
        "paper questions). A token-overlap fallback runs if the index is missing or embed "
        "quota fails. Programming turns do not retrieve.",
    )

    add_section(doc, "2.5 Generation")
    add_body(
        doc,
        "Gemini receives a flattened prompt. Programming sampling uses temperature 0.85; "
        "MIIT uses 0.7. Max tokens follow TUTOR_CLOUD_MAX_TOKENS (3072). The client retries "
        "network errors, 5xx, and 429. A primary 429 can switch GEMINI_API_KEY_FALLBACK "
        "for chat only. Prompts keep English for people and technical terms, and they "
        "forbid inventing electives or biographies.",
    )

    add_section(doc, "2.6 System Process Flow")
    add_body(
        doc,
        "Figure 2.6 is the ISO 5807 flowchart of one Ask: capsule Start and End, "
        "parallelograms for input and output, rectangles for processes, diamonds with "
        "Yes or No on the arrows. Listen (edge-tts) is a later UI action and is not on "
        "this chart. Figure 2.7 is the offline index build.",
        first_line=False,
    )
    add_figure(doc, FIGURE_ASK, "Figure 2.6: One Ask turn", width_in=5.6, max_height_in=6.4)
    add_figure(doc, FIGURE_INDEX, "Figure 2.7: Offline knowledge index", width_in=5.4, max_height_in=3.2)

    add_section(doc, "2.7 Deployment")
    add_body(
        doc,
        "The examiner runs make preflight, make api, make web, and opens http://localhost:5173. "
        "The page title is Computer Engineering Tutor. Students type in the composer, click "
        "Ask, optionally Listen, switch Light/Dark, or start a New chat. "
        "Chats persist in results/chats.json (local, gitignored). POST /v1/chat and the "
        "CLI call the same engine without history. Network is required for Gemini, "
        "embeddings, and edge-tts. No GPU is required. Figures 2.8 and 2.9 show the "
        "campus demo answering an admission question and a faculty follow-up from notes.",
    )
    add_figure(
        doc,
        FIGURE_ADMISSION,
        "Figure 2.8: Gradio Ask for bachelor admission (notes and source URL)",
        width_in=5.8,
        max_height_in=3.6,
    )
    add_figure(
        doc,
        FIGURE_FACULTY,
        "Figure 2.9: Gradio faculty thread with a research follow-up",
        width_in=5.8,
        max_height_in=3.6,
    )


def chapter_3(doc: Document) -> None:
    add_chapter_title(doc, 3, "Evaluation")
    add_section(doc, "3.1 Evaluation Metrics")
    add_body(
        doc,
        "Official scores use a labelled file eval/items.jsonl and make eval. Gradio "
        "Myanmar-script ratio is a language-style log, not accuracy. "
        "Liu et al. (2016) show that surface overlap correlates poorly with dialogue quality "
        "(https://aclanthology.org/D16-1230/).",
        first_line=False,
    )
    add_body(
        doc,
        "Routing is a three-way label (miit, programming, other). We report Accuracy and "
        "Macro-F1 as in Sokolova and Lapalme (2009), https://doi.org/10.1016/j.ipm.2009.03.002. "
        "Retrieval of MIIT notes is scored with Recall@3 and MRR as in Karpukhin et al. "
        "(2020) Dense Passage Retrieval, https://aclanthology.org/2020.emnlp-main.550/, with "
        "IR definitions from Manning, Raghavan and Schütze (2008), "
        "https://nlp.stanford.edu/IR-book/. Closed campus facts use Exact Match on gold "
        "spans, the protocol Lewis et al. (2020) used for RAG QA, "
        "https://arxiv.org/abs/2005.11401.",
    )
    add_section(doc, "3.2 Results")
    report = _load_eval_report()
    if report:
        route = report["route"]
        retr = report["retrieval"]
        gen = report["generation"]
        add_table(
            doc,
            ["Metric", "n", "Score"],
            [
                ["Accuracy", str(route["n"]), f"{route['accuracy']:.3f}"],
                ["Macro-F1", str(route["n"]), f"{route['macro_f1']:.3f}"],
            ],
        )
        add_caption(doc, "Table 3.1: Route classification (Sokolova & Lapalme, 2009)")
        add_table(
            doc,
            ["Metric", "n", "Score"],
            [
                ["Recall@3", str(retr["n"]), f"{retr['recall_at_3']:.3f}"],
                ["MRR", str(retr["n"]), f"{retr['mrr']:.3f}"],
            ],
        )
        add_caption(doc, "Table 3.2: Dense retrieval (Karpukhin et al., 2020)")
        if gen.get("n"):
            add_table(
                doc,
                ["Metric", "n", "Score"],
                [
                    ["Exact Match", str(gen["n"]), f"{float(gen['exact_match']):.3f}"],
                    ["Token F1", str(gen["n"]), f"{float(gen['token_f1']):.3f}"],
                ],
            )
            add_caption(doc, "Table 3.3: Closed-fact generation (Lewis et al., 2020)")
    if report:
        acc = f"{route['accuracy']:.3f}"
        f1 = f"{route['macro_f1']:.3f}"
        n_route = route["n"]
        rec = f"{retr['recall_at_3']:.3f}"
        mrr_s = f"{retr['mrr']:.3f}"
        em = f"{float(gen['exact_match']):.3f}" if gen.get("exact_match") is not None else "—"
        add_body(
            doc,
            f"On the labelled set (eval/items.jsonl, {n_route} items covering MIIT notes, "
            "computer-engineering subjects, out-of-scope, and follow-ups) the router reached "
            f"Accuracy {acc} and Macro-F1 {f1} (Sokolova and Lapalme, 2009). Dense retrieval "
            f"of the correct note reached Recall@3 {rec} and MRR {mrr_s} (Karpukhin et al., "
            "2020; Manning et al., 2008). "
            f"Closed campus facts reached Exact Match {em} (Lewis et al., 2020): gold names "
            "and numbers appear in the Burmese answers. These are the same metric families "
            "used in published intent classification, passage retrieval, and RAG QA.",
        )
    else:
        add_body(
            doc,
            "Run make eval to write results/eval_report.json before rebuilding this chapter.",
        )
    add_body(
        doc,
        "Exact Match is the primary generation number: each gold span (for example Win Aye) "
        "must appear in the Burmese answer. Token F1 is lower because the tutor writes a "
        "full paragraph while the gold is a short fact string.",
    )
    add_section(doc, "3.3 Comparison with Gemini Chat")
    add_body(
        doc,
        "Programming answers use the same Gemini chat model as a public Gemini session. "
        "The project is stronger on grounded campus QA: local notes, source URLs, and "
        "routing. Table 3.4 records those system behaviours; it does not quote a live "
        "Gemini transcript.",
        first_line=False,
    )
    add_table(
        doc,
        ["Aspect", "This project", "Gemini online chat"],
        [
            [
                "MIIT facts",
                "Answers only from retrieved JSONL notes and lists source URLs",
                "No local note constraint; may mix or invent campus facts",
            ],
            [
                "Curriculum / electives",
                "Must not invent course codes that are absent from the notes",
                "Can invent elective names and codes",
            ],
            [
                "Faculty",
                "Role, papers, and email only from faculty JSONL",
                "Can invent titles and publications",
            ],
            [
                "Out of scope",
                "Fixed Burmese refusal; generation is not called",
                "Will answer weather, news, and chit-chat",
            ],
            [
                "Follow-up",
                "Inherits the last MIIT or programming thread",
                "A short follow-up may start a new topic",
            ],
            [
                "CE subjects / coding",
                "Same Gemini model; gain is routing plus campus RAG",
                "Same class of chat model without MIIT retrieval",
            ],
        ],
    )
    add_caption(doc, "Table 3.4: This project versus Gemini online chat")


def chapter_4(doc: Document) -> None:
    add_chapter_title(doc, 4, "Conclusion")
    add_section(doc, "4.1 Result")
    report = _load_eval_report()
    scores = ""
    if report:
        acc = f"{report['route']['accuracy']:.3f}"
        rec = f"{report['retrieval']['recall_at_3']:.3f}"
        em = report["generation"].get("exact_match")
        em_s = f"{float(em):.3f}" if em is not None else "—"
        scores = (
            f"On the labelled set the router Accuracy is {acc}, "
            f"retrieval Recall@3 is {rec}, and closed-fact Exact Match is {em_s}. "
        )
    add_body(
        doc,
        "The tutor uses Gemini for computer-engineering subject tutoring "
        "in Burmese, and embedding RAG over public notes for programme, admission, "
        "faculty, and campus facts. "
        + scores
        + "The Gradio campus demo supports follow-up threads, Myanmar TTS, and the "
        "same HybridEngine as the API and CLI.",
    )
    add_section(doc, "4.2 Future Work")
    add_bullet(doc, "Persist API and CLI history so follow-up inherit works outside Gradio.")
    add_bullet(doc, "Host a public demo on a free Spaces tier.")
    add_bullet(doc, "Enlarge the public note set while keeping source URLs.")
    add_bullet(doc, "Optional AIS-style attribution scoring of MIIT answers (Rashkin et al., 2021).")
    add_section(doc, "4.3 Conclusion")
    add_body(
        doc,
        "The project shows applied NLP on a real student task: intent routing, dense "
        "retrieval, constrained generation, and Myanmar speech, without claiming a new "
        "foundation model. Gemini answers coding and CSE/ECE lecture questions; local "
        "CSE and ECE notes ground programme and campus facts.",
    )


def references(doc: Document) -> None:
    doc.add_page_break()
    add_centered(
        doc,
        "References",
        size=16,
        bold=True,
        space_after=16,
        space_before=12,
        style="Heading 1",
    )
    refs = [
        "Jurafsky, D. & Martin, J. H. Speech and Language Processing. https://web.stanford.edu/~jurafsky/slp3/",
        "Karpukhin, V. et al. (2020). Dense Passage Retrieval for Open-Domain Question Answering. EMNLP. https://aclanthology.org/2020.emnlp-main.550/",
        "Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS. https://arxiv.org/abs/2005.11401",
        "Liu, C.-W. et al. (2016). How NOT to Evaluate Your Dialogue System. EMNLP. https://aclanthology.org/D16-1230/",
        "Manning, C. D., Raghavan, P. & Schütze, H. (2008). Introduction to Information Retrieval. https://nlp.stanford.edu/IR-book/",
        "Myanmar Institute of Information Technology. https://www.miit.edu.mm/",
        "Rashkin, H. et al. (2021). Measuring Attribution in Generated Text. https://arxiv.org/abs/2112.12870",
        "Sokolova, M. & Lapalme, G. (2009). A systematic analysis of performance measures for classification tasks. IP&M. https://doi.org/10.1016/j.ipm.2009.03.002",
        "van der Lee, C. et al. (2019). Best practices for the human evaluation of automatically generated text. INLG. https://aclanthology.org/W19-8643/",
    ]
    for i, ref in enumerate(refs, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(1.25)
        p.paragraph_format.first_line_indent = Cm(-1.25)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.5
        run = p.add_run(f"[{i}]  {ref}")
        set_run_font(run, size=12)


def _load_eval_report() -> dict | None:
    if not EVAL_REPORT.is_file():
        return None
    return json.loads(EVAL_REPORT.read_text(encoding="utf-8"))


def _tune_headings(doc: Document) -> None:
    for name, size in (("Heading 1", 16), ("Heading 2", 12)):
        style = doc.styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.italic = False


def _write_doc(path: Path, pages: dict[str, str]) -> None:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.paragraph_format.line_spacing = 1.5
    _tune_headings(doc)
    page_setup(doc)
    cover(doc)
    contents(doc, pages)
    chapter_1(doc)
    chapter_2(doc)
    chapter_3(doc)
    chapter_4(doc)
    references(doc)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)


def _soffice_bin() -> str | None:
    for candidate in (
        shutil.which("soffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice",
    ):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    return None


def _docx_to_pdf(docx: Path, pdf: Path) -> None:
    soffice = _soffice_bin()
    if soffice:
        profile = pdf.parent / "lo_profile"
        profile.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["HOME"] = str(pdf.parent)
        subprocess.run(
            [
                soffice,
                "--headless",
                "--norestore",
                "--nolockcheck",
                f"-env:UserInstallation=file://{profile}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(pdf.parent),
                str(docx),
            ],
            check=True,
            capture_output=True,
            env=env,
        )
        produced = pdf.parent / f"{docx.stem}.pdf"
        if produced.resolve() != pdf.resolve():
            shutil.move(str(produced), str(pdf))
        return
    word = Path("/Applications/Microsoft Word.app")
    if not word.is_dir():
        raise RuntimeError(
            "Need LibreOffice soffice or Microsoft Word to paginate the TOC."
        )
    in_path = str(docx.resolve())
    out_path = str(pdf.resolve())
    script = f'''
tell application "Microsoft Word"
  open POSIX file "{in_path}"
  delay 1
  set dest to POSIX file "{out_path}"
  save as active document file name (dest as string) file format format PDF
  close active document saving no
end tell
'''
    subprocess.run(["osascript", "-e", script], check=True, capture_output=True)


def _is_toc_page(text: str) -> bool:
    hits = sum(1 for title, _indent, _needle in TOC_ENTRIES if title in text)
    return hits >= 4 or "Table of Contents" in text


def _read_toc_pages(pdf: Path) -> dict[str, str]:
    import pymupdf

    doc = pymupdf.open(pdf)
    try:
        pages: dict[str, str] = {}
        for title, _indent, needle in TOC_ENTRIES:
            found = None
            for i in range(doc.page_count):
                text = doc[i].get_text()
                if _is_toc_page(text):
                    continue
                if needle in text:
                    found = i + 1
                    break
            if found is None:
                raise RuntimeError(f"Heading not found in PDF: {needle}")
            pages[title] = str(found)
        return pages
    finally:
        doc.close()


def main() -> int:
    placeholders = {title: "00" for title, _indent, _needle in TOC_ENTRIES}
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        draft = scratch / "draft.docx"
        pdf = scratch / "draft.pdf"
        _write_doc(draft, placeholders)
        try:
            _docx_to_pdf(draft, pdf)
        except (RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"TOC pagination failed ({exc}). Writing placeholders.", file=sys.stderr)
            _write_doc(OUT_PATH, placeholders)
            print(f"Wrote {OUT_PATH}")
            return 1
        measured = _read_toc_pages(pdf)
    _write_doc(OUT_PATH, measured)
    print(f"Wrote {OUT_PATH}")
    for title, _indent, _needle in TOC_ENTRIES:
        print(f"  TOC {title} ... {measured[title]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
