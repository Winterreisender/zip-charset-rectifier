from enum import Enum
import shutil
import sys
import tempfile
from tkinter import *
from tkinter.ttk import *
import tkinter.messagebox as messagebox
from typing import Any, Dict
from dataclasses import dataclass
from tkinterdnd2 import DND_FILES, TkinterDnD
from pathlib import Path
from libzipcharsetconv import zipconv, zipdetect, ziplint, SUPPORTED_FORMAT
import json
import logging

LOGGER = logging.getLogger("gui")
TMP_DIR=None


#Config
class Config:
    def __init__(self) -> None:
        self.file_path = Path("~/.config/zip_charset_rectifier_gui/").expanduser()
        self.data = {

        }

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def load(self):
        with open(self.file_path, 'r', encoding='utf-8') as f:
            self.data=json.load(f)

# Model
class ZipValid(Enum):
    NOT_CHECKED=0 # 未进行检测
    VALID=1 # 是UTF8格式完整的ZIP文件,无需转换
    INVALID=2 # 非是UTF8格式完整的ZIP文件,无需转换
    BROKEN=3 # 压缩文件已损坏,无法转换
    CONVERT_FAILED=4 # 转换失败

    def __str__(self):
        return {
            ZipValid.VALID: "valid",
            ZipValid.INVALID: "invalid",
            ZipValid.BROKEN: "broken",
            ZipValid.NOT_CHECKED: "not checked",
            ZipValid.CONVERT_FAILED: "convert failed",
        }[self]

    def to_color(self) -> str:
        return {
            ZipValid.VALID: "green",
            ZipValid.INVALID: "orange",
            ZipValid.BROKEN: "red",
            ZipValid.NOT_CHECKED: "white",
            ZipValid.CONVERT_FAILED: "pink",
        }[self]

@dataclass
class PathInfo:
    status :ZipValid = ZipValid.NOT_CHECKED
    index :int|None = None
    encoding :str = 'unknown'

    @classmethod
    def get_columns(cls):
        return ('status','index','encoding')

    def to_tuple(self) -> list[str]:
        return str(self.status), str(self.index), self.encoding
        

state_path_info :Dict[Path, PathInfo]= {}
state_overwrite_compression: BooleanVar
state_debug: BooleanVar

# Update
def update_ui():
    global fileTable
    global state_path_info
    global LOGGER

    fileTable.delete(*fileTable.get_children()) # clear fileTable
    for i,(path,info) in enumerate(state_path_info.items()):
        info.index = i
        fileTable.insert('', info.index, values=(str(path), *info.to_tuple()), tags=(str(info.status),))
        fileTable.tag_configure(str(info.status), background=info.status.to_color())
    LOGGER.setLevel((logging.WARN, logging.DEBUG)[state_debug.get()])
    LOGGER.info(f"{state_path_info=}")

def ui_action(func):
    def wrapper(*args, **kw):
        func(*args, **kw)
        update_ui()
    return wrapper

# View
@ui_action
def on_files_drop(event :TkinterDnD.DnDEvent):
    global state_path_info, LOGGER
    for x in fileTable.tk.splitlist(event.data):
        file_path = Path(x)
        # rectify args
        if not file_path.exists():
            LOGGER.info(f"{file_path=} not exists, skipping")
            continue
        if file_path.suffix.lower() not in SUPPORTED_FORMAT:
            LOGGER.info(f"{file_path.suffix.lower()} format not supported")
            continue
        # do jobs
        state_path_info |= { Path(file_path): PathInfo(status=ZipValid.NOT_CHECKED, index=None)}
    LOGGER.info(f"{type(event.data)=}, {event.data=}")

@ui_action
def on_lint_button_clicked():
    global state_path_info
    for path,info in state_path_info.items():
        try:
            info.encoding = zipdetect(path)
            info.status= ZipValid.VALID if info.encoding=='utf8' else ZipValid.INVALID
        except AssertionError as err:
            info.status = ZipValid.BROKEN
            messagebox.showerror("Warning", str(err))

@ui_action
def on_conv_button_clicked():
    convertButton.config(state=DISABLED)

    def mkbackup(file_path :Path):
        backup_dirname = ".zipchasetconv_backup"
        backup_dir = file_path.parent/backup_dirname
        backup_dir.mkdir(exist_ok=True)
        shutil.copy(str(file_path),str(backup_dir))
    for i,(path,info) in enumerate(state_path_info.items()):
        print(f"Converting {i+1}/{len(state_path_info)}...")
        if info.status==ZipValid.INVALID:
            try:
                mkbackup(path)
                
                tmpdir = tempfile.TemporaryDirectory("_zipconv")
                LOGGER.info(tmpdir.name)
                zipconv(path, path.with_suffix(".zip"), decoding=zipdetect(path), force_deflated=state_overwrite_compression.get(), tmpdir=Path(tmpdir.name))
                info.status=ZipValid.VALID
                tmpdir.cleanup()
            except Exception as err:
                messagebox.showerror("Error", str(err.with_traceback(None)))
                info.status=ZipValid.CONVERT_FAILED
    convertButton.config(state=NORMAL)

# Use smallPascalCase for widgets and snake_case for others.

if __name__=='__main__':
    LOGGER.addHandler(logging.StreamHandler(stream=sys.stdout))

    app = TkinterDnD.Tk()
    # Menu
    menu = Menu(app)
    submenuHelp = Menu(menu)
    submenuHelp.add_command(label="About", command=lambda :messagebox.showinfo("About","Hello World"))

    menu.add_cascade(label="Help", menu=submenuHelp, accelerator="Ctrl+H")
    app.config(menu=menu)

    # Left Frame
    frml = Frame(app, padding=10)

    lintButton = Button(frml, text="Lint",    command = on_lint_button_clicked )
    lintButton.pack()
    convertButton = Button(frml, text="Convert", command = on_conv_button_clicked )
    convertButton.pack()
    Button(frml, text="Clear",   command = ui_action(state_path_info.clear)).pack()
    state_overwrite_compression = BooleanVar()
    Checkbutton(frml, text="Overwrite Compression", variable=state_overwrite_compression, onvalue=True, offvalue=False).pack(fill='x')
    state_debug = BooleanVar()
    Checkbutton(frml, text="Debug", variable=state_debug, onvalue=True, offvalue=False).pack(fill='x')

    frml.pack(side='left',fill='y')
    
    # Right Frame
    frmr = Frame(app, padding=10)

    Label(frmr, text="Drop files here:").pack()
    
    fileTable = Treeview(
        frmr, height=32,
        columns=['path', *PathInfo.get_columns()],
        show='headings'
    )
    for column in ['path', *PathInfo.get_columns()]:
        fileTable.heading(column, text=column.capitalize())
        fileTable.column(column, width=100)
    fileTable.column('path', width=600)

    fileTable.drop_target_register(DND_FILES)
    fileTable.dnd_bind('<<Drop>>', on_files_drop)
    scrollbarInput = Scrollbar(frmr)
    fileTable.config(yscrollcommand = scrollbarInput.set)
    scrollbarInput.config(command = fileTable.yview)
    scrollbarInput.pack(side='right', fill='y')
    fileTable.pack()

    frmr.pack(side='left')

    app.mainloop()

