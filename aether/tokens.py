# src/aether/tokens.py

from enum import Enum, auto
from dataclasses import dataclass

class TokenType(Enum):
    # Special
    INDENT = auto(); DEDENT = auto(); NEWLINE = auto(); EOF = auto()
    # Literals
    INT = auto(); STRING = auto(); FORMAT_STRING = auto(); TRUE = auto(); FALSE = auto()
    # Identifiers & Keywords
    IDENT = auto(); NAMESPACE = auto(); DEF = auto(); CLASS = auto(); IMPORT = auto(); LOCAL = auto()
    IF = auto(); ELIF = auto(); ELSE = auto(); FOR = auto(); WHILE = auto(); RETURN = auto()
    IN = auto(); RANGE = auto(); SELF = auto()
    AND = auto(); OR = auto(); NOT = auto()
    INT_TYPE = auto(); STRING_TYPE = auto(); BOOL_TYPE = auto()
    # Operators
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto(); PERCENT = auto()
    ASSIGN = auto(); EQ = auto(); NEQ = auto(); LT = auto(); GT = auto(); LTE = auto(); GTE = auto()
    PLUSEQ = auto(); MINUSEQ = auto(); STAREQ = auto(); SLASHEQ = auto(); PERCENTEQ = auto()
    COLON = auto(); DOT = auto(); COMMA = auto(); ARROW = auto()
    # Delimiters
    LPAREN = auto(); RPAREN = auto(); LBRACKET = auto(); RBRACKET = auto()
    AT = auto() # Added for decorators

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int

    def __repr__(self): return f"Token({self.type.name}, '{self.value}')"

KEYWORDS = {
    "namespace": TokenType.NAMESPACE, "def": TokenType.DEF, "class": TokenType.CLASS, "import": TokenType.IMPORT,
    "local": TokenType.LOCAL,
    "if": TokenType.IF, "elif": TokenType.ELIF, "else": TokenType.ELSE, "for": TokenType.FOR, "while": TokenType.WHILE,
    "return": TokenType.RETURN, "in": TokenType.IN, "range": TokenType.RANGE, "self": TokenType.SELF,
    "true": TokenType.TRUE, "false": TokenType.FALSE,
    "int": TokenType.INT_TYPE, "string": TokenType.STRING_TYPE, "bool": TokenType.BOOL_TYPE,
    "and": TokenType.AND, "or": TokenType.OR, "not": TokenType.NOT,
}