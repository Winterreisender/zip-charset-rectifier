#!/bin/env python3

import argparse
from libzipcharsetconv import zipconv, ziplint
from pathlib import Path
import random
import tempfile
import shutil

TMP_DIR=None

def should_exist(exist_code :int = 0):
    if TMP_DIR is not None:
        TMP_DIR.cleanup()
    exit(exist_code)

if __name__=='__main__':
    argparser = argparse.ArgumentParser("zipconv")
    argparser.add_argument("file_path", type=Path)
    argparser.add_argument("-d","--decoding", default='shift-jis', help="shift-jis (default), gbk, ...")
    argparser.add_argument("-o","--output", type=Path)
    argparser.add_argument("-O","--overwrite", action="store_true")
    argparser.add_argument("--debug",  action="store_true")
    argparser.add_argument("--force",  action="store_true", help="do not backup for overwrite, do not check if output exists")
    argparser.add_argument("-L", "--lint-only",  action="store_true", help="check if is encoded")
    argparser.add_argument("-e","--encoding", default='utf-8', help="for lint: utf-8, gbk, ...")
    argparser.add_argument("--tmpdir", type=Path)
    args = argparser.parse_args()

    # rectify args
    assert args.file_path.exists(),f"{args.file_path} not exists"
    if args.overwrite:
        args.output = args.file_path.with_suffix(".zip")
    
    if args.output is None:
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        stemsuffix=''.join(random.choices(alphabet, k=8))
        args.output=args.file_path.with_stem(f"{args.file_path.stem}_{stemsuffix}").with_suffix(".zip")
    
    if not args.force:
        assert args.output.suffix in [".zip"], f"Unsupport output format {args.output.suffix}"

        if args.overwrite:
            backup_dirname = ".zipchasetconv_backup"
            args.backup_dir = args.file_path.parent/backup_dirname
            args.backup_dir.mkdir(exist_ok=True)
            shutil.copy(str(args.file_path),str(args.backup_dir))
        else:
            assert not args.output.exists(),f"{args.output} already exists"

    if args.tmpdir is None:
        TMP_DIR = tempfile.TemporaryDirectory("_zipconv")
        args.tmpdir = Path(TMP_DIR.name)
        
    # should not raise exception below

    # call
    if args.debug:
        print(args)
    try:
        if args.lint_only:
            print(ziplint(file_path=args.file_path, encoding=args.encoding))
        else:
            zipconv(file_path=args.file_path, output_path=args.output, decoding=args.decoding, tmpdir=args.tmpdir)
    except Exception as err:
        print(err)
        args.output.unlink(missing_ok=True)
        should_exist(1)
    else:
        should_exist(0)
