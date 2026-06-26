# aether/tokens.py
from enum import Enum, auto
from dataclasses import dataclass

class TokenType(Enum):
    EOF = auto()
    INT = auto(); STRING = auto(); RAW_CMD = auto(); RAW_TEXT = auto(); TRUE = auto(); FALSE = auto()
    IDENT = auto(); NAMESPACE = auto(); FN = auto(); LET = auto(); CONST = auto(); VAR = auto(); MUT = auto(); EXECUTE = auto()
    IF = auto(); ELSE = auto(); FOR = auto(); IN = auto(); OF = auto(); RETURN = auto()
    AND = auto(); OR = auto(); NOT = auto()
    INT_TYPE = auto(); STRING_TYPE = auto(); BOOL_TYPE = auto()
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto(); PERCENT = auto()
    PLUSPLUS = auto(); MINUSMINUS = auto()
    ASSIGN = auto(); EQ = auto(); NEQ = auto(); LT = auto(); GT = auto(); LTE = auto(); GTE = auto()
    PLUSEQ = auto(); MINUSEQ = auto(); STAREQ = auto(); SLASHEQ = auto(); PERCENTEQ = auto()
    COLON = auto(); SEMICOLON = auto(); DOT = auto(); COMMA = auto(); ARROW = auto(); DOTDOT = auto()
    LPAREN = auto(); RPAREN = auto(); LBRACE = auto(); RBRACE = auto(); LBRACKET = auto(); RBRACKET = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int

    def __repr__(self): return f"Token({self.type.name}, '{self.value}')"

KEYWORDS = {
    "namespace": TokenType.NAMESPACE,
    "function": TokenType.FN,
    "fn": TokenType.FN,
    "let": TokenType.LET,
    "const": TokenType.CONST,
    "var": TokenType.VAR,
    "mut": TokenType.MUT,
    "execute": TokenType.EXECUTE,
    "if": TokenType.IF, "else": TokenType.ELSE, "for": TokenType.FOR, "in": TokenType.IN, "of": TokenType.OF, "return": TokenType.RETURN,
    "true": TokenType.TRUE, "false": TokenType.FALSE,
    "int": TokenType.INT_TYPE, "string": TokenType.STRING_TYPE, "bool": TokenType.BOOL_TYPE,
    "and": TokenType.AND, "or": TokenType.OR, "not": TokenType.NOT,
}
