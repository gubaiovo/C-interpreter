import re
from collections import namedtuple

OPERATORS = [
    # 长运算符优先
    "<<=", ">>=",  # 复合运算符
    "++", "--", "<<", ">>", "<=", ">=", "==", "!=",
    "&&", "||", "+=", "-=", "*=", "/=", "%=", "&=",
    "^=", "|=", "->", 
    # 单字符运算符
    "+", "-", "*", "/", "<", ">", "=", "!", "^", 
    "&", "|", "%", "~", "?", ":"
]
SEPARATORS = [
    ";", "(", ")", "[", "]", "{", "}", 
    ".", ",", "#", "\\", "'", "\""
]
KEYWORDS = [
    "auto", "break", "case", "const", "continue","default", "do",  "else", "enum", "extern",
  "for", "goto", "if", "register", "return", "short", "signed", "sizeof", "static",
    "struct", "switch", "typedef", "union",  "volatile", "while", "printf"
]
CMP = [
    "==","!=","<",">","<=",">="
]
TYPES = [
    "int","float","char","double","void","long","unsigned","string"
]

Token = namedtuple('Token', ['type', 'value', 'line', 'column'])

class LexerError(Exception):
    def __init__(self, message, line, column):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{message} (Line {line}, Column {column})")

class CLexer:
    def __init__(self, code):
        self.code = code
        self.pos = 0
        self.line = 1
        self.line_start = 0
        self._regex = self._build_regex()
        
    def _build_regex(self):
        regex_rules = [
            # comments and escape
            (r'//[^\n]*', None),
            (r'/\*[\s\S]*?\*/', 'COMMENT'),
            (r'\n', 'NEWLINE'),
            (r'[ \t\r]+', None),
            # literal
            (r'"(\\["\\nrt0]|.)*?"', 'STR'),
            (r"'(\\['\"\\nrt0]|.)'", 'CHAR'),
            (r'0[xX][0-9a-fA-F]+', 'HEX'),
            (r'0[0-7]+', 'OCT'),
            (r'\d+\.\d+([eE][+-]?\d+)?', 'FLOAT'),
            (r'\d+', 'INT'),
            # type and keyword
            (r'\b(' + '|'.join(KEYWORDS) + r')\b', 'KEYWORD'),
            (r'\b(' + '|'.join(TYPES) + r')\b', 'TYPE'),
            # identifiers
            (r'[a-zA-Z_]\w*', 'IDENTIFIER'),
            # operators and separators
            (r'[' + re.escape(''.join(SEPARATORS)) + r']', 'SEPARATOR'),
            (r'(' + '|'.join(map(re.escape, sorted(OPERATORS, key=lambda x: -len(x)))) + r')', 'OPERATOR')
        ]
        # build regex
        parts = []
        for pattern, tag in regex_rules:
            if tag:
                parts.append(f'(?P<{tag}>{pattern})')
            else:
                parts.append(f'(?:{pattern})')
        return re.compile('|'.join(parts), re.DOTALL)
    
    def tokenize(self):
        tokens = []
        while self.pos < len(self.code):
            match = self._regex.match(self.code, self.pos)
            if not match:
                line, col = self._get_position()
                raise LexerError("Invalid character", line, col)
            token_type = next((k for k, v in match.groupdict().items() if v), None)
            value = match.group()
            line, col = self._get_position()
            self.pos = match.end()
            
            # handle special cases
            if token_type == 'NEWLINE':
                self.line += 1
                self.line_start = self.pos
            elif token_type == 'COMMENT':
                self._handle_comment(value)
                continue
            elif token_type == 'CHAR':
                value = self._parse_char(value[1:-1]) # remove quotes
            elif token_type == 'STR':
                value = self._parse_string(value[1:-1]) # remove quotes
            
            if token_type:
                tokens.append(Token(token_type, value, line, col))
                
        tokens.append(Token('EOF', '', self.line, 0))
        return tokens
        
    def _get_position(self):
        return (self.line, self.pos - self.line_start + 1)
    
    def _handle_comment(self, comment):
        newlines = comment.count('\n')
        if newlines:
            self.line += newlines
            last_nl = comment.rfind('\n')
            self.line_start = self.pos - (len(comment) - last_nl - 1)
    
    def _parse_char(self, value):
        if len(value) == 1:
            return value
        if value[0] == '\\':
            return {'n': '\n', 't': '\t', 'r': '\r', '0': '\0'}.get(value[1], value[1])
        return value
    
    def _parse_string(self, s):
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i+1 < len(s):
                result.append({'n': '\n', 't': '\t', 'r': '\r'}.get(s[i+1], s[i+1]))
                i += 2
            else:
                result.append(s[i])
                i += 1
        return ''.join(result)
    
if __name__ == '__main__':
    sample_code = """
    /* comment /* inner */
    int main() {
        printf("%d\\n", 42);//test comment
        int x = a <<= 1;      // 测试复合运算符
    }
    void test() {
        printf("Hello, world!");
    }
    """
    
    lexer = CLexer(sample_code)
    try:
        tokens = lexer.tokenize()
        for token in tokens:
            print(f"{token.line:3}:{token.column:<3} {token.type:<12} {repr(token.value)}")
    except LexerError as e:
        print(f"词法错误: {e}")
        
'''
❯ python lexer.py
  1:1   NEWLINE      '\n'
  4:7   NEWLINE      '\n'
  5:5   TYPE         'int'
  5:9   IDENTIFIER   'main'
  5:13  SEPARATOR    '('
  5:14  SEPARATOR    ')'
  5:16  SEPARATOR    '{'
  5:17  NEWLINE      '\n'
  6:9   KEYWORD      'printf'
  6:15  SEPARATOR    '('
  6:16  STR          '%d\n'
  6:22  SEPARATOR    ','
  6:24  INT          '42'
  6:26  SEPARATOR    ')'
  6:27  SEPARATOR    ';'
  6:42  NEWLINE      '\n'
  7:9   TYPE         'int'
  7:13  IDENTIFIER   'x'
  7:15  OPERATOR     '='
  7:17  IDENTIFIER   'a'
  7:19  OPERATOR     '<<='
  7:23  INT          '1'
  7:24  SEPARATOR    ';'
  7:41  NEWLINE      '\n'
  8:5   SEPARATOR    '}'
  8:6   NEWLINE      '\n'
  9:5   TYPE         'void'
  9:10  IDENTIFIER   'test'
  9:14  SEPARATOR    '('
  9:15  SEPARATOR    ')'
  9:17  SEPARATOR    '{'
  9:18  NEWLINE      '\n'
 10:9   KEYWORD      'printf'
 10:15  SEPARATOR    '('
 10:16  STR          'Hello, world!'
 10:31  SEPARATOR    ')'
 10:32  SEPARATOR    ';'
 10:33  NEWLINE      '\n'
 11:5   SEPARATOR    '}'
 11:6   NEWLINE      '\n'
 12:0   EOF          ''
'''