from app.invoices.validation import IssueSeverity, ValidationIssue

# Plurobi-internal findings the supplier cannot fix by reissuing the document.
INTERNAL_ISSUE_CODES = frozenset({"duplicate_invoice", "low_extraction_confidence"})


def supplier_fixable_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    """Blocking errors that a corrected supplier document would resolve. Warnings never qualify."""
    return [
        issue
        for issue in issues
        if issue.severity == IssueSeverity.error and issue.code not in INTERNAL_ISSUE_CODES
    ]
