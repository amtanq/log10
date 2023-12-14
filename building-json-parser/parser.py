from glob import iglob
from unittest import main, TestCase
from json import loads


class JsonParseException(Exception):
  ...


class TokenNotFound:
  ...


def lookahead() -> str:
  if index < size:
    return code[index]
  return chr(0)


def forward() -> None:
  global index
  index += 1


def processed() -> str:
  return code[index - 1]


def get_array(depth) -> list:
  if lookahead() == "[":
    forward()
    skip_whitespace()
    if lookahead() == "]":
      forward()
      return []
    elements = get_elements(depth + 1)
    if elements == TokenNotFound:
      elements = []
      skip_whitespace()
    if lookahead() == "]":
      forward()
      return elements
    raise JsonParseException("Expected ]")
  return TokenNotFound


def get_character() -> str:
  if lookahead() == "\"":
    return TokenNotFound
  if lookahead() == "\\":
    forward()
    escape = get_escape()
    if escape == TokenNotFound:
      raise JsonParseException("Expected Escape")
    return escape
  if 0x20 <= ord(lookahead()) <= 0x10FFFF:
    forward()
    return processed()
  return TokenNotFound


def get_characters() -> str:
  character = get_character()
  if character == TokenNotFound:
    return TokenNotFound
  characters = get_characters()
  if characters == TokenNotFound:
    return character
  return character + characters


def get_digit() -> str:
  if lookahead() == "0":
    forward()
    return processed()
  return get_one_to_nine()


def get_digits() -> str:
  digit = get_digit()
  if digit == TokenNotFound:
    return TokenNotFound
  digits = get_digits()
  if digits == TokenNotFound:
    return digit
  return digit + digits


def get_element(depth) -> object:
  skip_whitespace()
  value = get_value(depth)
  skip_whitespace()
  return value


def get_elements(depth) -> object:
  if depth == 20:
    raise JsonParseException("Deep")
  element = get_element(depth)
  if element == TokenNotFound:
    return TokenNotFound
  if lookahead() == ",":
    forward()
    elements = get_elements(depth)
    if elements == TokenNotFound:
      return elements
    if isinstance(elements, list):
      return [element, *elements]
    return {**element, **elements}
  return [element]


def get_escape() -> str:
  if lookahead() in "\"\\/":
    forward()
    return processed()
  if lookahead() in "bfnrt":
    forward()
    return escape_map[processed()]
  if lookahead() == "u":
    forward()
    hex = [get_hex(), get_hex(), get_hex(), get_hex()]
    if TokenNotFound in hex:
      raise JsonParseException("Expected Hex")
    return chr(int(str().join(hex), 16))
  return TokenNotFound


def get_exponent() -> str:
  if lookahead() in "Ee":
    forward()
    sign = get_sign()
    if sign == TokenNotFound:
      sign = str()
    digits = get_digits()
    if digits == TokenNotFound:
      raise JsonParseException("Expected Digit")
    return "E" + sign + digits
  return TokenNotFound


def get_fraction() -> str:
  if lookahead() == ".":
    forward()
    digits = get_digits()
    if digits == TokenNotFound:
      raise JsonParseException("Expected Digit")
    return "." + digits
  return TokenNotFound


def get_hex() -> str:
  if lookahead() in "ABCDEFabcdef":
    forward()
    return processed()
  return get_digit()


def get_integer() -> str:
  sign = str()
  if lookahead() == "-":
    forward()
    sign = processed()
  one_to_nine = get_one_to_nine()
  if one_to_nine == TokenNotFound:
    digit = get_digit()
    if digit == TokenNotFound:
      raise JsonParseException("Expected Number")
    return sign + digit
  digits = get_digits()
  if digits == TokenNotFound:
    return sign + one_to_nine
  return sign + one_to_nine + digits


def get_json(s: str) -> object:
  global index, size, code
  code = s
  [index, size] = [0, len(s)]
  element = get_element(0)
  if index != size:
    raise JsonParseException()
  if type(element) not in [list, dict]:
    raise JsonParseException()
  return element


def get_member(depth) -> object:
  skip_whitespace()
  string = get_string()
  if string == TokenNotFound:
    raise JsonParseException("Expected String")
  skip_whitespace()
  if lookahead() == ":":
    forward()
    element = get_element(depth)
    if element == TokenNotFound:
      raise JsonParseException("Expected Element")
    return {string: element}
  raise JsonParseException("Expected :")


def get_members(depth) -> object:
  if depth == 20:
    raise JsonParseException("Deep")
  member = get_member(depth)
  if member == TokenNotFound:
    return TokenNotFound
  if lookahead() == ",":
    forward()
    members = get_members(depth)
    if members == TokenNotFound:
      return members
    if isinstance(members, list):
      return [member, *members]
    return {**member, **members}
  return member


def get_number() -> float | int:
  integer = get_integer()
  if integer == TokenNotFound:
    return TokenNotFound
  fraction = get_fraction()
  if fraction == TokenNotFound:
    exponent = get_exponent()
    if exponent == TokenNotFound:
      return int(integer)
    return float(integer + exponent)
  exponent = get_exponent()
  if exponent == TokenNotFound:
    return float(integer + fraction)
  return float(integer + fraction + exponent)


def get_object(depth) -> object:
  if lookahead() == "{":
    forward()
    skip_whitespace()
    if lookahead() == "}":
      forward()
      return {}
    members = get_members(depth + 1)
    if members == TokenNotFound:
      members = {}
      skip_whitespace()
    if lookahead() == "}":
      forward()
      return members
    raise JsonParseException("Expected }")
  return TokenNotFound


def get_one_to_nine() -> str:
  if lookahead() in "123456789":
    forward()
    return processed()
  return TokenNotFound


def get_sign() -> str:
  if lookahead() in "+-":
    forward()
    return processed()
  return TokenNotFound


def get_string() -> str:
  if lookahead() == "\"":
    forward()
    characters = get_characters()
    if characters == TokenNotFound:
      characters = str()
    if lookahead() == "\"":
      forward()
      return characters
    raise JsonParseException("Expected \"")
  return TokenNotFound


def get_value(depth) -> object:
  if lookahead() == "t":
    forward(), forward(), forward(), forward()
    return True
  if lookahead() == "f":
    forward(), forward(), forward(), forward(), forward()
    return False
  if lookahead() == "n":
    forward(), forward(), forward(), forward()
    return None
  object = get_object(depth)
  if object != TokenNotFound:
    return object
  array = get_array(depth)
  if array != TokenNotFound:
    return array
  string = get_string()
  if string != TokenNotFound:
    return string
  number = get_number()
  if number != TokenNotFound:
    return number
  raise JsonParseException("Unexpected Value")


def skip_whitespace() -> None:
  while ord(lookahead()) in [0x9, 0xA, 0xD, 0x20]:
    forward()


class TestJsonParser(TestCase):
  def test_valid(self):
    for path in iglob("test/pass*"):
      with open(path) as reader:
        code = reader.read()
      self.assertEqual(loads(code), get_json(code))

  def test_invalid(self):
    for path in iglob("test/fail*"):
      with open(path) as reader:
        code = reader.read()
      with self.assertRaises(JsonParseException):
        get_json(code)


escape_map = dict(b="\b", f="\f", n="\n", r="\r", t="\t")

if __name__ == "__main__":
  main()
