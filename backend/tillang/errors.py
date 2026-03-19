class TILCompileError(Exception):
    def __init__(self, message: str, line: int | None = None, column: int | None = None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self.__str__())

    def __str__(self) -> str:
        loc = ""
        if self.line is not None:
            loc = f" (строка {self.line}"
            if self.column is not None:
                loc += f", колонка {self.column}"
            loc += ")"
        return f"{self.message}{loc}"


class TILRuntimeError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

