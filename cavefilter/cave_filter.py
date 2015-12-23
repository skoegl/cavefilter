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
import os
import os.path
import pickle
import re
import subprocess
import sys
from collections import OrderedDict
from itertools import islice


class CaveFilter(object):
	def __init__(self, args):
		super(CaveFilter, self).__init__()
		self.args = args
		self.cache_dir = os.path.expanduser("~/.cache")
		self.config_dir = os.path.expanduser("~/.config")
		self.config_path = os.path.join(self.config_dir, "cavefilter.conf")
		self.cache_path = os.path.join(self.cache_dir, "cavefilter.cache")
		self.selection_path = os.path.join(self.cache_dir,
		                                   "cavefilter.selection")
		self.cache = dict()
		self.config = None
		self.packages = OrderedDict()
		self.result = list()
		self.issues = OrderedDict()
		self.type_db = dict()

		self.check_dirs()
		self.load_cache()
		self.apply_cache()

	def start(self):
		self.loadConfig()

		if not self.args.retry:
			self.doFreshRun()
		else:
			self.loadSelection()

		self.userSelection()

		self.selectPackages()
		self.saveSelection()
		self.saveCacheNew()
		self.doUpdate()

	def check_dirs(self):

		if not os.path.isdir(self.cache_dir):
			os.mkdir(self.cache_dir, mode=0o700)

		if not os.path.isdir(self.config_dir):
			os.mkdir(self.config_dir, mode=0o700)

	def load_cache(self):
		with open(self.cache_path, "rb") as cache_file:
			self.cache = pickle.load(cache_file)

	def apply_cache(self):
		"""filters packages based on cached package selection from last run.

		The cache is saved under "~/.cache/cave_output_filter"
		"""

		for key, value in self.cache.items():
			if key in self.packages:
				self.packages[key] = False

	def saveCacheNew(self):
		with open(self.cache_path, "wb") as cache_file:
			pickle.dump(self.cache, cache_file, pickle.HIGHEST_PROTOCOL)

	def saveSelection(self):
		tmp = [self.packages, self.issues, self.result, self.type_db]
		with open(self.selection_path, "wb") as selection_file:
			pickle.dump(tmp, selection_file)

	def loadSelection(self):
		try:
			with open(self.selection_path, "rb") as selection_file:
				data = pickle.load(selection_file)
				self.packages, self.issues, self.result, self.type_db = data
		except ValueError:
			pass

	def loadConfig(self):
		self.config = configparser.ConfigParser()
		self.config.read(self.config_path)

	def selectPackages(self):
		self.result.clear()
		for k, v in self.packages.items():
			if not v:
				self.cache[k] = False
			else:
				self.result.append(k)

	def doFreshRun(self):
		self.checkResume()  # perhaps we're done here
		self.doSync()

		outs, errs = self.getUpdates()
		self.getPackages(outs, self.packages)
		self.getPackages(errs, self.issues)

	def getUpdates(self):
		query = 'cave resolve %s %s' % (
			self.args.target, self.config.get("main", "search_flags"))
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

	def invertSelection(self):
		for k, v in self.packages.items():
			self.packages[k] = not v

	def toggle_packages(self):
		for k, v in self.packages.items():
			self.packages[k] = False

	def toggle_updates(self):
		for k, v in self.type_db.items():
			if v == "u":
				self.packages[k] = not self.packages[k]

	def toggle_downgrades(self):
		for k, v in self.type_db.items():
			if v == "d":
				self.packages[k] = not self.packages[k]

	def toggle_rebuilds(self):
		for k, v in self.type_db.items():
			if v == "r":
				self.packages[k] = not self.packages[k]

	def toggle_new(self):
		for k, v in self.type_db.items():
			if v == "n":
				self.packages[k] = not self.packages[k]

	def invertSelectionRange(self, begin, end):
		for k, v in islice(self.packages.items(), begin, end):
			self.packages[k] = not v

	def invertPrefix(self, prefix):
		for k, v in self.packages.items():
			if k.startswith(prefix):
				self.packages[k] = not v

	def match_packages(self, regex, type_id, line, packages):
		matched = regex.match(line)
		if matched:
			package = matched.group(1) + "/" + matched.group(2) + "-" + \
			          matched.group(5) + "::" + matched.group(4)
			packages[package] = True
			self.type_db[package] = type_id

	def getPackages(self, data, packages):

		update_regex = re.compile("u   (.*?)/(.*?):(.*?)::(.*?)(?: \("
		                          "formerly from .*?\))? (.*?) .*")
		rebuild_regex = re.compile("r   (.*?)/(.*?):(.*?)::(.*?)(?: \("
		                           "formerly from .*?\))? (.*?) .*")
		downgrade_regex = re.compile("d   (.*?)/(.*?):(.*?)::(.*?)(?: \("
		                             "formerly from .*?\))? (.*?) .*")
		new_regex = re.compile("n   (.*?)/(.*?):(.*?)::(.*?)(?: \("
		                       "formerly from .*?\))? (.*?) .*")
		lines = data.split("\n")
		for line in lines:
			self.match_packages(update_regex, "u", line, packages)
			self.match_packages(rebuild_regex, "r", line, packages)
			self.match_packages(downgrade_regex, "d", line, packages)
			self.match_packages(new_regex, "n", line, packages)

	def create_item(self, selected, index, package, issue, type_id):
		return "%s %s: %s%s [%s]" % (selected, index, package, issue, type_id)

	def create_menu(self):
		out = list()
		for ix, i in enumerate(self.packages.items()):
			out.append(self.create_item(
					(i[1] and "[x]" or "").rjust(4),
					str(ix + 1).rjust(5),
					i[0], i[0] in
					      self.issues and " (!!!)" or "",
					self.type_db[i[0]]))
		return "\n".join(out)

	def userSelection(self):
		count_map = dict()
		for ix, i in enumerate(self.packages.keys()):
			count_map[ix] = i

		usage_text = "    Choose one of the following operations:\n" \
		             "    int: inverts the specified package with number int\n" \
		             "    int-int: inverts the specified package range from int till int\n" \
		             "    -1: inverts all packages\n" \
		             "    0: start\n" \
		             "    q: exit\n" \
		             "    sometext: inverts all packages starting with sometext\n"

		while 1:
			ip = input("%s\n\n%s" % (self.create_menu(), usage_text))
			try:
				num = int(ip)
				if num == 0:
					break
				elif num == -1:
					self.invertSelection()
				else:
					try:
						k = count_map[num - 1]
					except KeyError:
						continue
					try:
						self.packages[k] = not self.packages[k]
					except IndexError as e:
						continue
			except ValueError as e:
				if ip == "q":
					sys.exit(0)
				elif ip == "t":
					self.toggle_packages()
				elif ip == "u":
					self.toggle_updates()
				elif ip == "r":
					self.toggle_rebuilds()
				elif ip == "d":
					self.toggle_downgrades()
				elif ip == "n":
					self.toggle_new()
				else:
					try:
						begin, end = ip.split("-", 1)
						begin = int(begin) - 1
						end = int(end)
						self.invertSelectionRange(begin, end)
					except ValueError:
						pass
						self.invertPrefix(ip)

	def doUpdate(self):

		cmd_args = "/usr/bin/cave resolve %s %s" % (self.config.get("main",
		                                                            "install_flags"),
		                                            " ".join(["'=%s'" % i for i in self.result]))
		print("Emitting: %s" % cmd_args)
		try:
			query_proc = subprocess.Popen(cmd_args, shell=True)
			query_proc.communicate()
			sys.exit(0)
		except Exception:
			pass

	def checkResume(self):
		if self.args.ignore_resume:
			try:
				os.remove("cave.resume")
			except OSError:
				pass

		if os.path.isfile("cave.resume"):
			query = 'cave resume -rR -Ca --resume-file cave.resume'
			query_proc = subprocess.Popen(query, shell=True)
			query_proc.communicate()
			sys.exit(0)

	def doSync(self):
		if self.args.sync:
			sync_proc = subprocess.Popen("cave sync", shell=True)
			sync_proc.communicate()


def main():
	parser = argparse.ArgumentParser()

	parser.add_argument('-s', "--sync", action="store_true",
	                    default=False, help="sync repos")
	parser.add_argument('-n', "--no-cache", action="store_true",
	                    default=False, help="ignore cave_filter's package selection cache")
	parser.add_argument('-r', "--retry", action="store_true",
	                    default=False, help="retry selection")
	parser.add_argument('-i', "--ignore_resume", action="store_true",
	                    default=False, help="ignore cave resume file")
	parser.add_argument("-t", '--target',
	                    default="world", help="target to resolve, default=world")

	args = parser.parse_args(sys.argv[1:])

	cavefilter = CaveFilter(args)
	cavefilter.start()


if __name__ == '__main__':
	main()
