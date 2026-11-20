"""Reads and validates the versioned configuration of the generated documents (ORD-02, REL-01).

`report_templates.json` holds `default` (the id of a template) and `templates`, a map from id to
template: `version`, `entry_style`, `page`, `header_lines`, `title`, `identification`,
`body_heading`, `group_map`, `sections` and the vocabulary of the conference of the wording
(`allowed_terms`, `formal_vocabulary`, `forbidden_words`, `max_new_words`). The `match` of a
section is not written in the file: it is what the `group_map` sends to the section, so the
sections and the map cannot disagree. `dossier_order.json` holds `items`, the documents of the
dossier in delivery order.

A broken file stops the loading with a `ConfigError` that names the file and the field.
"""

import json
import re
from pathlib import Path
from typing import Any

from app.domain.entities.generated import DocumentKind
from app.domain.entities.report import (
    DossierItem,
    EntrySpec,
    GroupBy,
    MatchRule,
    PageSetup,
    ReportLayout,
    ReportTemplate,
    TemplateSection,
)
from app.domain.rules.report_draft import ENTRY_MARKERS, GroupTarget, ReportConfig
from app.domain.rules.report_grounding import WordingVocabulary

CONFIG_DIR = Path(__file__).parent / "config"
REPORT_TEMPLATES = CONFIG_DIR / "report_templates.json"
DOSSIER_ORDER = CONFIG_DIR / "dossier_order.json"

# Markers of the lines of the header and of the identification, written by the document model.
LAYOUT_MARKERS = frozenset(
    {
        "unit_name",
        "professor_name",
        "current_class",
        "current_level",
        "target_class",
        "target_level",
        "interstice",
    }
)
ENTRY_STYLES = frozenset({"campos", "narrativo"})
_MARKER = re.compile(r"\{(\w+)\}")
_OPTIONAL_PART = re.compile(r"\[[^\[\]]*\]")


class ConfigError(Exception):
    """A configuration file that cannot be used; the message names the file and the field."""

    def __init__(self, file: str, field: str, problem: str) -> None:
        super().__init__(f"{file}: {field}: {problem}")
        self.file = file
        self.field = field


class _Reader:
    """Typed access to a parsed file; each failure names the file and the path of the field."""

    def __init__(self, file: str) -> None:
        self.file = file

    def fail(self, field: str, problem: str) -> ConfigError:
        return ConfigError(self.file, field, problem)

    def obj(self, value: Any, field: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise self.fail(field, "deve ser um objeto")
        return value

    def require(self, parent: dict[str, Any], key: str, field: str) -> Any:
        if key not in parent:
            raise self.fail(f"{field}.{key}" if field else key, "ausente")
        return parent[key]

    def text(self, parent: dict[str, Any], key: str, field: str) -> str:
        value = self.require(parent, key, field)
        path = f"{field}.{key}" if field else key
        if not isinstance(value, str) or not value.strip():
            raise self.fail(path, "deve ser um texto não vazio")
        return value

    def integer(self, parent: dict[str, Any], key: str, field: str, minimum: int) -> int:
        value = self.require(parent, key, field)
        path = f"{field}.{key}" if field else key
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise self.fail(path, f"deve ser um número inteiro a partir de {minimum}")
        return value

    def positive_number(self, parent: dict[str, Any], key: str, field: str) -> float:
        value = self.require(parent, key, field)
        path = f"{field}.{key}" if field else key
        if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
            raise self.fail(path, "deve ser um número maior que zero")
        return float(value)

    def items(self, parent: dict[str, Any], key: str, field: str) -> list[Any]:
        value = self.require(parent, key, field)
        path = f"{field}.{key}" if field else key
        if not isinstance(value, list) or not value:
            raise self.fail(path, "deve ser uma lista com ao menos um item")
        return value

    def texts(self, parent: dict[str, Any], key: str, field: str) -> tuple[str, ...]:
        value = self.require(parent, key, field)
        path = f"{field}.{key}" if field else key
        if not isinstance(value, list):
            raise self.fail(path, "deve ser uma lista")
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise self.fail(f"{path}[{index}]", "deve ser um texto não vazio")
        return tuple(value)

    def markers(self, text: str, allowed: frozenset[str], field: str) -> None:
        """Every `{marker}` is one of `allowed` and no brace or bracket is left unpaired."""
        for name in _MARKER.findall(text):
            if name not in allowed:
                raise self.fail(field, f"marcador desconhecido {{{name}}}")
        rest = _OPTIONAL_PART.sub("", _MARKER.sub("", text))
        if any(char in rest for char in "{}[]"):
            raise self.fail(field, "marcador ou parte opcional mal formado")


def _load_json(path: Path) -> tuple[_Reader, Any]:
    reader = _Reader(path.name)
    try:
        return reader, json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise reader.fail("(arquivo)", f"não foi possível ler: {error.strerror}") from None
    except json.JSONDecodeError as error:
        raise reader.fail(
            "(arquivo)", f"JSON inválido ({error.msg}, linha {error.lineno})"
        ) from None


def _page(reader: _Reader, template: dict[str, Any], base: str) -> PageSetup:
    page = reader.obj(reader.require(template, "page", base), f"{base}.page")
    where = f"{base}.page"
    size = reader.text(page, "size", where)
    if size != "A4":
        raise reader.fail(f"{where}.size", "só A4 é aceito")
    margins = reader.obj(reader.require(page, "margins_mm", where), f"{where}.margins_mm")
    sides = {
        side: reader.positive_number(margins, side, f"{where}.margins_mm")
        for side in ("left", "right", "top", "bottom")
    }
    return PageSetup(
        margin_left_mm=sides["left"],
        margin_right_mm=sides["right"],
        margin_top_mm=sides["top"],
        margin_bottom_mm=sides["bottom"],
        font_name=reader.text(page, "font", where),
        font_size_pt=reader.positive_number(page, "font_size", where),
        size=size,
    )


def _marked_lines(
    reader: _Reader, template: dict[str, Any], key: str, base: str
) -> tuple[str, ...]:
    lines = reader.items(template, key, base)
    for index, line in enumerate(lines):
        field = f"{base}.{key}[{index}]"
        if not isinstance(line, str) or not line.strip():
            raise reader.fail(field, "deve ser um texto não vazio")
        reader.markers(line, LAYOUT_MARKERS, field)
    return tuple(lines)


def _entry(reader: _Reader, section: dict[str, Any], field: str) -> EntrySpec:
    where = f"{field}.entry"
    entry = reader.obj(reader.require(section, "entry", field), where)
    if ("line" in entry) == ("fields" in entry):
        raise reader.fail(where, "deve ter `line` ou `fields`, não os dois nem nenhum")
    if "line" in entry:
        line = reader.text(entry, "line", where)
        reader.markers(line, ENTRY_MARKERS, where)
        return EntrySpec(line=line)
    pairs = []
    for index, item in enumerate(reader.items(entry, "fields", where)):
        here = f"{where}.fields[{index}]"
        item = reader.obj(item, here)
        text = reader.text(item, "text", here)
        reader.markers(text, ENTRY_MARKERS, here)
        pairs.append((reader.text(item, "label", here), text))
    return EntrySpec(fields=tuple(pairs))


def _group_by(reader: _Reader, section: dict[str, Any], field: str) -> GroupBy:
    value = section.get("group_by", GroupBy.NONE.value)
    try:
        return GroupBy(value)
    except ValueError:
        allowed = ", ".join(g.value for g in GroupBy)
        raise reader.fail(f"{field}.group_by", f"deve ser um de: {allowed}") from None


def _group_map(
    reader: _Reader, template: dict[str, Any], base: str, keys: set[str]
) -> dict[MatchRule, GroupTarget]:
    rules: dict[MatchRule, GroupTarget] = {}
    for index, raw in enumerate(reader.items(template, "group_map", base)):
        field = f"{base}.group_map[{index}]"
        rule = reader.obj(raw, field)
        match = MatchRule(
            reader.integer(rule, "group", field, 1),
            reader.integer(rule, "item", field, 1) if "item" in rule else None,
        )
        section = reader.text(rule, "section", field)
        if section not in keys:
            raise reader.fail(f"{field}.section", f"a seção {section!r} não existe")
        if match in rules:
            raise reader.fail(field, "regra repetida para o mesmo grupo e item")
        subtitle = reader.text(rule, "subtitle", field) if "subtitle" in rule else None
        rules[match] = GroupTarget(section, subtitle)
    return rules


def _sections(
    reader: _Reader,
    template: dict[str, Any],
    base: str,
    group_map: dict[MatchRule, GroupTarget] | None = None,
) -> list[tuple[dict[str, Any], str]]:
    """The raw sections with their paths, checked for `key` and `title`; keys are unique."""
    found, seen = [], set()
    for index, raw in enumerate(reader.items(template, "sections", base)):
        field = f"{base}.sections[{index}]"
        section = reader.obj(raw, field)
        key = reader.text(section, "key", field)
        if key in seen:
            raise reader.fail(f"{field}.key", f"seção repetida {key!r}")
        seen.add(key)
        reader.text(section, "title", field)
        found.append((section, field))
    return found


def _template(reader: _Reader, template_id: str, raw: Any) -> ReportConfig:
    base = f"templates.{template_id}"
    template = reader.obj(raw, base)
    raw_sections = _sections(reader, template, base)
    group_map = _group_map(reader, template, base, {s["key"] for s, _ in raw_sections})
    sections = tuple(
        TemplateSection(
            key=section["key"],
            title=section["title"],
            match=tuple(
                r for r, target in group_map.items() if target.section_key == section["key"]
            ),
            group_by=_group_by(reader, section, field),
            entry=_entry(reader, section, field),
            order_items=_flag(reader, section, "order_items", field),
        )
        for section, field in raw_sections
    )
    style = reader.text(template, "entry_style", base)
    if style not in ENTRY_STYLES:
        raise reader.fail(
            f"{base}.entry_style", f"deve ser um de: {', '.join(sorted(ENTRY_STYLES))}"
        )
    layout = ReportLayout(
        page=_page(reader, template, base),
        header_lines=_marked_lines(reader, template, "header_lines", base),
        title=reader.text(template, "title", base),
        identification=_marked_lines(reader, template, "identification", base),
        body_heading=reader.text(template, "body_heading", base),
        entry_style=style,
    )
    vocabulary = WordingVocabulary(
        max_new_words=reader.integer(template, "max_new_words", base, 0),
        allowed_terms=reader.texts(template, "allowed_terms", base),
        formal_vocabulary=reader.texts(template, "formal_vocabulary", base),
        forbidden_words=reader.texts(template, "forbidden_words", base),
    )
    return ReportConfig(
        template=ReportTemplate(
            template_id, reader.integer(template, "version", base, 1), sections
        ),
        group_map=group_map,
        vocabulary=vocabulary,
        layout=layout,
    )


def _flag(reader: _Reader, parent: dict[str, Any], key: str, field: str) -> bool:
    value = parent.get(key, False)
    if not isinstance(value, bool):
        raise reader.fail(f"{field}.{key}", "deve ser verdadeiro ou falso")
    return value


def load_report_config(
    path: Path = REPORT_TEMPLATES, template_id: str | None = None
) -> ReportConfig:
    """The template `template_id`, or the one the file marks as `default`."""
    reader, data = _load_json(Path(path))
    root = reader.obj(data, "(arquivo)")
    templates = reader.obj(reader.require(root, "templates", ""), "templates")
    default = reader.text(root, "default", "")
    if default not in templates:
        raise reader.fail("default", f"o modelo {default!r} não está em `templates`")
    chosen = template_id or default
    if chosen not in templates:
        raise reader.fail("templates", f"o modelo {chosen!r} não existe")
    return _template(reader, chosen, templates[chosen])


class ReportConfigLoader:
    """The `ReportConfigProvider` port: the template of the setting `REPORT_TEMPLATE_ID`, or the
    one the file marks as default, read from the versioned file at every call."""

    def __init__(self, template_id: str | None = None, path: Path = REPORT_TEMPLATES) -> None:
        self._template_id = template_id
        self._path = path

    def load(self) -> ReportConfig:
        return load_report_config(self._path, self._template_id)


def load_dossier_order(path: Path = DOSSIER_ORDER) -> tuple[DossierItem, ...]:
    """The documents of the dossier in delivery order; the order values must go up."""
    reader, data = _load_json(Path(path))
    root = reader.obj(data, "(arquivo)")
    items, previous = [], 0
    for index, raw in enumerate(reader.items(root, "items", "")):
        field = f"items[{index}]"
        item = reader.obj(raw, field)
        order = reader.integer(item, "order", field, 1)
        if order <= previous:
            raise reader.fail(f"{field}.order", "a ordem deve crescer ao longo do arquivo")
        previous = order
        items.append(
            DossierItem(
                order, reader.text(item, "title", field), _generated_by(reader, item, field)
            )
        )
    return tuple(items)


def _generated_by(reader: _Reader, item: dict[str, Any], field: str) -> DocumentKind | None:
    value = item.get("generated_by")
    if value is None:
        return None
    try:
        return DocumentKind(value)
    except ValueError:
        allowed = ", ".join(k.value for k in DocumentKind)
        raise reader.fail(f"{field}.generated_by", f"deve ser vazio ou um de: {allowed}") from None
