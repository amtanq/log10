#!/usr/bin/env python3
from queue import Queue
from re import finditer
from requests import get
from threading import Thread
from tkinter import ALL, BOTH, Canvas, NW, PhotoImage, StringVar, Tk
from tkinter.messagebox import showinfo
from tkinter.ttk import Entry

gc, links = [], []
def render(page: str) -> None:
  offset = 0
  gc.clear()
  links.clear()
  ctx.delete(ALL)

  for match in finditer(r"([a-z]+)\[([^\]]+)\]: (.*)", page):
    tag, conf, text = match.group(1), match.group(2), match.group(3)
    x, y, width = 10, offset + 10, 480
    if tag == "h":
      id = ctx.create_text(x, y, width=width, anchor=NW, fill=conf, font=("default", 24), text=text)
    elif tag == "p":
      id = ctx.create_text(x, y, width=width, anchor=NW, fill=conf, text=text)
    elif tag == "i":
      gc.append(PhotoImage(data=get(conf).content))
      id = ctx.create_image(x, y, anchor=NW, image=gc[-1])
    elif tag == "a":
      name = f"link{len(links)}"
      id = ctx.create_text(x, y, width=width, anchor=NW, fill="#00f", text=text, tags=[name])
      ctx.tag_bind(name, "<Button-1>", navigator(conf))
      links.append(conf)
    offset = ctx.bbox(id)[3]

def navigator(url: str) -> None:
  def _(_) -> None:
    target.set(url)
    enqueue(None)
  return _

q = Queue()
def enqueue(_) -> None:
  if not q.unfinished_tasks: q.put(target.get())
  else: showinfo("info", "task in progress")

def worker() -> None:
  while True:
    url = q.get()
    root.title(f"loading: {url}")
    try: render(get(url).text)
    except: showinfo("info", "error while connecting")
    finally:
      root.title("web")
      q.task_done()

if __name__ == "__main__":
  root = Tk()
  target = StringVar(value="https://i12.netlify.app/home.web")
  searchbar = Entry(textvariable=target)
  searchbar.pack(expand=True, fill=BOTH)
  searchbar.bind("<Return>", enqueue)
  ctx = Canvas(bg="#fff", height=500, width=500)
  ctx.pack()

  Thread(target=worker).start()
  enqueue(None)

  root.resizable(False, False)
  root.title("web")
  root.mainloop()