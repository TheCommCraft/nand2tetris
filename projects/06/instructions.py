from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

class Instruction(ABC):
    @abstractmethod
    def to_bytes(self) -> bytes:
        pass

    def to_raw(self):
        return RawInstruction(self.to_bytes())

@dataclass
class RawInstruction(Instruction):
    bytes_representation: bytes
    def to_bytes(self):
        return self.bytes_representation

@dataclass
class CInstruction(Instruction):
    dest: str
    comp: tuple[str, Optional[tuple[str, str]]]
    jump: str
    _dest_map = {
        "": 0,
        "M": 1,
        "D": 2,
        "DM": 3,
        "A": 4,
        "AM": 5,
        "AD": 6,
        "ADM": 7
    }
    _jmp_map = {
        '': 0,
        'JGT': 1,
        'JEQ': 2,
        'JGE': 3,
        'JLT': 4,
        'JNE': 5,
        'JLE': 6,
        'JMP': 7
    }
    
    def to_bytes(self) -> bytes:
        a = self.comp[0] == "M" or (self.comp[1] or (None, None))[1] == "M"
        c = 0
        if (self.comp[1] or (None, None))[1] == "":
            match self.comp[0], (self.comp[1] or (None, None))[0]:
                case ("1", "-"):
                    c = 0b111010
                case ("D", "!"):
                    c = 0b001101
                case ("A", "!"):
                    c = 0b110001
                case ("M", "!"):
                    c = 0b110001
                case ("D", "-"):
                    c = 0b001111
                case ("A", "-"):
                    c = 0b110011
                case ("M", "-"):
                    c = 0b110011
                case _:
                    raise SyntaxError("Unknown comp symbol or operator.")
        if not self.comp[1]:
            match self.comp[0]:
                case "0":
                    c = 0b101010
                case "1":
                    c = 0b111111
                case "D":
                    c = 0b001100
                case "A":
                    c = 0b110000
                case "M":
                    c = 0b110000
                case _:
                    raise SyntaxError("Unknown comp symbol or operator.")
        if (self.comp[1] or (None, None))[1]:
            match self.comp[0], self.comp[1]:
                case ("D", ("+", "1")):
                    c = 0b011111
                case ("A", ("+", "1")):
                    c = 0b110111
                case ("M", ("+", "1")):
                    c = 0b110111

                case ("D", ("-", "1")):
                    c = 0b001110
                case ("A", ("-", "1")):
                    c = 0b110010
                case ("M", ("-", "1")):
                    c = 0b110010

                case ("D", ("+", "A")):
                    c = 0b000010
                case ("D", ("+", "M")):
                    c = 0b000010
                case ("D", ("-", "A")):
                    c = 0b010011
                case ("D", ("-", "M")):
                    c = 0b010011

                case ("A", ("-", "D")):
                    c = 0b000111
                case ("M", ("-", "D")):
                    c = 0b000111

                case ("D", ("&", "A")):
                    c = 0b000000
                case ("D", ("&", "M")):
                    c = 0b000000

                case ("D", ("|", "A")):
                    c = 0b010101
                case ("D", ("|", "M")):
                    c = 0b010101
                case _:
                    raise SyntaxError("Unknown comp symbol or operator.")
        try:
            d = self._dest_map[self.dest]
        except KeyError as exp:
            raise SyntaxError("Unknown dest.") from exp
        try:
            j = self._jmp_map[self.jump]
        except KeyError as exp:
            raise SyntaxError("Unknown jump.") from exp
        num = 0b1110_0000_0000_0000 | (a << 12) | (c << 6) | (d << 3) | j
        return num.to_bytes(2)

@dataclass
class AInstruction(Instruction):
    dest: int
    
    def to_bytes(self) -> bytes:
        if self.dest > 32767:
            raise SyntaxError("A Instruction destination too big.")
        if self.dest < 0:
            raise SyntaxError("A Instruction destination too small.")
        return self.dest.to_bytes(2)
