#!/usr/bin/python
##############################################################################
#
# This file is part of cavefilter.
#
# %(name)s is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# %(name)s is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with %(name)s.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import argparse
import configparser
import sys
import re
import subprocess
import os.path
import os
import shutil

from collections import OrderedDict
from itertools import islice


def selectPackages(cache, packages):
    res = list()

    for k, v in packages.items():
        if not v:
            cache[k] = v
        else:
            res.append(k)

    return cache, res


def saveCache(cache):
    with open(os.path.expanduser("~/.cache/cave_output_filter"), "w") as cacheigfile:
        cacheigfile.write("\n".join(["%s = %s" % (k, v) for k, v in cache.items()]) + "\n")


def loadConfig():
    if os.path.isfile(os.path.expanduser("~/.config/cave_output_filter.cfg")):
        path = os.path.expanduser("~/.config/cave_output_filter.cfg")
    else:
        if not os.path.isfile("/etc/cave_output_filter.cfg"):
            print("Error: cannot find config file:", file=sys.stderr)
            print("Error: searched in %r and %r" % (os.path.expanduser("~/.config/cave_output_filter.cfg"), "/etc/cave_output_filter.cfg"), file=sys.stderr)
            sys.exit(-1)
        path = "/etc/cave_output_filter.cfg"

    print("using config file %s:" % path)
    conf = configparser.SafeConfigParser()
    conf.read(path)
    print("Search flags: %s" % conf.get("main", "search_flags"))
    print("Install flags: %s" % conf.get("main", "install_flags"))
    return conf


def applyCache(packages, args):
    """filters packages based on cached package selection from last run.

    The cache is saved under "~/.cache/cave_output_filter"
    """

    cache = dict()
    if args.no_cache:
        return cache

    if not os.path.isdir(os.path.expanduser("~/.cache")):
        os.mkdir(os.path.expanduser("~/.cache"), mode=0o700)

    real_path = os.path.expanduser("~/.cache/cave_output_filter")
    if not os.path.isfile(real_path):
        print("Info: no cache file found in %s" % real_path)
        return cache

    lines = open(real_path).readlines()
    for line in lines:
        try:
            key, value = line.split(" = ")
            if key in packages:
                packages[key] = False
            cache[key] = False
        except ValueError:
            pass

    return cache


def invertSelection(packages):
    for k, v in packages.items():
        packages[k] = not v


def invertSelectionRange(packages, begin, end):
    for k, v in islice(packages.items(), begin, end):
        packages[k] = not v


def invertPrefix(packages, prefix):
    for k, v in packages.items():
        if k.startswith(prefix):
            packages[k] = not v


def getPackages(data):
    packages = OrderedDict()
    for txt in data.split("\n"):
        m1 = re.match("[urdn]   (.*?)/(.*?):(.*?)::(.*?)(?: \(formerly from .*?\))? (.*?) .*", txt)
        if m1:
            packages[m1.group(1) + "/" + m1.group(2) + "-" + m1.group(5) + "::" + m1.group(4)] = True
    return packages


def getUpdates(conf, args):
    query = 'cave resolve -c %s %s' % (args.target, conf.get("main", "search_flags"))
    print("Emitting: %s" % query)
    query_proc = subprocess.Popen(query, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outs, errs = query_proc.communicate()
    packages_text, other = outs.decode("UTF-8").split("Total: ")
    packages_text = packages_text.strip()
    try:
        dust, error_text = other.split("I cannot proceed without being permitted to do the following:")
        error_text = error_text
    except ValueError:
        error_text = ""
    return packages_text, error_text


def userSelection(packages, issues):
    count_map = dict()
    for ix, i in enumerate(packages.keys()):
        count_map[ix] = i

    usage_text = "    Choose one of the following operations:\n" \
        "    int: inverts the specified package with number int\n" \
        "    int-int: inverts the specified package range from int till int\n" \
        "    -1: inverts all packages\n" \
        "    0: start\n" \
        "    q: exit\n" \
        "    sometext: inverts all packages starting with sometext\n"

    while 1:
        ip = input("\n".join(["%s %s: %s%s" % ((i[1] and "[x]" or "").rjust(4), str(ix+1).rjust(5), i[0], i[0] in issues and " (!!!)" or "") for ix, i in enumerate(packages.items())]) + "\n\n" + usage_text)
        try:
            num = int(ip)
            if num == 0:
                break
            elif num == -1:
                invertSelection(packages)
            else:
                try:
                    k = count_map[num-1]
                    packages[k] = not packages[k]
                except IndexError as e:
                    pass
        except ValueError as e:
            if ip == "q":
                sys.exit(0)
            else:
                try:
                    begin, end = ip.split("-", 1)
                    begin = int(begin) - 1
                    end = int(end)
                    invertSelectionRange(packages, begin, end)
                except ValueError:
                    pass
                invertPrefix(packages, ip)


def doUpdate(res, conf):

    cmd_args = "/usr/bin/cave resolve %s %s" % (conf.get("main", "install_flags"), " ".join(["'=%s'" % i for i in res]))
    print("Emitting: %s" % cmd_args)
    try:
        query_proc = subprocess.Popen(cmd_args, shell=True)
        query_proc.communicate()
        sys.exit(0)
    except Exception:
        pass


def checkResume(args):
    if args.ignore_resume:
        try:
            os.remove("cave.resume")
        except OSError:
            pass

    if os.path.isfile("cave.resume"):
        query = 'cave resume -rR -Ca --resume-file cave.resume'
        query_proc = subprocess.Popen(query, shell=True)
        query_proc.communicate()
        sys.exit(0)


def doSync(args):
    if args.sync:
        sync_proc = subprocess.Popen("cave sync", shell=True)
        sync_proc.communicate()



def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', "--sync", action="store_true",
        default=False, help="sync repos")
    parser.add_argument('-n', "--no-cache", action="store_true",
        default=False, help="ignore cave_filter's package selection cache")
    parser.add_argument('-i', "--ignore_resume", action="store_true",
        default=False, help="ignore cave resume file")
    parser.add_argument("-t", '--target',
        default="world", help="target to resolve, default=world")

    args = parser.parse_args(sys.argv[1:])

    checkResume(args) #perhaps we're done here
    doSync(args)

    conf = loadConfig()
    outs, errs = getUpdates(conf, args)
    packages = getPackages(outs)
    issues = getPackages(errs)

    cache = applyCache(packages, args)

    userSelection(packages, issues)

    cache, res = selectPackages(cache, packages)
    saveCache(cache)
    doUpdate(res, conf)



if __name__ == '__main__':
    main()
