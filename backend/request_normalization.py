def _trim_and_reject_blank(value: str) -> str:
    trimmed = value.strip()
    if trimmed == "":
        raise ValueError("must not be empty or whitespace-only")
    return trimmed


def normalize_request_text(text: str) -> str:
    return _trim_and_reject_blank(text)


def normalize_selected_folder(folder: str) -> str:
    return _trim_and_reject_blank(folder)
