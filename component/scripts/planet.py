from datetime import datetime
import re

from component import parameter as cp


def planet_moasics(mosaic):
    """from a planet mosaic name extract a meaningful short name"""

    if re.compile(cp.regex_monthly).match(mosaic):
        year, start = re.search(cp.regex_monthly, mosaic).groups()
        start = datetime.strptime(start, "%m").strftime("%b")
        res = f"{start} {year}"
    elif re.compile(cp.regex_bianual).match(mosaic):
        year, start, end = re.search(cp.regex_bianual, mosaic).groups()
        start = datetime.strptime(start, "%m").strftime("%b")
        end = datetime.strptime(end, "%m").strftime("%b")
        res = f"{start}-{end} {year}"
    else:
        raise Exception(f"{mosaic} is not an NCFI level 1 recognized mosaic name")

    return res
