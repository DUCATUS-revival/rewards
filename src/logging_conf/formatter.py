import logging
from copy import copy
from typing import Optional

import click

TRACE_LOG_LEVEL = 5


class CustomFormatter(logging.Formatter):
    level_name_colors = {
        TRACE_LOG_LEVEL: lambda level_name: click.style(str(level_name), fg="blue"),
        logging.DEBUG: lambda level_name: click.style(str(level_name), fg="cyan"),
        logging.INFO: lambda level_name: click.style(str(level_name), fg="green"),
        logging.WARNING: lambda level_name: click.style(str(level_name), fg="yellow"),
        logging.ERROR: lambda level_name: click.style(str(level_name), fg="red"),
        logging.CRITICAL: lambda level_name: click.style(
            str(level_name), fg="bright_red"
        ),
    }

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = "%",
    ):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def color_level_name(self, level_name: str, level_no: int) -> str:
        def default(level_name: str) -> str:
            return str(level_name)  # pragma: no cover

        func = self.level_name_colors.get(level_no, default)
        return func(level_name)

    def formatMessage(self, record: logging.LogRecord) -> str:
        recordcopy = copy(record)
        levelname = recordcopy.levelname
        recordcopy.__dict__["asctime"] = click.style(
            recordcopy.asctime, fg="bright_magenta"
        )
        recordcopy.__dict__["filename"] = click.style("File ", fg="blue") + click.style(
            "'" + recordcopy.filename + "'", fg="bright_cyan"
        )
        recordcopy.__dict__["funcName"] = click.style(
            recordcopy.funcName, fg="red"
        ) + click.style("():", fg="red")

        recordcopy.__dict__["message"] = click.style(
            recordcopy.message, fg="bright_cyan"
        )
        seperator = " " * (8 - len(recordcopy.levelname))
        levelname = self.color_level_name(levelname, recordcopy.levelno)
        recordcopy.__dict__["levelprefix"] = levelname + ":" + seperator
        recordcopy.__dict__["line"] = (
            click.style("line", fg="green")
            + " "
            + click.style(recordcopy.lineno, "green")
        )
        recordcopy.__dict__["in_func"] = click.style("in func", fg="yellow")
        return super().formatMessage(recordcopy)
