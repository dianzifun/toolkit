#!/usr/bin/env python

# One script to manage my manga books.
#
# Author: Santa Zhang (santa1987@gmail.com)
#

import sys
import os
import re
import time
import traceback
import shutil
import socket
import zlib
import gzip
import zipfile
import urllib2
from urllib2 import HTTPError
from utils import *
from urllib2 import urlparse
import fancycbz

SOCKET_TIMEOUT = 30
socket.setdefaulttimeout(SOCKET_TIMEOUT)

# fetch global const values
ZIP_FILES = get_config("zip_f", "true")
if ZIP_FILES.lower().startswith("y") or ZIP_FILES.lower().startswith("t"):
    ZIP_FILES = True
else:
    ZIP_FILES = False

MANGA_FOLDER = get_config("manga_folder")


def mang_message(message):
    try:
        print message
    except:
        pass

def prepare_folder(path):
    if os.path.exists(path) == False:
        os.makedirs(path)
        mang_message("[mkdir] %s" % path)

def mang_print_help():
        print """manga.py: manage my manga books
usage: manga.py <command>
available commands:

    check-corrupt        check for corrupt zip files and images
    check-cruft          find useless .DS_Store, Thumb.db files
    check-missing        find possible missing files
    check-origin [dir]   check origin manga server to check if manga archives are healthy
    download             download a manga book
    download-reverse     download a manga book, in reverse order
    download-tieba       download from baidu tieba
    help                 display this help message
    list-library         list contents in library
    pack-all             packup all manga books
    server               start SimpleHTTPServer for ComicGlass on iOS
    stat                 state info about all manga book
    update               update specified managed manga books
    update-all           update all managed manga books

author: Santa Zhang (santa1987@gmail.com)"""

def mg_stat():
    zip_cnt = 0
    img_cnt = 0
    zip_total_size = 0
    img_total_size = 0
    max_img_per_zip = 0
    scan_counter = 0
    max_img_zip_fn = ""
    for root, dirnames, fnames in os.walk(MANGA_FOLDER):
        for fn in fnames:
            fpath = os.path.join(root, fn)
            if not fpath.lower().endswith(".zip"):
                continue
            this_img_cnt = 0
            zip_cnt += 1
            zip_total_size += os.stat(fpath).st_size
            zf = None
            try:
                zf = ZipFile(fpath)
            except:
                write_log("[failure] failed to open zip file: '%s'" % fpath)
                continue
            for zinfo in zf.infolist():
                if is_image(zinfo.filename):
                    img_cnt += 1
                    this_img_cnt += 1
                    img_total_size += zinfo.file_size
            scan_counter += 1
            if scan_counter % 100 == 0:
                print "%d manga archives checked\r" % scan_counter
            if max_img_per_zip < this_img_cnt:
                max_img_per_zip = this_img_cnt
                max_img_zip_fn = fpath
    if scan_counter % 100 != 0:
        print "%d manga archives checked\r" % scan_counter
    print
    print "%d zip archives" % zip_cnt
    print "%s total zip size" % pretty_fsize(zip_total_size)
    print "%d images" % img_cnt
    print "%s total image size" % pretty_fsize(img_total_size)
    print "max: %d images in one zip (%s)" % (max_img_per_zip, max_img_zip_fn)


def mg_check_cruft():
    scan_counter = 0
    for root, dirnames, fnames in os.walk(MANGA_FOLDER):
        for fn in fnames:
            fpath = os.path.join(root, fn)
            if not fpath.lower().endswith(".zip"):
                continue
            zf = ZipFile(fpath)
            has_cruft = False
            cruft_fn = ""
            for zinfo in zf.infolist():
                test_str = zinfo.filename.lower()
                if test_str.endswith(".ds_store") or test_str.endswith("thumbs.db") or test_str.endswith(".txt") or test_str.endswith(".url")  or test_str.endswith(".html") or test_str.endswith(".db") or test_str.endswith(".nfo") or test_str.endswith(".sfv") or test_str.endswith(".jar") or test_str.endswith("housekeeper.crc32") or test_str.endswith(".jp") or test_str.endswith(".ion") or test_str.endswith(".doc"):
                    has_cruft = True
                    cruft_fn = zinfo.filename
                    break
            if has_cruft:
                write_log("[warning] has cruft file: '%s' (curft='%s')" % (fpath, cruft_fn))
            scan_counter += 1
            if scan_counter % 100 == 0:
                print "%d manga archives checked\r" % scan_counter
    if scan_counter % 100 != 0:
        print "%d manga archives checked\r" % scan_counter


def extract_numbers(str):
    nums = []
    s = ""
    for c in str:
        if c.isdigit():
            s += c
        elif s != "":
            nums += int(s),
            s = ""
    if s != "":
        nums += s,
    return nums


def remove_continuous_pages(pages):
    if len(pages) < 5:
        return pages
    idx = 0
    idx2 = 1
    while idx2 < len(pages):
        if pages[idx2] == pages[idx2 - 1] + 1:
            pass
        else:
            if idx2 - idx >= 5:
                # do crop
                pages = pages[:idx] + pages[idx2 + 1:]
            idx = idx2
        idx2 += 1
    if idx2 - idx >= 5:
        pages = pages[:idx] + pages[idx2 + 1:]
    return pages


def mg_check_missing():
    # very inaccurate algorithm
    scan_counter = 0
    for root, dirnames, fnames in os.walk(MANGA_FOLDER):
        for fn in fnames:
            fpath = os.path.join(root, fn)
            if not fpath.lower().endswith(".zip"):
                continue
            zf = None
            try:
                zf = ZipFile(fpath)
            except:
                write_log("[failure] error opening zip file: '%s'" % fpath)
                continue
            all_nums = set()
            page_nums = set()
            for zinfo in zf.infolist():
                nums = extract_numbers(zinfo.filename)
                for n in nums:
                    all_nums.add(n)
                if len(nums) > 0 and nums[-1] < 300:
                    page_nums.add(nums[-1])
            if len(page_nums) > 0:
                missing = []
                for p in range(min(page_nums), max(page_nums)):
                    if not p in all_nums:
                        missing += p,
                if len(missing) >= len(page_nums):
                    pass # too much missing, which is unlikely
                elif len(missing) > 0:
                    # remove continuous pages
                    missing.sort()
                    missing = remove_continuous_pages(missing)
                    if len(missing) > 0:
                        write_log("[warning] (inaccurate!) '%s' possibly missing pages: %s" % (fpath, ", ".join(map(str, missing))))
            scan_counter += 1
            if scan_counter % 100 == 0:
                print "%d manga archives checked\r" % scan_counter
    if scan_counter % 100 != 0:
        print "%d manga archives checked\r" % scan_counter

def mang_is_image(fname):
    return is_image(fname)


def folder_contains_images(dirpath):
    for fn in os.listdir(dirpath):
        if mang_is_image(fn):
            return True
    return False

def mang_ensure_manga_packed_walker(arg, dirname, fnames):
    has_image = False
    has_subdir = False
    archive_name = os.path.abspath(dirname) + ".zip"
    for fn in fnames:
        fpath = dirname + os.path.sep + fn
        if os.path.isdir(fpath):
            has_subdir = True
            continue
        if mang_is_image(fn):
            has_image = True
        if fn == "NOT_FINISHED" or fn == "ERROR":
            # a bad folder
            print "found a bad folder, not zipping it"
            if os.path.exists(archive_name):
                print "zip archive already exists, removing folder"
                shutil.rmtree(dirname)
            return
    if has_subdir == True:
        print "has subdir, not zipping it"
        return
    if has_image == False:
        print "found an empty folder, skipping it"
        return

    # do zipping
    print "zipping"

    def ignore_func(fn):
        fn = fn.lower()
        return fn.endswith(".ds_store") or fn.endswith("thumbs.db") or fn.endswith(".txt") or fn.endswith(".url") or fn.endswith(".html") or fn.endswith(".db") or fn.endswith(".nfo") or fn.endswith(".sfv") or fn.endswith(".jar") or fn.endswith("housekeeper.crc32") or fn.endswith(".jp") or fn.endswith(".ion") or fn.endswith(".doc")

    if zipdir(dirname, archive_name, ignore_func) == True:
        shutil.rmtree(dirname)
        print "zip done, removing original folder"
    else:
        print "[error] failed to create zip archive!"

def mang_ensure_manga_packed(root_dir=None):
    if root_dir == None:
        return
    mang_message("[zip] %s" % root_dir)
    if ZIP_FILES == True:
        mang_message("packing manga books")
        os.path.walk(root_dir, mang_ensure_manga_packed_walker, None)

def mang_pack_all():
    for entry in os.listdir(MANGA_FOLDER):
        fpath = os.path.join(MANGA_FOLDER, entry)
        if os.path.isdir(fpath):
            mang_ensure_manga_packed(fpath)

def gunzip_content(data):
    try:
        gz_f = open("/tmp/manga.py.tmp.gz", "wb")
        gz_f.write(data)
        gz_f.close()
        gz_f = gzip.open("/tmp/manga.py.tmp.gz", "r")
        orig_data = gz_f.read()
        gz_f.close()
    finally:
        os.remove("/tmp/manga.py.tmp.gz")
    return orig_data

def mang_download_manhua178(manga_url, **opt):
    print "[toc] %s" % manga_url
    root_page = manga_url
    page_src = urllib2.urlopen(root_page).read()
    idx = page_src.find("var g_comic_name = \"")
    if idx < 0:
        # fall back to gzip
        page_src = gunzip_content(page_src)
        idx = page_src.find("var g_comic_name = \"")
        if idx < 0:
            # failure again!
            raise "failed to locate comic name ('g_comic_name')!"
    idx += 20

    idx2 = page_src.index("\r\n", idx) - 2
    comic_name = page_src[idx:idx2].replace(" ", "").decode("utf-8")
    comic_name = comic_name.strip()

    idx = page_src.index("cartoon_online_border")
    idx = page_src.index("<ul>", idx)
    idx2 = page_src.index("<script type=\"", idx)
    toc_src = page_src[idx:idx2]
    toc_src_split = toc_src.split("\r\n")
    toc_arr = []
    for sp in toc_src_split:
        idx = sp.find('<li><a title="')
        if idx == -1:
            continue
        idx += 14
        idx2 = sp.find('" href="', idx)
        title = sp[idx:idx2]
        idx = idx2 + 8
        idx2 = sp.find('"', idx)
        href = sp[idx:idx2]
        if title.strip() == "":
            continue
        toc_arr += (title, href),

    # download new chapters if necessary
    if opt.has_key("reverse") and opt["reverse"] == True:
        toc_arr.reverse()

    comic_name = comic_name.replace('/', "~")
    comic_folder_path = MANGA_FOLDER + os.path.sep + comic_name + "(acg178)"
    prepare_folder(comic_folder_path)
    link_f = open(comic_folder_path + os.path.sep + "downloaded_from.txt", "w")
    print "writing download url file"
    link_f.write(manga_url + "\n")
    link_f.close()

    # now download chapter
    for chap in toc_arr:
        try:
            chap_title = chap[0].decode("utf-8")
            chap_title = chap_title.replace('/', "~")
            chap_title = chap_title.strip()
            chap_href = chap[1]
            chapter_folder_path = comic_folder_path + u"/" + chap_title

            # pass chapter if zip exists or the folder does not have NOT_FINISHED & ERROR file
            chapter_zip_fn = comic_folder_path + u"/" + chap_title + ".zip"
            if os.path.exists(chapter_zip_fn):
                print "zip exists, pass chapter"
                continue
            else:
                print "zip not exists!"

            prepare_folder(chapter_folder_path)

            error_log_fn = chapter_folder_path + u"/ERROR"
            not_finished_fn = chapter_folder_path + u"/NOT_FINISHED"
            if os.path.exists(error_log_fn) == False and os.path.exists(not_finished_fn) == False and folder_contains_images(chapter_folder_path):
                print "chapter already downloaded, skip"
                mang_ensure_manga_packed(comic_folder_path)
                continue
            else:
                print "still have to download chapter"

            idx = root_page.rfind("/")
            idx = root_page[0:idx].rfind("/")
            base_url = root_page[0:idx]
            if chap_href.startswith("http://"):
                chap_url = chap_href
            else:
                chap_url = base_url + chap_href[2:]
            chap_url = chap_url.replace(" ", "%20")

            print "[chap url] %s" % chap_url

            chap_src = urllib2.urlopen(chap_url).read()
            idx = chap_src.find("var pages")
            if idx < 0:
                # first fall back, gzipped content
                chap_src = gunzip_content(chap_src)
            idx = chap_src.find("var pages")
            if idx < 0:
                # second fall back
                raise Exception("'var pages' not found!")
            idx += 13
            idx2 = chap_src.find("\r\n", idx) - 2
            comic_pages_src = chap_src[idx:idx2].replace("\\/", "/")
            comic_pages_url = eval(comic_pages_src)

            # remove possibly existing error log file
            if os.path.exists(error_log_fn):
                os.remove(error_log_fn)

            # create a place holder
            open(not_finished_fn, "w").close()

            chapter_download_ok = True # whether the chapter is successfully downloaded
            for pg in comic_pages_url:
                try:
                    full_pg = (base_url + "/imgs/" + pg)
                    idx = full_pg.rfind("/") + 1
                    leaf_nm = full_pg[idx:]
                    print leaf_nm
                    fn = comic_folder_path + u"/" + chap_title + u"/" + leaf_nm.decode("unicode_escape")
                    mang_message(fn)
                    down_filename = fn
                    if os.path.exists(down_filename):
                        mang_message("[pass] %s" % down_filename)
                        continue
                    down_f = None
                    full_pg_unescaped = full_pg.decode("unicode_escape").encode("utf-8")
                    full_pg_unescaped = full_pg_unescaped.replace(" ", "%20")
                    try:
                        down_data = urllib2.urlopen(full_pg_unescaped).read()
                        down_f = open(fn + u".tmp", "wb")
                        down_f.write(down_data)
                        down_f.close()
                        shutil.move(fn + u".tmp", fn)
                    except HTTPError, e:
                        print "download failure!"
                        if down_f != None:
                            down_f.close()
                        if os.path.exists(fn + u".tmp"):
                            os.remove(fn + u".tmp")
                        err_log_f = open(error_log_fn, "a")
                        try:
                            err_log_f.write("failed to download: %s\n" % fn)
                        except:
                            err_log_f.write("failed to download from: %s\n" % full_pg_unescaped)
                        finally:
                            err_log_f.close()
                        chapter_download_ok = False
                except:
                    traceback.print_exc()
                    err_log_f = open(error_log_fn, "a")
                    try:
                        err_log_f.write("failed to download: %s\n" % pg)
                    finally:
                        err_log_f.close()
                    chapter_download_ok = False

            # remove the place holder
            if os.path.exists(not_finished_fn):
                os.remove(not_finished_fn)

            # pack the folder if necessary
            mang_ensure_manga_packed(comic_folder_path)

        except:
            traceback.print_exc()
            time.sleep(1)


def bengou_down_page(page_url, down_dir, page_id):
    ok = True
    print "[down] id=%d, url=%s" % (page_id, page_url)
    page_src = urllib2.urlopen(page_url).read()

    # get pic url:
    idx = page_src.index('"disp"')
    idx = page_src.index('http://', idx)
    idx2 = page_src.index('"', idx)
    img_url = page_src[idx:idx2]
    print "[img] %s" % img_url

    error_log_fn = os.path.join(down_dir, "ERROR")

    # download pic:
    img_ext = img_url[img_url.rfind("."):]
    pic_fn = down_dir + os.path.sep + ("%03d" % page_id) + img_ext
    if os.path.exists(pic_fn):
        try:
            print "[skip] %s" % pic_fn
        except:
            pass
    else:
        pic_f = None
        try:
            pic_data = urllib2.urlopen(img_url).read()
            pic_f = open(pic_fn + u".tmp", "wb")
            pic_f.write(pic_data)
            pic_f.close()
            shutil.move(pic_fn + u".tmp", pic_fn)
        except HTTPError, e:
            ok = False
            if pic_f != None:
                pic_f.close()
            if os.path.exists(pic_fn + u".tmp"):
                os.remove(pic_fn + u".tmp")
            print "[failure] %s" % page_url
            err_log_f = open(error_log_fn, "a")
            try:
                err_log_f.write("failed to download: %s\n" % pic_fn)
            except:
                err_log_f.write("failed to download from: %s\n" % img_url)
            finally:
                err_log_f.close()
    return ok

def bengou_down_vol(vol_url, down_dir):
    all_ok = True
    print "[vol-url] %s" % vol_url
    page_src = urllib2.urlopen(vol_url).read()
    root_url = vol_url[:vol_url.rfind("/")]

    # get pic tree
    idx = page_src.index("var pictree")
    idx2 = page_src.index(";", idx)
    pictree_src = page_src[(idx + 14):idx2]
    exec "pictree=%s" % pictree_src
    counter = 1
    error_log_fn = down_dir + u"/ERROR"
    for pic in pictree:
        try:
            ok = bengou_down_page(root_url + "/" + pic, down_dir, counter)
            if ok == False:
                all_ok = False
        except:
            all_ok = False
            traceback.print_exc()
            f = open(error_log_fn, "a")
            f.write("failed to download page %d, url=%s\n" % (counter, root_url + "/" + pic))
            f.close()
            time.sleep(1)
        finally:
            counter += 1
    return all_ok


def mang_download_bengou(index_url, **opt):
    page_src = urllib2.urlopen(index_url).read()
    index_root = index_url[:index_url.rfind("/")]
    # find manga name
    idx = page_src.index("sectioninfo ")
    idx = page_src.index("title=", idx)
    idx2 = page_src.index('"', idx + 7)
    comic_name = page_src[(idx + 7):idx2].decode("utf-8")
    mang_message(comic_name)
    mang_message("[index-url] %s" % index_url)

    comic_folder_path = MANGA_FOLDER + os.path.sep + comic_name + "(bengou)"

    # find the volumes
    idx = page_src.index("mhlist")
    #idx2 = page_src.index("</div>", idx)
    # This page has sub-div in the li tags:
    #   http://www.bengou.com/080819/hzw0008081910/index.html
    idx2 = page_src.index('<br class="clearall"', idx)
    mhlist_src = page_src[idx:idx2]


    manga_list = []
    idx = 0
    idx2 = 0
    while True:
        idx = mhlist_src.find("href", idx2)
        if idx < 0:
            break
        idx2 = mhlist_src.index("target", idx)
        vol_url = index_root + "/" + mhlist_src[(idx + 6):(idx2 - 2)]
        idx = mhlist_src.find("span", idx2)
        idx2 = mhlist_src.index("</span>", idx)
        vol_name = mhlist_src[(idx + 17):(idx2)].decode("utf-8")
        manga_list += (vol_name, vol_url),

    # download new chapters if necessary
    if opt.has_key("reverse") and opt["reverse"] == True:
        manga_list.reverse()

    for vol_name, vol_url in manga_list:
        mang_message(vol_name)
        mang_message("[vol-page] %s" % vol_url)
        chapter_folder_path = os.path.join(comic_folder_path, vol_name)
        chapter_zip_fn = chapter_folder_path + ".zip"

        if os.path.exists(chapter_zip_fn):
            print "zip exists, pass chapter"
            continue
        else:
            print "zip not exists!"

        prepare_folder(chapter_folder_path)

        error_log_fn = chapter_folder_path + u"/ERROR"
        not_finished_fn = chapter_folder_path + u"/NOT_FINISHED"
        if os.path.exists(error_log_fn) == False and os.path.exists(not_finished_fn) == False and folder_contains_images(chapter_folder_path):
            print "chapter already downloaded, skip"
            mang_ensure_manga_packed(comic_folder_path)
            continue
        else:
            print "still have to download chapter"

        # remove possibly existing error log file
        if os.path.exists(error_log_fn):
            os.remove(error_log_fn)

        # create a place holder
        open(not_finished_fn, "w").close()

        all_ok = bengou_down_vol(vol_url, chapter_folder_path)
        if all_ok == False:
            open(error_log_fn, "w").close()

        # remove the place holder
        if os.path.exists(not_finished_fn):
            os.remove(not_finished_fn)

        # pack the folder if necessary
        mang_ensure_manga_packed(comic_folder_path)




def comic131_down_vol(vol_url, down_dir):
    all_ok = True
    print "[vol-url] %s" % vol_url
    page_src = urllib2.urlopen(vol_url).read()
    root_url = vol_url[:vol_url.rfind("/")]

    # get total count
    idx = page_src.index("var total")
    idx2 = page_src.index(";", idx)
    total_cnt = int(page_src[idx + 12 : idx2])

    page_url_prefix = vol_url[:vol_url.rfind("/")]
    error_log_fn = os.path.join(down_dir, "ERROR")
    for cnt in range(1, total_cnt + 1):
        if os.path.exists(os.path.join(down_dir, "%03d.jpg" % cnt)) or os.path.exists(os.path.join(down_dir, "%03d.png" % cnt)):
            mang_message("[skip] page %d" % cnt)
            continue

        page_url = page_url_prefix + "/" + str(cnt) + ".html"
        page_src = urllib2.urlopen(page_url).read()
        idx = page_src.index('onclick="NextPage();" src=')
        idx += 27
        idx2 = page_src.index('"', idx)
        pic_url = page_src[idx:idx2]
        pic_fn = ("%03d" % cnt) + pic_url[pic_url.rfind('.'):]
        pic_fpath = os.path.join(down_dir, pic_fn)

        mang_message("[pic] %s => %s" % (pic_url, pic_fpath))

        pic_f = None
        try:
            pic_data = urllib2.urlopen(pic_url).read()
            pic_f = open(pic_fpath + ".tmp", "wb")
            pic_f.write(pic_data)
            pic_f.close()
            shutil.move(pic_fpath + ".tmp", pic_fpath)
        except:
            all_ok = False
            if pic_f != None:
                pic_f.close()
            if os.path.exists(pic_fpath + ".tmp"):
                os.remove(pic_fpath + ".tmp")
            print "[failure] %s" % pic_url

            traceback.print_exc()
            f = open(error_log_fn, "a")
            f.write("failed to download page %d, url=%s\n" % (cnt, pic_url))
            f.close()
            time.sleep(1)

    return all_ok


def mang_download_comic131(index_url, **opt):
    page_src = urllib2.urlopen(index_url).read()

    # find manga name
    idx = page_src.index('<p class="name"')
    idx = page_src.index('<strong>', idx) + 8
    idx2 = page_src.index('</strong>', idx)
    comic_name = page_src[idx:idx2]
    mang_message(comic_name)

    comic_folder_path = MANGA_FOLDER + os.path.sep + comic_name + "(comic131)"
    mang_message(comic_folder_path)

    # find the volumes
    idx = page_src.index('<ul class="list-directory"')
    idx2 = page_src.index('</li></ul>', idx)
    mhlist_src = page_src[idx:idx2]
    manga_list = []
    idx = 0
    idx2 = 0
    while True:
        idx = mhlist_src.find('href="', idx2)
        if idx < 0:
            break
        idx += 6
        idx2 = mhlist_src.find('html"', idx) + 4
        href = mhlist_src[idx:idx2]
        idx = mhlist_src.find(">", idx2)
        idx += 1
        idx2 = mhlist_src.find("<", idx)
        chap_name = mhlist_src[idx:idx2]
        manga_list += (chap_name, href),

    # download new chapters if necessary
    if opt.has_key("reverse") and opt["reverse"] == True:
        manga_list.reverse()

    for vol_name, vol_url in manga_list:
        mang_message(vol_name)
        mang_message("[vol-page] %s" % vol_url)
        chapter_folder_path = os.path.join(comic_folder_path, vol_name)
        print chapter_folder_path
        chapter_zip_fn = chapter_folder_path + ".zip"

        if os.path.exists(chapter_zip_fn):
            print "zip exists, pass chapter"
            continue
        else:
            print "zip not exists!"

        prepare_folder(chapter_folder_path)

        error_log_fn = os.path.join(chapter_folder_path, "ERROR")
        not_finished_fn = os.path.join(chapter_folder_path, "NOT_FINISHED")
        if os.path.exists(error_log_fn) == False and os.path.exists(not_finished_fn) == False and folder_contains_images(chapter_folder_path):
            print "chapter already downloaded, skip"
            mang_ensure_manga_packed(comic_folder_path)
            continue
        else:
            print "still have to download chapter"

        # remove possibly existing error log file
        if os.path.exists(error_log_fn):
            os.remove(error_log_fn)

        # create a place holder
        open(not_finished_fn, "w").close()

        all_ok = comic131_down_vol(vol_url, chapter_folder_path)
        if all_ok == False:
            open(error_log_fn, "w").close()

        # remove the place holder
        if os.path.exists(not_finished_fn):
            os.remove(not_finished_fn)

        # pack the folder if necessary
        mang_ensure_manga_packed(comic_folder_path)





def mang_download_print_help():
    print "download a manga book"
    print "usage: manga.py download <url>"
    print "<url> is the table of contents page"

def mang_download_real(url, **opt):
    if url.startswith("http://") == False:
        url = "http://" + url
    if url.find("manhua.178.com") >= 0:
        mang_download_manhua178(url, **opt)
    elif url.find("bengou.com") >= 0:
        mang_download_bengou(url, **opt)
    elif url.find("comic.131.com") >= 0:
        mang_download_comic131(url, **opt)
    else:
        print "sorry, the manga book site is not supported!"


def mang_download(**opt):
    if len(sys.argv) <= 2:
        mang_download_print_help()
        exit()
    url = sys.argv[2]
    mang_download_real(url, **opt)


def mang_load_library():
    library_fn = os.path.join(os.path.split(__file__)[0], "manga.library")
#  print library_fn
    lib_f = open(library_fn)
    name = None
    url = None
    library = {}
    for line in lib_f.readlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        if line == "":
            if name != None and url != None:
                if library.has_key(name):
                    print "[warning] duplicate name '%s' in manga.library" % name
                library[name] = url
                name = None
                url = None
        if line.startswith("name="):
            name = line[5:]
        elif line.startswith("url="):
            url = line[4:]
    if name != None and url != None:
        if library.has_key(name):
            print "[warning] duplicate name '%s' in manga.library" % name
        library[name] = url
        name = None
        url = None
    lib_f.close()
    return library

def mang_update_all():
    library = mang_load_library()
    for manga_name in library:
        try:
            url = library[manga_name]
            print "downloading '%s' from '%s'" % (manga_name, url)
            mang_download_real(url)
        except:
            traceback.print_exc()
            time.sleep(1)

def mang_update_show_help():
    print "update specific manga books"
    print "usage: manga.py update <manga1> [manga2] [manga3]"

def mang_update():
    if len(sys.argv) <= 2:
        mang_update_show_help()
        return()
    library = mang_load_library()
    for i in range(2, len(sys.argv)):
        manga_name = sys.argv[i]
        if library.has_key(manga_name) == False:
            print "[warning] no such manga: '%s', skipping it" % manga_name
            continue
        else:
            url = library[manga_name]
            print "downloading '%s' from '%s'" % (manga_name, url)
            mang_download_real(url)


def mang_list_library():
    library = mang_load_library()
    print "library content:"
    print
    for item in library:
        print "%s => %s" % (item, library[item])
    print
    print "%d items in library" % len(library)


def bin_to_str(magic):
    l = []
    for m in magic:
        l += "%02x" % ord(m),
    return " ".join(l)

def my_zip_img_check(the_zip_file):
    for info in the_zip_file.infolist():
#        print info.filename, info.file_size
        # consider 4KB a threshold of small files
        if info.filename.endswith("/"):
            # folder
            continue
        if info.file_size < 4096 and is_image(info.filename):
            write_log("[corrupt] Possibly broken file (too small) '%s', size=%d" % (info.filename, info.file_size))
            return info.filename
        if not is_image(info.filename):
            continue
        # check if bad image
        ret = None
        zf = the_zip_file.open(info.filename, 'r')
        lower_fn = info.filename.lower()
        if lower_fn.endswith(".png"):
            magic = zf.read(4)
            if magic[1:4] != "PNG":
                ret = info.filename
                write_log("[corrupt] Possibly broken PNG: '%s', magic='%s'" % (info.filename, bin_to_str(magic)))
        if lower_fn.endswith(".gif"):
            magic = zf.read(4)
            if magic[0:3] != "GIF":
                ret = info.filename
                write_log("[corrupt] Possibly broken GIF: '%s', magic='%s'" % (info.filename, bin_to_str(magic)))
        if lower_fn.endswith(".jpg") or lower_fn.endswith(".jpeg"):
            magic = zf.read(10)
            if not (magic[6:10] == "JFIF" or magic[6:10] == "Exif" or magic[6:10] == "Phot"):
                ret = info.filename
                write_log("[corrupt] Possibly broken JPEG: '%s', magic='%s'" % (info.filename, bin_to_str(magic)))
        zf.close()
        return ret
    return None


def util_check_corrupt_zip():
    tmp_folder = get_config("tmp_folder")
    print "tmp folder:", tmp_folder
    bad_list = []
    for root, dirnames, fnames in os.walk(MANGA_FOLDER):
        for fn in fnames:
            if fn.startswith("."):
                continue
            fpath = os.path.join(root, fn)
            if fpath.lower().endswith(".zip"):
                print "checking zip file:", fpath
                the_zip_file = None
                try:
                    the_zip_file = ZipFile(fpath)
                except:
                    traceback.print_exc()
                    bad_list += (fpath, ret),
                    continue
                ret = the_zip_file.testzip()
                if ret == None:
                    ret = my_zip_img_check(the_zip_file)
                if ret is not None:
                    try:
                        print "*** first bad file in zip: %s" % ret
                        write_log("[corrupt] bad file '%s' in zip archive '%s'" % (ret, fpath))
                    except:
                        traceback.print_exc()
                    finally:
                        bad_list += (fpath, ret),
                the_zip_file.close()

    if len(bad_list) == 0:
        print "*** all files are consistent"
    else:
        print "*** corruption found:"
        for bad in bad_list:
            try:
                print "%s, %s" % (bad[0], bad[1])
            except:
                traceback.print_exc()


# used in util_check_corrupt_images_in_zip, wrap binary as a file object for PIL
class FileObjForPIL(object):

    def __init__(self, bin_data):
        self.bin_data = bin_data
        self.pos = 0

    def read(self, sz=None):
        if sz == None:
            sz = len(self.bin_data) - self.pos
        cnt = min(sz, len(self.bin_data) - self.pos)
        ret_data = self.bin_data[self.pos:(self.pos + cnt)]
        self.pos += cnt
        return ret_data

    def tell(self):
        return self.pos

    def seek(self, offset, whence=None):
        if whence == None:
            whence = os.SEEK_SET
        if whence == os.SEEK_SET:
            self.pos = offset
        elif whence == os.SEEK_CUR:
            self.pos += offset
        elif whence == os.SEEK_END:
            self.pos = len(self.bin_data) + offset
        if self.pos < 0:
            self.pos = 0
        if self.pos > len(self.bin_data):
            self.pos = len(self.bin_data)


def util_check_corrupt_images_in_zip(fpath):
    from PIL import Image
    print "checking images in zip file:", fpath
    zf = ZipFile(fpath)
    for zinfo in zf.infolist():
        if is_image(zinfo.filename.lower()):
            zobj = zf.open(zinfo.filename, "r")
            zdata = zobj.read()
            fobj = FileObjForPIL(zdata)
            vimg = Image.open(fobj)
            vimg.verify()
            zobj.close()
    zf.close()


def util_check_corrupt_images():
    tmp_folder = get_config("tmp_folder")
    print "tmp folder:", tmp_folder
    for root, dirnames, fnames in os.walk(MANGA_FOLDER):
        for fn in fnames:
            fpath = os.path.join(root, fn)
            if fpath.lower().endswith(".zip"):
                ret = util_check_corrupt_images_in_zip(fpath)


def mang_check_corrupt():
    pil_installed = False
    try:
        from PIL import Image
        pil_installed = True
    except:
        pass

    if pil_installed:
        util_check_corrupt_zip()
        util_check_corrupt_images()
    else:
        print "*** PIL not installed! only checking for corrupt zip files!"
        util_check_corrupt_zip()


def mg_check_178(dpath):
    print "[MANGA DIR] %s" % dpath
    f = open(os.path.join(dpath, "downloaded_from.txt"))
    manga_url = f.read().strip()
    f.close()
    print "[MANGA URL] %s" % manga_url

    root_page = manga_url
    page_src = urllib2.urlopen(root_page).read()
    idx = page_src.find("var g_comic_name = \"")
    if idx < 0:
        # fall back to gzip
        page_src = gunzip_content(page_src)
        idx = page_src.find("var g_comic_name = \"")
        if idx < 0:
            # failure again!
            raise "failed to locate comic name ('g_comic_name')!"
    idx += 20

    idx2 = page_src.index("\r\n", idx) - 2
    comic_name = page_src[idx:idx2].replace(" ", "").decode("utf-8")
    comic_name = comic_name.strip()

    idx = page_src.index("cartoon_online_border")
    idx = page_src.index("<ul>", idx)
    idx2 = page_src.index("<script type=\"", idx)
    toc_src = page_src[idx:idx2]
    toc_src_split = toc_src.split("\r\n")
    toc_arr = []
    for sp in toc_src_split:
        idx = sp.find('<li><a title="')
        if idx == -1:
            continue
        idx += 14
        idx2 = sp.find('" href="', idx)
        title = sp[idx:idx2]
        idx = idx2 + 8
        idx2 = sp.find('"', idx)
        href = sp[idx:idx2]
        if title.strip() == "":
            continue
        toc_arr += (title, href),

    comic_name = comic_name.replace('/', "~")
    comic_folder_path = MANGA_FOLDER + os.path.sep + comic_name + "(acg178)"

    # check chapters
    for chap in toc_arr:
        zipf = None
        try:
            chap_title = chap[0].decode("utf-8")
            chap_title = chap_title.replace('/', "~")
            chap_title = chap_title.strip()
            chap_href = chap[1]
            chapter_folder_path = comic_folder_path + u"/" + chap_title

            # pass chapter if zip exists or the folder does not have NOT_FINISHED & ERROR file
            chapter_zip_fn = comic_folder_path + u"/" + chap_title + ".zip"
            zipf = ZipFile(chapter_zip_fn)
            if not os.path.exists(chapter_zip_fn):
                print "zip not exists!"
                continue

            idx = root_page.rfind("/")
            idx = root_page[0:idx].rfind("/")
            base_url = root_page[0:idx]
            if chap_href.startswith("http://"):
                chap_url = chap_href
            else:
                chap_url = base_url + chap_href[2:]
            chap_url = chap_url.replace(" ", "%20")

            print "[CHAPTER URL] %s" % chap_url

            chap_src = urllib2.urlopen(chap_url).read()
            idx = chap_src.find("var pages")
            if idx < 0:
                # first fall back, gzipped content
                chap_src = gunzip_content(chap_src)
            idx = chap_src.find("var pages")
            if idx < 0:
                # second fall back
                raise Exception("'var pages' not found!")
            idx += 13
            idx2 = chap_src.find("\r\n", idx) - 2
            comic_pages_src = chap_src[idx:idx2].replace("\\/", "/")
            comic_pages_url = eval(comic_pages_src)

            chapter_download_ok = True # whether the chapter is successfully downloaded
            for pg in comic_pages_url:
                try:
                    full_pg = (base_url + "/imgs/" + pg)
                    idx = full_pg.rfind("/") + 1
                    leaf_nm = full_pg[idx:]

                    full_pg_unescaped = full_pg.decode("unicode_escape").encode("utf-8")
                    full_pg_unescaped = full_pg_unescaped.replace(" ", "%20")
                    response_header = getheadersonly(full_pg_unescaped)["headers"]

                    pic_size = int(response_header["Content-Length"])

                    print leaf_nm, "(%s)" % pretty_fsize(pic_size), "<==", full_pg_unescaped

                    # check page!
                    try:
                        info = zipf.getinfo(leaf_nm)
                        if info.file_size != pic_size and response_header["Content-Type"].lower().startswith("image"):
                            write_log("[failure] '%s' in '%s': fsize should be %d not %d" % (leaf_nm.encode("utf-8"), chapter_zip_fn.encode("utf-8"), pic_size, info.file_size))
                            write_log(str(response_header))
                    except KeyError:
                        write_log("[failure] checked by origin: '%s' missing in '%s'" % (leaf_nm, chapter_zip_fn))

                except:
                    traceback.print_exc()
                    time.sleep(1)

        except:
            traceback.print_exc()
            time.sleep(1)
        finally:
            if zipf != None:
                zipf.close()


class HeadRequest(urllib2.Request):
    def get_method(self):
        return 'HEAD'

def getheadersonly(url, redirections=True):
    opener = urllib2.OpenerDirector()
    opener.add_handler(urllib2.HTTPHandler())
    opener.add_handler(urllib2.HTTPDefaultErrorHandler())
    if redirections:
        # HTTPErrorProcessor makes HTTPRedirectHandler work
        opener.add_handler(urllib2.HTTPErrorProcessor())
        opener.add_handler(urllib2.HTTPRedirectHandler())
    try:
        res = opener.open(HeadRequest(url))
    except urllib2.HTTPError, res:
        pass
    res.close()
    return dict(code=res.code, headers=res.info(), finalurl=res.geturl())


def mg_check_origin():
    if len(sys.argv) > 2:
        dpath = sys.argv[2]
        if "acg178" in dpath:
            mg_check_178(dpath)
    else:
        for ent in os.listdir(MANGA_FOLDER):
            dpath = os.path.join(MANGA_FOLDER, ent)
            if not os.path.isdir(dpath):
                continue
            if "acg178" in dpath:
                try:
                    mg_check_178(dpath)
                except:
                    traceback.print_exc()
                    time.sleep(1)

def mg_tieba():
    url = raw_input("teiba url? ")
    folder = raw_input("download dir? ")
    if os.path.exists(folder) == False:
        os.makedirs(folder)
    page_src = urllib2.urlopen(url).read()
    idx = 0
    cnt = 1
    while True:
        idx = page_src.find('src=', idx)
        if idx < 0:
            break
        quot = page_src[idx + 4]
        idx2 = page_src.find(quot, idx + 5)
        try:
            target = urlparse.urlparse(page_src[idx + 5:idx2])
            if is_image(target.path):
                target_url = target.scheme + "://" + target.netloc + target.path
                print target_url
                img_fn = os.path.basename(target.path)
                local_fn = os.path.join(folder, "%03d-%s" % (cnt, img_fn))
                print local_fn
                try:
                    tmp_f = open(local_fn + ".tmp", "wb")
                    tmp_f.write(urllib2.urlopen(target_url).read())
                    tmp_f.close()
                    os.rename(local_fn + ".tmp", local_fn)
                except:
                    traceback.print_exc()
                    time.sleep(1)
                cnt += 1
        finally:
            idx = idx2


def mang_serve():
    port = get_config("http_svr_port")
    manga_folder = MANGA_FOLDER
    os.chdir(manga_folder)
    os.system("python -m SimpleHTTPServer %s" % port)

def ensure_manga_folder():
    if os.path.exists(MANGA_FOLDER) == False:
        print "manga folder '%s' not exists, quit now!" % MANGA_FOLDER
        exit(1)

def mg_webview():
    try:
        import tornado.ioloop
        import tornado.web
        import urllib
        import cgi
    except:
        print "tornado web server not installed! quit now!"
        return

    f = open(os.path.join(os.path.dirname(__file__), "manga.webview.html"))
    webview_template = f.read()
    f.close()

    class MangaHandler(tornado.web.RequestHandler):
        def get_fs_path(self, req_path):
            splt = req_path.split('/')
            p = ''
            for seg in splt:
                seg = urllib.unquote(seg)
                if seg != '':
                    if p == '':
                        p = seg
                    else:
                        p = p + os.path.sep + seg
            fs_path = os.path.join(MANGA_FOLDER, p)
            return fs_path

        def render_dir(self, fs_path):
            if self.request.path != '/':
                self.write("<a href='..'>Parent Dir</a>\n")
            self.write("<ul>\n")
            fn_list = os.listdir(fs_path)
            fn_list.sort()
            for fn in fn_list:
                if fn.startswith("."):
                    continue
                if fn == "download_from.txt" or fn == "housekeeper.crc32":
                    continue
                if self.request.path.endswith("/"):
                    sub_link = self.request.path + fn
                else:
                    sub_link = self.request.path + "/" + fn
                self.write("  <li><a href='%s'>" % sub_link)
                self.write(cgi.escape(fn))
                self.write("</a></li>\n")
            self.write("</ul>\n")

        def get_zip_pic_list(self, zip_fpath):
            pic_lst = []
            with ZipFile(zip_fpath, 'r') as zf:
                for zi in zf.infolist():
                    zi_lower = zi.filename.lower()
                    if zi_lower.endswith(".jpg") or zi_lower.endswith(".jpeg") or zi_lower.endswith(".png"):
                        pic_lst += zi.filename,
            pic_lst.sort()
            return pic_lst


        def render_book(self, fs_path):
            img_fn = self.get_argument('img_fn', '')
            if img_fn == '':
                # viewer page
                html = webview_template
                html = html.replace("<%img_list%>", repr(self.get_zip_pic_list(fs_path)))
                book_fn = fs_path.split(os.path.sep)[-1]
                html = html.replace("<%title%>", book_fn)
                html = html.replace("<%book_path%>", self.request.path)
                book_dir = "/".join(self.request.path.split("/")[:-1])
                html = html.replace("<%book_dir_href%>", book_dir)
                last_book_name = ""
                next_book_name = ""
                fn_list = os.listdir(os.path.dirname(fs_path))
                fn_list.sort()
                book_list = []
                for fn in fn_list:
                    if fn.endswith(".zip"):
                        book_list += fn,
                idx = book_list.index(book_fn)
                if idx - 1 >= 0:
                    last_book_name = book_list[idx - 1]
                if idx + 1 < len(book_list):
                    next_book_name = book_list[idx + 1]
                html = html.replace("<%last_book_name%>", last_book_name)
                html = html.replace("<%last_book_href%>", book_dir + "/" + last_book_name)
                html = html.replace("<%next_book_name%>", next_book_name)
                html = html.replace("<%next_book_href%>", book_dir + "/" + next_book_name)
                self.write(html)
            else:
                # image blob
                with ZipFile(fs_path, "r") as zf:
                    lower_fn = img_fn.lower()
                    if lower_fn.endswith(".jpg") or lower_fn.endswith(".jpeg"):
                        self.add_header("Content-Type", "image/jpeg")
                    elif lower_fn.endswith(".png"):
                        self.add_header("Content-Type", "image/png")
                    self.write(zf.open(img_fn).read())


        def get(self):
            fs_path = self.get_fs_path(self.request.path)
            if not fs_path.startswith(MANGA_FOLDER):
                self.send_error(403)
                return
            if not os.path.exists(fs_path):
                self.send_error(404)
            elif os.path.isdir(fs_path):
                self.render_dir(fs_path)
            elif fs_path.lower().endswith(".zip"):
                # render manga
                self.render_book(fs_path)
            else:
                # not supported
                self.send_error(416) # bad media type


    application = tornado.web.Application([
        (r".*", MangaHandler),
    ])

    webview_port = int(get_config("webview_port"))
    print "webview server running on port %d" % webview_port
    application.listen(webview_port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "help":
        mang_print_help()
    elif sys.argv[1] == "check-corrupt":
        ensure_manga_folder()
        mang_check_corrupt()
    elif sys.argv[1] == "check-cruft":
        ensure_manga_folder()
        mg_check_cruft()
    elif sys.argv[1] == "check-missing":
        ensure_manga_folder()
        mg_check_missing()
    elif sys.argv[1] == "check-origin":
        ensure_manga_folder()
        mg_check_origin()
    elif sys.argv[1] == "download":
        ensure_manga_folder()
        mang_download()
    elif sys.argv[1] == "download-reverse":
        ensure_manga_folder()
        mang_download(reverse=True)
    elif sys.argv[1] == "download-tieba":
        ensure_manga_folder()
        mg_tieba()
    elif sys.argv[1] == "list-library":
        mang_list_library()
    elif sys.argv[1] == "pack-all":
        ensure_manga_folder()
        mang_pack_all()
    elif sys.argv[1] == "server":
        ensure_manga_folder()
        mang_serve()
    elif sys.argv[1] == "stat":
        ensure_manga_folder()
        mg_stat()
    elif sys.argv[1] == "update":
        ensure_manga_folder()
        mang_update()
    elif sys.argv[1] == "update-all":
        ensure_manga_folder()
        mang_update_all()
    elif sys.argv[1] == "webview":
        ensure_manga_folder()
        mg_webview()
    else:
        print "command '%s' not understood, see 'manga.py help' for more info" % sys.argv[1]
