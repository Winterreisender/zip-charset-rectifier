import zipfile
import os
from pathlib import Path
import warnings
import logging

SUPPORTED_FORMAT = ['.zip', '.rar']


def _polyfill_pathwalk(p :Path):
    """Path.walk polyfill for MSYS2"""
    try:
        return p.walk()
    except AttributeError as err:
        warnings.warn(UserWarning("Path.walk is not support, using os.walk instead"))
        return ( (Path(dirpath), dirnames, filenames) for dirpath, dirnames, filenames in os.walk(p) )

def zipdetect(file_path :Path, possible_encoding :set[str]={'utf8', 'shift-jis', 'gbk'}) -> str | None:
    for encoding in possible_encoding:
        if ziplint(file_path, encoding):
            return encoding
    return None

def ziplint(file_path :Path, encoding :str='utf8', password :bytes | None = None) -> bool:
    match file_path.suffix.lower():
        case ".zip":
            try:
                with zipfile.ZipFile(file_path, 'r', metadata_encoding=encoding) as f:
                    assert f.testzip() is None, f'{file_path}:{f.testzip()} is broken!'
                    for i in f.namelist():
                        i
            except UnicodeDecodeError as err:
                return False
        case ".rar":
            import rarfile
            try:
                with rarfile.RarFile(file_path, mode='r', charset=encoding) as f:
                    if f.needs_password() and (password is not None):
                        f.setpassword(password)
                    assert f.testzip() is None, f'{file_path}:{f.testrar()} is broken!'
                    for i in f.namelist():
                        i
            except UnicodeDecodeError as err:
                return False
        case _:
            raise Exception(f"Unsupport format: {file_path.suffix}")
    return True

def zipconv(file_path :Path, output_path :Path, decoding :str='shift-jis', password :bytes | None = None, force_deflated=False, tmpdir :Path=Path("./out")):
    logger = logging.getLogger("zipconv")

    assert not any(tmpdir.iterdir()), 'tmpdir not empty!'

    # Decompress
    compression, compresslevel = zipfile.ZIP_DEFLATED, 3
    match file_path.suffix:
        case ".zip":
            with zipfile.ZipFile(file_path, 'r', metadata_encoding=decoding, strict_timestamps=False) as f:
                if password is not None:
                    f.setpassword(password)
                assert f.testzip() is None, f'Unconverted {file_path}:{f.testzip()} is broken!'
                compression,compresslevel = f.compression,f.compresslevel
                f.extractall(tmpdir)
        case ".rar":
            import rarfile
            with rarfile.RarFile(file_path, mode='r', charset=decoding) as f:
                assert f.testrar() is None, f'Unconverted {file_path}:{f.testrar()} is broken!'
                if f.needs_password() and (password is not None):
                    f.setpassword(password)
                f.extractall(tmpdir)
        case _:
            raise Exception(f"Unsupport format: {file_path.suffix}")

    # Re-compress
    if force_deflated:
        compression, compresslevel = zipfile.ZIP_DEFLATED, 5
    logger.debug(f'{compression=}, {compresslevel=}')
    with zipfile.ZipFile(output_path, 'w', strict_timestamps=False, compression=compression, compresslevel=compresslevel) as f:
        for dirpath, dirnames, filenames in _polyfill_pathwalk(tmpdir):
            for dirname in dirnames:
                f.mkdir(str((dirpath/dirname).relative_to(tmpdir)))
            for filename in filenames:
                filepath = dirpath/filename
                f.write(dirpath/filename, arcname=filepath.relative_to(tmpdir))
