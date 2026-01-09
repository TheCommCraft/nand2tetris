from dataclasses import dataclass, field
from instructions import Instruction, CInstruction, AInstruction
from collections.abc import Iterator
from itertools import batched

_default_names = {
    'R0': 0,
    'R1': 1,
    'R2': 2,
    'R3': 3,
    'R4': 4,
    'R5': 5,
    'R6': 6,
    'R7': 7,
    'R8': 8,
    'R9': 9,
    'R10': 10,
    'R11': 11,
    'R12': 12,
    'R13': 13,
    'R14': 14,
    'R15': 15,
    'SP': 0,
    'LCL': 1,
    'ARG': 2,
    'THIS': 3,
    'THAT': 4,
    'SCREEN': 16384,
    'KBD': 24576
}

@dataclass
class Namespace:
    names: dict[str, int] = field(default_factory=_default_names.copy)
    highest_name: int = 15

    def resolve(self, name: str) -> int:
        if (i := self.names.get(name)):
            return i
        self.highest_name += 1
        self.names[name] = self.highest_name
        return self.highest_name

@dataclass
class NamedAInstruction:
    name: str = field()

SYMBOL_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:$."
SYMBOL_START_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_:$."

@dataclass
class ParserIterator(Iterator[str]):
    string: str
    idx: int = 0
    
    def __next__(self) -> str:
        if self.idx >= len(self.string):
            raise StopIteration()
        try:
            return self.string[self.idx]
        finally:
            self.idx += 1
    
    def has_next(self) -> bool:
        return self.idx < len(self.string)

    def go_back(self):
        if self.idx <= 0:
            raise ValueError()
        self.idx -= 1

def preassemble(asm: str) -> tuple[list[Instruction | NamedAInstruction], Namespace]:
    namespace = Namespace()
    instructions: list[Instruction | NamedAInstruction] = []
    i = ParserIterator(asm)
    while i.has_next():
        n = next(i)
        while i.has_next() and not n.strip():
            n = next(i)
        if not n.strip():
            break
        if n == "/":
            n = next(i)
            if n == "*":
                while i.has_next() and next(i) != "*" or next(i) != "/":
                    pass
                continue
            elif n == "/":
                while i.has_next() and next(i) != "\n":
                    pass
                continue
            else:
                raise SyntaxError(("Expected '*' or '/' after '/'.", i))
        elif n == "@":
            if not i.has_next():
                raise SyntaxError(("Expected symbol or number after '@'.", i))
            n = next(i)
            dest = n
            if n.isnumeric():
                while i.has_next() and (n := next(i)).isnumeric():
                    dest += n
                dest_num = int(dest)
                if dest_num < 0 or dest_num > 32767:
                    raise SyntaxError(("Expected number to be a number ranging from 0 to 32767.", i))
                try:
                    instructions.append(AInstruction(dest_num).to_raw())
                except SyntaxError as exp:
                    raise SyntaxError(((exp.args and exp.args[0]) or "No error message supplied.", i)) from exp
            elif n in SYMBOL_START_CHARS:
                while i.has_next() and (n := next(i)) in SYMBOL_CHARS:
                    dest += n
                instructions.append(NamedAInstruction(dest))
            else:
                raise SyntaxError(("Expected symbol or number after '@'.", i))
        elif n in SYMBOL_START_CHARS or n in "-10!":
            dest = ""
            comp_part_a = n
            operator = ""
            if n in ("!", "-"):
                operator = n
                if not i.has_next():
                    raise SyntaxError((f"Expected 'A', 'D', 'M' or number after '{operator}'.", i))
                comp_part_a = next(i)
            comp_part_b = ""
            jump = ""
            while i.has_next() and (n := next(i)) in SYMBOL_CHARS:
                comp_part_a += n
            if n == "=":
                if operator:
                    raise SyntaxError(("Unexpected '='.", i))
                dest = comp_part_a
                if not i.has_next():
                    raise SyntaxError(("Expected 'A', 'D', 'M' or number after '='.", i))
                n = next(i)
                if n in ("!", "-"):
                    operator = n
                    if not i.has_next():
                        raise SyntaxError((f"Expected 'A', 'D', 'M' or number after '{operator}'.", i))
                    n = next(i)
                comp_part_a = n
                while i.has_next() and (n := next(i)) in SYMBOL_CHARS:
                    comp_part_a += n
                if not comp_part_a:
                    i.go_back()
                    raise SyntaxError(("Expected 'A', 'D', 'M' or number after '='.", i))
            if n in "+-&|":
                if operator:
                    raise SyntaxError((f"Unexpected '{n}'.", i))
                operator = n
                if not i.has_next():
                    raise SyntaxError((f"Expected 'A', 'D', 'M' or number after '{operator}'.", i))
                n = next(i)
                comp_part_b = n
                while i.has_next() and (n := next(i)) in SYMBOL_CHARS:
                    comp_part_b += n
                if not comp_part_b:
                    i.go_back()
                    raise SyntaxError((f"Expected 'A', 'D', 'M' or number after '{operator}'.", i))
            if n == ";":
                if not i.has_next():
                    raise SyntaxError(("Expected 'J' after ';'.", i))
                n = next(i)
                jump = n
                while i.has_next() and (n := next(i)) in SYMBOL_CHARS:
                    jump += n
                if not jump:
                    i.go_back()
                    raise SyntaxError((f"Expected 'J' after ';'.", i))
            try:
                instructions.append(CInstruction(dest, (comp_part_a, (operator, comp_part_b) if operator else None), jump).to_raw())
            except SyntaxError as exp:
                raise SyntaxError(((exp.args and exp.args[0]) or "No error message supplied.", i)) from exp
        elif n == "(":
            if not i.has_next():
                raise SyntaxError(("Expected a symbol after '('.", i))
            n = next(i)
            if n not in SYMBOL_START_CHARS:
                raise SyntaxError(("Expected a symbol after '('.", i))
            label = n
            while (n := next(i)) in SYMBOL_CHARS:
                label += n
            if n != ")":
                raise SyntaxError(("Expected ')' after '(' and a symbol.", i))
            namespace.names[label] = len(instructions)
            n = next(i)
        else:
            raise SyntaxError(("Expected comment or instruction.", i))
        if n.strip():
            raise SyntaxError(("Expected whitespace.", i))
    return instructions, namespace

def resolve_if_named_a_instruction(instruction: Instruction | NamedAInstruction, namespace: Namespace) -> Instruction:
    if isinstance(instruction, Instruction):
        return instruction
    return AInstruction(namespace.resolve(instruction.name))

def assemble(asm: str) -> bytes:
    preassembled, namespace = preassemble(asm)
    instructions = [resolve_if_named_a_instruction(i, namespace) for i in preassembled]
    return b"".join(i.to_bytes() for i in instructions)

def assembled_to_hack(assembled: bytes) -> str:
    return "\n".join(f"{(i<<8)|j:0>16b}" for i, j in batched(assembled, 2))

if __name__ == "__main__":
    assembled = assemble("""
    A=A
    A=A
    D=D
    @13
    // a wd @5
    @2
    /* awdfawd
    @3
    */
    @23
    @aaw
    @awda
    (awda)
    A=A+1
    """)
    
    print(assembled.hex())
    print()
    print(assembled_to_hack(assembled))