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
import string

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


class ConfigCmdParser:
   """  
   Helper class for calling a given *-config command and extracting
   various paths and other information from it.
   """
   
   def __init__(self, config_cmd):
      " config_cmd: The config command to call "
      self.config_cmd = config_cmd
      self.valid = True
      if not os.path.isfile(config_cmd):
         self.valid = False

      # Initialize regular expressions
      # Res that when matched against config output should match the options we want
      # In future could try to use INCPREFIX and other platform neutral stuff
      self.inc_re = re.compile(r'-I(\S*)', re.MULTILINE);
      self.lib_re = re.compile(r'-l(\S*)', re.MULTILINE);
      self.lib_path_re = re.compile(r'-L(\S*)', re.MULTILINE);
      
   def findLibs(self, arg="--libs"):
      if not self.valid:
         return ""
      return self.lib_re.findall(os.popen(self.config_cmd + " " + arg).read().strip())
   
   def findLibPaths(self, arg="--libs"):
      if not self.valid:
         return ""
      return self.lib_path_re.findall(os.popen(self.config_cmd + " " + arg).read().strip())

   def findIncludes(self, arg="--cflags"):
      if not self.valid:
         return ""
      return self.inc_re.findall(os.popen(self.config_cmd + " " + arg).read().strip())

   def getVersion(self, arg="--version"):
      if not self.valid:
         return ""
      return os.popen(self.config_cmd + " " + arg).read().strip()
   
def GetPlatform():
   "Get a platform string"
   if string.find(sys.platform, 'irix') != -1:
      return 'irix'
   elif string.find(sys.platform, 'linux') != -1:
      return 'linux'
   elif string.find(sys.platform, 'freebsd') != -1:
      return 'linux'
   elif string.find(sys.platform, 'cygwin') != -1:
      return 'win32'
   elif string.find(sys.platform, 'sun') != -1:
      return 'sun'
   else:
      return sys.platform   
   
