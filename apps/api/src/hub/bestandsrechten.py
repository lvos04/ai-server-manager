"""Privébestanden op POSIX en TrueNAS-datasets met een overgeërfde NFSv4-ACL."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def _nfs4_acl(fd: int) -> bool:
    for naam in ("system.nfs4_acl_xdr", "system.nfs4_acl"):
        try:
            if os.getxattr(fd, naam):
                return True
        except OSError:
            continue
    return False


def prive_rechten(fd: int, mode: int, eigenaar: int, *, nieuw: bool = False) -> bool:
    """Controleer dezelfde inode die gelezen of beschreven wordt. Geeft aan of chmod is uitgevoerd."""
    st = os.fstat(fd)
    juist_type = stat.S_ISDIR(st.st_mode) if mode == 0o700 else stat.S_ISREG(st.st_mode)
    if not juist_type or st.st_uid != eigenaar or st.st_mode & stat.S_IWOTH:
        raise PermissionError("Onveilig bestandstype, eigenaar of schrijfrecht voor anderen.")
    if not nieuw and stat.S_IMODE(st.st_mode) == mode:
        return False
    try:
        os.fchmod(fd, mode)
    except PermissionError:
        if not _nfs4_acl(fd):
            raise
        return False
    return True


def prive_map(path: Path, eigenaar: int, *, postgres: bool = False) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY)
    try:
        prive_rechten(fd, 0o700, eigenaar)
        if postgres and stat.S_IMODE(os.fstat(fd).st_mode) not in (0o700, 0o750):
            raise PermissionError("PostgreSQL vereist maprechten 0700 of 0750.")
    finally:
        os.close(fd)
