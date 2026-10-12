from __future__ import annotations

import json

from app.ai.document_terms import DocumentTerm
from app.services.documents.pdf_extract import PdfWord

AnnotationDict = dict[str, str | int | float]


def words_on_same_line(previous: PdfWord, current: PdfWord) -> bool:
    # Wrapped phrase: next word starts clearly to the left of the previous word.
    if current.x + 2.0 < previous.x:
        return False

    previous_center = previous.y + (previous.height / 2.0)
    current_center = current.y + (current.height / 2.0)
    delta_y = previous_center - current_center
    if delta_y < 0:
        delta_y = -delta_y

    average_height = (previous.height + current.height) / 2.0
    if average_height <= 0:
        return True

    # Same line only when vertical centers are close.
    if delta_y <= average_height * 0.35:
        return True
    return False


def group_words_by_line(matched_words: list[PdfWord]) -> list[list[PdfWord]]:
    groups: list[list[PdfWord]] = []
    if len(matched_words) == 0:
        return groups

    current_group: list[PdfWord] = []
    current_group.append(matched_words[0])
    groups.append(current_group)

    word_index = 1
    while word_index < len(matched_words):
        word = matched_words[word_index]
        previous_word = current_group[len(current_group) - 1]
        if words_on_same_line(previous_word, word):
            current_group.append(word)
        else:
            current_group = []
            current_group.append(word)
            groups.append(current_group)
        word_index = word_index + 1

    return groups


def merge_word_boxes(matched_words: list[PdfWord], display_text: str) -> PdfWord:
    first = matched_words[0]
    left = first.x
    top = first.y
    right = first.x + first.width
    bottom = first.y + first.height

    word_index = 1
    while word_index < len(matched_words):
        word = matched_words[word_index]
        if word.x < left:
            left = word.x
        if word.y < top:
            top = word.y
        word_right = word.x + word.width
        word_bottom = word.y + word.height
        if word_right > right:
            right = word_right
        if word_bottom > bottom:
            bottom = word_bottom
        word_index = word_index + 1

    width = right - left
    height = bottom - top
    merged = PdfWord(
        page=first.page,
        text=display_text,
        x=left,
        y=top,
        width=width,
        height=height,
    )
    return merged


def find_term_boxes(term: str, words: list[PdfWord]) -> list[PdfWord]:
    term_lower = term.lower()
    term_parts = term_lower.split()
    if len(term_parts) == 0:
        return []

    word_index = 0
    while word_index < len(words):
        first_word = words[word_index]
        first_lower = first_word.text.lower()
        if not first_lower.startswith(term_parts[0]):
            word_index = word_index + 1
            continue

        matched_words: list[PdfWord] = []
        matched_words.append(first_word)

        matched = True
        part_index = 1
        while part_index < len(term_parts):
            next_index = word_index + part_index
            if next_index >= len(words):
                matched = False
                break
            next_word = words[next_index]
            if next_word.page != first_word.page:
                matched = False
                break
            next_lower = next_word.text.lower()
            if not next_lower.startswith(term_parts[part_index]):
                matched = False
                break
            matched_words.append(next_word)
            part_index = part_index + 1

        if matched:
            line_groups = group_words_by_line(matched_words)
            boxes: list[PdfWord] = []
            group_index = 0
            while group_index < len(line_groups):
                group = line_groups[group_index]
                display_text = group[0].text
                merged = merge_word_boxes(group, display_text)
                boxes.append(merged)
                group_index = group_index + 1
            return boxes

        word_index = word_index + 1

    return []


def build_annotations(terms: list[DocumentTerm], words: list[PdfWord]) -> list[AnnotationDict]:
    annotations: list[AnnotationDict] = []
    seen: set[str] = set()

    for item in terms:
        cleaned_term = item.term.strip()
        if len(cleaned_term) < 2:
            continue
        key = cleaned_term.lower()
        if key in seen:
            continue
        seen.add(key)

        boxes = find_term_boxes(cleaned_term, words)
        if len(boxes) == 0:
            continue

        definition = item.definition.strip()
        box_index = 0
        while box_index < len(boxes):
            box = boxes[box_index]
            annotation: AnnotationDict = {}
            annotation['term'] = cleaned_term
            annotation['definition'] = definition
            annotation['page'] = box.page
            annotation['x'] = box.x
            annotation['y'] = box.y
            annotation['width'] = box.width
            annotation['height'] = box.height
            annotations.append(annotation)
            box_index = box_index + 1

    return annotations


def annotations_to_json(annotations: list[AnnotationDict]) -> str:
    encoded = json.dumps(annotations)
    return encoded


def annotations_from_json(raw_json: str) -> list[AnnotationDict]:
    parsed = json.loads(raw_json)
    annotations: list[AnnotationDict] = []
    for item in parsed:
        annotation: AnnotationDict = {}
        annotation['term'] = str(item['term'])
        annotation['definition'] = str(item['definition'])
        annotation['page'] = int(item['page'])
        annotation['x'] = float(item['x'])
        annotation['y'] = float(item['y'])
        annotation['width'] = float(item['width'])
        annotation['height'] = float(item['height'])
        annotations.append(annotation)
    return annotations
