from dataclasses import dataclass

from internal.colors import Colorize


@dataclass
class FlowConfig:
    colorize: Colorize = Colorize.ALL
