#!/usr/bin/env python3
from __future__ import annotations
from argparse import ArgumentParser
from hashlib import md5
from heapq import heapify, heappop, heappush
from os.path import isfile

INT_WIDTH = 32
MD5_WIDTH = 128
EXTENSION = ".he"

class Node:
  def __init__(self: Node, id: int = None) -> None:
    self.id = id
    self.count = 0
    self.left = self.right = None

  def __lt__(self: Node, other: Node) -> bool:
    return self.count < other.count

def bits(number: int, padding: int = 8) -> str:
  return bin(number)[2:].rjust(padding, "0")

def encode(name: str) -> str:
  with open(name, "rb") as reader:
    buffer = reader.read()

  nodes = [Node(id) for id in range(256)]
  for byte in buffer: nodes[byte].count += 1
  nodes = [node for node in nodes if node.count]
  heapify(nodes)
  while len(nodes) > 1:
    node = Node()
    node.left = heappop(nodes)
    node.right = heappop(nodes)
    node.count = node.left.count + node.right.count
    heappush(nodes, node)

  def serializer(node: Node, path: str) -> str:
    if node.id is not None:
      code[node.id] = path
      return "1" + bits(node.id, 8)
    left = serializer(node.left, path + "0")
    right = serializer(node.right, path + "1")
    return left + right + "0"

  dsum = md5(buffer)
  code = [None] * (256)
  tree = serializer(nodes[0], str())
  data = "".join(code[byte] for byte in buffer)
  data = bits(len(data), INT_WIDTH) + tree + "0" + data
  data = data + "0" * (8 - len(data) % 8)
  with open(name + EXTENSION, "wb") as writer:
    writer.write(bytes([
      int(data[index:index+8], 2)
      for index in range(0, len(data), 8)]))
    writer.write(dsum.digest())
  return dsum.hexdigest()

def decode(name: str) -> str:
  with open(name, "rb") as reader:
    buffer = "".join(map(bits, reader.read()))

  stack = []
  index = INT_WIDTH
  while True:
    index += 1
    if buffer[index - 1] == '0':
      if len(stack) == 1: break
      node = Node()
      node.right = stack.pop()
      node.left = stack.pop()
      stack.append(node)
    else:
      id = int(buffer[index:index+8], 2)
      stack.append(Node(id))
      index += 8

  data = []
  root = stack[0]
  limit = int(buffer[:INT_WIDTH], 2) + index
  while index <= limit:
    if root.id is not None:
      data.append(root.id)
      root = stack[0]
    elif buffer[index] == '0':
      root = root.left
      index += 1
    else:
      root = root.right
      index += 1

  data = bytes(data)
  dsum = md5(data).hexdigest()
  fsum = hex(int(buffer[-MD5_WIDTH:], 2))[2:]
  if fsum != dsum: return None
  with open(name[:-3], "wb") as writer:
    writer.write(bytes(data))
  return fsum

if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("file")
  args = parser.parse_args()

  if not isfile(args.file):
    parser.error("file not found")

  if args.file.endswith(EXTENSION):
    csum = decode(args.file)
  else:
    csum = encode(args.file)

  if not csum:
    parser.error("invalid file")
  print(f"md5: {csum}")