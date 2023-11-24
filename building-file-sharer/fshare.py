#!/usr/bin/env python3
from Cryptodome.Cipher import ChaCha20_Poly1305, PKCS1_OAEP
from Cryptodome.PublicKey import RSA
from Cryptodome.Random import get_random_bytes
from functools import partial
from gzip import compress, decompress
from os import stat
from os.path import splitext
from queue import Queue
from requests import get, put
from threading import Thread
from tkinter import EW, IntVar, StringVar, Tk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror, showinfo
from tkinter.ttk import Button, Entry, Progressbar
from typing import Callable
from urllib.parse import urlparse

CHUNK_SIZE = 1 << 20
PRESIGNER = "https://store.log10.workers.dev"
BLOBSTORE = "https://bucket.log10.dev"

def upload(key: str, name: str, progress: Callable[[float], None]) -> str:
  progress(0.0)
  secret = get_random_bytes(32)
  public = RSA.import_key(open(key).read())

  def encrypt(data: bytes) -> bytes:
    header = get_random_bytes(4)
    cipher = ChaCha20_Poly1305.new(key=secret)
    cipher.update(header)
    text, tag = cipher.encrypt_and_digest(compress(data))
    return cipher.nonce + header + tag + text

  def store(data: bytes) -> str:
    url = get(PRESIGNER).text
    put(url, data=data)
    return urlparse(url).path[1:]

  current, total = 0, stat(name).st_size
  meta = [splitext(name)[1], str(total),
    PKCS1_OAEP.new(public).encrypt(secret).hex()]
  with open(name, "rb") as reader:
    while chunk := reader.read(CHUNK_SIZE):
      meta.append(store(encrypt(chunk)))
      current += len(chunk)
      progress(current / total)
  return store(" ".join(meta))

def download(key: str, token: str, progress: Callable[[float], None]) -> None:
  progress(0.0)
  response = get(f"{BLOBSTORE}/{token}")
  if response.status_code != 200: return

  private = RSA.import_key(open(key).read())
  ftype, total, secret, *meta = response.text.split()
  secret = PKCS1_OAEP.new(private).decrypt(bytes.fromhex(secret))

  def decrypt(data: bytes) -> bytes:
    nonce, header, tag, text = data[:12], data[12:16], data[16:32], data[32:]
    cipher = ChaCha20_Poly1305.new(key=secret, nonce=nonce)
    cipher.update(header)
    return decompress(cipher.decrypt_and_verify(text, tag))

  current, total = 0, int(total)
  with open(token[:10] + ftype, "wb") as writer:
    for hash in meta:
      chunk = decrypt(get(f"{BLOBSTORE}/{hash}").content)
      writer.write(chunk)
      current += len(chunk)
      progress(current / total)

q = Queue()
def enqueue(task: Callable[[], None]) -> None:
  if not q.unfinished_tasks: q.put(task)
  else: showinfo("info", "task in progress")

def worker() -> None:
  def _progress(value: float) -> None:
    progress.set(int(value * 100))

  while True:
    task = q.get()
    key = askopenfilename(title="Public Key")
    try:
      if task == upload:
        file = askopenfilename()
        token.set(upload(key, file, _progress))
      elif task == download:
        download(key, token.get(), _progress)
      showinfo("info", "task complete")
    except: showerror("error", "bad input")
    q.task_done()

root = Tk()
root.title("sync")
root.resizable(False, False)
token = StringVar(value="...")
progress = IntVar(value=0)

Thread(target=worker).start()
Entry(textvariable=token).grid(row=0, column=0, columnspan=2, sticky=EW, padx=10, pady=(10, 0))
Progressbar(variable=progress).grid(row=1, column=0, columnspan=2, sticky=EW, padx=10)
Button(text="upload", command=partial(enqueue, upload)).grid(row=2, column=0, padx=(10, 2.5), pady=(0, 10))
Button(text="download", command=partial(enqueue, download)).grid(row=2, column=1, padx=(2.5, 10), pady=(0, 10))
exit(root.mainloop())