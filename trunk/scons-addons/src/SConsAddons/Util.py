"""
General Util methods and classes for SConsAddons.

This should NOT be a final resting point for code, but more a place
to put things while refactoring and deciding where they should end
up long term.
"""

#
# __COPYRIGHT__
#
# This file is part of scons-addons.
#
# Scons-addons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Scons-addons is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with scons-addons; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

import os
import sys
import re

pj = os.path.join


def fileExtensionMatches(f, fexts):
   """ Returns true if f has an extension in the list fexts """
   for ext in fexts:
      if f.endswith(ext):
         return True
   return False
      
def getPredFilesRecursive(tree_root, predicateMethod):
   """ Return list of sources recursively.  Returned paths are related to the tree_root """
   def dir_method(f_list, dirpath, namelist):
      for f in namelist:
         if predicateMethod(f):
            f_list.append(os.path.normpath(pj(dirpath, f)))
   cur_dir = os.getcwd()
   os.chdir(tree_root)
   f_list = [];
   os.path.walk('.', dir_method, f_list);
   os.chdir(cur_dir)
   return f_list

def getFilesRecursiveByExt(tree_root, fexts):
   def hasExtension(f):
      return fileExtensionMatches(f, fexts)
   return getPredFilesRecursive(tree_root, hasExtension)

def getSourcesRecursive(tree_root):
   """ Return list of sources recursively """
   return getFilesRecursiveByExt(tree_root, ['.cpp','.C'])

def getHeadersRecursive(tree_root):
   """ Return list of headers recursively """
   return getFilesRecursiveByExt(tree_root, ['.h','.hpp'])
