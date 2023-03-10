import os.path
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import re
from os.path import exists
import glob
import logging
from pidng.core import RPICAM2DNG
import cv2
from process_raw import DngFile


module_logger = logging.getLogger('3dModelApp.utilities')


def cleanfolder(path, ext = "*.*"):
    """
    cleanup transfer directory either via menu option or when pics are taken.
    """
    trail = os.path.join(path, '')
    for f in glob.glob(f"{trail}{ext}"):
        os.remove(f)


def get_ip_address():
    # host = socket.gethostname()
    ipnum = subprocess.check_output(["hostname", "-I"]).decode("utf-8")
    return ipnum.split()[0].strip()


def tryparse(string, base=10):
    """
        Usage:>>> if (n := tryparse("123")) is not None:
    ...     print(n)
    ...
    123
    if (n := tryparse("abc")) is None:
    ...     print(n)
    None
    """

    try:
        return int(string, base=base)
    except ValueError:
        return None


def copyfiles(src_path, trg_path, just_single_pic=False):
    """
    while copying files if a file exists, increment till it doesnt' appear.
    """
    filecnt = 0

    new_name = src_path
    dest_file = trg_path

    if just_single_pic == False:
        found = exists(dest_file)
        while found:
            new_name = re.sub(
                '(_photo)([0-9]{2})', increment, f'{dest_file}')
            dest_file = new_name
            found = exists(dest_file)

    shutil.copy(f'{src_path}', dest_file)
    module_logger.info(f'Copied file: {dest_file}')
    convertpics(dest_file)
    filecnt += 1
    return new_name


def convertpics(image):
    """
    Converts raw images in jpg format to DNG that can be used in RawThereppe for conversion into TIFF
    """
    source = os.path.dirname(image)
    todng = RPICAM2DNG()
    dngDestPath = os.path.join(source, "dng")
    jpgDestPath = os.path.join(source, "jpg")
   
    convertedname = todng.convert(image)
    module_logger.info(f"Converted: {image}")
    dngname = os.path.join(dngDestPath, os.path.basename(convertedname))
    jpgname = os.path.join(jpgDestPath, os.path.basename(image))
    shutil.move(os.path.join(source, os.path.basename(convertedname)), dngname)

    #convert dng to jpg for display in grid
    dng = DngFile.read(dngname)
    rgb1 = dng.postprocess()  # demosaicing ... converts raw camera image to jpg
    cv2.imwrite(jpgname, rgb1[:, :, ::-1])


def increment(num):
    # Return the first match which is 'E'. Return the 2nd match + 1 which is 'x + 1'
    return num.group(1) + str(int(num.group(2)) + 1).zfill(2)


def getsocket():
    # regarding socket.IP_MULTICAST_TTL
    # ---------------------------------
    # for all packets sent, after two hops on the network the packet will not
    # be re-sent/broadcast (see https://www.tldp.org/HOWTO/Multicast-HOWTO-6.html)
    MULTICAST_TTL = 1

    sock = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP,
                    socket.IP_MULTICAST_TTL, MULTICAST_TTL)
    
    return sock
