; Identifier naming conventions

(identifier) @variable
(attribute attribute: (identifier) @property)

((identifier) @type.class
 (#match? @type.class "^_*[A-Z][A-Za-z0-9_]*$"))

((identifier) @constant
 (#match? @constant "^_*[A-Z][A-Z0-9_]*$"))

(type (identifier) @type)
(generic_type (identifier) @type)

; Literals

(comment) @comment
(string) @string
(escape_sequence) @string.escape

[
  (true)
  (false)
] @boolean

[
  (none)
  (ellipsis)
] @constant.builtin

[
  (integer)
  (float)
] @number

; Function calls

(call
  function: (attribute
    attribute: (identifier) @function.method.call))

(call
  function: (identifier) @function.call)

(decorator
  "@" @punctuation.special)

(decorator
  [
    (identifier) @function.decorator
    (attribute
      attribute: (identifier) @function.decorator)
    (call
      function: (identifier) @function.decorator.call)
    (call
      function: (attribute
        attribute: (identifier) @function.decorator.call))
  ])

; Definitions

(function_definition
  name: (identifier) @function.definition)

(class_definition
  name: (identifier) @type.class.definition)

(class_definition
  superclasses: (argument_list
    (identifier) @type.class.inheritance))

(call
  function: (identifier) @type.class.call
  (#match? @type.class.call "^_*[A-Z][A-Za-z0-9_]*$"))

; Function arguments

(function_definition
  parameters: (parameters
    [
      (identifier) @variable.parameter
      (typed_parameter
        (identifier) @variable.parameter)
      (default_parameter
        name: (identifier) @variable.parameter)
      (typed_default_parameter
        name: (identifier) @variable.parameter)
    ]))

(call
  arguments: (argument_list
    (keyword_argument
      name: (identifier) @function.kwargs)))

; Builtins

((call
  function: (identifier) @function.builtin)
 (#match? @function.builtin "^(abs|all|any|ascii|bin|bool|breakpoint|bytearray|bytes|callable|chr|classmethod|compile|complex|delattr|dict|dir|divmod|enumerate|eval|exec|filter|float|format|frozenset|getattr|globals|hasattr|hash|help|hex|id|input|int|isinstance|issubclass|iter|len|list|locals|map|max|memoryview|min|next|object|oct|open|ord|pow|print|property|range|repr|reversed|round|set|setattr|slice|sorted|staticmethod|str|sum|super|tuple|type|vars|zip|__import__)$"))

; Self references

((parameters
  (identifier) @variable.special)
 (#match? @variable.special "^(self|cls)$"))

((attribute
  (identifier) @variable.special)
 (#match? @variable.special "^(self|cls)$"))

; Punctuation and operators

[
  "."
  ","
  ":"
] @punctuation.delimiter

[
  "("
  ")"
  "["
  "]"
  "{"
  "}"
] @punctuation.bracket

(interpolation
  "{" @punctuation.special
  "}" @punctuation.special) @embedded

[
  "-"
  "-="
  "!="
  "*"
  "**"
  "**="
  "*="
  "/"
  "//"
  "//="
  "/="
  "&"
  "&="
  "%"
  "%="
  "@"
  "@="
  "^"
  "^="
  "+"
  "->"
  "+="
  "<"
  "<<"
  "<<="
  "<="
  "<>"
  "="
  ":="
  "=="
  ">"
  ">="
  ">>"
  ">>="
  "|"
  "|="
  "~"
] @operator

[
  "and"
  "in"
  "is"
  "not"
  "or"
  "is not"
  "not in"
] @keyword.operator

[
  "as"
  "assert"
  "async"
  "await"
  "break"
  "class"
  "continue"
  "def"
  "del"
  "elif"
  "else"
  "except"
  "exec"
  "finally"
  "for"
  "from"
  "global"
  "if"
  "import"
  "lambda"
  "nonlocal"
  "pass"
  "print"
  "raise"
  "return"
  "try"
  "while"
  "with"
  "yield"
  "match"
  "case"
] @keyword

[
  "async"
  "def"
  "class"
  "lambda"
] @keyword.definition

(decorator
  (identifier) @attribute.builtin
  (#match? @attribute.builtin "^(classmethod|staticmethod|property)$"))
