class InsertText:
    def __init__(self, *, index: int, text: str) -> None:
        self.index = index
        self.text = text


class DeleteContent:
    def __init__(self, *, start_index: int, end_index: int) -> None:
        self.start_index = start_index
        self.end_index = end_index


class EditScript:
    def __init__(self, *, edits: list[InsertText | DeleteContent]) -> None:
        self.edits = edits
