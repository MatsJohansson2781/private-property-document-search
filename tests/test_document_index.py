from datetime import date

from property_search.document_index import (
    DocumentKind,
    PropertyDocument,
    PropertyDocumentIndex,
    SearchRequest,
)


VECTORS = {
    "Leaking kitchen tap\nWater is pooling below the sink.": [1.0, 0.0],
    "Annual smoke alarm inspection\nCheck every alarm in unit 4B.": [0.0, 1.0],
    "water below sink": [1.0, 0.0],
}


def test_search_is_property_scoped_and_marks_due_inspections() -> None:
    index = PropertyDocumentIndex(VECTORS.__getitem__, today=lambda: date(2026, 8, 14))
    index.add(
        PropertyDocument(
            document_id="maint-17",
            property_id="cedar-court",
            kind=DocumentKind.MAINTENANCE_REQUEST,
            title="Leaking kitchen tap",
            content="Water is pooling below the sink.",
        )
    )
    inspection = index.add(
        PropertyDocument(
            document_id="inspect-4b",
            property_id="cedar-court",
            kind=DocumentKind.INSPECTION_REMINDER,
            title="Annual smoke alarm inspection",
            content="Check every alarm in unit 4B.",
            due_date=date(2026, 8, 10),
        )
    )

    hits = index.search(
        SearchRequest(property_id="cedar-court", query="water below sink", limit=1)
    )

    assert inspection.needs_follow_up is True
    assert [hit.document_id for hit in hits] == ["maint-17"]
    assert hits[0].score == 1.0

